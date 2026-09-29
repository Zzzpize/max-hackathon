import asyncio
import json
import logging
import re

import httpx
from fastapi import HTTPException

from app.llm.gigachat import gigachat_client
from app.models.roadmap import Roadmap
from app.modules.roadmap.prompts import GENERATE_SYSTEM, SUBJECT_CONTEXT

logger = logging.getLogger(__name__)
WEEKS = re.compile(r"([1-9]\d?)(?:-([1-9]\d?))?\Z")


def validate_content(data: object) -> dict:
    """Проверить ответ модели и вернуть content для Roadmap."""
    if not isinstance(data, dict):
        raise ValueError("Ответ должен быть объектом")

    segments = data.get("segments")
    if not isinstance(segments, list) or not 1 <= len(segments) <= 40:
        raise ValueError("Нужно от 1 до 40 сегментов")

    used_weeks: set[int] = set()
    result = []

    for expected_index, item in enumerate(segments, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Сегмент {expected_index} должен быть объектом")
        if type(item.get("index")) is not int or item["index"] != expected_index:
            raise ValueError(f"Неверный index сегмента {expected_index}")

        weeks = item.get("weeks")
        match = WEEKS.fullmatch(weeks) if isinstance(weeks, str) else None
        if match is None:
            raise ValueError(f"Неверный weeks сегмента {expected_index}")

        first = int(match.group(1))
        last = int(match.group(2) or first)
        if first > last or last > 40:
            raise ValueError(f"Недели сегмента {expected_index} вне диапазона 1–40")

        current_weeks = set(range(first, last + 1))
        if used_weeks & current_weeks:
            raise ValueError(f"Недели сегмента {expected_index} пересекаются с другими")
        used_weeks.update(current_weeks)

        topic = item.get("topic")
        if not isinstance(topic, str) or not 1 <= len(topic.strip()) <= 120:
            raise ValueError(f"Неверная тема сегмента {expected_index}")

        objectives = item.get("objectives")
        materials_hint = item.get("materials_hint")
        if not isinstance(objectives, str) or not objectives.strip():
            raise ValueError(f"Нет цели сегмента {expected_index}")
        if not isinstance(materials_hint, str):
            raise ValueError(f"Нет поля materials_hint в сегменте {expected_index}")

        hours = item.get("hours")
        if type(hours) is not int or hours < 0:
            raise ValueError(f"Неверные часы сегмента {expected_index}")

        result.append({
            "index": expected_index,
            "weeks": weeks,
            "topic": topic.strip(),
            "objectives": objectives.strip(),
            "hours": hours,
            "materials_hint": materials_hint.strip(),
        })

    return {"segments": result}


async def generate_roadmap(
    teacher_id: str, subject: str, grade: int, prompt: str
) -> Roadmap:
    if not teacher_id.strip():
        raise ValueError("Не указан учитель")
    if subject not in SUBJECT_CONTEXT:
        raise ValueError("Неизвестный предмет")
    if not 1 <= grade <= 11:
        raise ValueError("Класс должен быть от 1 до 11")
    if not 10 <= len(prompt.strip()) <= 2000:
        raise ValueError("Длина запроса должна быть от 10 до 2000 символов")

    system_prompt = GENERATE_SYSTEM.format(
        subject_context=SUBJECT_CONTEXT[subject]
    )
    payload = {
        "subject": subject,
        "grade": grade,
        "teacher_prompt": prompt.strip(),
    }

    for attempt in range(2):
        try:
            raw = await gigachat_client.chat_completion(
                system_prompt,
                json.dumps(payload, ensure_ascii=False),
            )
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Ответ должен быть объектом")

            title = data.get("title")
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
                raise ValueError("Неверное название плана")

            content = validate_content(data)
            return Roadmap(
                teacher_id=teacher_id,
                title=title.strip(),
                subject=subject,
                grade=grade,
                prompt=prompt.strip(),
                content=content,
            )
        except (httpx.TransportError, TimeoutError, ConnectionError):
            logger.warning("Ошибка соединения с GigaChat", exc_info=True)
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            raise HTTPException(status_code=502, detail="Не удалось связаться с моделью")
        except (ValueError, TypeError) as exc:
            logger.warning("Невалидный план от GigaChat: %s", exc)
            payload["previous_error"] = str(exc)

    raise HTTPException(
        status_code=502,
        detail="модель вернула невалидный план, попробуйте другую формулировку",
    )
