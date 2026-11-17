from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import engine
from app.config.settings import settings
from app.routers.auth import router
from app.routers.system import router as system_router
from app.services.auth import secret
from app.utils.responses import ApiError, api_error_handler, validation_error_handler


@asynccontextmanager
async def lifespan(app):
    secret()
    yield
    await engine.dispose()


app = FastAPI(title="MES 后端", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.include_router(router)
app.include_router(system_router)
