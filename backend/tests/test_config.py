from app.core.config import Settings

def test_cors_origins_se_lee_separado_por_comas(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:4200, https://app.iondu.org")
    assert Settings().cors_origins == ["http://localhost:4200", "https://app.iondu.org"]

def test_variables_vacias_usan_el_valor_por_defecto(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("DATABASE_URL", "")
    settings = Settings()
    assert settings.cors_origins == []
    assert settings.database_url is None


def test_urls_independientes_de_worker_y_migraciones(monkeypatch):
    monkeypatch.setenv(
        "WORKER_DATABASE_URL",
        "postgresql+psycopg://worker:fake@localhost/iondu",
    )
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL",
        "postgresql+psycopg://migrator:fake@localhost/iondu",
    )

    settings = Settings()

    assert settings.worker_database_url.startswith(
        "postgresql+psycopg://worker:"
    )
    assert settings.migration_database_url.startswith(
        "postgresql+psycopg://migrator:"
    )
