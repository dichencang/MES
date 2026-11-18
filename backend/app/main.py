from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.config.database import engine
from app.config.settings import settings
from app.routers.auth import router
from app.routers.changes import router as changes_router
from app.routers.management import router as management_router
from app.routers.system import router as system_router
from app.services.auth import secret
from app.utils.responses import ApiError, api_error_handler, validation_error_handler


@asynccontextmanager
async def lifespan(app):
    secret()
    async with Redis.from_url(
        settings().redis_url.get_secret_value(), socket_connect_timeout=2, socket_timeout=2,
    ) as redis:
        app.state.redis = redis
        try:
            yield
        finally:
            await engine.dispose()


app = FastAPI(title="MES 后端", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.exception_handler(Exception)
async def unexpected_error(request, error):
    logging.getLogger(__name__).error("Unexpected API error", exc_info=error)
    return JSONResponse(
        status_code=500,
        content={"code": 9001, "message": "服务端错误", "data": None},
    )


app.include_router(router)
app.include_router(system_router)
app.include_router(management_router)
app.include_router(changes_router)
