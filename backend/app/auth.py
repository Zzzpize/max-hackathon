import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from app.config import settings


def current_teacher(x_init_data: str | None = Header(default=None)) -> str:
    unauthorized = HTTPException(status_code=401, detail="Invalid MAX initData")
    if not x_init_data or not settings.max_bot_token:
        raise unauthorized

    try:
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
    except (KeyError, TypeError, ValueError):
        raise unauthorized from None
