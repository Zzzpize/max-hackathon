from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models import CheckResult, Student, Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.check import pipeline


@pytest.mark.asyncio
async def test_pipeline_with_stub_llm(sessions, monkeypatch):
    work = WorkTemplate(
        id="work-1",
        teacher_id="teacher-1",
        title="Сложение",
        grade=2,
        tasks=[
            {"index": 1, "statement": "1 + 1", "expected_answer": "2", "max_points": 2},
            {"index": 2, "statement": "2 + 2", "expected_answer": "4", "max_points": 1},
        ],
    )
    submission = Submission(
        id="submission-1", work_id=work.id, student_id="student-1", photos=[]
    )
    async with sessions() as session:
        session.add_all([
            Student(id="student-1", teacher_id="teacher-1", class_id="class-1", display_name="Ученик", grade=2),
            work,
            submission,
        ])
        await session.commit()

    recognize = AsyncMock(return_value=[
        {"task_index": 1, "answer": "2", "confidence": 0.9},
        {"task_index": 2, "answer": "4", "confidence": 0.7},
    ])
    check = AsyncMock(side_effect=[
        {"correct": True, "explanation": "", "reasoning_graph": []},
        {"correct": False, "explanation": "Ошибка", "reasoning_graph": []},
    ])
    monkeypatch.setattr(pipeline.gigachat_client, "recognize_answers", recognize)
    monkeypatch.setattr(pipeline.gigachat_client, "check_task", check)

    post = AsyncMock(return_value=SimpleNamespace(raise_for_status=lambda: None))

    class BotClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def post(self, *args, **kwargs):
            return await post(*args, **kwargs)

    monkeypatch.setattr(
        pipeline, "httpx", SimpleNamespace(AsyncClient=lambda **_kwargs: BotClient(), HTTPError=Exception)
    )

    await pipeline.run_check(submission.id)

    async with sessions() as session:
        saved = await session.get(Submission, submission.id)
        result = await session.get(CheckResult, submission.id)
        assert saved.status == SubmissionStatus.checked
        assert [task["task_index"] for task in result.per_task] == [1, 2]
        assert result.total_score == 2
        assert result.confidence == pytest.approx(0.8)
    assert check.await_count == 2
    assert post.await_args.kwargs["json"] == {
        "teacher_id": "teacher-1",
        "event": "submission_checked",
        "submission_id": submission.id,
    }
