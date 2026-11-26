"""Inicio de sesión propio (docs/API.md, sección 5: Sesión).

- POST /api/auth/login: correo y contraseña → token de acceso + cookie de renovación.
- POST /api/auth/refresh: con la cookie → nuevo token de acceso y cookie rotada.
- POST /api/auth/logout: revoca la cookie de renovación y la borra.

La cookie es httpOnly (JavaScript no puede leerla), SameSite=Strict y solo viaja a
/api/auth. El token de acceso lo guarda el frontend en memoria.
"""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Response, status
from pydantic import Field

from app.api.deps import DbSession, UsuarioActual, get_emisor
from app.core.config import get_settings
from app.core.correo import Enviador, crear_enviador, enviar_sin_fallar
from app.core.errors import ServiceUnavailableError
from app.core.seguridad import EmisorTokens
from app.schemas.common import ApiInput, ApiModel
from app.schemas.usuario import PasswordChange
from app.services.autenticacion import ServicioAutenticacion, SesionEmitida
from app.services.recuperacion import ServicioRecuperacion, correo_recuperacion

router = APIRouter(prefix="/auth", tags=["Sesión"])
# Rutas de la cuenta que exigen el token de acceso (fuera de /api/auth, que usa la cookie).
cuenta_router = APIRouter(tags=["Sesión"])

COOKIE_REFRESH = "iondu_refresh"
RUTA_COOKIE = "/api/auth"


class Credenciales(ApiInput):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UsuarioSesion(ApiModel):
    id: UUID
    email: str
    created_at: datetime


class TokenAcceso(ApiModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UsuarioSesion


def get_servicio(
    db: DbSession,
    emisor: Annotated[EmisorTokens | None, Depends(get_emisor)],
) -> ServicioAutenticacion:
    if emisor is None:
        raise ServiceUnavailableError(
            "El inicio de sesión no está configurado (falta AUTH_JWT_PRIVATE_KEY).",
            code="AUTH_NOT_CONFIGURED",
        )
    dias = get_settings().auth_refresh_token_days
    return ServicioAutenticacion(db, emisor, duracion_refresh=timedelta(days=dias))


Servicio = Annotated[ServicioAutenticacion, Depends(get_servicio)]
CookieRefresh = Annotated[str | None, Cookie(alias=COOKIE_REFRESH)]


def _responder(response: Response, sesion: SesionEmitida) -> TokenAcceso:
    response.set_cookie(
        COOKIE_REFRESH,
        sesion.refresh_token,
        max_age=get_settings().auth_refresh_token_days * 86400,
        path=RUTA_COOKIE,
        httponly=True,
        samesite="strict",
        # En local se usa http://localhost; en cualquier otro entorno, solo HTTPS.
        secure=get_settings().app_env != "development",
    )
    response.headers["Cache-Control"] = "no-store"
    return TokenAcceso(
        access_token=sesion.access_token,
        expires_in=sesion.expires_in,
        user=UsuarioSesion(id=sesion.usuario_id, email=sesion.email, created_at=sesion.creado_en),
    )


@router.post("/login", response_model=TokenAcceso)
def login(datos: Credenciales, response: Response, servicio: Servicio):
    return _responder(response, servicio.iniciar_sesion(datos.email, datos.password))


@router.post("/refresh", response_model=TokenAcceso)
def refresh(response: Response, servicio: Servicio, refresh_token: CookieRefresh = None):
    return _responder(response, servicio.renovar(refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(servicio: Servicio, refresh_token: CookieRefresh = None) -> Response:
    servicio.cerrar(refresh_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(COOKIE_REFRESH, path=RUTA_COOKIE, httponly=True, samesite="strict")
    return response


@cuenta_router.post("/me/password", response_model=TokenAcceso)
def change_password(
    datos: PasswordChange, usuario: UsuarioActual, response: Response, servicio: Servicio
):
    """Cambia la contraseña del usuario de la sesión. Cierra sus demás sesiones y
    entrega una nueva para este navegador (token y cookie)."""
    sesion = servicio.cambiar_contrasena(usuario.id, datos.current_password, datos.new_password)
    return _responder(response, sesion)


# ---------- Recuperación de contraseña por correo ----------
def get_enviador() -> Enviador | None:
    """Servidor SMTP según SMTP_*; None si no está configurado. Las pruebas lo reemplazan."""
    return crear_enviador(get_settings())


EnviadorActual = Annotated[Enviador | None, Depends(get_enviador)]
MENSAJE_RECUPERACION = (
    "Si el correo está registrado, te enviamos un enlace para elegir una contraseña nueva. "
    "Revisa tu bandeja de entrada y la carpeta de spam."
)


class PasswordResetRequest(ApiInput):
    email: str = Field(min_length=3, max_length=254)


class PasswordResetConfirm(ApiInput):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class MensajeRespuesta(ApiModel):
    message: str


@router.post("/password-reset", response_model=MensajeRespuesta, status_code=202)
def request_password_reset(
    datos: PasswordResetRequest, db: DbSession, enviador: EnviadorActual, tareas: BackgroundTasks
):
    """Envía un enlace de un solo uso. Responde igual exista o no el correo."""
    if enviador is None:
        raise ServiceUnavailableError(
            "La recuperación por correo no está disponible. "
            "Pide al Administrador que restablezca tu contraseña.",
            code="EMAIL_NOT_CONFIGURED",
        )
    enlace = ServicioRecuperacion(db).solicitar(datos.email)
    if enlace is not None:
        correo = correo_recuperacion(get_settings().app_public_url, enlace.token)
        tareas.add_task(
            enviar_sin_fallar,
            enviador,
            enlace.destinatario,
            correo.asunto,
            correo.texto,
            correo.html,
        )
    return MensajeRespuesta(message=MENSAJE_RECUPERACION)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(datos: PasswordResetConfirm, db: DbSession) -> Response:
    """Cambia la contraseña con el enlace del correo y cierra todas las sesiones."""
    ServicioRecuperacion(db).confirmar(datos.token, datos.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
