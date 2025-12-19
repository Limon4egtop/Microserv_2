import uuid
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

def get_or_create_request_id(request: Request) -> str:
    rid = request.headers.get(REQUEST_ID_HEADER)
    if rid and len(rid) <= 128:
        return rid
    return str(uuid.uuid4())

def set_request_id(response: Response, request_id: str) -> None:
    response.headers[REQUEST_ID_HEADER] = request_id
