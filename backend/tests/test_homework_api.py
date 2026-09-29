from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import app
from app.modules.generate import core


PAYLOAD = {
    "subject": "physics", "grade": 7, "topic": "Сила",
    "n_tasks": 1, "prompt": "Задача про силу",
}
TASK = {"index": 1, "statement": "Найди силу", "expected_answer": "5 Н"}


@pytest.mark.asyncio
async def test_generate_and_list(sessions, monkeypatch, auth_headers):
    monkeypatch.setattr(core, "generate_tasks", AsyncMock(return_value=[TASK]))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/homework", json=PAYLOAD, headers=auth_headers(1))
        assert created.status_code == 201, created.text
        listed = await client.get("/homework", headers=auth_headers(1))
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [created.json()["id"]]


@pytest.mark.asyncio
async def test_tenant_isolation(sessions, monkeypatch, auth_headers):
    generate = AsyncMock(return_value=[TASK])
    monkeypatch.setattr(core, "generate_tasks", generate)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/homework", json=PAYLOAD, headers=auth_headers(1))
        homework_id = created.json()["id"]
        other = auth_headers(2)
        assert (await client.get("/homework", headers=other)).json() == []
        for method, path, kwargs in (
            (client.get, f"/homework/{homework_id}", {}),
            (client.post, f"/homework/{homework_id}/regenerate", {"json": {}}),
            (client.get, f"/homework/{homework_id}/export?format=txt", {}),
            (client.patch, f"/homework/{homework_id}", {"json": {"title": "Чужое"}}),
            (client.delete, f"/homework/{homework_id}", {}),
        ):
            response = await method(path, headers=other, **kwargs)
            assert response.status_code == 403, response.text
        assert generate.await_count == 1


@pytest.mark.asyncio
async def test_regenerate_replaces_tasks(sessions, monkeypatch, auth_headers):
    replacement = {"index": 1, "statement": "Найди массу", "expected_answer": "2 кг"}
    generate = AsyncMock(side_effect=[[TASK], [replacement]])
    monkeypatch.setattr(core, "generate_tasks", generate)
    headers = auth_headers(1)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/homework", json=PAYLOAD, headers=headers)
        homework_id = created.json()["id"]
        regenerated = await client.post(
            f"/homework/{homework_id}/regenerate",
            json={"extra_prompt": "Сделай другую задачу"}, headers=headers,
        )
        assert regenerated.status_code == 200, regenerated.text
        assert regenerated.json()["id"] == homework_id
        assert regenerated.json()["tasks"] == [replacement]
        assert generate.await_args.args == (
            "physics", 7, "Сила", 1, "Задача про силу\nСделай другую задачу"
        )
        saved = await client.get(f"/homework/{homework_id}", headers=headers)
        assert saved.json()["tasks"] == [replacement]
