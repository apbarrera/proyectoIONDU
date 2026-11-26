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
    # Conexión exclusiva de la autenticación (rol iondu_auth): login, renovación, cierre y
    # cambio de contraseña. Es el único rol que lee hashes de contraseñas y sesiones.
    auth_database_url: str | None = None
    migration_database_url: str | None = None

    # Almacenamiento de archivos por la API S3: SeaweedFS en local, Supabase Storage (su
    # endpoint S3) u otro proveedor compatible en producción. Sin endpoint, no hay RIDE.
    storage_endpoint_url: str | None = None
    storage_region: str = "us-east-1"
    storage_access_key_id: str | None = None
    storage_secret_access_key: SecretStr | None = None
    storage_bucket: str = "rides"

    master_encryption_key: SecretStr | None = None

    # Facturación de demostración sin .p12 (app/sri/simulado.py): ids de empresa separados
    # por comas, p. ej. SRI_SIMULADO_EMPRESAS=1. Solo actúa si la empresa está en ambiente
    # de PRUEBAS; en producción se ignora. Se quita cuando la empresa sube su .p12.
    sri_simulado_empresas: Annotated[frozenset[int], NoDecode] = Field(default_factory=frozenset)

    @field_validator("sri_simulado_empresas", mode="before")
    @classmethod
    def _split_sri_simulado(cls, value: object) -> object:
        if isinstance(value, str):
            return frozenset(int(item) for item in value.split(",") if item.strip())
        return value

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
    # Voz a texto (RF-6.4): API de OpenAI /v1/audio/transcriptions. En local, el servicio
    # "stt" (Whisper) de docker-compose.override.yml. Vacío: el agente no acepta audio.
    stt_base_url: str | None = None
    stt_model: str = "Systran/faster-whisper-small"
    stt_api_key: SecretStr | None = None

    # Inicio de sesión propio: llave privada EC P-256 (PEM) que firma los tokens de acceso (ES256).
    # En .env puede escribirse en una línea, con "\n" en lugar de los saltos de línea.
    auth_jwt_private_key: SecretStr | None = None
    auth_access_token_minutes: int = Field(default=15, gt=0)
    auth_refresh_token_days: int = Field(default=7, gt=0)

    # Correo saliente (recuperación de contraseña e invitaciones). Cualquier SMTP: en local,
    # Mailpit (docker-compose.override.yml); en producción, el proveedor que se contrate.
    # Sin SMTP_HOST no se envían correos y los usuarios se crean con contraseña temporal.
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, gt=0)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_from: str = "IONDU <no-responder@iondu.ec>"
    # Dirección pública de la app, para los enlaces de los correos (sin "/" final).
    app_public_url: str = "http://localhost:8080"

    # Cada cuánto el worker lee los buzones de correo de facturas (RF-3.2).
    imap_intervalo_segundos: int = Field(default=300, ge=30)

    worker_heartbeat_file: str = "/tmp/worker-heartbeat"
    worker_tick_seconds: int = Field(default=30, gt=0)

    @field_validator(
        "database_url",
        "worker_database_url",
        "auth_database_url",
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
        "auth_database_url",
        "migration_database_url",
        "storage_endpoint_url",
        "storage_access_key_id",
        "storage_secret_access_key",
        "llm_base_url",
        "llm_api_key",
        "llm_vision_model",
        "stt_base_url",
        "stt_api_key",
        "smtp_host",
        "smtp_username",
        "smtp_password",
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
