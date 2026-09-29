from datetime import date

from app.models import Homework
from app.modules.generate import core


async def generate_homework(
    teacher_id: str, subject: str, grade: int, topic: str,
    n_tasks: int, prompt: str, title: str | None = None,
) -> Homework:
    tasks = await core.generate_tasks(subject, grade, topic, n_tasks, prompt)
    return Homework(
        teacher_id=teacher_id,
        title=title or f"{topic}, {date.today():%d.%m.%Y}",
        subject=subject,
        grade=grade,
        topic=topic,
        prompt=prompt,
        tasks=tasks,
    )
