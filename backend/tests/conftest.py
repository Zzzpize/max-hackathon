import sys
import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, get_session  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.check import pipeline  # noqa: E402


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def auth_headers(monkeypatch):
    token = "test-max-bot-token"
    monkeypatch.setattr(settings, "max_bot_token", token)

    def make(user_id: int, auth_date: int | None = None) -> dict[str, str]:
        fields = {
            "auth_date": str(auth_date if auth_date is not None else int(time.time())),
            "user": json.dumps({"id": user_id}, separators=(",", ":")),
        }
        signed = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        fields["hash"] = hmac.new(secret, signed.encode(), hashlib.sha256).hexdigest()
        return {"X-Init-Data": urlencode(fields)}

    return make


@pytest_asyncio.fixture
async def sessions(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    monkeypatch.setattr(pipeline, "SessionLocal", factory)
    try:
        yield factory
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
