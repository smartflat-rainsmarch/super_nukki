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
        "DATABASE_URL", "sqlite:///./ui2psd_dev.db"
    )
    redis_url: str = _require_env("REDIS_URL", "redis://localhost:6379/0")
    storage_path: str = "./storage"
    max_upload_size_mb: int = 20
    max_upload_chunk_size: int = 1024 * 1024
    allowed_extensions: set[str] = {"png", "jpg", "jpeg", "webp"}

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/callback?provider=google"

    # Kakao OAuth
    kakao_client_id: str = ""
    kakao_client_secret: str = ""
    kakao_redirect_uri: str = "http://localhost:3000/auth/callback?provider=kakao"

    # AI Inpainting
    lama_model_path: str = "./models/lama/big-lama"
    lama_device: str = "cpu"

    # SMTP (Gmail)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    model_config = ConfigDict(env_file=".env")


settings = Settings()
