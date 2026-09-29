from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import app
from app.models import Roadmap
from app.routers import roadmaps


@pytest.mark.asyncio
async def test_generate_and_list(sessions, auth_headers, monkeypatch):
    segment = {
        "index": 1,
        "weeks": "1-2",
        "topic": "Дроби",
        "objectives": "Научиться складывать дроби",
        "hours": 4,
        "materials_hint": "",
    }
    generate = AsyncMock(return_value=Roadmap(
        teacher_id="1", title="Название модели", subject="math", grade=3,
        prompt="План по дробям", content={"segments": [segment]},
    ))
    monkeypatch.setattr(roadmaps, "generate_roadmap", generate)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers=auth_headers(1)) as client:
        created = await client.post("/roadmaps", json={
            "title": "План учителя", "subject": "math", "grade": 3,
            "prompt": "План по дробям",
        })
        assert created.status_code == 201, created.text
        roadmap_id = created.json()["id"]
        assert created.json()["title"] == "План учителя"
        assert len((await client.get("/roadmaps")).json()) == 1
        assert (await client.get(f"/roadmaps/{roadmap_id}")).status_code == 200

        for bad_content in ({"segments": "bad"}, {"segments": ["bad"]}):
            response = await client.patch(f"/roadmaps/{roadmap_id}", json={"content": bad_content})
            assert response.status_code == 422, response.text

        updated = await client.patch(f"/roadmaps/{roadmap_id}", json={
            "content": {"segments": [{**segment, "topic": "Новая тема", "materials_hint": None}]}
        })
        assert updated.status_code == 422  # Invalid materials remain invalid.

        updated = await client.patch(f"/roadmaps/{roadmap_id}", json={
            "content": {"segments": [{k: v for k, v in segment.items() if k != "materials_hint"}]}
        })
        assert updated.status_code == 200, updated.text
        assert updated.json()["content"]["segments"][0]["materials_hint"] == ""

    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers=auth_headers(2)) as client:
        assert (await client.get("/roadmaps")).json() == []


@pytest.mark.asyncio
async def test_tenant_isolation(sessions, auth_headers):
    async with sessions() as session:
        roadmap = Roadmap(
            teacher_id="1", title="Частный план", subject="math", grade=3,
            prompt="План для третьего класса",
            content={"segments": [{
                "index": 1, "weeks": "1-2", "topic": "Счёт",
                "objectives": "Считать", "hours": 4, "materials_hint": "",
            }]},
        )
        session.add(roadmap)
        await session.commit()
        roadmap_id = roadmap.id

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers=auth_headers(2)) as client:
        assert (await client.get("/roadmaps")).json() == []
        assert (await client.get(f"/roadmaps/{roadmap_id}")).status_code == 404
        assert (await client.patch(f"/roadmaps/{roadmap_id}", json={"title": "Чужой"})).status_code == 404
        assert (await client.patch(f"/roadmaps/{roadmap_id}/segments/1", json={"refine_prompt": "Новая тема"})).status_code == 404
        assert (await client.delete(f"/roadmaps/{roadmap_id}")).status_code == 404
        assert (await client.get(f"/roadmaps/{roadmap_id}/export?format=txt")).status_code == 404
