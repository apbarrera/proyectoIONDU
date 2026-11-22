import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_se_lee_separado_por_comas(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:4200, https://app.iondu.org")
    assert Settings().cors_origins == ["http://localhost:4200", "https://app.iondu.org"]


def test_variables_vacias_usan_el_valor_por_defecto(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("WORKER_DATABASE_URL", "")
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "")
    settings = Settings()
    assert settings.cors_origins == []
    assert settings.database_url is None
    assert settings.worker_database_url is None
    assert settings.migration_database_url is None


def test_conexiones_de_api_worker_y_migraciones_son_independientes():
    settings = Settings(
        database_url="postgresql://api.example/iondu",
        worker_database_url="postgres://worker.example/iondu",
        migration_database_url="postgresql+psycopg://admin.example/iondu",
    )

    assert settings.database_url == "postgresql+psycopg://api.example/iondu"
    assert settings.worker_database_url == "postgresql+psycopg://worker.example/iondu"
    assert settings.migration_database_url == "postgresql+psycopg://admin.example/iondu"


@pytest.mark.parametrize(
    "campo",
    ["database_url", "worker_database_url", "migration_database_url"],
)
@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        (
            "postgres://api.example/iondu",
            "postgresql+psycopg://api.example/iondu",
        ),
        (
            "postgresql://api.example/iondu",
            "postgresql+psycopg://api.example/iondu",
        ),
        (
            "postgresql+psycopg://api.example/iondu",
            "postgresql+psycopg://api.example/iondu",
        ),
        (
            "postgresql://usuario:clave@db.example:5432/iondu?sslmode=require",
            "postgresql+psycopg://usuario:clave@db.example:5432/iondu?sslmode=require",
        ),
    ],
)
def test_conexion_postgresql_normaliza_driver_psycopg(campo, entrada, esperada):
    settings = Settings(**{campo: entrada})

    assert getattr(settings, campo) == esperada


def test_worker_tick_seconds_tiene_valor_predeterminado_positivo():
    assert Settings().worker_tick_seconds == 30


@pytest.mark.parametrize("valor", [0, -1, -30])
def test_worker_tick_seconds_rechaza_valores_no_positivos(valor):
    with pytest.raises(ValidationError):
        Settings(worker_tick_seconds=valor)
