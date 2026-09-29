from unittest.mock import AsyncMock

import httpx
import pytest

from app.main import app
from app.models import Roadmap
from app.routers import roadmaps


@pytest.mark.asyncio
async def test_txt_and_pdf(sessions, auth_headers, monkeypatch):
    segment = {
        "index": 1, "weeks": "1-2", "topic": "Дроби",
        "objectives": "Складывать дроби", "hours": 4, "materials_hint": "",
    }
    monkeypatch.setattr(roadmaps, "generate_roadmap", AsyncMock(return_value=Roadmap(
        teacher_id="1", title="План по дробям", subject="math", grade=3,
        prompt="План по дробям", content={"segments": [segment]},
    )))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers=auth_headers(1),
    ) as client:
        created = await client.post("/roadmaps", json={
            "subject": "math", "grade": 3, "prompt": "План по дробям",
        })
        assert created.status_code == 201, created.text
        roadmap_id = created.json()["id"]
        txt = await client.get(f"/roadmaps/{roadmap_id}/export?format=txt")
        assert txt.status_code == 200
        assert txt.headers["content-type"].startswith("text/plain")
        assert "Дроби" in txt.content.decode("utf-8")
        assert "filename*=UTF-8''roadmap-" in txt.headers["content-disposition"]

        pdf = await client.get(f"/roadmaps/{roadmap_id}/export?format=pdf")
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF-") and b"%%EOF" in pdf.content[-100:]
        assert len(pdf.content) > 1000


@pytest.mark.asyncio
async def test_regenerate_one_segment(sessions, auth_headers, monkeypatch):
    segments = [
        {"index": 1, "weeks": "1-2", "topic": "Счёт", "objectives": "Считать",
         "hours": 4, "materials_hint": ""},
        {"index": 2, "weeks": "3-4", "topic": "Дроби", "objectives": "Складывать дроби",
         "hours": 4, "materials_hint": ""},
    ]
    monkeypatch.setattr(roadmaps, "generate_roadmap", AsyncMock(return_value=Roadmap(
        teacher_id="1", title="Математика", subject="math", grade=3,
        prompt="План по математике", content={"segments": segments},
    )))
    completion = AsyncMock(side_effect=[
        '{"index":2,"weeks":"5-6","topic":"Умножение","objectives":"Умножать","hours":4,"materials_hint":""}',
        '{"index":2,"weeks":"3-4","topic":"Умножение","objectives":"Умножать","hours":4,"materials_hint":""}',
    ])
    monkeypatch.setattr("app.modules.roadmap.pipeline.gigachat_client.chat_completion", completion)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers=auth_headers(1),
    ) as client:
        created = await client.post("/roadmaps", json={
            "subject": "math", "grade": 3, "prompt": "План по математике",
        })
        roadmap_id = created.json()["id"]
        response = await client.patch(
            f"/roadmaps/{roadmap_id}/segments/2", json={"refine_prompt": "Умножение"}
        )
        assert response.status_code == 200, response.text
        updated = response.json()["content"]["segments"]
        assert updated[0] == segments[0]
        assert updated[1]["weeks"] == "3-4"
        assert updated[1]["topic"] == "Умножение"
        assert completion.await_count == 2
        assert (await client.get(f"/roadmaps/{roadmap_id}")).json()["content"]["segments"] == updated
