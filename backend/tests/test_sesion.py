"""Empresa y rol del usuario desde su token y usuario_empresa (necesitan TEST_DATABASE_URL)."""

import uuid

import pytest

from app.api.deps import Contexto, get_verificador, requiere_administrador
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.main import app
from app.models import Rol, UsuarioEmpresa
from app.models.rol import ADMINISTRADOR, OPERATIVO
from tests.tokens import crear_token, verificador_de_prueba


@pytest.fixture(autouse=True)
def supabase_falso():
    app.dependency_overrides[get_verificador] = verificador_de_prueba
    yield
    app.dependency_overrides.pop(get_verificador, None)


@pytest.fixture
def roles(db) -> dict[str, int]:
    admin, operativo = Rol(nombre=ADMINISTRADOR), Rol(nombre=OPERATIVO)
    db.add_all([admin, operativo])
    db.flush()
    return {ADMINISTRADOR: admin.id_rol, OPERATIVO: operativo.id_rol}


@pytest.fixture
def nuevo_usuario(db, roles):
    def crear(id_empresa: int, rol: str = ADMINISTRADOR, estado: str = "ACTIVO") -> uuid.UUID:
        usuario = uuid.uuid4()
        db.add(
            UsuarioEmpresa(
                id_usuario=usuario,
                id_empresa=id_empresa,
                id_rol=roles[rol],
                nombre="Ana Torres",
                estado=estado,
            )
        )
        db.flush()
        return usuario

    return crear


def _con_token(usuario: uuid.UUID, **extra) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(usuario)}"} | extra


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


# ---------- La empresa sale del token ----------
def test_el_token_manda_sobre_el_encabezado_de_empresa(client, empresas, nuevo_usuario):
    a, b = empresas
    # La empresa B tiene una categoría (creada con el encabezado de desarrollo, sin token).
    client.post("/api/product-categories", json={"name": "De B"}, headers={"X-Empresa-Id": str(b)})
    usuario_a = nuevo_usuario(a)

    # Un usuario de A que además envía X-Empresa-Id de B sigue viendo solo lo de A.
    response = client.get(
        "/api/product-categories", headers=_con_token(usuario_a, **{"X-Empresa-Id": str(b)})
    )
    assert response.status_code == 200
    assert response.json() == []

    creada = client.post(
        "/api/product-categories", json={"name": "De A"}, headers=_con_token(usuario_a)
    )
    assert creada.status_code == 201
    nombres_b = client.get("/api/product-categories", headers={"X-Empresa-Id": str(b)}).json()
    assert [c["name"] for c in nombres_b] == ["De B"]


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
