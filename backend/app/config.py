from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else PROJECT_ROOT / value


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "8000"))
    web_origin: str = os.getenv("WEB_ORIGIN", "http://localhost:5174")
    token_secret: str = os.getenv("TOKEN_SECRET", "development-secret-change-me")
    token_ttl_minutes: int = int(os.getenv("TOKEN_TTL_MINUTES", "480"))
    database_path: Path = _path_env("DATABASE_PATH", ".data/docuflux.db")
    upload_directory: Path = _path_env("UPLOAD_DIRECTORY", ".data/uploads")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "12"))
    worker_enabled: bool = _bool_env("PIPELINE_WORKER_ENABLED", True)
    worker_poll_interval: float = float(os.getenv("PIPELINE_POLL_INTERVAL", "0.5"))
    pipeline_stage_delay: float = float(os.getenv("PIPELINE_STAGE_DELAY", "0.12"))
    remote_ai_url: str | None = os.getenv("REMOTE_AI_URL")
    remote_ai_token: str | None = os.getenv("REMOTE_AI_TOKEN")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024
