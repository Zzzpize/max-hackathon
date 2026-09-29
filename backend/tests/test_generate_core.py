import json
from unittest.mock import AsyncMock

from fastapi import HTTPException
from gigachat.exceptions import ResponseError
import httpx
import pytest
from sqlalchemy import inspect

from app.modules.generate import core, pipeline as work_pipeline
from app.modules.homework import pipeline as homework_pipeline


TASK = {"index": 1, "statement": "Вычисли 2 + 2.", "expected_answer": "4"}


@pytest.mark.asyncio
async def test_shared_engine(monkeypatch):
    generate = AsyncMock(return_value=[{**TASK, "difficulty": "easy"}])
    monkeypatch.setattr(core, "generate_tasks", generate)
    monkeypatch.setattr(work_pipeline.gigachat_client, "_credentials", "test")

    work = await work_pipeline.generate_work("Сложение", 3, 1)
    hw = await homework_pipeline.generate_homework(
        "teacher", "algebra", 7, "Уравнения", 1, "Нужны простые задачи"
    )

    first, second = generate.await_args_list
    assert first.args[:4] == ("math", 3, "Сложение", 1)
    assert json.loads(first.args[4])["max_number"] == 1000
    assert second.args == ("algebra", 7, "Уравнения", 1, "Нужны простые задачи")
    assert work.tasks == [{**TASK, "max_points": 1.0}]
    assert work.title == "Контрольная: Сложение"
    assert hw.tasks == [{**TASK, "difficulty": "easy"}]
    assert inspect(hw).transient  # Pipeline neither adds to a session nor commits.
    assert inspect(work).transient


@pytest.mark.asyncio
@pytest.mark.parametrize("subject,grade,keyword", [
    ("math", 2, "арифметика"), ("algebra", 9, "неравенства"),
    ("geometry", 11, "стереометрия"), ("physics", 8, "единицы измерения"),
])
async def test_subject_prompts_reach_llm(monkeypatch, subject, grade, keyword):
    completion = AsyncMock(return_value=json.dumps({"tasks": [{
        "statement": "  Объясни решение.  ",
        "expected_answer": "  Развёрнутый ответ с обоснованием.  ",
        "difficulty": "medium",
    }]}))
    monkeypatch.setattr(core.gigachat_client, "chat_completion", completion)
    tasks = await core.generate_tasks(subject, grade, "Тема", 1, "Пожелание учителя")
    system, raw_payload = completion.await_args.args
    assert keyword in system and f"Класс: {grade}" in system
    assert json.loads(raw_payload) == {
        "subject": subject, "grade": grade, "topic": "Тема", "n_tasks": 1,
        "extra_context": "Пожелание учителя",
    }
    assert tasks == [{
        "index": 1, "statement": "Объясни решение.",
        "expected_answer": "Развёрнутый ответ с обоснованием.", "difficulty": "medium",
    }]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [
    "not json", "[]", "null", "{}", '{"tasks": []}', '{"tasks": "bad"}',
    '{"tasks": [null]}', '{"tasks": [1]}',
    json.dumps({"tasks": [{**TASK, "statement": "   "}]}),
    json.dumps({"tasks": [{**TASK, "expected_answer": "  "}]}),
    json.dumps({"tasks": [{**TASK, "expected_answer": 4}]}),
    json.dumps({"tasks": [{**TASK, "difficulty": "expert"}]}),
    json.dumps({"tasks": [{**TASK, "difficulty": None}]}),
])
async def test_invalid_llm_tasks_rejected(monkeypatch, raw):
    monkeypatch.setattr(core.gigachat_client, "generate_tasks", AsyncMock(return_value=raw))
    with pytest.raises((ValueError, TypeError)):
        await core.generate_tasks("math", 3, "Сложение", 1, "")


@pytest.mark.asyncio
async def test_homework_retries_invalid_tasks_once(monkeypatch):
    completion = AsyncMock(side_effect=[
        json.dumps({"tasks": [{**TASK, "expected_answer": ""}]}),
        json.dumps({"tasks": [TASK]}),
    ])
    monkeypatch.setattr(core.gigachat_client, "generate_tasks", completion)
    hw = await homework_pipeline.generate_homework("1", "math", 3, "Сложение", 1, "Для урока")
    assert hw.tasks == [TASK]
    assert completion.await_count == 2
    assert "Исправь ошибку" in json.loads(completion.await_args.args[0])["extra_context"]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [
    httpx.ConnectError("offline"), httpx.ReadTimeout("timeout"),
    ResponseError("service unavailable"), ValueError("Ответ без текста"),
    RuntimeError("GigaChat не вернул access token"),
])
async def test_homework_returns_502_after_second_failure(monkeypatch, error):
    completion = AsyncMock(side_effect=error)
    monkeypatch.setattr(core.gigachat_client, "generate_tasks", completion)
    monkeypatch.setattr(homework_pipeline.asyncio, "sleep", AsyncMock())
    with pytest.raises(HTTPException) as exc:
        await homework_pipeline.generate_homework("1", "math", 3, "Сложение", 1, "Для урока")
    assert exc.value.status_code == 502
    assert completion.await_count == 2


@pytest.mark.asyncio
async def test_work_still_falls_back_without_credentials(monkeypatch):
    generate = AsyncMock()
    monkeypatch.setattr(core, "generate_tasks", generate)
    monkeypatch.setattr(work_pipeline.gigachat_client, "_credentials", "")
    work = await work_pipeline.generate_work("Сложение", 2, 3)
    assert len(work.tasks) == 3
    assert work.tasks[0]["expected_answer"] == "4"
    generate.assert_not_awaited()
