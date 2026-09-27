import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class GigaChatClient:
    """Обёртка над GigaChat SDK.

    MVP: два метода. Распознать ответы по фото (VLM) и проверить
    одно задание (LLM с эталоном)
    """

    def __init__(self) -> None:
        self._auth_key = settings.gigachat_auth_key
        self._scope = settings.gigachat_scope
        self._model = settings.gigachat_model
        self._verify_ssl = settings.gigachat_verify_ssl_certs

    async def recognize_answers(
        self,
        photos: list[Path],
        system_prompt: str,
    ) -> list[dict]:
        """Vision-запрос: извлечь ответы ученика с фото работы."""
        if not self._auth_key:
            logger.warning("GIGACHAT_AUTH_KEY not set — returning stub answers")
            return []

        # TODO(backend, LLM): загрузка изображений в GigaChat через SDK,
        # вызов чата с system_prompt + attachments, парсинг JSON-ответа.
        raise NotImplementedError("GigaChat vision call not implemented yet")

    async def check_task(
        self,
        system_prompt: str,
        statement: str,
        expected_answer: str,
        student_answer: str,
    ) -> dict:
        """Проверка одного задания через LLM с эталоном."""
        if not self._auth_key:
            logger.warning("GIGACHAT_AUTH_KEY not set — returning stub verdict")
            return {
                "correct": student_answer.strip() == expected_answer.strip(),
                "explanation": "",
                "reasoning_graph": [],
            }

        user_payload = json.dumps(
            {
                "statement": statement,
                "expected_answer": expected_answer,
                "student_answer": student_answer,
            },
            ensure_ascii=False,
        )
        # TODO(backend, LLM): вызвать GigaChat chat.completions,
        # system=system_prompt, user=user_payload, распарсить JSON.
        raise NotImplementedError("GigaChat chat call not implemented yet")


gigachat_client = GigaChatClient()
