from __future__ import annotations

import json
from fastapi import FastAPI, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, desc, asc
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from common.config import settings
from common.responses import ok, fail
from common.logging import setup_logging, get_logger
from common.tracing import setup_tracing

from .db import Base
from .deps import engine, get_db, get_current_user, ensure_user_exists, can_access_order, AuthUser
from .models import Order
from .schemas import CreateOrderRequest, UpdateStatusRequest
from .events import publisher, DomainEvent

setup_logging("service_orders")
setup_tracing("service_orders", settings.otel_service_namespace, settings.otel_exporter_otlp_endpoint)

Base.metadata.create_all(bind=engine)
SQLAlchemyInstrumentor().instrument(engine=engine)
HTTPXClientInstrumentor().instrument()

app = FastAPI(title="Service Orders", version="1.0.0", openapi_url="/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")] if settings.cors_allow_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)
log = get_logger("service_orders")

VALID_STATUSES = {"created", "in_progress", "completed", "cancelled"}

@app.post("/v1/orders")
async def create_order(payload: CreateOrderRequest, auth: AuthUser = Depends(get_current_user), db=Depends(get_db)):
    request_id = None  # gateway forwards X-Request-ID; optional to pass here
    exists = await ensure_user_exists(auth.user_id, request_id=request_id)
    if not exists:
        return fail("USER_NOT_FOUND", "User does not exist", 400)

    order = Order(
        user_id=auth.user_id,
        items_json=json.dumps([i.model_dump() for i in payload.items]),
        status="created",
        total_sum=float(payload.total_sum),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    publisher.publish(DomainEvent(name="order.created", payload={"order_id": order.id, "user_id": auth.user_id}))
    return ok(order.to_public())

@app.get("/v1/orders/{order_id}")
def get_order(order_id: str = Path(...), auth: AuthUser = Depends(get_current_user), db=Depends(get_db)):
    order = db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        return fail("NOT_FOUND", "Order not found", 404)
    if not can_access_order(auth, order):
        return fail("FORBIDDEN", "Not allowed to access this order", 403)
    return ok(order.to_public())

@app.get("/v1/orders")
def list_my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    auth: AuthUser = Depends(get_current_user),
    db=Depends(get_db),
):
    q = select(Order).where(Order.user_id == auth.user_id)
    sort_col = getattr(Order, sort, Order.created_at)
    q = q.order_by(desc(sort_col) if order.lower() == "desc" else asc(sort_col))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.offset((page-1)*page_size).limit(page_size)).all()
    return ok({
        "items": [o.to_public() for o in items],
        "page": page,
        "page_size": page_size,
        "total": int(total or 0),
    })

@app.patch("/v1/orders/{order_id}/status")
def update_status(order_id: str, payload: UpdateStatusRequest, auth: AuthUser = Depends(get_current_user), db=Depends(get_db)):
    order_obj = db.scalar(select(Order).where(Order.id == order_id))
    if not order_obj:
        return fail("NOT_FOUND", "Order not found", 404)
    if not can_access_order(auth, order_obj):
        return fail("FORBIDDEN", "Not allowed", 403)
    if payload.status not in VALID_STATUSES:
        return fail("VALIDATION_ERROR", "Invalid status", 400)
    order_obj.status = payload.status
    db.add(order_obj)
    db.commit()
    db.refresh(order_obj)
    publisher.publish(DomainEvent(name="order.status_updated", payload={"order_id": order_obj.id, "status": order_obj.status}))
    return ok(order_obj.to_public())

@app.post("/v1/orders/{order_id}/cancel")
def cancel_order(order_id: str, auth: AuthUser = Depends(get_current_user), db=Depends(get_db)):
    order_obj = db.scalar(select(Order).where(Order.id == order_id))
    if not order_obj:
        return fail("NOT_FOUND", "Order not found", 404)
    if order_obj.user_id != auth.user_id and "admin" not in auth.roles:
        return fail("FORBIDDEN", "Not allowed to cancel this order", 403)
    if order_obj.status == "cancelled":
        return ok(order_obj.to_public())
    order_obj.status = "cancelled"
    db.add(order_obj)
    db.commit()
    db.refresh(order_obj)
    publisher.publish(DomainEvent(name="order.cancelled", payload={"order_id": order_obj.id}))
    return ok(order_obj.to_public())
