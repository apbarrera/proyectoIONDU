from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

TIMEZONE = "America/Guayaquil"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: str = "production"
    log_level: str = "info"

    # Solo para desarrollo con `ng serve` (en producción todo es mismo origen).
    # Se escribe separado por comas: CORS_ORIGINS=http://localhost:4200,https://app.iondu.org
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # Supabase: conexión por Session Pooler (puerto 5432).
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    master_encryption_key: SecretStr | None = None

    worker_heartbeat_file: str = "/tmp/worker-heartbeat"
    worker_tick_seconds: int = 30

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
