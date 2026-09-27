from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image

from app.main import app
from app.models import Student, StudentProfile, Submission, WorkTemplate
from app.modules.check import pipeline
from app.modules.memory import profile
from app.routers import submissions as submission_router


@pytest.mark.asyncio
async def test_submission_lifecycle(sessions, monkeypatch, tmp_path):
    work = WorkTemplate(
        id="work-1",
        teacher_id="teacher-1",
        title="Сложение",
        grade=2,
        tasks=[
            {"index": 1, "statement": "1 + 1", "expected_answer": "2", "max_points": 1}
        ],
    )
    async with sessions() as session:
        session.add_all([
            Student(id="student-1", class_id="class-1", display_name="Ученик", grade=2),
            work,
        ])
        await session.commit()

    monkeypatch.setattr(submission_router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(
        pipeline.gigachat_client,
        "recognize_answers",
        AsyncMock(return_value=[
            {"task_index": 1, "answer": "2", "confidence": 0.8}
        ]),
    )
    monkeypatch.setattr(
        pipeline.gigachat_client,
        "check_task",
        AsyncMock(return_value={
            "correct": True, "explanation": "Верно", "reasoning_graph": []
        }),
    )
    monkeypatch.setattr(profile.gigachat_client, "summarize_mistakes", AsyncMock(return_value=[]))
    profile_update = AsyncMock(wraps=submission_router.on_submission_confirmed)
    monkeypatch.setattr(submission_router, "on_submission_confirmed", profile_update)

    class BotClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def post(self, *_args, **_kwargs):
            return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(
        pipeline, "httpx", SimpleNamespace(AsyncClient=lambda **_kwargs: BotClient(), HTTPError=Exception)
    )

    photo = BytesIO()
    Image.new("RGB", (1, 1), "white").save(photo, format="PNG")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/submissions",
            data={"work_id": work.id, "student_id": "student-1"},
            files={"photos": ("work.png", photo.getvalue(), "image/png")},
        )
        assert created.status_code == 202, created.text
        submission_id = created.json()["id"]

        checked = await client.get(f"/submissions/{submission_id}")
        assert checked.status_code == 200
        assert checked.json()["status"] == "checked"
        assert checked.json()["per_task"][0]["teacher_verdict"] is None

        reviewed = await client.patch(
            f"/submissions/{submission_id}/review",
            json={"per_task": [
                {"task_index": 1, "is_correct": False, "comment": "Ошибка в решении"}
            ]},
        )
        assert reviewed.status_code == 200, reviewed.text

        confirmed = await client.get(f"/submissions/{submission_id}")
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"
        assert confirmed.json()["per_task"][0]["teacher_verdict"] == {
            "is_correct": False,
            "comment": "Ошибка в решении",
        }
        repeated = await client.patch(
            f"/submissions/{submission_id}/review",
            json={"per_task": [
                {"task_index": 1, "is_correct": False, "comment": "Ошибка в решении"}
            ]},
        )
        assert repeated.status_code == 200

    async with sessions() as session:
        saved_profile = await session.get(StudentProfile, "student-1")
        assert saved_profile.submissions_count == 1
        assert saved_profile.avg_score == 0
    profile_update.assert_awaited_once()


@pytest.mark.asyncio
async def test_review_rolls_back_when_profile_update_fails(sessions, monkeypatch):
    async with sessions() as session:
        session.add_all([
            Student(id="student-1", class_id="class-1", display_name="Ученик", grade=2),
            WorkTemplate(id="work-1", teacher_id="teacher-1", title="Сложение", grade=2,
                         tasks=[{"index": 1, "statement": "1 + 1", "expected_answer": "2"}]),
            Submission(id="submission-1", work_id="work-1", student_id="student-1", status="checked"),
        ])
        await session.commit()

    async def fail_update(*_args):
        raise RuntimeError("profile update failed")

    monkeypatch.setattr(submission_router, "on_submission_confirmed", fail_update)
    async with sessions() as session:
        from app.models import CheckResult
        session.add(CheckResult(submission_id="submission-1", per_task=[{
            "task_index": 1, "teacher_verdict": None,
        }]))
        await session.commit()

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/submissions/submission-1/review", json={
            "per_task": [{"task_index": 1, "is_correct": True}]
        })
        assert response.status_code == 500

    async with sessions() as session:
        saved = await session.get(Submission, "submission-1")
        assert saved.status == "checked"
        assert await session.get(StudentProfile, "student-1") is None


@pytest.mark.asyncio
async def test_internal_bot_notify_validates_submission(sessions):
    async with sessions() as session:
        session.add_all([
            Student(id="student-1", class_id="class-1", display_name="Ученик", grade=2),
            WorkTemplate(id="work-1", teacher_id="42", title="Сложение", grade=2, tasks=[]),
            Submission(id="submission-1", work_id="work-1", student_id="student-1", status="checked"),
        ])
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"teacher_id": "42", "event": "submission_checked", "submission_id": "submission-1"}
        assert (await client.post("/internal/bot/notify", json=payload)).status_code == 200
        assert (await client.post("/internal/bot/notify", json={**payload, "teacher_id": "43"})).status_code == 404
        assert (await client.post("/internal/bot/notify", json={**payload, "event": "other"})).status_code == 422
        assert "/internal/bot/notify" not in (await client.get("/openapi.json")).json()["paths"]
