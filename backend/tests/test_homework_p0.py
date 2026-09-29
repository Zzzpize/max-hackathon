from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import app
from app.modules.generate import core
from app.modules.homework.export import render_txt


@pytest.mark.asyncio
@pytest.mark.parametrize("subject,grade,expected", [
    ("math", 4, "арифметика и простые уравнения"),
    ("algebra", 5, "уравнения, неравенства и функции"),
    ("geometry", 7, "планиметрия, стереометрия и теоремы"),
    ("physics", 11, "расчётные задачи, формулы и единицы измерения"),
    ("math", 11, "уравнения, функции, геометрия и прикладные задачи"),
    ("physics", 2, "начальная школа"),
])
async def test_generate_tasks_prompt_matches_subject_and_grade(monkeypatch, subject, grade, expected):
    llm = AsyncMock(return_value='{"tasks":[{"statement":"Условие","expected_answer":"Ответ"}]}')
    monkeypatch.setattr(core.gigachat_client, "generate_tasks", llm)

    tasks = await core.generate_tasks(subject, grade, "Тема", 1, "Контекст")

    assert tasks[0]["statement"] == "Условие"
    system_prompt = llm.await_args.kwargs["system_prompt"]
    assert expected in system_prompt
    assert ("начальная школа" in system_prompt) == (grade <= 4)


@pytest.mark.asyncio
async def test_homework_crud_and_txt(sessions, monkeypatch, auth_headers):
    generated = AsyncMock(return_value=[{
        "index": 1, "statement": "Реши задачу", "expected_answer": "Ответ",
    }])
    monkeypatch.setattr(core, "generate_tasks", generated)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post("/homework", json={
            "subject": "physics", "grade": 7, "topic": "Сила",
            "n_tasks": 1, "prompt": "Задача про силу",
        }, headers=auth_headers(42))
        assert created.status_code == 201, created.text
        homework = created.json()
        homework_id = homework["id"]
        generated.assert_awaited_once_with("physics", 7, "Сила", 1, "Задача про силу")

        listed = await client.get("/homework", headers=auth_headers(42))
        assert [item["id"] for item in listed.json()] == [homework_id]
        assert (await client.get("/homework", headers=auth_headers(43))).json() == []
        assert (await client.get(f"/homework/{homework_id}", headers=auth_headers(43))).status_code == 403

        changed = await client.patch(f"/homework/{homework_id}", json={
            "tasks": [{"index": 4, "statement": "Новое условие", "expected_answer": "Новый ответ"}],
            "notes": "Для класса",
        }, headers=auth_headers(42))
        assert changed.status_code == 200, changed.text
        assert changed.json()["tasks"][0]["index"] == 1
        assert changed.json()["notes"] == "Для класса"

        async with sessions() as session:
            from app.models import Homework
            saved = await session.get(Homework, homework_id)
            exported = render_txt(saved).decode()
            assert "Новое условие" in exported
            assert "Новый ответ" in exported

        assert (await client.delete(f"/homework/{homework_id}", headers=auth_headers(43))).status_code == 403
        assert (await client.delete(f"/homework/{homework_id}", headers=auth_headers(42))).status_code == 204
        assert (await client.get(f"/homework/{homework_id}", headers=auth_headers(42))).status_code == 404
