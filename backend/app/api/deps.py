"""Dependencias comunes de los endpoints.

Uso en un endpoint:
    def listar(empresa_id: EmpresaId, db: DbSession): ...
"""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthenticatedError
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_empresa_id(
    x_empresa_id: Annotated[int | None, Header(gt=0)] = None,
) -> int:
    """Empresa con la que trabaja la petición.

    PROVISIONAL hasta integrar Supabase Auth: solo con APP_ENV=development se acepta
    el encabezado `X-Empresa-Id`. En cualquier otro entorno siempre responde 401, para
    que esto nunca quede abierto en el servidor. Con Supabase, la empresa saldrá del
    token y solo cambia el interior de esta función.
    """
    if get_settings().app_env != "development" or x_empresa_id is None:
        raise UnauthenticatedError("Inicia sesión para continuar.")
    return x_empresa_id


EmpresaId = Annotated[int, Depends(get_empresa_id)]
