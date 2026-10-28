"""Dependencias comunes de los endpoints.

Uso en un endpoint:
    def listar(empresa_id: EmpresaId, db: DbSession): ...
    def perfil(usuario: UsuarioActual): ...
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthenticatedError
from app.core.seguridad import UsuarioAutenticado, VerificadorTokens
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]


@lru_cache
def _verificador_supabase(supabase_url: str) -> VerificadorTokens:
    return VerificadorTokens.para_supabase(supabase_url)


def get_verificador() -> VerificadorTokens:
    """Verificador de tokens de Supabase (las pruebas lo reemplazan por uno propio)."""
    supabase_url = get_settings().supabase_url
    if not supabase_url:
        raise UnauthenticatedError("El inicio de sesión no está configurado (falta SUPABASE_URL).")
    return _verificador_supabase(supabase_url)


def get_usuario_actual(
    verificador: Annotated[VerificadorTokens, Depends(get_verificador)],
    authorization: Annotated[str | None, Header()] = None,
) -> UsuarioAutenticado:
    """Usuario de la petición, según el token de Supabase (`Authorization: Bearer <token>`)."""
    esquema, _, token = (authorization or "").partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise UnauthenticatedError("Inicia sesión para continuar.")
    return verificador.verificar(token)


UsuarioActual = Annotated[UsuarioAutenticado, Depends(get_usuario_actual)]


def get_empresa_id(
    x_empresa_id: Annotated[int | None, Header(gt=0)] = None,
) -> int:
    """Empresa con la que trabaja la petición.

    PROVISIONAL: solo con APP_ENV=development se acepta el encabezado `X-Empresa-Id`.
    En cualquier otro entorno siempre responde 401, para que esto nunca quede abierto
    en el servidor. Cuando exista la tabla usuario_empresa, la empresa saldrá del
    usuario autenticado (UsuarioActual) y solo cambia el interior de esta función.
    """
    if get_settings().app_env != "development" or x_empresa_id is None:
        raise UnauthenticatedError("Inicia sesión para continuar.")
    return x_empresa_id


EmpresaId = Annotated[int, Depends(get_empresa_id)]
