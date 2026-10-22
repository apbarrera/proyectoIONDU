from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def test_migraciones_forman_una_sola_cadena():
    # Dos migraciones creadas en paralelo sobre la misma base dejan dos "heads";
    # se resuelve con: alembic merge heads -m "unir migraciones"
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    assert len(script.get_heads()) <= 1, f"Hay varias cabezas: {script.get_heads()}"
