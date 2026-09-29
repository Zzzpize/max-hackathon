from datetime import datetime
import json
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.config import settings
from app.main import app
from app.models import Homework, Roadmap, Student, Submission, WorkTemplate
from app.modules.generate import core


REQUEST = {
    "subject": "math", "grade": 3, "topic": "Сложение",
    "n_tasks": 3, "prompt": "Задачи средней сложности",
}
TASK = {"index": 1, "statement": "Вычисли 2 + 2.", "expected_answer": "4"}


@pytest.fixture
def llm(monkeypatch):
    async def generate(payload, **_kwargs):
        count = json.loads(payload)["n_tasks"]
        return json.dumps({"tasks": [
            {**TASK, "index": i, "statement": f"Вычисли {i} + 2.", "expected_answer": str(i + 2)}
            for i in range(1, count + 1)
        ]})

    mock = AsyncMock(side_effect=generate)
    monkeypatch.setattr(core.gigachat_client, "generate_tasks", mock)
    return mock


@pytest_asyncio.fixture
async def client(sessions, auth_headers):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers=auth_headers(1),
    ) as client:
        yield client


async def create(client, **changes):
    response = await client.post("/homework", json={**REQUEST, **changes})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_generate_and_list(client, llm, sessions):
    hw = await create(client, title="  Домашка на завтра  ", teacher_id="999")
    assert hw["teacher_id"] == "1"
    assert hw["title"] == "Домашка на завтра"
    assert hw["notes"] is None
    assert len(hw["tasks"]) == 3
    assert "difficulty" not in hw["tasks"][0]
    assert (await client.get("/homework")).json() == [hw]
    assert (await client.get(f"/homework/{hw['id']}")).json() == hw
    llm.assert_awaited_once()
    async with sessions() as session:
        assert await session.get(Homework, hw["id"]) is not None
        for model in (WorkTemplate, Submission, Student, Roadmap):
            assert await session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("subject", ["math", "algebra", "physics", "geometry"])
@pytest.mark.parametrize("grade", range(1, 12))
async def test_all_subject_grade_combinations(client, llm, subject, grade):
    hw = await create(client, subject=subject, grade=grade)
    assert hw["subject"] == subject and hw["grade"] == grade
    assert len(hw["tasks"]) == 3
    payload = json.loads(llm.await_args.args[0])
    assert payload["subject"] == subject and payload["grade"] == grade
    assert payload["extra_context"] == REQUEST["prompt"]


@pytest.mark.asyncio
async def test_tenant_isolation(client, llm, auth_headers):
    hw = await create(client)
    llm.reset_mock()
    client.headers.update(auth_headers(2))
    assert (await client.get("/homework?teacher_id=1")).json() == []
    url = f"/homework/{hw['id']}"
    for method, suffix, body in (
        ("GET", "", None), ("PATCH", "", {"title": "Чужое"}),
        ("DELETE", "", None), ("POST", "/regenerate", {}),
        ("GET", "/export?format=txt", None), ("GET", "/export?format=pdf", None),
    ):
        response = await client.request(method, url + suffix, json=body)
        assert response.status_code == 403, response.text
    llm.assert_not_awaited()
    client.headers.update(auth_headers(1))
    assert (await client.get(url)).json() == hw


@pytest.mark.asyncio
async def test_missing_resources(client, llm):
    url = "/homework/missing"
    for method, suffix, body in (
        ("GET", "", None), ("PATCH", "", {"title": "Новое"}),
        ("DELETE", "", None), ("POST", "/regenerate", {}),
        ("GET", "/export?format=txt", None),
    ):
        assert (await client.request(method, url + suffix, json=body)).status_code == 404
    llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_all_routes_require_auth(client, llm):
    client.headers.clear()
    for method, path, body in (
        ("GET", "", None), ("POST", "", REQUEST), ("GET", "/id", None),
        ("PATCH", "/id", {"title": "Новое"}), ("DELETE", "/id", None),
        ("POST", "/id/regenerate", {}), ("GET", "/id/export?format=txt", None),
    ):
        assert (await client.request(method, "/homework" + path, json=body)).status_code == 401
    llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_bot_auth(client, llm):
    client.headers.clear()
    client.headers.update({"Authorization": f"Bearer {settings.max_bot_token}", "X-Teacher-Id": "2"})
    hw = await create(client)
    assert hw["teacher_id"] == "2"
    assert (await client.get("/homework")).json() == [hw]
    client.headers["Authorization"] = "Bearer invalid"
    assert (await client.get("/homework")).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"subject": "history"}, {"grade": 0}, {"grade": 12}, {"grade": True},
    {"topic": "   "}, {"topic": "x" * 201}, {"prompt": "abcd"},
    {"prompt": "x" * 2001}, {"prompt": "     "}, {"title": "  "},
    {"title": "x" * 201}, {"n_tasks": 0}, {"n_tasks": 31}, {"n_tasks": 1.5},
])
async def test_invalid_create(client, llm, change):
    assert (await client.post("/homework", json={**REQUEST, **change})).status_code == 422
    llm.assert_not_awaited()
    assert (await client.get("/homework")).json() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("n_tasks", [1, 30])
async def test_boundary_values_and_generated_title(client, llm, n_tasks):
    hw = await create(client, topic="Т" * 200, n_tasks=n_tasks, prompt="А" * 2000)
    assert len(hw["tasks"]) == n_tasks
    assert len(hw["title"]) <= 200
    assert hw["title"].endswith(datetime.now().strftime(", %d.%m.%Y"))


@pytest.mark.asyncio
async def test_patch_and_delete(client, llm):
    hw = await create(client)
    url = f"/homework/{hw['id']}"
    task = {**TASK, "statement": "  Объясни, почему 2 + 2 = 4.  ", "difficulty": "hard"}
    response = await client.patch(url, json={"title": "Новое", "notes": "Для себя", "tasks": [task]})
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["tasks"] == [{**task, "statement": task["statement"].strip()}]
    assert updated["notes"] == "Для себя"
    assert updated["updated_at"] > hw["updated_at"]
    assert updated["created_at"] == hw["created_at"]
    assert (await client.patch(url, json={"notes": None})).json()["notes"] is None
    assert (await client.get(url)).json()["tasks"] == updated["tasks"]
    response = await client.delete(url)
    assert response.status_code == 204 and response.content == b""
    assert (await client.get(url)).status_code == 404
    assert (await client.get("/homework")).json() == []
    llm.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("patch", [
    {}, {"title": None}, {"title": " "}, {"tasks": None}, {"tasks": []},
    {"tasks": [{**TASK, "statement": "  "}]},
    {"tasks": [{**TASK, "expected_answer": ""}]},
    {"tasks": [{**TASK, "difficulty": "unknown"}]},
    {"tasks": [{**TASK, "difficulty": None}]},
    {"tasks": [TASK, TASK]}, {"tasks": [{**TASK, "index": 2}]},
    {"tasks": [{**TASK, "index": True}]},
    {"tasks": [{**TASK, "index": i} for i in range(1, 32)]},
    {"teacher_id": "2"}, {"title": "Новое", "tasks": ["invalid"]},
])
async def test_invalid_patch_is_atomic(client, llm, patch):
    hw = await create(client)
    url = f"/homework/{hw['id']}"
    response = await client.patch(url, json=patch)
    assert response.status_code == 422, response.text
    assert (await client.get(url)).json() == hw


@pytest.mark.asyncio
async def test_regenerate_replaces_tasks(client, llm):
    hw = await create(client, title="Сохранить название")
    url = f"/homework/{hw['id']}"
    await client.patch(url, json={"tasks": [TASK], "notes": "Сохранить заметки"})
    llm.side_effect = None
    replacement = {**TASK, "statement": "Вычисли 3 + 3.", "expected_answer": "6"}
    llm.return_value = json.dumps({"tasks": [replacement]})
    response = await client.post(url + "/regenerate", json={"extra_prompt": "Попроще"})
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["id"] == hw["id"]
    assert updated["tasks"] == [replacement]
    assert updated["title"] == hw["title"]
    assert updated["notes"] == "Сохранить заметки"
    assert updated["prompt"] == hw["prompt"]
    assert updated["created_at"] == hw["created_at"]
    assert updated["updated_at"] > hw["updated_at"]
    payload = json.loads(llm.await_args.args[0])
    assert payload["n_tasks"] == 1
    assert "Попроще" in payload["extra_context"] and hw["prompt"] in payload["extra_context"]
    assert (await client.get(url)).json() == updated


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [None, {}, {"extra_prompt": ""}, {"extra_prompt": None}])
async def test_regenerate_without_extra_context(client, llm, body):
    hw = await create(client)
    response = await client.post(f"/homework/{hw['id']}/regenerate", json=body)
    assert response.status_code == 200, response.text
    assert llm.await_count == 2  # A fresh call even with identical context.


@pytest.mark.asyncio
async def test_generation_failure_does_not_save_or_overwrite(client, llm):
    hw = await create(client)
    llm.reset_mock()
    llm.side_effect = None
    llm.return_value = "not json"
    assert (await client.post("/homework", json=REQUEST)).status_code == 502
    assert llm.await_count == 2
    llm.reset_mock()
    url = f"/homework/{hw['id']}"
    assert (await client.post(url + "/regenerate", json={})).status_code == 502
    assert llm.await_count == 2
    assert (await client.get(url)).json() == hw
    assert (await client.get("/homework")).json() == [hw]


@pytest.mark.asyncio
async def test_filters_pagination_and_update_order(client, llm, sessions):
    first = await create(client, subject="math", grade=3, topic="Сложение дробей")
    second = await create(client, subject="physics", grade=7, topic="Скорость")
    third = await create(client, subject="math", grade=3, topic="Проценты 50%_тест")
    assert [h["id"] for h in (await client.get("/homework?subject=math&grade=3")).json()] == [third["id"], first["id"]]
    assert (await client.get("/homework", params={"topic": "дроб"})).json() == [first]
    assert (await client.get("/homework", params={"topic": "%_"})).json() == [third]
    assert (await client.get("/homework?limit=1&offset=1")).json() == [second]
    assert (await client.get("/homework?limit=0")).status_code == 422
    assert (await client.get("/homework?offset=-1")).status_code == 422
    assert (await client.get("/homework?grade=12")).status_code == 422
    assert (await client.get("/homework?subject=history")).status_code == 422

    # Exercise the deterministic id tie-break independently of clock resolution.
    async with sessions() as session:
        for hw in (await session.scalars(select(Homework))).all():
            hw.updated_at = datetime(2026, 1, 1)
        await session.commit()
    listed = (await client.get("/homework")).json()
    assert [h["id"] for h in listed] == sorted([first["id"], second["id"], third["id"]])
    await client.patch(f"/homework/{first['id']}", json={"notes": "Правка"})
    assert (await client.get("/homework?limit=1")).json()[0]["id"] == first["id"]
