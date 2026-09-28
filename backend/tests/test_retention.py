import httpx
import pytest

from app.config import settings
from app.main import app
from app.models import CheckResult, Student, StudentProfile, Submission, WorkTemplate


@pytest.mark.asyncio
async def test_delete_student_removes_data_and_photos(sessions, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    async with sessions() as session:
        session.add_all([
            Student(id="student-1", teacher_id="1", class_id="2A", display_name="A", grade=2),
            Student(id="student-2", teacher_id="1", class_id="2A", display_name="B", grade=2),
            WorkTemplate(id="work-1", teacher_id="1", title="Math", grade=2, tasks=[]),
            StudentProfile(student_id="student-1", memory={"weak_topics": ["math"]}),
            Submission(id="submission-1", work_id="work-1", student_id="student-1"),
            Submission(id="submission-2", work_id="work-1", student_id="student-1"),
            CheckResult(submission_id="submission-1", per_task=[]),
        ])
        await session.commit()

    photo_dir = tmp_path / "submission-1"
    photo_dir.mkdir()
    (photo_dir / "0.png").write_bytes(b"photo")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=auth_headers(1),
    ) as client:
        response = await client.delete("/students/student-1")
        assert response.status_code == 204, response.text
        assert (await client.delete("/students/student-1")).status_code == 404

    async with sessions() as session:
        assert await session.get(Student, "student-1") is None
        assert await session.get(StudentProfile, "student-1") is None
        assert await session.get(Submission, "submission-1") is None
        assert await session.get(Submission, "submission-2") is None
        assert await session.get(CheckResult, "submission-1") is None
        assert await session.get(Student, "student-2") is not None
        assert await session.get(WorkTemplate, "work-1") is not None
    assert not photo_dir.exists()
