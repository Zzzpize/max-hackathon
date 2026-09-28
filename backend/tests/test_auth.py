import time

import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_max_init_data_required_and_verified(sessions, auth_headers):
    valid = auth_headers(42)["X-Init-Data"]
    expired = auth_headers(42, int(time.time()) - 3601)["X-Init-Data"]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/works")).status_code == 401
        assert (await client.get("/works", headers={"X-Init-Data": valid})).json() == []
        created = await client.post(
            "/works",
            headers={"X-Init-Data": valid},
            json={"teacher_id": "999", "title": "Test", "grade": 2, "tasks": []},
        )
        assert created.status_code == 201
        assert created.json()["teacher_id"] == "42"
        assert len((await client.get(
            "/works?teacher_id=999", headers={"X-Init-Data": valid}
        )).json()) == 1
        assert (await client.get("/works", headers={"X-Init-Data": valid + "&start_param=changed"})).status_code == 401
        assert (await client.get("/works", headers={"X-Init-Data": expired})).status_code == 401
        assert (await client.get("/works", headers={"X-Init-Data": valid + "&user=other"})).status_code == 401
        assert (await client.get("/health")).status_code == 200
