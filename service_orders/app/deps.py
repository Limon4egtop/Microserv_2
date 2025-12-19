from __future__ import annotations
from typing import Generator
from fastapi import Header
from sqlalchemy.orm import Session
from sqlalchemy import select
import httpx

from common.config import settings
from common.auth import get_bearer_token, decode_token, JwtError
from common.responses import fail
from .db import make_engine, make_session_factory
from .models import Order

engine = make_engine(settings.database_url)
SessionLocal = make_session_factory(engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AuthUser:
    def __init__(self, user_id: str, roles: list[str]):
        self.user_id = user_id
        self.roles = roles

def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    token = get_bearer_token(authorization)
    if not token:
        raise fail("UNAUTHORIZED", "Missing bearer token", 401)
    try:
        payload = decode_token(
            token=token,
            secret=settings.jwt_secret,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        return AuthUser(user_id=payload["sub"], roles=payload.get("roles", []))
    except JwtError:
        raise fail("UNAUTHORIZED", "Invalid token", 401)

async def ensure_user_exists(user_id: str, request_id: str | None = None) -> bool:
    if settings.disable_user_check:
        return True
    # Service-to-service check (prepare for future broker, but now direct call)
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{settings.users_service_url}/v1/users/internal/{user_id}", headers=headers)
        return r.status_code == 200

def can_access_order(auth: AuthUser, order: Order) -> bool:
    if order.user_id == auth.user_id:
        return True
    if "admin" in auth.roles:
        return True
    return False
