"""Usuario de la sesión actual (docs/API.md, sección 5: Sesión)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter

from app.api.deps import ContextoActual, DbSession, UsuarioActual
from app.core.errors import UnauthenticatedError
from app.db.session import establecer_contexto_rls
from app.models.rol import ADMINISTRADOR
from app.repositories.usuario_empresa import obtener_empresas_activas
from app.schemas.common import ApiModel

router = APIRouter(tags=["Sesión"])


class EmpresaDelUsuario(ApiModel):
    """Una empresa a la que el usuario pertenece (para el selector de empresa)."""

    id: int
    name: str
    trade_name: str | None
    ruc: str
    role: Literal["admin", "operator"]


@router.get("/me/companies", response_model=list[EmpresaDelUsuario])
def mis_empresas(usuario: UsuarioActual, db: DbSession):
    """Empresas con pertenencia activa del usuario. No exige haber elegido empresa:
    con más de una, el frontend muestra el selector y envía X-Empresa-Id."""
    establecer_contexto_rls(db, usuario_id=str(usuario.id), empresa_id=None)
    return [
        EmpresaDelUsuario(
            id=e.id_empresa,
            name=e.razon_social,
            trade_name=e.nombre_comercial,
            ruc=e.ruc,
            role="admin" if e.rol == ADMINISTRADOR else "operator",
        )
        for e in obtener_empresas_activas(db, usuario.id)
    ]


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
