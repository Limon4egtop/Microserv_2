from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import jwt

class JwtError(Exception):
    pass

def create_token(*, user_id: str, roles: list[str], secret: str, issuer: str, audience: str, exp_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
        "iss": issuer,
        "aud": audience,
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_token(*, token: str, secret: str, issuer: str, audience: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], issuer=issuer, audience=audience)
    except jwt.PyJWTError as e:
        raise JwtError(str(e)) from e

def get_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None
