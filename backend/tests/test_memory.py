from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.models import CheckResult, Student, Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.memory import profile


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ([5, 4, 3, 2, 1], "regressing"),
        ([1, 2, 3, 4, 5], "improving"),
        ([3, 3, 3, 3, 3], "stable"),
    ],
)
async def test_trend_regression(sessions, monkeypatch, scores, expected):
    monkeypatch.setattr(
        profile.gigachat_client, "summarize_mistakes", AsyncMock(return_value=[])
    )
    work = WorkTemplate(
        id="work-1", teacher_id="teacher-1", title="Сложение", grade=2,
        tasks=[
            {"index": index, "statement": str(index), "expected_answer": str(index)}
            for index in range(1, 6)
        ],
    )
    async with sessions() as session:
        session.add(Student(
            id="student-1", teacher_id="teacher-1", class_id="class-1", display_name="Ученик", grade=2
        ))
        session.add(work)
        for index, score in enumerate(scores):
            submission_id = f"submission-{index}"
            session.add(Submission(
                id=submission_id,
                work_id=work.id,
                student_id="student-1",
                status=SubmissionStatus.confirmed,
                created_at=datetime(2026, 1, 1) + timedelta(days=index),
            ))
            session.add(CheckResult(
                submission_id=submission_id,
                per_task=[
                    {
                        "task_index": task_index,
                        "teacher_verdict": {"is_correct": task_index <= score},
                    }
                    for task_index in range(1, 6)
                ],
            ))
        await session.commit()

        result = await profile.build_profile(session, "student-1")

    assert result.submissions_count == 5
    assert result.trend == expected
