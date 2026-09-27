import asyncio
import json
import logging
from pathlib import Path

import httpx
from gigachat import GigaChat

from app.config import settings

logger = logging.getLogger(__name__)


class GigaChatClient:
    def __init__(self) -> None:
        self._credentials = settings.gigachat_credentials
        self._scope = settings.gigachat_scope
        self._model = settings.gigachat_model
        self._verify_ssl = settings.gigachat_verify_ssl_certs

    def _client(self) -> GigaChat:
        return GigaChat(
            credentials=self._credentials,
            scope=self._scope,
            model=self._model,
            verify_ssl_certs=self._verify_ssl,
        )

    async def recognize_answers(
        self,
        photos: list[Path],
        system_prompt: str,
    ) -> list[dict]:
        if not self._credentials:
            logger.warning("GigaChat credentials not set")
            return []

        for attempt in range(2):
            try:
                async with self._client() as client:
                    attachments = []
                    for photo in photos:
                        with photo.open("rb") as file:
                            uploaded = await client.aupload_file(
                                (photo.name, file), purpose="general"
                            )
                        attachments.append(uploaded.id)

                    response = await client.achat({
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": "Распознай ответы на приложенных фото.",
                                "attachments": attachments,
                            },
                        ],
                    })

                data = json.loads(response.choices[0].message.content)
                return [
                    {
                        "task_index": int(item["task_index"]),
                        "answer": str(item["answer"]),
                        "confidence": float(item["confidence"]),
                    }
                    for item in data["answers"]
                ]
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError):
                logger.warning("Invalid GigaChat vision response, attempt %s", attempt + 1)
            except httpx.TransportError:
                logger.warning("GigaChat vision request failed, attempt %s", attempt + 1)
                if attempt == 0:
                    await asyncio.sleep(1)

        return []

    async def check_task(
        self,
        system_prompt: str,
        statement: str,
        expected_answer: str,
        student_answer: str,
    ) -> dict:
        fallback = {
            "correct": student_answer.strip() == expected_answer.strip(),
            "explanation": "",
            "reasoning_graph": [],
        }
        if not self._credentials:
            logger.warning("GigaChat credentials not set")
            return fallback

        payload = json.dumps(
            {
                "statement": statement,
                "expected_answer": expected_answer,
                "student_answer": student_answer,
            },
            ensure_ascii=False,
        )

        for attempt in range(2):
            try:
                async with self._client() as client:
                    response = await client.achat({
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": payload},
                        ],
                    })

                data = json.loads(response.choices[0].message.content)
                if not isinstance(data["correct"], bool):
                    raise ValueError("correct must be boolean")
                if not isinstance(data["explanation"], str):
                    raise ValueError("explanation must be string")
                if not isinstance(data["reasoning_graph"], list):
                    raise ValueError("reasoning_graph must be list")
                return {
                    "correct": data["correct"],
                    "explanation": data["explanation"],
                    "reasoning_graph": data["reasoning_graph"],
                }
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError):
                logger.warning("Invalid GigaChat check response, attempt %s", attempt + 1)
            except httpx.TransportError:
                logger.warning("GigaChat check request failed, attempt %s", attempt + 1)
                if attempt == 0:
                    await asyncio.sleep(1)

        return fallback


gigachat_client = GigaChatClient()