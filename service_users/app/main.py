from __future__ import annotations

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from common.config import settings
from common.responses import ok, fail
from common.logging import setup_logging, get_logger
from common.tracing import setup_tracing

from .db import Base
from .deps import engine, get_db, get_current_user, require_admin, get_user_by_id, AuthUser
from .models import User
from .schemas import RegisterRequest, LoginRequest, UpdateProfileRequest
from .security import hash_password, verify_password
from common.auth import create_token

setup_logging("service_users")
setup_tracing("service_users", settings.otel_service_namespace, settings.otel_exporter_otlp_endpoint)

Base.metadata.create_all(bind=engine)
SQLAlchemyInstrumentor().instrument(engine=engine)

app = FastAPI(title="Service Users", version="1.0.0", openapi_url="/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")] if settings.cors_allow_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)
log = get_logger("service_users")

@app.post("/v1/users/register")
def register(payload: RegisterRequest, db=Depends(get_db)):
    user = User(email=payload.email, password_hash=hash_password(payload.password), name=payload.name, roles="user")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return fail("EMAIL_EXISTS", "User with this email already exists", 409)
    db.refresh(user)
    return ok(user.to_public())

@app.post("/v1/users/login")
def login(payload: LoginRequest, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        return fail("INVALID_CREDENTIALS", "Invalid email or password", 401)
    token = create_token(
        user_id=user.id,
        roles=user.roles_list(),
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        exp_minutes=settings.jwt_exp_minutes,
    )
    return ok({"token": token})

@app.get("/v1/users/me")
def me(auth: AuthUser = Depends(get_current_user), db=Depends(get_db)):
    user = get_user_by_id(db, auth.user_id)
    if not user:
        return fail("NOT_FOUND", "User not found", 404)
    return ok(user.to_public())

@app.put("/v1/users/me")
def update_me(payload: UpdateProfileRequest, auth: AuthUser = Depends(get_current_user), db=Depends(get_db)):
    user = get_user_by_id(db, auth.user_id)
    if not user:
        return fail("NOT_FOUND", "User not found", 404)
    if payload.name is not None:
        user.name = payload.name
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok(user.to_public())

@app.get("/v1/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    email: str | None = Query(default=None),
    _: AuthUser = Depends(require_admin),
    db=Depends(get_db)
):
    q = select(User)
    if email:
        q = q.where(User.email.ilike(f"%{email}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.offset((page-1)*page_size).limit(page_size)).all()
    return ok({
        "items": [u.to_public() for u in items],
        "page": page,
        "page_size": page_size,
        "total": int(total or 0),
    })

@app.get("/v1/users/internal/{user_id}")
def internal_user_exists(user_id: str, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        return fail("NOT_FOUND", "User not found", 404)
    return ok({"exists": True, "id": user.id})
