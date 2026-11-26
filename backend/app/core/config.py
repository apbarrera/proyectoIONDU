from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

TIMEZONE = "America/Guayaquil"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=False,
        extra="ignore",
    )

    app_env: str = "production"
    dev_user_id: UUID | None = None
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

    # PostgreSQL. En Supabase: Session Pooler (puerto 5432).
    database_url: str | None = None
    worker_database_url: str | None = None
    migration_database_url: str | None = None

    # Almacenamiento de archivos por la API S3: SeaweedFS en local, Supabase Storage (su
    # endpoint S3) u otro proveedor compatible en producción. Sin endpoint, no hay RIDE.
    storage_endpoint_url: str | None = None
    storage_region: str = "us-east-1"
    storage_access_key_id: str | None = None
    storage_secret_access_key: SecretStr | None = None
    storage_bucket: str = "rides"

    master_encryption_key: SecretStr | None = None

    # Agente de IA: cualquier servicio con la API de OpenAI (/v1/chat/completions).
    # En local, Ollama: LLM_BASE_URL=http://host.docker.internal:11434/v1 y sin clave.
    # Sin LLM_BASE_URL el agente responde que no está configurado.
    llm_base_url: str | None = None
    llm_model: str = "qwen2.5:7b"
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: int = Field(default=120, gt=0)
    # Modelo con visión para leer fotos de facturas y tickets (en local, qwen2.5vl:7b).
    # Usa el mismo servicio que LLM_BASE_URL. Vacío: el agente no acepta imágenes.
    llm_vision_model: str | None = None

    # Inicio de sesión propio: llave privada EC P-256 (PEM) que firma los tokens de acceso (ES256).
    # En .env puede escribirse en una línea, con "\n" en lugar de los saltos de línea.
    auth_jwt_private_key: SecretStr | None = None
    auth_access_token_minutes: int = Field(default=15, gt=0)
    auth_refresh_token_days: int = Field(default=7, gt=0)

    worker_heartbeat_file: str = "/tmp/worker-heartbeat"
    worker_tick_seconds: int = Field(default=30, gt=0)

    @field_validator(
        "database_url",
        "worker_database_url",
        "migration_database_url",
        mode="before",
    )
    @classmethod
    def _normalize_postgresql_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://") :]

        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]

        return value

    @field_validator(
        "database_url",
        "worker_database_url",
        "migration_database_url",
        "storage_endpoint_url",
        "storage_access_key_id",
        "storage_secret_access_key",
        "llm_base_url",
        "llm_api_key",
        "auth_jwt_private_key",
        "dev_user_id",
        mode="before",
    )
    @classmethod
    def _empty_strings_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
