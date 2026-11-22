from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MES_", env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://postgres@127.0.0.1:5432/mes"
    work_order_transfer_enabled: bool = True
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    jwt_secret: SecretStr = SecretStr("")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    seed_admin_password: SecretStr = SecretStr("admin123")


@lru_cache
def settings() -> Settings:
    return Settings()
