"""Recuperación de contraseña e invitaciones por correo (enlaces de un solo uso)."""

# Los fixtures `usuario`, `emisor_de_prueba` y `admin_a` vienen de otros módulos de prueba.
# ruff: noqa: F811
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.auth import get_enviador
from app.main import app
from app.models import RestablecimientoContrasena, SesionRefresh, Usuario
from app.services.recuperacion import MAX_SOLICITUDES_POR_HORA
from tests.test_auth import CONTRASENA, _login, emisor_de_prueba, usuario  # noqa: F401
from tests.test_usuarios import _crear, admin_a  # noqa: F401

pytestmark = pytest.mark.usefixtures("supabase_falso")
NUEVA = "Otra-clave-segura-2026"


class BuzonFalso:
    def __init__(self):
        self.enviados: list[dict] = []

    def enviar(self, destinatario, asunto, texto, html=None):
        self.enviados.append({"para": destinatario, "asunto": asunto, "texto": texto, "html": html})

    def token(self, indice=-1) -> str:
        return re.search(r"token=([\w-]+)", self.enviados[indice]["texto"]).group(1)


@pytest.fixture
def buzon():
    falso = BuzonFalso()
    app.dependency_overrides[get_enviador] = lambda: falso
    yield falso
    app.dependency_overrides.pop(get_enviador, None)


def _pedir(client, email="ana@empresa.ec"):
    return client.post("/api/auth/password-reset", json={"email": email})


def _confirmar(client, token, clave=NUEVA):
    return client.post(
        "/api/auth/password-reset/confirm", json={"token": token, "newPassword": clave}
    )


def test_el_enlace_cambia_la_contrasena_y_cierra_las_sesiones(client, db, usuario, buzon):
    assert _login(client).status_code == 200  # una sesión abierta

    respuesta = _pedir(client, "  ANA@empresa.ec ")
    assert respuesta.status_code == 202
    [correo] = buzon.enviados
    assert correo["para"] == "ana@empresa.ec"
    assert "/reset-password?token=" in correo["texto"]

    assert _confirmar(client, buzon.token()).status_code == 204
    assert _login(client).status_code == 401  # la contraseña anterior ya no sirve
    assert _login(client, password=NUEVA).status_code == 200
    abiertas = db.scalars(
        select(SesionRefresh).where(
            SesionRefresh.id_usuario == usuario.id, SesionRefresh.revocada_en.is_(None)
        )
    ).all()
    assert len(abiertas) == 1  # solo la del último login


def test_el_token_solo_se_guarda_como_hash(client, db, usuario, buzon):
    _pedir(client)
    guardado = db.scalar(select(RestablecimientoContrasena.token_hash))
    assert guardado != buzon.token() and len(guardado) == 64


def test_el_enlace_se_usa_una_sola_vez(client, usuario, buzon):
    _pedir(client)
    token = buzon.token()
    assert _confirmar(client, token).status_code == 204
    respuesta = _confirmar(client, token, "Tercera-clave-2026")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_el_enlace_vence(client, db, usuario, buzon):
    _pedir(client)
    enlace = db.scalar(select(RestablecimientoContrasena))
    enlace.expira_en = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    assert _confirmar(client, buzon.token()).status_code == 422


def test_usar_un_enlace_invalida_los_demas(client, usuario, buzon):
    _pedir(client)
    _pedir(client)
    primero, segundo = buzon.token(0), buzon.token(1)
    assert _confirmar(client, segundo).status_code == 204
    assert _confirmar(client, primero).status_code == 422


def test_un_correo_desconocido_responde_igual_y_no_envia_nada(client, usuario, buzon):
    conocido = _pedir(client).json()
    desconocido = _pedir(client, "nadie@empresa.ec")
    assert desconocido.status_code == 202
    assert desconocido.json() == conocido  # no revela si la cuenta existe
    assert len(buzon.enviados) == 1


def test_maximo_de_solicitudes_por_hora(client, usuario, buzon):
    for _ in range(MAX_SOLICITUDES_POR_HORA + 2):
        assert _pedir(client).status_code == 202
    assert len(buzon.enviados) == MAX_SOLICITUDES_POR_HORA


def test_contrasena_debil_no_se_acepta(client, usuario, buzon):
    _pedir(client)
    respuesta = _confirmar(client, buzon.token(), "corta")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "WEAK_PASSWORD"
    assert _confirmar(client, buzon.token()).status_code == 204  # el enlace sigue sirviendo


def test_el_enlace_quita_el_bloqueo_por_intentos(client, db, usuario, buzon):
    usuario.bloqueado_hasta = datetime.now(UTC) + timedelta(minutes=10)
    usuario.intentos_fallidos = 5
    db.flush()
    _pedir(client)
    _confirmar(client, buzon.token())
    assert _login(client, password=NUEVA).status_code == 200


def test_sin_correo_configurado_lo_dice(client, usuario):
    app.dependency_overrides[get_enviador] = lambda: None
    try:
        respuesta = _pedir(client)
    finally:
        app.dependency_overrides.pop(get_enviador, None)
    assert respuesta.status_code == 503
    assert respuesta.json()["error"]["code"] == "EMAIL_NOT_CONFIGURED"


def test_crear_usuario_envia_una_invitacion(client, db, admin_a, buzon):
    respuesta = _crear(client, admin_a, email="invitada@empresa.ec", nombre="Invitada")
    assert respuesta.status_code == 201
    assert respuesta.json()["invitationSent"] is True
    [correo] = buzon.enviados
    assert correo["para"] == "invitada@empresa.ec" and "Empresa A" in correo["asunto"]

    assert _confirmar(client, buzon.token()).status_code == 204
    assert _login(client, email="invitada@empresa.ec", password=NUEVA).status_code == 200
    enlace = db.scalar(select(RestablecimientoContrasena))
    assert enlace.motivo == "invitacion"
    assert db.scalar(select(Usuario).where(Usuario.email == "invitada@empresa.ec")) is not None


def test_sin_correo_la_creacion_sigue_con_contrasena_temporal(client, admin_a):
    app.dependency_overrides[get_enviador] = lambda: None
    try:
        respuesta = _crear(client, admin_a)
    finally:
        app.dependency_overrides.pop(get_enviador, None)
    assert respuesta.json()["invitationSent"] is False
    assert respuesta.json()["temporaryPassword"]
