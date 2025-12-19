from __future__ import annotations
from typing import Generator

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from common.config import settings
from common.auth import get_bearer_token, decode_token, JwtError
from common.responses import fail
from .db import make_engine, make_session_factory
from .models import User
from sqlalchemy import select

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

def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if "admin" not in user.roles:
        raise fail("FORBIDDEN", "Admin role required", 403)
    return user

def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.id == user_id))
