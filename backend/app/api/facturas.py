"""Endpoints de emisión de facturas electrónicas."""

from typing import Annotated

from fastapi import APIRouter, Path, Request, Response

from app.api.deps import ContextoActual, DbSession, EmpresaId
from app.core.errors import ForbiddenError, NotFoundError
from app.schemas.factura import Invoice, invoice_desde_factura
from app.services.almacenamiento import AlmacenamientoRideService
from app.services.factura import FacturaService
from app.services.venta import VentaService

router = APIRouter(tags=["Facturación"])

SaleId = Annotated[int, Path(gt=0)]


def _obtener_almacenamiento(request: Request) -> AlmacenamientoRideService | None:
    """Obtiene el servicio a partir del cliente compartido de Supabase."""

    cliente = getattr(request.app.state, "supabase", None)
    if cliente is None:
        return None

    return AlmacenamientoRideService(cliente)


@router.post("/sales/{id}/invoice", response_model=Invoice, status_code=201)
def issue_invoice(
    id: SaleId,
    request: Request,
    contexto: ContextoActual,
    db: DbSession,
):
    if contexto.usuario is None:
        raise ForbiddenError(
            "Para emitir facturas debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )

    servicio = FacturaService(db, contexto.empresa_id)
    servicio.almacenamiento = _obtener_almacenamiento(request)
    factura = servicio.emitir(id)

    return invoice_desde_factura(factura)


@router.get("/sales/{id}/invoice", response_model=Invoice)
def get_invoice(id: SaleId, empresa_id: EmpresaId, db: DbSession):
    """Estado actual de la factura de una venta (para seguirla mientras el worker la autoriza)."""
    factura = VentaService(db, empresa_id).obtener(id).invoice
    if factura is None:
        raise NotFoundError("La venta todavía no tiene factura.", code="INVOICE_NOT_FOUND")
    return factura


@router.get("/sales/{id}/invoice/ride")
def download_invoice_ride(
    id: SaleId,
    request: Request,
    contexto: ContextoActual,
    db: DbSession,
):
    """Descarga el RIDE de una factura de la empresa activa."""

    if contexto.usuario is None:
        raise ForbiddenError(
            "Para descargar facturas debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )

    servicio = FacturaService(db, contexto.empresa_id)
    servicio.almacenamiento = _obtener_almacenamiento(request)
    contenido = servicio.obtener_ride(id)

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="factura-{id}-ride.pdf"'},
    )
