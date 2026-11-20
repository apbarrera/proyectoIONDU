"""Endpoints de emisión de facturas electrónicas."""

from typing import Annotated

from fastapi import APIRouter, Path, Request, Response

from app.api.deps import ContextoActual, DbSession
from app.core.errors import ForbiddenError
from app.schemas.factura import Invoice, InvoiceMessage
from app.services.almacenamiento import AlmacenamientoRideService
from app.services.factura import FacturaService

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

    return Invoice(
        id=factura.id_factura,
        sale_id=factura.id_venta,
        invoice_number=factura.numero_comprobante,
        access_key=factura.clave_acceso,
        authorization_status=factura.estado_autorizacion,
        authorization_number=factura.numero_autorizacion,
        authorization_date=factura.fecha_autorizacion,
        messages=[
            InvoiceMessage(
                identifier=mensaje["identificador"],
                message=mensaje["mensaje"],
                additional_information=mensaje.get("informacion_adicional"),
                type=mensaje["tipo"],
            )
            for mensaje in factura.mensajes_sri
        ],
        issue_date=factura.fecha_emision,
        subtotal=factura.subtotal,
        taxes=factura.impuestos,
        total=factura.total,
    )


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
            "Para descargar facturas debes iniciar sesi?n con tu usuario.",
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
