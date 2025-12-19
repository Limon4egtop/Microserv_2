from typing import Any
from fastapi.responses import JSONResponse

def ok(data: Any):
    return {"success": True, "data": data}

def fail(code: str, message: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )
