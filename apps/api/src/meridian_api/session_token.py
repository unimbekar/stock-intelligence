from __future__ import annotations

import hmac
import time
from hashlib import sha256

from meridian_config.settings import get_settings


def issue_token(user_id: str, ttl_seconds: int = 7 * 24 * 3600) -> str:
    expires = int(time.time()) + ttl_seconds
    body = f"{user_id}|{expires}"
    signature = hmac.new(get_settings().secret_key.encode(), body.encode(), sha256).hexdigest()
    return f"{body}|{signature}"


def read_token(token: str) -> str | None:
    try:
        user_id, expires, signature = token.split("|", 2)
        expires_at = int(expires)
    except ValueError:
        return None
    if expires_at < int(time.time()):
        return None
    body = f"{user_id}|{expires}"
    expected = hmac.new(get_settings().secret_key.encode(), body.encode(), sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    return user_id
