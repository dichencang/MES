from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def success(data=None):
    return {"code": 0, "message": "ok", "data": data}


class ApiError(Exception):
    def __init__(self, status, code, message, data=None):
        self.status, self.code, self.message = status, code, message
        self.data = data


async def api_error_handler(request: Request, error: ApiError):
    return JSONResponse(
        status_code=error.status,
        content={"code": error.code, "message": error.message, "data": error.data},
    )


async def validation_error_handler(request: Request, error: RequestValidationError):
    def field_path(parts):
        if request.scope["path"].split("/")[1] not in {"materials", "processes", "boms", "routings", "plan", "workorders"}:
            return ".".join(map(str, parts))
        path = ""
        for part in parts:
            if isinstance(part, int):
                path += f"[{part}]"
            else:
                path += f".{part}" if path else part
        return path

    errors = [
        {"field": field_path(item["loc"][1:]), "message": "参数无效"}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={"code": 1001, "message": "参数校验失败", "data": {"errors": errors}},
    )
