from unittest.mock import AsyncMock
from contextlib import asynccontextmanager

import pytest

from app.llm.gigachat import GigaChatClient


@pytest.mark.asyncio
async def test_check_task_cached(monkeypatch):
    client = GigaChatClient()
    class Cache:
        def __init__(self):
            self.values = {}
            self.recent = {}

        @asynccontextmanager
        async def lock(self, *_args, **_kwargs):
            yield

        async def hget(self, _name, key):
            return self.values.get(key)

        async def hset(self, _name, key, value):
            self.values[key] = value

        async def zadd(self, _name, values):
            self.recent.update(values)

        async def zrange(self, _name, start, end):
            keys = sorted(self.recent, key=self.recent.get)
            return keys[start:end + 1] if end >= 0 else keys[start:end + 1 or None]

        async def hdel(self, _name, *keys):
            for key in keys:
                self.values.pop(key, None)

        async def zrem(self, _name, *keys):
            for key in keys:
                self.recent.pop(key, None)

    client._redis = Cache()
    llm = AsyncMock(return_value={
        "correct": True, "explanation": "Верно", "reasoning_graph": []
    })
    monkeypatch.setattr(client, "_check_task_uncached", llm)
    kwargs = {
        "system_prompt": "Проверь ответ",
        "statement": "1 + 1",
        "expected_answer": "2",
        "student_answer": "2",
    }

    first = await client.check_task(**kwargs)
    first["correct"] = False
    second = await client.check_task(**kwargs)

    assert second["correct"] is True
    llm.assert_awaited_once()

    other_client = GigaChatClient()
    other_client._redis = client._redis
    other_llm = AsyncMock()
    monkeypatch.setattr(other_client, "_check_task_uncached", other_llm)
    assert (await other_client.check_task(**kwargs))["correct"] is True
    other_llm.assert_not_awaited()
