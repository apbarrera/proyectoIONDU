"""Gestión de usuarios de la empresa (solo Administrador) y cambio de la propia contraseña."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.auth import COOKIE_REFRESH
from app.api.deps import get_emisor
from app.core import contrasenas
from app.core.errors import ConflictError
from app.core.seguridad import EmisorTokens
from app.main import app
from app.models import SesionRefresh, Usuario, UsuarioEmpresa
from app.models.rol import OPERATIVO
from app.schemas.usuario import UserUpdate
from app.services.usuarios import UsuarioService
from tests.conftest import con_token
from tests.tokens import LLAVE_IONDU

pytestmark = pytest.mark.usefixtures("supabase_falso")


@pytest.fixture
def admin_a(usuarios_empresa, empresas) -> uuid.UUID:
    return usuarios_empresa[empresas[0]]


def _codigo(response) -> str:
    return response.json()["error"]["code"]


def _crear(client, admin, email="nuevo@empresa.ec", role="operator", nombre="Nuevo Usuario"):
    return client.post(
        "/api/users",
        json={"email": email, "fullName": nombre, "role": role},
        headers=con_token(admin),
    )


# ---------- Listar ----------
def test_el_administrador_ve_solo_los_usuarios_de_su_empresa(client, admin_a, usuarios_empresa):
    response = client.get("/api/users", headers=con_token(admin_a))

    assert response.status_code == 200
    ids = {u["id"] for u in response.json()}
    assert str(admin_a) in ids
    assert all(str(otro) not in ids for otro in usuarios_empresa.values() if otro != admin_a)
    assert set(response.json()[0]) == {"id", "email", "fullName", "role", "active", "createdAt"}


def test_un_operativo_no_puede_gestionar_usuarios(client, empresas, nuevo_usuario):
    operador = nuevo_usuario(empresas[0], rol=OPERATIVO)

    response = client.get("/api/users", headers=con_token(operador))
    assert response.status_code == 403


# ---------- Crear ----------
def test_crear_un_usuario_nuevo_entrega_una_contrasena_temporal(client, db, admin_a):
    response = _crear(client, admin_a, email="  Nuevo@Empresa.EC ")

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    cuerpo = response.json()
    assert cuerpo["user"]["email"] == "nuevo@empresa.ec"
    assert (cuerpo["user"]["role"], cuerpo["user"]["active"]) == ("operator", True)

    temporal = cuerpo["temporaryPassword"]
    assert len(temporal) >= 16
    cuenta = db.scalar(select(Usuario).where(Usuario.email == "nuevo@empresa.ec"))
    assert contrasenas.verificar(cuenta.password_hash, temporal)


def test_un_correo_de_otra_empresa_se_agrega_sin_tocar_su_contrasena(
    client, db, admin_a, empresas, nuevo_usuario
):
    de_b = nuevo_usuario(empresas[1])
    cuenta = db.get(Usuario, de_b)
    hash_original = cuenta.password_hash

    response = _crear(client, admin_a, email=cuenta.email)

    assert response.status_code == 201
    assert response.json()["temporaryPassword"] is None
    db.expire_all()
    assert db.get(Usuario, de_b).password_hash == hash_original
    assert db.get(UsuarioEmpresa, (de_b, empresas[0])) is not None


def test_no_se_repite_un_usuario_en_la_misma_empresa(client, admin_a):
    _crear(client, admin_a)
    response = _crear(client, admin_a)
    assert (response.status_code, _codigo(response)) == (409, "USER_ALREADY_MEMBER")


@pytest.mark.parametrize("email", ["sin-arroba", "a@b", "@empresa.ec"])
def test_rechaza_correos_invalidos(client, admin_a, email):
    response = _crear(client, admin_a, email=email)
    assert response.status_code == 422


# ---------- Editar ----------
def test_editar_nombre_rol_y_desactivar(client, admin_a, empresas, nuevo_usuario):
    operador = nuevo_usuario(empresas[0], rol=OPERATIVO)

    response = client.patch(
        f"/api/users/{operador}",
        json={"fullName": "Luis Pérez", "role": "admin", "active": False},
        headers=con_token(admin_a),
    )

    assert response.status_code == 200
    assert response.json()["fullName"] == "Luis Pérez"
    assert (response.json()["role"], response.json()["active"]) == ("admin", False)


def test_un_usuario_desactivado_pierde_el_acceso_a_la_empresa(
    client, admin_a, empresas, nuevo_usuario
):
    operador = nuevo_usuario(empresas[0], rol=OPERATIVO)
    client.patch(f"/api/users/{operador}", json={"active": False}, headers=con_token(admin_a))

    response = client.get("/api/me", headers=con_token(operador))
    assert (response.status_code, _codigo(response)) == (403, "NO_COMPANY")


@pytest.mark.parametrize("cambio", [{"role": "operator"}, {"active": False}])
def test_el_administrador_no_puede_quitarse_el_rol_ni_desactivarse(client, admin_a, cambio):
    response = client.patch(f"/api/users/{admin_a}", json=cambio, headers=con_token(admin_a))
    assert (response.status_code, _codigo(response)) == (409, "CANNOT_MODIFY_SELF")


def test_puede_cambiar_su_propio_nombre(client, admin_a):
    response = client.patch(
        f"/api/users/{admin_a}", json={"fullName": "Ana T."}, headers=con_token(admin_a)
    )
    assert response.status_code == 200


def test_la_empresa_nunca_se_queda_sin_administrador_activo(db, admin_a, empresas):
    # El fixture `empresas` también hace Administrador al usuario demo: se desactiva para
    # que admin_a sea el único. Sin usuario actual (p. ej., un proceso interno) la regla
    # del último Administrador sigue protegiendo a la empresa.
    for pertenencia in db.scalars(
        select(UsuarioEmpresa).where(
            UsuarioEmpresa.id_empresa == empresas[0], UsuarioEmpresa.id_usuario != admin_a
        )
    ):
        pertenencia.estado = "INACTIVO"
    db.flush()
    servicio = UsuarioService(db, empresas[0], None)
    with pytest.raises(ConflictError) as error:
        servicio.actualizar(admin_a, UserUpdate(role="operator"))
    assert error.value.code == "LAST_ADMIN"


def test_no_se_edita_un_usuario_de_otra_empresa(client, admin_a, usuarios_empresa, empresas):
    de_b = usuarios_empresa[empresas[1]]
    response = client.patch(
        f"/api/users/{de_b}", json={"fullName": "X"}, headers=con_token(admin_a)
    )
    assert (response.status_code, _codigo(response)) == (404, "USER_NOT_FOUND")


# ---------- Restablecer contraseña ----------
def test_restablecer_contrasena_desbloquea_y_cierra_sus_sesiones(
    client, db, admin_a, empresas, nuevo_usuario
):
    operador = nuevo_usuario(empresas[0], rol=OPERATIVO)
    cuenta = db.get(Usuario, operador)
    cuenta.intentos_fallidos = 3
    cuenta.bloqueado_hasta = datetime.now(UTC) + timedelta(minutes=10)
    db.add(
        SesionRefresh(
            id_usuario=operador,
            token_hash="a" * 64,
            expira_en=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db.flush()

    response = client.post(f"/api/users/{operador}/reset-password", headers=con_token(admin_a))

    assert response.status_code == 200
    temporal = response.json()["temporaryPassword"]
    db.expire_all()
    cuenta = db.get(Usuario, operador)
    assert contrasenas.verificar(cuenta.password_hash, temporal)
    assert (cuenta.intentos_fallidos, cuenta.bloqueado_hasta) == (0, None)
    sesion = db.scalar(select(SesionRefresh).where(SesionRefresh.id_usuario == operador))
    assert sesion.revocada_en is not None


def test_no_restablece_la_contrasena_de_quien_trabaja_en_otra_empresa(
    client, admin_a, empresas, nuevo_usuario, agregar_pertenencia
):
    compartido = nuevo_usuario(empresas[0], rol=OPERATIVO)
    agregar_pertenencia(compartido, empresas[1], OPERATIVO)

    response = client.post(f"/api/users/{compartido}/reset-password", headers=con_token(admin_a))
    assert (response.status_code, _codigo(response)) == (409, "USER_IN_OTHER_COMPANY")


def test_el_administrador_no_restablece_su_propia_contrasena(client, admin_a):
    response = client.post(f"/api/users/{admin_a}/reset-password", headers=con_token(admin_a))
    assert (response.status_code, _codigo(response)) == (409, "CANNOT_MODIFY_SELF")


# ---------- Cambiar la propia contraseña ----------
CLAVE_ACTUAL = "Clave-actual-2026"
CLAVE_NUEVA = "Clave-nueva-2026"


@pytest.fixture
def con_clave(db, admin_a) -> uuid.UUID:
    app.dependency_overrides[get_emisor] = lambda: EmisorTokens(
        LLAVE_IONDU, duracion=timedelta(minutes=15)
    )
    db.get(Usuario, admin_a).password_hash = contrasenas.hashear(CLAVE_ACTUAL)
    db.flush()
    yield admin_a
    app.dependency_overrides.pop(get_emisor, None)


def _cambiar(client, usuario, actual=CLAVE_ACTUAL, nueva=CLAVE_NUEVA):
    return client.post(
        "/api/me/password",
        json={"currentPassword": actual, "newPassword": nueva},
        headers=con_token(usuario),
    )


def test_cambiar_la_contrasena_entrega_una_sesion_nueva_y_cierra_las_demas(client, db, con_clave):
    db.add(
        SesionRefresh(
            id_usuario=con_clave,
            token_hash="b" * 64,
            expira_en=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db.flush()

    response = _cambiar(client, con_clave)

    assert response.status_code == 200
    assert response.json()["accessToken"]
    assert COOKIE_REFRESH in response.cookies
    db.expire_all()
    assert contrasenas.verificar(db.get(Usuario, con_clave).password_hash, CLAVE_NUEVA)
    vieja = db.scalar(select(SesionRefresh).where(SesionRefresh.token_hash == "b" * 64))
    assert vieja.revocada_en is not None


def test_la_contrasena_actual_incorrecta_no_cambia_nada(client, con_clave):
    response = _cambiar(client, con_clave, actual="no-es-la-clave")
    assert (response.status_code, _codigo(response)) == (422, "INVALID_CURRENT_PASSWORD")


@pytest.mark.parametrize("nueva", ["corta", CLAVE_ACTUAL])
def test_la_contrasena_nueva_debe_ser_valida_y_distinta(client, con_clave, nueva):
    assert _cambiar(client, con_clave, nueva=nueva).status_code == 422


def test_cambiar_la_contrasena_exige_sesion(client):
    response = client.post(
        "/api/me/password", json={"currentPassword": "x", "newPassword": CLAVE_NUEVA}
    )
    assert response.status_code == 401
