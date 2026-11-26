"""Recuperación de contraseña e invitaciones por correo (enlaces de un solo uso).

- El token es aleatorio (32 bytes) y solo viaja en el correo; en la base va su SHA-256.
- Recuperación: vence en 30 minutos. Invitación: 7 días.
- Pedir un enlace siempre responde igual, exista o no el correo (no revela usuarios), y
  hay un máximo de solicitudes por hora para no inundar la bandeja de nadie.
- Al usar el enlace se cambia la contraseña, se quita el bloqueo por intentos, se cierran
  todas las sesiones y se invalidan los demás enlaces pendientes del usuario.
"""

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import escape

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core import contrasenas
from app.core.errors import UnprocessableError
from app.models import RestablecimientoContrasena, SesionRefresh, Usuario
from app.services.autenticacion import hash_token, normalizar_email

RECUPERACION = "recuperacion"
INVITACION = "invitacion"
DURACION = {RECUPERACION: timedelta(minutes=30), INVITACION: timedelta(days=7)}
MAX_SOLICITUDES_POR_HORA = 3


@dataclass(frozen=True)
class Enlace:
    destinatario: str
    token: str


@dataclass(frozen=True)
class Correo:
    asunto: str
    texto: str
    html: str


def _enlace_invalido() -> UnprocessableError:
    return UnprocessableError(
        "El enlace no es válido o ya venció. Pide uno nuevo.", code="INVALID_RESET_TOKEN"
    )


class ServicioRecuperacion:
    def __init__(self, db: Session, *, reloj: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.db = db
        self._reloj = reloj

    def crear_enlace(self, usuario: Usuario, motivo: str) -> Enlace:
        token = secrets.token_urlsafe(32)
        self.db.add(
            RestablecimientoContrasena(
                id_usuario=usuario.id,
                token_hash=hash_token(token),
                motivo=motivo,
                expira_en=self._reloj() + DURACION[motivo],
            )
        )
        self.db.commit()
        return Enlace(usuario.email, token)

    def solicitar(self, email: str) -> Enlace | None:
        """None si no hay a quién enviarlo (o se superó el máximo): el llamador responde igual."""
        usuario = self.db.scalar(select(Usuario).where(Usuario.email == normalizar_email(email)))
        if usuario is None or not usuario.activo:
            return None
        recientes = self.db.scalar(
            select(func.count())
            .select_from(RestablecimientoContrasena)
            .where(
                RestablecimientoContrasena.id_usuario == usuario.id,
                RestablecimientoContrasena.motivo == RECUPERACION,
                RestablecimientoContrasena.creado_en > self._reloj() - timedelta(hours=1),
            )
        )
        if recientes >= MAX_SOLICITUDES_POR_HORA:
            return None
        return self.crear_enlace(usuario, RECUPERACION)

    def confirmar(self, token: str, contrasena_nueva: str) -> None:
        ahora = self._reloj()
        enlace = self.db.scalar(
            select(RestablecimientoContrasena)
            .where(RestablecimientoContrasena.token_hash == hash_token(token))
            .with_for_update()
        )
        if enlace is None or enlace.usado_en is not None or enlace.expira_en <= ahora:
            raise _enlace_invalido()
        usuario = self.db.get(Usuario, enlace.id_usuario, with_for_update=True)
        if usuario is None or not usuario.activo:
            raise _enlace_invalido()
        try:
            contrasenas.validar_nueva(contrasena_nueva)
        except ValueError as exc:
            raise UnprocessableError(str(exc), code="WEAK_PASSWORD") from exc

        usuario.password_hash = contrasenas.hashear(contrasena_nueva)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        self.db.execute(
            update(SesionRefresh)
            .where(SesionRefresh.id_usuario == usuario.id, SesionRefresh.revocada_en.is_(None))
            .values(revocada_en=ahora)
        )
        # Este y cualquier otro enlace pendiente del usuario quedan usados.
        self.db.execute(
            update(RestablecimientoContrasena)
            .where(
                RestablecimientoContrasena.id_usuario == usuario.id,
                RestablecimientoContrasena.usado_en.is_(None),
            )
            .values(usado_en=ahora)
        )
        self.db.commit()


# ---------- Contenido de los correos ----------
def _url(base: str, token: str) -> str:
    return f"{base.rstrip('/')}/reset-password?token={token}"


def _html(parrafos: list[str], url: str, boton: str) -> str:
    cuerpo = "".join(f"<p>{escape(p)}</p>" for p in parrafos)
    return (
        '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1f2937;max-width:520px">'
        f"{cuerpo}"
        f'<p><a href="{escape(url)}" style="display:inline-block;padding:10px 18px;'
        'background:#0f766e;color:#fff;border-radius:6px;text-decoration:none">'
        f"{escape(boton)}</a></p>"
        f'<p style="font-size:12px;color:#6b7280">Si el botón no funciona, copia este enlace: '
        f"{escape(url)}</p></div>"
    )


def correo_recuperacion(base_url: str, token: str) -> Correo:
    url = _url(base_url, token)
    parrafos = [
        "Recibimos una solicitud para cambiar la contraseña de tu cuenta de IONDU.",
        "El enlace vence en 30 minutos y solo se puede usar una vez.",
        "Si no fuiste tú, ignora este correo: tu contraseña no cambia.",
    ]
    texto = "\n\n".join([parrafos[0], f"Elige una contraseña nueva aquí: {url}", *parrafos[1:]])
    return Correo("Cambia tu contraseña de IONDU", texto, _html(parrafos, url, "Elegir contraseña"))


def correo_invitacion(base_url: str, token: str, empresa: str, nombre: str) -> Correo:
    url = _url(base_url, token)
    parrafos = [
        f"Hola, {nombre}. Te dieron acceso a «{empresa}» en IONDU.",
        "Para entrar, elige tu contraseña. El enlace vence en 7 días y solo se usa una vez.",
    ]
    texto = "\n\n".join([parrafos[0], f"Elige tu contraseña aquí: {url}", parrafos[1]])
    return Correo(
        f"Te invitaron a {empresa} en IONDU", texto, _html(parrafos, url, "Elegir contraseña")
    )
