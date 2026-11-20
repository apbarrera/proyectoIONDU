"""Empresa y rol del usuario desde su token y usuario_empresa (necesitan TEST_DATABASE_URL)."""

import uuid

import pytest

from app.api.deps import Contexto, requiere_administrador
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.models.rol import ADMINISTRADOR, OPERATIVO
from tests.conftest import con_token as _con_token


@pytest.fixture(autouse=True)
def _sesion(supabase_falso):
    """Todas las pruebas de este archivo usan el "Supabase falso" (fixture en conftest)."""


# ---------- /api/me ----------
def test_me_devuelve_el_perfil_que_espera_el_frontend(client, empresas, nuevo_usuario):
    a, _ = empresas
    usuario = nuevo_usuario(a)
    response = client.get("/api/me", headers=_con_token(usuario))
    assert response.status_code == 200
    assert response.json() == {
        "id": str(usuario),
        "email": "ana@empresa.ec",
        "fullName": "Ana Torres",
        "role": "admin",
        "tenantId": a,
        "active": True,
    }


def test_un_operativo_tiene_rol_operator(client, empresas, nuevo_usuario):
    a, _ = empresas
    usuario = nuevo_usuario(a, rol=OPERATIVO)
    assert client.get("/api/me", headers=_con_token(usuario)).json()["role"] == "operator"


@pytest.mark.parametrize("estado", [None, "INACTIVO"])  # None: sin empresa asignada
def test_sin_empresa_o_inactivo_responde_403(client, empresas, nuevo_usuario, estado):
    a, _ = empresas
    usuario = uuid.uuid4() if estado is None else nuevo_usuario(a, estado=estado)
    response = client.get("/api/products", headers=_con_token(usuario))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NO_COMPANY"


def test_me_sin_token_no_sirve_con_el_encabezado_de_desarrollo(client, empresas):
    a, _ = empresas
    assert client.get("/api/me", headers={"X-Empresa-Id": str(a)}).status_code == 401


# ---------- Selección de empresa ----------
def test_lista_sus_empresas_activas_sin_haber_elegido_una(
    client, empresas, nuevo_usuario, agregar_pertenencia
):
    a, b = empresas
    usuario = nuevo_usuario(a)
    agregar_pertenencia(usuario, b, rol=OPERATIVO)

    response = client.get("/api/me/companies", headers=_con_token(usuario))

    assert response.status_code == 200
    assert response.json() == [
        {"id": a, "name": "Empresa A", "tradeName": None, "ruc": "0990000000001", "role": "admin"},
        {
            "id": b,
            "name": "Empresa B",
            "tradeName": None,
            "ruc": "0990000000002",
            "role": "operator",
        },
    ]


def test_la_lista_de_empresas_no_incluye_las_inactivas_ni_sirve_sin_token(
    client, empresas, nuevo_usuario, agregar_pertenencia
):
    a, b = empresas
    usuario = nuevo_usuario(a)
    agregar_pertenencia(usuario, b, estado="INACTIVO")
    assert [
        e["id"] for e in client.get("/api/me/companies", headers=_con_token(usuario)).json()
    ] == [a]
    assert client.get("/api/me/companies", headers={"X-Empresa-Id": str(a)}).status_code == 401


def test_usuario_con_varias_empresas_debe_seleccionar_una(
    client, empresas, nuevo_usuario, agregar_pertenencia
):
    a, b = empresas
    usuario = nuevo_usuario(a)
    agregar_pertenencia(usuario, b)

    response = client.get("/api/product-categories", headers=_con_token(usuario))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "COMPANY_SELECTION_REQUIRED"


def test_usuario_puede_cambiar_entre_sus_empresas(
    client, empresas, nuevo_usuario, agregar_pertenencia
):
    a, b = empresas

    # Crear datos independientes en cada empresa usando el modo desarrollo.
    client.post(
        "/api/product-categories",
        json={"name": "De A"},
        headers={"X-Empresa-Id": str(a)},
    )
    client.post(
        "/api/product-categories",
        json={"name": "De B"},
        headers={"X-Empresa-Id": str(b)},
    )

    usuario = nuevo_usuario(a)
    agregar_pertenencia(usuario, b)

    categorias_a = client.get(
        "/api/product-categories",
        headers=_con_token(usuario, **{"X-Empresa-Id": str(a)}),
    )
    categorias_b = client.get(
        "/api/product-categories",
        headers=_con_token(usuario, **{"X-Empresa-Id": str(b)}),
    )

    assert categorias_a.status_code == 200
    assert [c["name"] for c in categorias_a.json()] == ["De A"]

    assert categorias_b.status_code == 200
    assert [c["name"] for c in categorias_b.json()] == ["De B"]


def test_el_rol_corresponde_a_la_empresa_seleccionada(
    client, empresas, nuevo_usuario, agregar_pertenencia
):
    a, b = empresas
    usuario = nuevo_usuario(a, rol=ADMINISTRADOR)
    agregar_pertenencia(usuario, b, rol=OPERATIVO)

    respuesta_a = client.get(
        "/api/me",
        headers=_con_token(usuario, **{"X-Empresa-Id": str(a)}),
    )
    respuesta_b = client.get(
        "/api/me",
        headers=_con_token(usuario, **{"X-Empresa-Id": str(b)}),
    )

    assert respuesta_a.status_code == 200
    assert respuesta_a.json()["role"] == "admin"
    assert respuesta_a.json()["tenantId"] == a

    assert respuesta_b.status_code == 200
    assert respuesta_b.json()["role"] == "operator"
    assert respuesta_b.json()["tenantId"] == b


def test_no_puede_seleccionar_una_empresa_sin_pertenencia_activa(
    client, empresas, nuevo_usuario, agregar_pertenencia
):
    a, b = empresas
    usuario = nuevo_usuario(a)

    # La pertenencia a B existe, pero está inactiva.
    agregar_pertenencia(usuario, b, estado="INACTIVO")

    response = client.get(
        "/api/product-categories",
        headers=_con_token(usuario, **{"X-Empresa-Id": str(b)}),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "COMPANY_ACCESS_DENIED"


def test_con_token_funciona_tambien_en_produccion(client, empresas, nuevo_usuario, monkeypatch):
    a, _ = empresas
    usuario = nuevo_usuario(a)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        con_token = client.get("/api/product-categories", headers=_con_token(usuario))
        solo_encabezado = client.get("/api/product-categories", headers={"X-Empresa-Id": str(a)})
    finally:
        get_settings.cache_clear()
    assert con_token.status_code == 200
    assert solo_encabezado.status_code == 401


# ---------- Permisos por rol ----------
def test_solo_el_administrador_pasa_requiere_administrador():
    assert requiere_administrador(Contexto(empresa_id=1, rol=ADMINISTRADOR)).es_administrador
    with pytest.raises(ForbiddenError, match="solo para administradores"):
        requiere_administrador(Contexto(empresa_id=1, rol=OPERATIVO))


# ---------- Usuario demo (solo desarrollo, para Swagger) ----------
def _demo(usuario, empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id), "X-Usuario-Id": str(usuario)}


def test_usuario_demo_actua_con_su_rol_real(client, empresas, nuevo_usuario):
    a, _ = empresas
    operador = nuevo_usuario(a, rol=OPERATIVO)
    perfil = client.get("/api/me", headers=_demo(operador, a))
    assert perfil.status_code == 200
    assert (perfil.json()["id"], perfil.json()["role"]) == (str(operador), "operator")
    # Es Operativo de verdad: no entra a lo exclusivo del Administrador.
    response = client.put("/api/company", json={"tradeName": "X"}, headers=_demo(operador, a))
    assert response.status_code == 403


def test_usuario_demo_sin_pertenencia_a_la_empresa(client, empresas, nuevo_usuario):
    a, b = empresas
    usuario = nuevo_usuario(a)
    for headers in (_demo(usuario, b), _demo(uuid.uuid4(), a)):
        response = client.get("/api/me", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "COMPANY_ACCESS_DENIED"


def test_usuario_demo_no_existe_en_produccion(client, empresas, nuevo_usuario, monkeypatch):
    a, _ = empresas
    usuario = nuevo_usuario(a)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        response = client.get("/api/me", headers=_demo(usuario, a))
    finally:
        get_settings.cache_clear()
    assert response.status_code == 401
