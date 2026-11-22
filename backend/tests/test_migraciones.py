from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"

def test_migraciones_forman_una_sola_cadena():
    # Dos migraciones creadas en paralelo sobre la misma base dejan dos "heads";
    # se resuelve con: alembic merge heads -m "unir migraciones"
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    assert len(script.get_heads()) <= 1, f"Hay varias cabezas: {script.get_heads()}"


def test_alembic_exige_url_de_migraciones_independiente():
    env_py = ALEMBIC_INI.parent / "alembic" / "env.py"
    source = env_py.read_text(encoding="utf-8")

    assert "get_settings().migration_database_url" in source
    assert "MIGRATION_DATABASE_URL" in source
    assert "get_settings().database_url" not in source
