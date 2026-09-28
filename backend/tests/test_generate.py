import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import app
from app.models import WorkTemplate
from app.modules.generate import pipeline


@pytest.mark.asyncio
async def test_generate_retries_invalid_answer_and_saves_work(
    sessions, monkeypatch, auth_headers
):
    generated = AsyncMock(side_effect=[
        json.dumps({"tasks": [{
            "statement": "Вычисли: 20 + 2.",
            "expected_answer": "20 + 2 = 22, потому что прибавили 2",
        }]}),
        json.dumps({"tasks": [{
            "statement": "Вычисли: 20 + 2.",
            "expected_answer": "22",
        }]}),
    ])
    monkeypatch.setattr(pipeline.gigachat_client, "_credentials", "test")
    monkeypatch.setattr(pipeline.gigachat_client, "generate_tasks", generated)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/works/generate",
            json={"topic": "Сложение", "grade": 2, "n_tasks": 1},
            headers=auth_headers(42),
        )
        assert response.status_code == 201, response.text
        work = response.json()
        assert work["teacher_id"] == "42"
        assert work["tasks"][0]["expected_answer"] == "22"
        assert (await client.get(
            f"/works/{work['id']}", headers=auth_headers(42)
        )).status_code == 200
        assert (await client.get(
            f"/works/{work['id']}", headers=auth_headers(43)
        )).status_code == 403
    generated.assert_awaited()
    assert generated.await_count == 2

    async with sessions() as session:
        assert await session.get(WorkTemplate, work["id"]) is not None


@pytest.mark.asyncio
async def test_generate_falls_back_after_two_invalid_responses(monkeypatch):
    generated = AsyncMock(return_value=json.dumps({"tasks": [{
        "statement": "Вычисли: 101 + 1.",
        "expected_answer": "102",
    }]}))
    monkeypatch.setattr(pipeline.gigachat_client, "_credentials", "test")
    monkeypatch.setattr(pipeline.gigachat_client, "generate_tasks", generated)

    work = await pipeline.generate_work("Сложение", 2, 1)
    assert generated.await_count == 2
    assert work.tasks[0]["expected_answer"] == "4"
    assert work.tasks[0]["statement"] == "Вычисли: 2 + 2."


@pytest.mark.parametrize("grade, statement, answer", [
    (2, "Вычисли: 101 + 1", "102"),
    (3, "Вычисли: 1001 + 1", "1002"),
    (4, "Вычисли: 10001 + 1", "10002"),
    (2, "Вычисли: 1 000 + 1", "1001"),
    (2, "Вычисли: 2 + 2", "2 или 4"),
    (2, "Вычисли: 2 + 2", "4 потому"),
])
def test_generate_rejects_invalid_tasks(grade, statement, answer):
    raw = json.dumps({"tasks": [{
        "statement": statement,
        "expected_answer": answer,
    }]})
    with pytest.raises(ValueError):
        pipeline._validate_tasks(raw, grade, 1)
