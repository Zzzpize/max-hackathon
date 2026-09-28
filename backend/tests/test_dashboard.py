import httpx
import pytest

from app.main import app
from app.models import Student, StudentProfile


@pytest.mark.asyncio
async def test_dashboard_aggregates_only_teachers_class(sessions, auth_headers):
    async with sessions() as session:
        session.add_all([
            Student(id="a", teacher_id="1", class_id="2A", display_name="A", grade=2),
            Student(id="b", teacher_id="1", class_id="2A", display_name="B", grade=2),
            Student(id="c", teacher_id="1", class_id="2A", display_name="C", grade=2),
            Student(id="other", teacher_id="2", class_id="2A", display_name="D", grade=2),
            StudentProfile(student_id="a", avg_score=3, memory={
                "trend": "stable", "weak_topics": [{"topic": "Дроби", "error_rate": 0.5}],
            }),
            StudentProfile(student_id="b", avg_score=5, memory={
                "trend": "regressing", "weak_topics": [{"topic": "Дроби", "error_rate": 1.0}],
            }),
            StudentProfile(student_id="other", avg_score=0, memory={
                "trend": "regressing", "weak_topics": [{"topic": "Чужая тема", "error_rate": 1.0}],
            }),
        ])
        await session.commit()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=auth_headers(1),
    ) as client:
        response = await client.get("/classes/2A/dashboard")

    assert response.status_code == 200
    body = response.json()
    body["students_needing_help"].sort(key=lambda item: item["student_id"])
    assert body == {
        "class_id": "2A",
        "students_count": 3,
        "avg_score": 4.0,
        "weak_topics": [{"topic": "Дроби", "error_rate": 0.75}],
        "students_needing_help": [
            {"student_id": "a", "reason": "low_score"},
            {"student_id": "b", "reason": "regressing"},
        ],
    }
