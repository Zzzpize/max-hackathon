from io import BytesIO

import httpx
import pytest
from PIL import Image

from app.main import app
from app.models import CheckResult, Student, Submission, WorkTemplate


@pytest.mark.asyncio
async def test_cross_tenant_student_cannot_submit_to_work(sessions, auth_headers):
    async with sessions() as session:
        session.add_all([
            Student(id="student-a", teacher_id="1", class_id="2A", display_name="A", grade=2),
            Student(id="student-b", teacher_id="2", class_id="2A", display_name="B", grade=2),
            WorkTemplate(id="work-a", teacher_id="1", title="Work", grade=2, tasks=[]),
        ])
        await session.commit()

    photo = BytesIO()
    Image.new("RGB", (1, 1), "white").save(photo, format="PNG")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers(1)) as client:
        response = await client.post(
            "/submissions",
            data={"work_id": "work-a", "student_id": "student-b"},
            files={"photos": ("work.png", photo.getvalue(), "image/png")},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_denied(sessions, auth_headers):
    async with sessions() as session:
        session.add_all([
            Student(id="student-a", teacher_id="1", class_id="2A", display_name="A", grade=2),
            Student(id="student-b", teacher_id="2", class_id="2A", display_name="B", grade=2),
            WorkTemplate(id="work-a", teacher_id="1", title="A", grade=2, tasks=[]),
            Submission(id="submission-a", work_id="work-a", student_id="student-a", status="checked"),
            CheckResult(submission_id="submission-a", per_task=[]),
        ])
        await session.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers(2)) as client:
        assert (await client.get("/works/work-a?teacher_id=1")).status_code == 403
        assert (await client.get("/submissions/submission-a?teacher_id=1")).status_code == 403
        assert (await client.patch(
            "/submissions/submission-a/review?teacher_id=1", json={"per_task": []}
        )).status_code == 403
        assert (await client.get("/students/student-a/profile?teacher_id=1")).status_code == 403
        assert (await client.delete("/students/student-a?teacher_id=1")).status_code == 403
        assert (await client.get("/works?teacher_id=1")).json() == []
        assert (await client.get("/submissions?teacher_id=1")).json() == []
        assert [student["id"] for student in (await client.get("/students?teacher_id=1")).json()] == ["student-b"]
        assert (await client.get("/classes/2A/dashboard?teacher_id=1")).json()["students_count"] == 1


@pytest.mark.asyncio
async def test_create_student_and_submission_owner(sessions, auth_headers):
    async with sessions() as session:
        session.add(WorkTemplate(id="work-a", teacher_id="1", title="A", grade=2, tasks=[]))
        await session.commit()

    photo = BytesIO()
    Image.new("RGB", (1, 1), "white").save(photo, format="PNG")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers(1)) as client:
        created = await client.post("/students", json={
            "teacher_id": "2", "class_id": "2A", "display_name": "A", "grade": 2,
        })
        assert created.status_code == 201
        assert created.json()["teacher_id"] == "1"
        student_id = created.json()["id"]
        assert (await client.post(
            "/submissions",
            data={"work_id": "work-a", "student_id": student_id, "teacher_id": "1"},
            files={"photos": ("work.png", photo.getvalue(), "image/png")},
            headers=auth_headers(2),
        )).status_code == 403
