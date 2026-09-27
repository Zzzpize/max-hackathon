from unittest.mock import AsyncMock

import pytest

from app.llm.gigachat import GigaChatClient


@pytest.mark.asyncio
async def test_check_task_cached(monkeypatch):
    client = GigaChatClient()
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
