import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from app.config import settings


def _verify_init_data(x_init_data: str) -> str:
    if not settings.max_bot_token:
        raise ValueError("Server not configured for MAX auth")

    pairs = parse_qsl(x_init_data, keep_blank_values=True, strict_parsing=True)
    data = dict(pairs)
    if len(data) != len(pairs) or not data.get("hash"):
        raise ValueError("Missing hash or duplicate parameter")

    signed = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs) if key != "hash"
    )
    secret = hmac.new(
        b"WebAppData", settings.max_bot_token.encode(), hashlib.sha256
    ).digest()
    expected = hmac.new(secret, signed.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, data["hash"]):
        raise ValueError("Invalid signature")

    age = time.time() - int(data["auth_date"])
    if not -60 <= age <= 3600:
        raise ValueError("Expired initData")

    user_id = json.loads(data["user"])["id"]
    if type(user_id) is not int or user_id <= 0:
        raise ValueError("Invalid user id")
    return str(user_id)


def _verify_bot_service_token(
    authorization: str | None, x_teacher_id: str | None
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ValueError("Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not settings.max_bot_token or not hmac.compare_digest(
        token, settings.max_bot_token
    ):
        raise ValueError("Invalid bot service token")
    if not x_teacher_id or not x_teacher_id.strip():
        raise ValueError("Missing X-Teacher-Id")
    try:
        as_int = int(x_teacher_id)
        if as_int <= 0:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Invalid teacher id") from exc
    return str(as_int)


def current_teacher(
    x_init_data: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    x_teacher_id: str | None = Header(default=None),
) -> str:
    """Auth resolves teacher_id from one of two paths.

    MiniApp path: signed `X-Init-Data` from MAX Bridge (HMAC over bot token).
    Bot service path: `Authorization: Bearer <MAX_BOT_TOKEN>` plus
    `X-Teacher-Id` header. Only trusted between compose services; do not
    expose bot token to third parties.
    """
    unauthorized = HTTPException(status_code=401, detail="Unauthorized")

    if x_init_data:
        try:
            return _verify_init_data(x_init_data)
        except (KeyError, TypeError, ValueError):
            raise unauthorized from None

    if authorization:
        try:
            return _verify_bot_service_token(authorization, x_teacher_id)
        except ValueError:
            raise unauthorized from None

    raise unauthorized
