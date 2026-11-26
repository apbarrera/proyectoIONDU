"""Validación de credenciales de scripts/configurar_roles_locales.py (sin base de datos)."""

import pytest

from scripts.configurar_roles_locales import validar_credenciales


def _urls(app="clave-app-2026", auth="clave-auth-2026", worker="clave-worker-2026", **cambios):
    base = {
        "DATABASE_URL": f"postgresql+psycopg://iondu_app:{app}@db:5432/iondu",
        "AUTH_DATABASE_URL": f"postgresql+psycopg://iondu_auth:{auth}@db:5432/iondu",
        "WORKER_DATABASE_URL": f"postgresql+psycopg://iondu_worker:{worker}@db:5432/iondu",
    }
    return base | cambios


def test_acepta_una_contrasena_distinta_por_rol():
    assert validar_credenciales(_urls(), "clave-admin-2026") == {
        "iondu_app": "clave-app-2026",
        "iondu_auth": "clave-auth-2026",
        "iondu_worker": "clave-worker-2026",
    }


@pytest.mark.parametrize(
    ("urls", "mensaje"),
    (
        (_urls(AUTH_DATABASE_URL=None), "Define AUTH_DATABASE_URL"),
        (
            _urls(DATABASE_URL="postgresql+psycopg://iondu_auth:clave-larga-2026@db/iondu"),
            "DATABASE_URL debe usar el usuario iondu_app",
        ),
        (_urls(app="corta"), "al menos 12"),
        (_urls(worker="<otra clave>-2026"), "marcador"),
        (_urls(auth="clave-app-2026"), "distinta"),
        (_urls(app="clave-admin-2026"), "administrador"),
    ),
)
def test_rechaza_credenciales_inseguras_o_mal_asignadas(urls, mensaje):
    with pytest.raises(SystemExit, match=mensaje):
        validar_credenciales(urls, "clave-admin-2026")
