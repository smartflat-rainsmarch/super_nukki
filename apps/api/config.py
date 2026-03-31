import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


def _require_env(key: str, default_for_dev: str) -> str:
    value = os.getenv(key)
    if value:
        return value
    if os.getenv("ENV", "development") == "development":
        return default_for_dev
    raise ValueError(f"{key} environment variable is required in production")


class Settings(BaseSettings):
    database_url: str = _require_env(
        "DATABASE_URL", "postgresql://ui2psd:devpassword@localhost:5432/ui2psd"
    )
    redis_url: str = _require_env("REDIS_URL", "redis://localhost:6379/0")
    storage_path: str = "./storage"
    max_upload_size_mb: int = 20
    max_upload_chunk_size: int = 1024 * 1024
    allowed_extensions: set[str] = {"png", "jpg", "jpeg", "webp"}

    model_config = ConfigDict(env_file=".env")


settings = Settings()
