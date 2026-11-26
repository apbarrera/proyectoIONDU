"""Dependencias comunes de los endpoints.

Uso en un endpoint:
    def listar(empresa_id: EmpresaId, db: DbSession): ...
    def perfil(contexto: ContextoActual): ...
    def dashboard(contexto: SoloAdministrador): ...
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    UnauthenticatedError,
)
from app.core.seguridad import (
    EmisorTokens,
    UsuarioAutenticado,
    VerificadorTokens,
    cargar_llave_privada,
)
from app.db.session import establecer_contexto_rls, get_db
from app.models.rol import ADMINISTRADOR
from app.repositories.usuario_empresa import (
    obtener_empresas_activas,
    obtener_pertenencia_activa,
)
from app.services.auditoria import Auditor

DbSession = Annotated[Session, Depends(get_db)]


# ---------- Tokens del inicio de sesión propio ----------
@lru_cache
def _emisor_tokens(pem: str, minutos: int) -> EmisorTokens:
    return EmisorTokens(cargar_llave_privada(pem), duracion=timedelta(minutes=minutos))


def get_emisor() -> EmisorTokens | None:
    """Firma los tokens de acceso; None si no está configurado AUTH_JWT_PRIVATE_KEY."""
    settings = get_settings()
    if settings.auth_jwt_private_key is None:
        return None
    return _emisor_tokens(
        settings.auth_jwt_private_key.get_secret_value(), settings.auth_access_token_minutes
    )


def get_verificador(
    emisor: Annotated[EmisorTokens | None, Depends(get_emisor)],
) -> VerificadorTokens | None:
    """Verificador de los tokens de acceso. Las pruebas lo reemplazan por uno con
    llaves propias."""
    return emisor.verificador() if emisor else None


def _token_bearer(authorization: str | None) -> str | None:
    esquema, _, token = (authorization or "").partition(" ")
    return token if esquema.lower() == "bearer" and token else None


def get_usuario_actual(
    verificador: Annotated[VerificadorTokens | None, Depends(get_verificador)],
    authorization: Annotated[str | None, Header()] = None,
) -> UsuarioAutenticado:
    """Usuario con sesión, SIN exigir que haya elegido empresa (p. ej., para listar
    sus empresas y mostrar el selector)."""
    token = _token_bearer(authorization)
    if not token:
        raise UnauthenticatedError("Inicia sesión para continuar.")
    if verificador is None:
        raise UnauthenticatedError(
            "El inicio de sesión no está configurado (falta AUTH_JWT_PRIVATE_KEY)."
        )
    return verificador.verificar(token)


UsuarioActual = Annotated[UsuarioAutenticado, Depends(get_usuario_actual)]


# ---------- Contexto de la petición: usuario, empresa y rol ----------
@dataclass(frozen=True)
class Contexto:
    empresa_id: int
    rol: str
    usuario: UsuarioAutenticado | None = None
    nombre: str | None = None

    @property
    def es_administrador(self) -> bool:
        return self.rol == ADMINISTRADOR


def _contexto_con_membresia(
    db: Session,
    usuario: UsuarioAutenticado,
    x_empresa_id: int | None,
) -> Contexto:
    """Resuelve y valida la empresa bajo el contexto RLS del usuario."""

    # Primero se establece únicamente el usuario para consultar sus empresas.
    establecer_contexto_rls(
        db,
        usuario_id=usuario.id,
        empresa_id=None,
    )

    empresas = obtener_empresas_activas(db, usuario.id)

    if x_empresa_id is not None:
        empresa_seleccionada = next(
            (empresa for empresa in empresas if empresa.id_empresa == x_empresa_id),
            None,
        )

        if empresa_seleccionada is None:
            raise ForbiddenError(
                "No tienes una pertenencia activa a la empresa seleccionada.",
                code="COMPANY_ACCESS_DENIED",
            )

        id_empresa = empresa_seleccionada.id_empresa
    else:
        if not empresas:
            raise ForbiddenError(
                "Tu usuario no tiene una empresa asignada o está inactivo.",
                code="NO_COMPANY",
            )

        if len(empresas) > 1:
            raise ConflictError(
                "Debes seleccionar una empresa para continuar.",
                code="COMPANY_SELECTION_REQUIRED",
            )

        id_empresa = empresas[0].id_empresa

    # Después se establece el contexto completo de usuario y empresa.
    establecer_contexto_rls(
        db,
        usuario_id=usuario.id,
        empresa_id=id_empresa,
    )

    # Se vuelve a comprobar la pertenencia bajo el contexto RLS seleccionado.
    pertenencia = obtener_pertenencia_activa(
        db,
        usuario.id,
        id_empresa,
    )

    if pertenencia is None:
        raise ForbiddenError(
            "No tienes una pertenencia activa a la empresa seleccionada.",
            code="COMPANY_ACCESS_DENIED",
        )

    return Contexto(
        empresa_id=pertenencia.id_empresa,
        rol=pertenencia.rol,
        usuario=usuario,
        nombre=pertenencia.nombre,
    )


def get_contexto(
    db: DbSession,
    verificador: Annotated[VerificadorTokens | None, Depends(get_verificador)],
    authorization: Annotated[str | None, Header()] = None,
    x_empresa_id: Annotated[int | None, Header(gt=0)] = None,
    x_usuario_id: Annotated[
        uuid.UUID | None,
        Header(description="Solo desarrollo: actuar como este usuario (con X-Empresa-Id)."),
    ] = None,
) -> Contexto:
    """Obtiene el contexto validando la pertenencia activa a la empresa."""

    token = _token_bearer(authorization)

    if token:
        if verificador is None:
            raise UnauthenticatedError(
                "El inicio de sesión no está configurado (falta AUTH_JWT_PRIVATE_KEY)."
            )

        usuario = verificador.verificar(token)
        return _contexto_con_membresia(db, usuario, x_empresa_id)

    settings = get_settings()

    # El acceso sin token solo existe en desarrollo y exige un usuario real.
    if settings.app_env == "development" and not authorization and x_empresa_id is not None:
        id_usuario = x_usuario_id or settings.dev_user_id

        if id_usuario is None:
            raise UnauthenticatedError(
                "Configura DEV_USER_ID o proporciona X-Usuario-Id para desarrollo."
            )

        usuario = UsuarioAutenticado(id=id_usuario, email=None)

        return _contexto_con_membresia(db, usuario, x_empresa_id)

    raise UnauthenticatedError("Inicia sesión para continuar.")


ContextoActual = Annotated[Contexto, Depends(get_contexto)]


def get_empresa_id(contexto: ContextoActual) -> int:
    return contexto.empresa_id


EmpresaId = Annotated[int, Depends(get_empresa_id)]


def requiere_administrador(contexto: ContextoActual) -> Contexto:
    """Para lo exclusivo del rol Administrador (por ejemplo, el dashboard financiero)."""
    if not contexto.es_administrador:
        raise ForbiddenError("Esta sección es solo para administradores.")
    return contexto


SoloAdministrador = Annotated[Contexto, Depends(requiere_administrador)]


def get_auditor(contexto: ContextoActual, db: DbSession) -> Auditor:
    """Registra en la auditoría de la empresa las acciones del usuario de la petición."""
    return Auditor(db, contexto.empresa_id, contexto.usuario.id if contexto.usuario else None)


AuditorActual = Annotated[Auditor, Depends(get_auditor)]
