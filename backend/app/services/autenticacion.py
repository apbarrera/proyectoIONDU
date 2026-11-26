"""Inicio de sesión propio: contraseñas, bloqueo por intentos y sesiones renovables.

- El token de acceso (JWT, 15 min por defecto) viaja en `Authorization: Bearer`.
- El token de renovación es un valor aleatorio que solo conoce el navegador (cookie
  httpOnly). En la base se guarda su hash SHA-256.
- Cada renovación lo rota. Si llega uno ya rotado fuera del margen de gracia, alguien
  lo copió: se cierran todas las sesiones del usuario.
"""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core import contrasenas
from app.core.errors import TooManyRequestsError, UnauthenticatedError
from app.core.seguridad import EmisorTokens
from app.models import SesionRefresh, Usuario

MAX_INTENTOS = 5
DURACION_BLOQUEO = timedelta(minutes=15)
# Dos pestañas pueden renovar a la vez con el mismo token: ese margen no es un robo.
GRACIA_ROTACION = timedelta(seconds=30)

MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."
MENSAJE_SESION = "Tu sesión terminó. Inicia sesión de nuevo."


@dataclass(frozen=True)
class SesionEmitida:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expira_en: datetime
    usuario_id: UUID
    email: str
    creado_en: datetime


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _credenciales_invalidas() -> UnauthenticatedError:
    return UnauthenticatedError(MENSAJE_CREDENCIALES, code="INVALID_CREDENTIALS")


def _sesion_invalida() -> UnauthenticatedError:
    return UnauthenticatedError(MENSAJE_SESION, code="SESSION_INVALID")


class ServicioAutenticacion:
    def __init__(
        self,
        db: Session,
        emisor: EmisorTokens,
        *,
        duracion_refresh: timedelta,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.db = db
        self.emisor = emisor
        self.duracion_refresh = duracion_refresh
        self._reloj = reloj

    # ---------- Inicio de sesión ----------
    def iniciar_sesion(self, email: str, contrasena: str) -> SesionEmitida:
        ahora = self._reloj()
        usuario = self.db.scalar(
            select(Usuario).where(Usuario.email == normalizar_email(email)).with_for_update()
        )
        if usuario is None:
            contrasenas.simular_verificacion(contrasena)
            raise _credenciales_invalidas()

        if usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > ahora:
            raise TooManyRequestsError(
                "Demasiados intentos fallidos. Intenta de nuevo en unos minutos."
            )

        if not contrasenas.verificar(usuario.password_hash, contrasena):
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= MAX_INTENTOS:
                usuario.intentos_fallidos = 0
                usuario.bloqueado_hasta = ahora + DURACION_BLOQUEO
            self.db.commit()
            raise _credenciales_invalidas()

        # Con la contraseña correcta, una cuenta desactivada recibe el mismo mensaje.
        if not usuario.activo:
            raise _credenciales_invalidas()

        if usuario.intentos_fallidos or usuario.bloqueado_hasta is not None:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
        if contrasenas.necesita_rehash(usuario.password_hash):
            usuario.password_hash = contrasenas.hashear(contrasena)

        # Limpieza: las sesiones vencidas de este usuario ya no sirven.
        self.db.execute(
            delete(SesionRefresh).where(
                SesionRefresh.id_usuario == usuario.id, SesionRefresh.expira_en <= ahora
            )
        )
        sesion = self._crear_sesion(usuario, ahora)
        self.db.commit()
        return sesion

    # ---------- Renovación ----------
    def renovar(self, refresh_token: str | None) -> SesionEmitida:
        if not refresh_token:
            raise _sesion_invalida()
        ahora = self._reloj()
        fila = self.db.scalar(
            select(SesionRefresh)
            .where(SesionRefresh.token_hash == hash_token(refresh_token))
            .with_for_update()
        )
        if fila is None or fila.revocada_en is not None or fila.expira_en <= ahora:
            raise _sesion_invalida()

        if fila.rotada_en is not None and ahora - fila.rotada_en > GRACIA_ROTACION:
            # Reutilización de un token ya rotado: se cierran todas las sesiones.
            self._revocar_todas(fila.id_usuario, ahora)
            self.db.commit()
            raise _sesion_invalida()

        usuario = self.db.get(Usuario, fila.id_usuario)
        if usuario is None or not usuario.activo:
            self._revocar_todas(fila.id_usuario, ahora)
            self.db.commit()
            raise _sesion_invalida()

        if fila.rotada_en is None:
            fila.rotada_en = ahora
        sesion = self._crear_sesion(usuario, ahora)
        self.db.commit()
        return sesion

    # ---------- Cierre de sesión ----------
    def cerrar(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        self.db.execute(
            update(SesionRefresh)
            .where(
                SesionRefresh.token_hash == hash_token(refresh_token),
                SesionRefresh.revocada_en.is_(None),
            )
            .values(revocada_en=self._reloj())
        )
        self.db.commit()

    # ---------- Internos ----------
    def _crear_sesion(self, usuario: Usuario, ahora: datetime) -> SesionEmitida:
        refresh_token = secrets.token_urlsafe(32)
        expira_en = ahora + self.duracion_refresh
        self.db.add(
            SesionRefresh(
                id_usuario=usuario.id,
                token_hash=hash_token(refresh_token),
                expira_en=expira_en,
            )
        )
        return SesionEmitida(
            access_token=self.emisor.emitir(usuario.id, usuario.email, ahora=ahora),
            expires_in=self.emisor.duracion_segundos,
            refresh_token=refresh_token,
            refresh_expira_en=expira_en,
            usuario_id=usuario.id,
            email=usuario.email,
            creado_en=usuario.creado_en,
        )

    def _revocar_todas(self, id_usuario: UUID, ahora: datetime) -> None:
        self.db.execute(
            update(SesionRefresh)
            .where(SesionRefresh.id_usuario == id_usuario, SesionRefresh.revocada_en.is_(None))
            .values(revocada_en=ahora)
        )
