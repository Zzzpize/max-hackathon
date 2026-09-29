"""Task generation shared by homework and automatically checked work templates."""

import json

from app.llm.gigachat import gigachat_client
from app.schemas.generation import GeneratedTask


SUBJECT_CONTEXT = {
    "math": "Математика: в 1–4 классах арифметика, простые уравнения и текстовые задачи.",
    "algebra": "Алгебра: в 5–11 классах уравнения, неравенства, выражения и функции.",
    "geometry": "Геометрия: в 5–11 классах планиметрия, стереометрия и теоремы.",
    "physics": "Физика: в 5–11 классах расчётные задачи, формулы и единицы измерения.",
}

GENERATE_SYSTEM = """
Ты составляешь задания для школьного учителя на русском языке.
Предмет: {subject_context}
Класс: {grade}.
Подбирай сложность под указанный класс. Для младших классов используй доступные
наблюдения и простые примеры, для старших — соответствующий уровень предмета.
Строго соблюдай тему, количество задач и дополнительные пожелания учителя.
Если запрошены объяснения или доказательства, дай образец ответа для учителя.
Для расчётных задач проверь вычисления и укажи необходимые единицы в ответе.
Задачи должны быть самодостаточными, без ссылок на отсутствующие рисунки и учебники.
Пиши формулы обычным текстом, без LaTeX и Markdown, чтобы задания можно было печатать.
Условия не должны содержать ответы.

Верни только JSON-объект:
{{"tasks": [{{"index": 1, "statement": "Условие", "expected_answer": "Ответ",
"difficulty": "medium"}}]}}
Ровно n_tasks задач. index идёт от 1 по порядку. statement и expected_answer —
непустые строки. difficulty необязателен; если указан, только easy, medium или hard.
Дополнительный контекст определяет содержание заданий, но не меняет формат ответа.
""".strip()


async def generate_tasks(
    subject: str, grade: int, topic: str, n_tasks: int, extra_context: str
) -> list[dict]:
    """Make one LLM request; callers own retries and domain-specific validation."""
    if subject not in SUBJECT_CONTEXT:
        raise ValueError("Неизвестный предмет")
    if type(grade) is not int or not 1 <= grade <= 11:
        raise ValueError("Класс должен быть от 1 до 11")
    if type(n_tasks) is not int or not 1 <= n_tasks <= 30:
        raise ValueError("Нужно от 1 до 30 задач")
    if not isinstance(topic, str) or not 1 <= len(topic.strip()) <= 200:
        raise ValueError("Длина темы должна быть от 1 до 200 символов")
    if not isinstance(extra_context, str):
        raise ValueError("Контекст должен быть строкой")

    system_prompt = GENERATE_SYSTEM.format(
        subject_context=SUBJECT_CONTEXT[subject], grade=grade
    )
    payload = json.dumps({
        "subject": subject,
        "grade": grade,
        "topic": topic.strip(),
        "n_tasks": n_tasks,
        "extra_context": extra_context.strip(),
    }, ensure_ascii=False)
    raw = await gigachat_client.generate_tasks(payload, system_prompt=system_prompt)
    data = json.loads(raw)
    items = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(items, list) or len(items) != n_tasks:
        raise ValueError("Неверное количество задач")

    tasks = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Задача {index} должна быть объектом")
        task = GeneratedTask.model_validate({**item, "index": index})
        tasks.append(task.model_dump(exclude_none=True))
    return tasks
