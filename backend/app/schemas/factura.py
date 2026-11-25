"""Datos de salida de facturas electrónicas."""

from datetime import datetime
from typing import Literal

from app.schemas.common import Amount, ApiModel

InvoiceStatus = Literal[
    "autorizada",
    "rechazada",
    "por_enviar",
    "por_autorizar",
]


class InvoiceMessage(ApiModel):
    identifier: str
    message: str
    additional_information: str | None
    type: Literal["ERROR", "ADVERTENCIA", "INFORMATIVO"]


class Invoice(ApiModel):
    id: int
    sale_id: int
    invoice_number: str
    access_key: str | None  # se genera al firmar
    authorization_status: InvoiceStatus
    authorization_number: str | None
    authorization_date: datetime | None
    messages: list[InvoiceMessage]
    issue_date: datetime
    subtotal: Amount
    taxes: Amount
    total: Amount


def invoice_desde_factura(factura) -> Invoice:
    """Convierte una fila de `factura` en la respuesta de la API (un solo lugar para armarla)."""
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
            for mensaje in factura.mensajes_sri or []
        ],
        issue_date=factura.fecha_emision,
        subtotal=factura.subtotal,
        taxes=factura.impuestos,
        total=factura.total,
    )
