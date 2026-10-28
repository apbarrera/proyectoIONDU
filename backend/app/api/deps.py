"""Dependencias comunes de los endpoints.

Uso en un endpoint:
    def listar(empresa_id: EmpresaId, db: DbSession): ...
    def perfil(contexto: ContextoActual): ...
    def dashboard(contexto: SoloAdministrador): ...
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ForbiddenError, UnauthenticatedError
from app.core.seguridad import UsuarioAutenticado, VerificadorTokens
from app.db.session import get_db
from app.models.rol import ADMINISTRADOR
from app.repositories.usuario_empresa import obtener_pertenencia_activa

DbSession = Annotated[Session, Depends(get_db)]


# ---------- Token de Supabase ----------
@lru_cache
def _verificador_supabase(supabase_url: str) -> VerificadorTokens:
    return VerificadorTokens.para_supabase(supabase_url)


def get_verificador() -> VerificadorTokens | None:
    """Verificador de tokens de Supabase; None si no está configurado SUPABASE_URL.
    Las pruebas lo reemplazan por uno con llaves propias."""
    supabase_url = get_settings().supabase_url
    return _verificador_supabase(supabase_url) if supabase_url else None


def _token_bearer(authorization: str | None) -> str | None:
    esquema, _, token = (authorization or "").partition(" ")
    return token if esquema.lower() == "bearer" and token else None


# ---------- Contexto de la petición: usuario, empresa y rol ----------
@dataclass(frozen=True)
class Contexto:
    empresa_id: int
    rol: str
    usuario: UsuarioAutenticado | None = None  # None solo con el encabezado de desarrollo
    nombre: str | None = None

    @property
    def es_administrador(self) -> bool:
        return self.rol == ADMINISTRADOR


def get_contexto(
    db: DbSession,
    verificador: Annotated[VerificadorTokens | None, Depends(get_verificador)],
    authorization: Annotated[str | None, Header()] = None,
    x_empresa_id: Annotated[int | None, Header(gt=0)] = None,
) -> Contexto:
    """Con token: la empresa y el rol salen de usuario_empresa (el token manda; el
    encabezado X-Empresa-Id se ignora). Sin token: solo en APP_ENV=development se
    acepta X-Empresa-Id, con rol Administrador, para probar sin login."""
    token = _token_bearer(authorization)
    if token:
        if verificador is None:
            raise UnauthenticatedError(
                "El inicio de sesión no está configurado (falta SUPABASE_URL)."
            )
        usuario = verificador.verificar(token)
        pertenencia = obtener_pertenencia_activa(db, usuario.id)
        if pertenencia is None:
            raise ForbiddenError(
                "Tu usuario no tiene una empresa asignada o está inactivo.", code="NO_COMPANY"
            )
        return Contexto(pertenencia.id_empresa, pertenencia.rol, usuario, pertenencia.nombre)

    if get_settings().app_env == "development" and x_empresa_id is not None:
        return Contexto(empresa_id=x_empresa_id, rol=ADMINISTRADOR)
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
