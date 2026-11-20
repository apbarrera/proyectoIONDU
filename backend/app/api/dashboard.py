"""Endpoint del dashboard financiero (docs/API.md, sección 13).

Solo lo ve el Administrador (RF-5.5).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession, SoloAdministrador
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard import DashboardService

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    contexto: SoloAdministrador,
    db: DbSession,
    desde: Annotated[date | None, Query(alias="from")] = None,  # "from" es palabra reservada
    hasta: Annotated[date | None, Query(alias="to")] = None,
):
    return DashboardService(db, contexto.empresa_id).resumen(desde, hasta)
