from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image

from app.main import app
from app.models import Student, WorkTemplate
from app.modules.check import pipeline
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
    profile_update = AsyncMock()
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
    profile_update.assert_awaited_once_with(submission_id)
