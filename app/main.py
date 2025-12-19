from __future__ import annotations

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.datastructures import Headers
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from common.config import settings
from common.http import get_or_create_request_id, set_request_id, REQUEST_ID_HEADER
from common.auth import get_bearer_token, decode_token, JwtError
from common.responses import fail
from common.logging import setup_logging, get_logger
from common.tracing import setup_tracing

setup_logging("api_gateway")
setup_tracing("api_gateway", settings.otel_service_namespace, settings.otel_exporter_otlp_endpoint)
HTTPXClientInstrumentor().instrument()

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

app = FastAPI(title="API Gateway", version="1.0.0", openapi_url="/openapi.json")
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, lambda r, e: JSONResponse(
    status_code=429,
    content={"success": False, "error": {"code": "RATE_LIMIT", "message": "Too many requests"}},
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")] if settings.cors_allow_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)
log = get_logger("api_gateway")

PUBLIC_PATHS = {
    ("POST", "/v1/users/register"),
    ("POST", "/v1/users/login"),
    ("GET", "/health"),
}

def is_protected(method: str, path: str) -> bool:
    if (method.upper(), path) in PUBLIC_PATHS:
        return False
    # everything under /v1/users/* except register/login is protected
    if path.startswith("/v1/users"):
        return True
    if path.startswith("/v1/orders"):
        return True
    return False

def verify_jwt_from_request(request: Request) -> dict | None:
    token = get_bearer_token(request.headers.get("Authorization"))
    if not token:
        return None
    try:
        return decode_token(token=token, secret=settings.jwt_secret, issuer=settings.jwt_issuer, audience=settings.jwt_audience)
    except JwtError:
        return None

async def proxy(request: Request, upstream_base: str) -> Response:
    request_id = get_or_create_request_id(request)

    if is_protected(request.method, request.url.path):
        payload = verify_jwt_from_request(request)
        if not payload:
            return fail("UNAUTHORIZED", "Missing or invalid token", 401)

    # Build upstream URL
    upstream_url = f"{upstream_base}{request.url.path}"
    if request.url.query:
        upstream_url += f"?{request.url.query}"

    # Forward headers (avoid hop-by-hop)
    headers = dict(request.headers)
    headers[REQUEST_ID_HEADER] = request_id
    headers.pop("host", None)

    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream_resp = await client.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            content=body,
        )

    response = Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        media_type=upstream_resp.headers.get("content-type"),
    )
    # Propagate request id back
    set_request_id(response, request_id)
    return response

@app.get("/health")
def health():
    return {"success": True, "data": {"status": "ok", "env": settings.app_env}}

# Users proxy
@app.api_route("/v1/users/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@limiter.limit(settings.rate_limit)
async def users_proxy(path: str, request: Request):
    return await proxy(request, settings.users_service_url)

# Orders proxy
@app.api_route("/v1/orders/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@limiter.limit(settings.rate_limit)
async def orders_proxy(path: str, request: Request):
    return await proxy(request, settings.orders_service_url)

# Root helpers
@app.get("/")
def root():
    return {"success": True, "data": {"message": "API Gateway. Use /docs for Swagger UI."}}
