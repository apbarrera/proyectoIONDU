"""Empresa y rol del usuario desde su token y usuario_empresa (necesitan TEST_DATABASE_URL)."""

import uuid

import pytest

from app.api.deps import Contexto, get_verificador, requiere_administrador
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.db.base import auth_users
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
        db.execute(auth_users.insert().values(id=usuario))
        db.add(
            UsuarioEmpresa(
                id_usuario=usuario,
                id_empresa=id_empresa,
                id_rol=roles[rol],
                nombre_visible="Ana Torres",
                estado=estado,
            )
        )
        db.flush()
        return usuario

    return crear


@pytest.fixture
def agregar_pertenencia(db, roles):
    def agregar(
        usuario: uuid.UUID,
        id_empresa: int,
        rol: str = ADMINISTRADOR,
        estado: str = "ACTIVO",
    ) -> None:
        db.add(
            UsuarioEmpresa(
                id_usuario=usuario,
                id_empresa=id_empresa,
                id_rol=roles[rol],
                nombre_visible="Ana Torres",
                estado=estado,
            )
        )
        db.flush()

    return agregar


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


# ---------- Selección de empresa ----------
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
