"""Endpoints de ventas (docs/API.md, sección 8).

Solo reciben la petición y llaman al servicio; las reglas viven en app/services.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import ContextoActual, DbSession, EmpresaId, SoloAdministrador
from app.core.errors import ForbiddenError
from app.schemas.common import Page, VoidRequest
from app.schemas.venta import PaymentMethod, Sale, SaleCreate
from app.services.venta import VentaService

router = APIRouter(tags=["Ventas"])

SaleId = Annotated[int, Path(gt=0)]


@router.post("/sales", response_model=Sale, status_code=201)
def create_sale(datos: SaleCreate, contexto: ContextoActual, db: DbSession):
    # La venta guarda qué usuario la hizo: el encabezado de desarrollo no tiene usuario.
    if contexto.usuario is None:
        raise ForbiddenError(
            "Para registrar ventas debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )
    return VentaService(db, contexto.empresa_id).crear(datos, contexto.usuario.id)


@router.get("/sales", response_model=Page[Sale])
def list_sales(
    empresa_id: EmpresaId,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    desde: Annotated[date | None, Query(alias="from")] = None,  # "from" es palabra reservada
    hasta: Annotated[date | None, Query(alias="to")] = None,
    customer_id: Annotated[int | None, Query(alias="customerId", gt=0)] = None,
    payment_method: Annotated[PaymentMethod | None, Query(alias="paymentMethod")] = None,
):
    return VentaService(db, empresa_id).listar(
        page=page,
        page_size=page_size,
        desde=desde,
        hasta=hasta,
        customer_id=customer_id,
        payment_method=payment_method,
    )


@router.get("/sales/{id}", response_model=Sale)
def get_sale(id: SaleId, empresa_id: EmpresaId, db: DbSession):
    return VentaService(db, empresa_id).obtener(id)


# RF-2.7: solo el Administrador anula; la venta queda en el historial como "anulada".
@router.post("/sales/{id}/void", response_model=Sale)
def void_sale(id: SaleId, datos: VoidRequest, contexto: SoloAdministrador, db: DbSession):
    if contexto.usuario is None:
        raise ForbiddenError(
            "Para anular ventas debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )
    return VentaService(db, contexto.empresa_id).anular(
        id, datos.reason, contexto.usuario.id, contexto.nombre
    )
