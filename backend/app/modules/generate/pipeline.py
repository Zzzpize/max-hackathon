import json
import logging
import re

from app.llm.gigachat import gigachat_client
from app.models import WorkTemplate
from app.modules.generate import core
from app.schemas.work import TaskDefinition

logger = logging.getLogger(__name__)

LIMITS = {2: 100, 3: 1000, 4: 10000}
NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")
SHORT_ANSWER = re.compile(
    r"-?\d+(?:[.,]\d+)?(?:\s*(?:мм|см|дм|км|м|кг|г|мл|л|ч|мин|с|руб|шт|%))?",
    re.I,
)


def _validate_tasks(raw: str, grade: int, n_tasks: int) -> list[dict]:
    items = json.loads(raw)["tasks"]
    if not isinstance(items, list) or len(items) != n_tasks:
        raise ValueError("Неверное количество задач")

    tasks = []
    for index, item in enumerate(items, start=1):
        task = TaskDefinition.model_validate({
            **item,
            "index": index,
            "max_points": 1.0,
        })
        statement = task.statement.strip()
        answer = task.expected_answer.strip()

        if not statement:
            raise ValueError("Пустое условие")
        if re.search(r"\d[ \u00a0]\d{3}\b", statement):
            raise ValueError("Число с разделителем тысяч")
        if any(
            abs(float(number.replace(",", "."))) > LIMITS[grade]
            for number in NUMBER.findall(statement)
        ):
            raise ValueError("Число не соответствует классу")
        if len(answer) > 32 or not SHORT_ANSWER.fullmatch(answer):
            raise ValueError("Эталон должен быть одним коротким ответом")

        tasks.append(
            task.model_copy(
                update={"statement": statement, "expected_answer": answer}
            ).model_dump()
        )
    return tasks


def _fallback(topic: str, n_tasks: int) -> tuple[str, list[dict]]:
    name = topic.casefold()
    if "вычит" in name:
        operation = "subtract"
    elif "умнож" in name:
        operation = "multiply"
    elif "делен" in name or "делени" in name:
        operation = "divide"
    elif "слож" in name:
        operation = "add"
    else:
        operation = "add"
        topic = "Арифметика"

    tasks = []
    for index in range(1, n_tasks + 1):
        a = 2 + (index - 1) % 8
        b = 2 + (index - 1) // 8

        if operation == "subtract":
            statement, answer = f"Вычисли: {a + b} − {b}.", a
        elif operation == "multiply":
            statement, answer = f"Вычисли: {a} × {b}.", a * b
        elif operation == "divide":
            statement, answer = f"Вычисли: {a * b} : {b}.", a
        else:
            statement, answer = f"Вычисли: {a} + {b}.", a + b

        tasks.append({
            "index": index,
            "statement": statement,
            "expected_answer": str(answer),
            "max_points": 1.0,
        })
    return topic, tasks


async def generate_work(topic: str, grade: int, n_tasks: int) -> WorkTemplate:
    topic = topic.strip()
    if not topic or grade not in LIMITS or not 1 <= n_tasks <= 20:
        raise ValueError("Некорректные параметры генерации")

    prompt = json.dumps({
        "topic": topic,
        "grade": grade,
        "n_tasks": n_tasks,
        "max_number": LIMITS[grade],
        "instruction": (
            "Сгенерируй указанное число задач по теме для этого класса. "
            "Числа в условиях не должны превышать max_number. "
            "Для каждой задачи верни условие и один короткий эталонный ответ."
        ),
    }, ensure_ascii=False)

    if gigachat_client._credentials:
        for attempt in range(2):
            try:
                generated = await core.generate_tasks("math", grade, topic, n_tasks, prompt)
                tasks = _validate_tasks(json.dumps({"tasks": generated}), grade, n_tasks)
                return WorkTemplate(
                    title=f"Контрольная: {topic}",
                    subject="math",
                    grade=grade,
                    tasks=tasks,
                )
            except Exception:
                logger.warning(
                    "Не удалось сгенерировать корректные задачи, попытка %s",
                    attempt + 1,
                    exc_info=True,
                )

    fallback_topic, tasks = _fallback(topic, n_tasks)
    return WorkTemplate(
        title=f"Контрольная: {fallback_topic}",
        subject="math",
        grade=grade,
        tasks=tasks,
    )
