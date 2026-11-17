from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def success(data=None):
    return {"code": 0, "message": "ok", "data": data}


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


async def api_error_handler(request: Request, error: ApiError):
    return JSONResponse(
        status_code=error.status,
        content={"code": error.code, "message": error.message, "data": None},
    )


async def validation_error_handler(request: Request, error: RequestValidationError):
    errors = [
        {"field": ".".join(map(str, item["loc"][1:])), "message": "参数无效"}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={"code": 1001, "message": "参数校验失败", "data": {"errors": errors}},
    )
