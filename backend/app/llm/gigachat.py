import asyncio
import json
import logging
import time
import hashlib
from pathlib import Path

import httpx

from gigachat import GigaChat
from gigachat.exceptions import ResponseError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)
ERROR_TYPES = {"вычислительная", "методологическая", "невнимательность", "не распознано"}


def _parse_json_object(content: str) -> dict:
    """Модель иногда оборачивает JSON в ```json …``` или добавляет текст вокруг."""
    text = (content or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in response")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON root is not an object")
    return data


class GigaChatClient:
    def __init__(self) -> None:
        self._credentials = settings.gigachat_credentials
        self._scope = settings.gigachat_scope
        self._model = settings.gigachat_model
        self._verify_ssl = settings.gigachat_verify_ssl_certs
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._token_lock = asyncio.Lock()

        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def _client(self, timeout: float | None = None) -> GigaChat:
        async with self._token_lock:
            if self._access_token is None or time.time() >= self._expires_at - 60:
                async with GigaChat(
                    credentials=self._credentials,
                    scope=self._scope,
                    verify_ssl_certs=self._verify_ssl,
                ) as auth_client:
                    await auth_client._aupdate_token()
                    token = auth_client._access_token
                    if token is None:
                        raise RuntimeError("GigaChat не вернул access token")
                    self._access_token = token.access_token
                    self._expires_at = token.expires_at / 1000

            extra = {"timeout": timeout} if timeout is not None else {}
            return GigaChat(
                access_token=self._access_token,
                model=self._model,
                verify_ssl_certs=self._verify_ssl,
                **extra,
            )

    async def transcribe_photos(
        self,
        photos: list[Path],
        system_prompt: str,
        user_content: str,
        temperature: float = 0.1,
    ) -> str:
        """Vision-вызов, возвращает сырой текст модели (построчная расшифровка).
        Полная расшифровка страницы у Ultra идёт дольше дефолтных 30 с SDK.

        Сетевые сбои и 5xx/429 от GigaChat после повтора пробрасываются:
        очередь проверок перезапустит работу с бэкоффом. Глушить их нельзя —
        пустая расшифровка превратила бы временный сбой в «всё на ручную
        проверку» и закрыла бы работу."""
        if not self._credentials:
            logger.warning("GigaChat credentials not set")
            return ""

        for attempt in range(2):
            try:
                async with await self._client(timeout=180) as client:
                    attachments = []
                    for photo in photos:
                        with photo.open("rb") as file:
                            uploaded = await client.aupload_file(
                                (photo.name, file), purpose="general"
                            )
                        attachments.append(uploaded.id_)

                    response = await client.achat({
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": user_content,
                                "attachments": attachments,
                            },
                        ],
                        "temperature": temperature,
                        "top_p": 0.1,
                        "repetition_penalty": 1.05,
                        "max_tokens": 2500,
                    })
                return str(response.choices[0].message.content or "")
            except (httpx.TransportError, httpx.TimeoutException, ResponseError):
                logger.warning("GigaChat transcribe request failed, attempt %s", attempt + 1)
                if attempt == 1:
                    raise
                await asyncio.sleep(3)
            except (AttributeError, IndexError, TypeError):
                logger.warning("Invalid GigaChat transcribe response, attempt %s", attempt + 1)

        return ""

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        """Text-only вызов с низкой температурой, ответ — JSON-объект.
        Возвращает {} при невалидном ответе после двух попыток."""
        if not self._credentials:
            logger.warning("GigaChat credentials not set")
            return {}

        for attempt in range(2):
            try:
                async with await self._client(timeout=120) as client:
                    response = await client.achat({
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        "temperature": 0.1,
                        "top_p": 0.1,
                    })
                return _parse_json_object(response.choices[0].message.content)
            except (json.JSONDecodeError, TypeError, ValueError, IndexError, AttributeError):
                logger.warning("Invalid GigaChat JSON response, attempt %s", attempt + 1)
            except (httpx.TransportError, httpx.TimeoutException, ResponseError):
                logger.warning("GigaChat JSON request failed, attempt %s", attempt + 1)
                if attempt == 1:
                    raise
                await asyncio.sleep(3)

        return {}
    
    
    async def check_task(
        self,
        system_prompt: str,
        statement: str,
        expected_answer: str,
        student_answer: str,
        student_work: str = "",
    ) -> dict:
        key = hashlib.sha256(json.dumps(
            [system_prompt, statement, expected_answer, student_answer, student_work],
            ensure_ascii=False,
        ).encode()).hexdigest()

        # Кэш чтения — без глобального лока, чтобы параллельные проверки
        # одной работы не сериализовались на LLM-вызове.
        try:
            cached = await self._redis.hget("check:cache", key)
            if cached is not None:
                await self._redis.zadd("check:cache:lru", {key: time.time_ns()})
                return json.loads(cached)
        except RedisError:
            logger.warning("Redis cache read failed; falling back to LLM")

        result = await self._check_task_uncached(
            system_prompt, statement, expected_answer, student_answer, student_work
        )

        try:
            await self._redis.hset("check:cache", key, json.dumps(result, ensure_ascii=False))
            await self._redis.zadd("check:cache:lru", {key: time.time_ns()})
            old = await self._redis.zrange("check:cache:lru", 0, -501)
            if old:
                await self._redis.hdel("check:cache", *old)
                await self._redis.zrem("check:cache:lru", *old)
        except RedisError:
            logger.warning("Redis cache write failed; result not cached")

        return result

    
    async def _check_task_uncached(
        self,
        system_prompt: str,
        statement: str,
        expected_answer: str,
        student_answer: str,
        student_work: str = "",
    ) -> dict:
        fallback = {
            "correct": student_answer.strip() == expected_answer.strip(),
            "explanation": "",
            "reasoning_graph": [],
            "error_type": None,
        }
        if not self._credentials:
            logger.warning("GigaChat credentials not set")
            return fallback

        payload = json.dumps(
            {
                "statement": statement,
                "expected_answer": expected_answer,
                "student_answer": student_answer,
                "student_work": student_work,
            },
            ensure_ascii=False,
        )

        for attempt in range(2):
            try:
                async with await self._client(timeout=120) as client:
                    response = await client.achat({
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": payload},
                        ],
                        "temperature": 0.1,
                        "top_p": 0.1,
                    })

                data = _parse_json_object(response.choices[0].message.content)
                if not isinstance(data["correct"], bool):
                    raise ValueError("correct must be boolean")
                if not isinstance(data["explanation"], str):
                    raise ValueError("explanation must be string")
                if not isinstance(data["reasoning_graph"], list):
                    raise ValueError("reasoning_graph must be list")
                error_type = data["error_type"]
                if error_type is not None and error_type not in ERROR_TYPES:
                    raise ValueError("invalid error_type")
                if data["correct"] and error_type is not None:
                    raise ValueError("correct answer cannot have error_type")
                if not data["correct"] and error_type is None:
                    raise ValueError("incorrect answer needs error_type")
                return {
                    "correct": data["correct"],
                    "explanation": data["explanation"],
                    "reasoning_graph": data["reasoning_graph"],
                    "error_type": error_type,
                }
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError):
                logger.warning("Invalid GigaChat check response, attempt %s", attempt + 1)
            except httpx.TransportError:
                logger.warning("GigaChat check request failed, attempt %s", attempt + 1)
                if attempt == 0:
                    await asyncio.sleep(1)

        return fallback


    async def summarize_mistakes(self, explanations: list[str], system_prompt: str) -> list[str]:
        if not explanations or not self._credentials:
            return []

        for attempt in range(2):
            try:
                async with await self._client() as client:
                    response = await client.achat({
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": json.dumps(explanations, ensure_ascii=False),
                            },
                        ],
                    })

                items = json.loads(response.choices[0].message.content)[
                    "recurring_mistakes"
                ]
                if not isinstance(items, list) or not all(
                    isinstance(item, str) for item in items
                ):
                    raise ValueError("invalid recurring_mistakes")
                return [item.strip() for item in items[:5] if item.strip()]
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError):
                logger.warning("Invalid memory response, attempt %s", attempt + 1)
            except httpx.TransportError:
                logger.warning("Memory request failed, attempt %s", attempt + 1)

        return []


    async def extract_reference(
        self,
        photos: list[Path],
        system_prompt: str,
    ) -> dict:
        """Извлечь задания и эталонные ответы с фото/страниц PDF.

        Возвращает dict вида
        {title, subject, grade, tasks: [{index, statement, expected_answer, confidence}]}.
        При ошибке — пустая заготовка.
        """
        empty = {"title": "", "subject": None, "grade": None, "tasks": []}
        if not self._credentials:
            logger.warning("GigaChat credentials not set")
            return empty

        for attempt in range(2):
            try:
                async with await self._client() as client:
                    attachments = []
                    for photo in photos:
                        with photo.open("rb") as file:
                            uploaded = await client.aupload_file(
                                (photo.name, file), purpose="general"
                            )
                        attachments.append(uploaded.id_)

                    response = await client.achat({
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": "Извлеки задания и эталонные ответы.",
                                "attachments": attachments,
                            },
                        ],
                    })

                data = json.loads(response.choices[0].message.content)
                tasks = []
                for item in data.get("tasks", []):
                    tasks.append({
                        "index": str(item.get("index", "")),
                        "statement": str(item.get("statement", "")).strip(),
                        "expected_answer": str(item.get("expected_answer", "")).strip(),
                        "confidence": float(item.get("confidence", 0.0)),
                    })
                return {
                    "title": str(data.get("title") or "").strip(),
                    "subject": data.get("subject"),
                    "grade": data.get("grade"),
                    "tasks": tasks,
                }
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError):
                logger.warning("Invalid GigaChat extract response, attempt %s", attempt + 1)
            except httpx.TransportError:
                logger.warning("GigaChat extract request failed, attempt %s", attempt + 1)
                if attempt == 0:
                    await asyncio.sleep(1)

        return empty


    async def generate_tasks(self, prompt: str, system_prompt: str | None = None) -> str:
        async with await self._client() as client:
            response = await client.achat({
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt or (
                            "Ты составляешь задачи по математике для учеников начальной школы. "
                            "Верни только JSON-объект вида "
                            '{"tasks":[{"statement":"...",'
                            '"expected_answer":"..."}]}. '
                            "В expected_answer указывай один короткий ответ "
                            "без решения и пояснений."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            })
        return response.choices[0].message.content

    async def chat_completion(self, system_prompt: str, user_payload: str) -> str:
        async with await self._client() as client:
            response = await client.achat({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_payload},
                ],
            })
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise ValueError("GigaChat вернул ответ без текста") from exc
        if not isinstance(content, str):
            raise ValueError("GigaChat вернул ответ без текста")
        return content


gigachat_client = GigaChatClient()
