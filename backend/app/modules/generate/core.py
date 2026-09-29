import json
import logging

from fastapi import HTTPException

from app.llm.gigachat import gigachat_client

logger = logging.getLogger(__name__)

SUBJECT_CONTEXT = {
    "math": "арифметика и простые уравнения",
    "algebra": "уравнения, неравенства и функции",
    "geometry": "планиметрия, стереометрия и теоремы",
    "physics": "расчётные задачи, формулы и единицы измерения",
}


def validate_tasks(items: object, n_tasks: int) -> list[dict]:
    if not isinstance(items, list) or len(items) != n_tasks:
        raise ValueError("Неверное количество задач")
    tasks = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError("Задача должна быть объектом")
        statement, answer = item.get("statement"), item.get("expected_answer")
        difficulty = item.get("difficulty")
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError("Пустое условие")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Пустой ответ")
        if difficulty is not None and difficulty not in ("easy", "medium", "hard"):
            raise ValueError("Неверная сложность")
        task = {"index": index, "statement": statement.strip(), "expected_answer": answer.strip()}
        if difficulty is not None:
            task["difficulty"] = difficulty
        tasks.append(task)
    return tasks


async def generate_tasks(
    subject: str, grade: int, topic: str, n_tasks: int, extra_context: str
) -> list[dict]:
    if subject not in SUBJECT_CONTEXT or not 1 <= grade <= 11 or not 1 <= n_tasks <= 30:
        raise ValueError("Некорректные параметры генерации")
    subject_context = SUBJECT_CONTEXT[subject]
    if grade <= 4:
        level_context = "начальная школа: только понятия и вычисления, доступные этому классу"
    else:
        level_context = "основная или старшая школа: сложность соответствует классу"
        if subject == "math":
            subject_context = "уравнения, функции, геометрия и прикладные задачи"
    system_prompt = (
        f"Ты составляешь домашние задания для {grade} класса по предмету {subject}. "
        f"Тематика предмета: {subject_context}. Уровень: {level_context}. "
        "Верни только JSON-объект вида "
        '{"tasks":[{"statement":"...","expected_answer":"...","difficulty":"easy"}]}. '
        "Ответ может быть развернутым, но должен быть конкретным."
    )
    prompt = json.dumps({
        "subject": subject, "grade": grade, "topic": topic,
        "n_tasks": n_tasks, "extra_context": extra_context,
    }, ensure_ascii=False)
    for attempt in range(2):
        try:
            raw = await gigachat_client.generate_tasks(prompt, system_prompt=system_prompt)
            return validate_tasks(json.loads(raw)["tasks"], n_tasks)
        except Exception:
            logger.warning("Не удалось сгенерировать задачи, попытка %s", attempt + 1, exc_info=True)
    raise HTTPException(status_code=502, detail="Не удалось сгенерировать задачи")
