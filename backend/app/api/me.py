"""Usuario de la sesión actual (docs/API.md, sección 5: Sesión)."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import UsuarioActual
from app.schemas.common import ApiModel

router = APIRouter(tags=["Sesión"])


class Me(ApiModel):
    id: UUID
    email: str | None


@router.get("/me", response_model=Me)
def me(usuario: UsuarioActual):
    """Quién es el usuario según su token. Sirve para comprobar que el login funciona."""
    return Me(id=usuario.id, email=usuario.email)
