"""Usuario de la sesión actual (docs/API.md, sección 5: Sesión)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter

from app.api.deps import ContextoActual
from app.core.errors import UnauthenticatedError
from app.schemas.common import ApiModel

router = APIRouter(tags=["Sesión"])


class Me(ApiModel):
    """Mismos campos que `User` del frontend (core/models/user.model.ts)."""

    id: UUID
    email: str | None
    full_name: str
    role: Literal["admin", "operator"]
    tenant_id: int
    active: bool


@router.get("/me", response_model=Me)
def me(contexto: ContextoActual):
    """Perfil del usuario según su token: empresa y rol. Sirve para comprobar el login."""
    if contexto.usuario is None:  # encabezado de desarrollo: no hay usuario real
        raise UnauthenticatedError("Inicia sesión para continuar.")
    return Me(
        id=contexto.usuario.id,
        email=contexto.usuario.email,
        full_name=contexto.nombre or "",
        role="admin" if contexto.es_administrador else "operator",
        tenant_id=contexto.empresa_id,
        active=True,  # get_contexto solo deja pasar usuarios activos
    )
