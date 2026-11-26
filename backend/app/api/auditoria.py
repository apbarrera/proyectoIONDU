"""Auditoría de la empresa: solo el Administrador la consulta (docs/API.md, sección 14)."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import DbSession, SoloAdministrador
from app.schemas.auditoria import AuditEntry, AuditModule
from app.schemas.common import Page
from app.services.auditoria import AuditoriaService

router = APIRouter(tags=["Auditoría"])


@router.get("/audit", response_model=Page[AuditEntry])
def list_audit(
    contexto: SoloAdministrador,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 50,
    module: AuditModule | None = None,
    user_id: Annotated[UUID | None, Query(alias="userId")] = None,
    desde: Annotated[date | None, Query(alias="from")] = None,  # "from" es palabra reservada
    hasta: Annotated[date | None, Query(alias="to")] = None,
):
    return AuditoriaService(db, contexto.empresa_id).listar(
        page=page,
        page_size=page_size,
        modulo=module,
        id_usuario=user_id,
        desde=desde,
        hasta=hasta,
    )
