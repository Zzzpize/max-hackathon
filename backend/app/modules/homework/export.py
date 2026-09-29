from datetime import date

from app.models import Homework
from app.modules.roadmap.export import SUBJECT_RU


def render_txt(hw: Homework) -> bytes:
    lines = [
        "Домашнее задание",
        f"Предмет: {SUBJECT_RU[hw.subject]}, класс: {hw.grade}",
        f"Тема: {hw.topic}",
        f"Дата: {date.today():%d.%m.%Y}",
        "",
    ]
    for task in hw.tasks:
        lines.extend((f"{task['index']}. {task['statement']}", ""))
    lines.extend(("---", "Ответы (для учителя)"))
    lines.extend(f"{task['index']}. {task['expected_answer']}" for task in hw.tasks)
    return "\n".join(lines).encode("utf-8")
