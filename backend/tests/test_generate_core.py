from unittest.mock import AsyncMock

import pytest

from app.modules.generate import pipeline as work_pipeline
from app.modules.homework import pipeline as homework_pipeline


@pytest.mark.asyncio
async def test_shared_engine(monkeypatch):
    generated = [{"index": 1, "statement": "Вычисли: 2 + 2.", "expected_answer": "4"}]
    shared = AsyncMock(return_value=generated)
    monkeypatch.setattr(work_pipeline, "generate_tasks", shared)
    monkeypatch.setattr(homework_pipeline.core, "generate_tasks", shared)
    monkeypatch.setattr(work_pipeline.gigachat_client, "_credentials", "test")

    work = await work_pipeline.generate_work("Сложение", 2, 1)
    homework = await homework_pipeline.generate_homework(
        "teacher", "math", 2, "Сложение", 1, "Придумай задачу"
    )

    assert work.tasks[0]["statement"] == homework.tasks[0]["statement"]
    assert shared.await_args_list[0].args == (
        "math", 2, "Сложение", 1,
        "Числа не больше 100. Один короткий числовой ответ без объяснения.",
    )
    assert shared.await_args_list[1].args == (
        "math", 2, "Сложение", 1, "Придумай задачу"
    )
