import asyncio
from datetime import date
import logging

import httpx
from fastapi import HTTPException
from gigachat.exceptions import GigaChatException

from app.models.homework import Homework
from app.modules.generate import core
from app.schemas.homework import HomeworkCreate, HomeworkRegenerate


logger = logging.getLogger(__name__)


async def _generate_tasks(
    subject: str, grade: int, topic: str, n_tasks: int, context: str
) -> list[dict]:
    for attempt in range(2):
        try:
            return await core.generate_tasks(subject, grade, topic, n_tasks, context)
        except (httpx.HTTPError, GigaChatException, TimeoutError, ConnectionError, RuntimeError):
            logger.warning("Ошибка запроса к GigaChat, попытка %s", attempt + 1, exc_info=True)
            if attempt == 0:
                await asyncio.sleep(1)
        except (ValueError, TypeError) as exc:
            logger.warning("Невалидные задачи от GigaChat, попытка %s: %s", attempt + 1, exc)
            context += f"\nИсправь ошибку предыдущего ответа: {exc}"

    raise HTTPException(
        status_code=502,
        detail="Не удалось сгенерировать домашнее задание, попробуйте ещё раз",
    )


async def generate_homework(
    teacher_id: str, subject: str, grade: int, topic: str, n_tasks: int, prompt: str
) -> Homework:
    if not teacher_id.strip():
        raise ValueError("Не указан учитель")
    payload = HomeworkCreate(
        subject=subject, grade=grade, topic=topic, n_tasks=n_tasks, prompt=prompt
    )
    tasks = await _generate_tasks(
        payload.subject, payload.grade, payload.topic, payload.n_tasks, payload.prompt
    )
    suffix = f", {date.today():%d.%m.%Y}"
    return Homework(
        teacher_id=teacher_id,
        title=payload.topic[:200 - len(suffix)] + suffix,
        subject=payload.subject,
        grade=payload.grade,
        topic=payload.topic,
        prompt=payload.prompt,
        tasks=tasks,
    )


async def regenerate_homework(hw: Homework, extra_prompt: str | None = None) -> list[dict]:
    extra = HomeworkRegenerate(extra_prompt=extra_prompt).extra_prompt
    context = hw.prompt + "\nСоставь новый вариант задач по той же теме."
    if extra:
        context += f"\nДополнительные пожелания учителя: {extra}"
    return await _generate_tasks(hw.subject, hw.grade, hw.topic, len(hw.tasks), context)
