from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor .env to the backend root so imports work regardless of cwd.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"), env_file_encoding="utf-8"
    )

    database_url: str
    redis_url: str

    jwt_secret: str
    jwt_expires_minutes: int = 1440

    # Single-user bootstrap credentials (ADR-001, ADR-013)
    admin_email: str
    admin_password: str


settings = Settings()
