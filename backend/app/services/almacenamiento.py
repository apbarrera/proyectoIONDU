"""Almacenamiento privado de archivos RIDE en Supabase Storage."""

import logging
from pathlib import PurePosixPath

from supabase import Client

from app.core.errors import NotFoundError, ServiceUnavailableError

logger = logging.getLogger(__name__)

BUCKET_RIDES = "rides"
CONTENT_TYPE_PDF = "application/pdf"


class AlmacenamientoRideService:
    """Gestiona los PDF RIDE en un bucket privado de Supabase."""

    def __init__(self, cliente: Client, bucket: str = BUCKET_RIDES):
        self.cliente = cliente
        self.bucket = bucket

    @staticmethod
    def construir_ruta(empresa_id: int, factura_id: int) -> str:
        """Genera una ruta determinista y aislada por empresa y factura."""

        if empresa_id <= 0 or factura_id <= 0:
            raise ValueError("Los identificadores deben ser positivos.")

        return f"empresas/{empresa_id}/facturas/{factura_id}/ride.pdf"

    def guardar(self, empresa_id: int, factura_id: int, contenido: bytes) -> str:
        """Sube o reemplaza el RIDE y devuelve su ruta privada."""

        if not isinstance(contenido, bytes) or not contenido:
            raise ValueError("El contenido del RIDE debe ser un PDF no vacío.")

        ruta = self.construir_ruta(empresa_id, factura_id)

        try:
            self.cliente.storage.from_(self.bucket).upload(
                ruta,
                contenido,
                {
                    "content-type": CONTENT_TYPE_PDF,
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )
        except Exception:
            logger.error("No se pudo almacenar el RIDE en Supabase Storage.")
            raise ServiceUnavailableError(
                "No fue posible almacenar el PDF de la factura.",
                code="RIDE_STORAGE_UNAVAILABLE",
            ) from None

        return ruta

    def descargar(self, ruta: str) -> bytes:
        """Descarga un RIDE mediante su ruta privada."""

        if not isinstance(ruta, str) or not ruta.strip():
            raise NotFoundError("La factura no tiene un PDF RIDE registrado.")

        ruta_validada = PurePosixPath(ruta)

        if (
            ruta_validada.is_absolute()
            or ".." in ruta_validada.parts
            or not ruta.startswith("empresas/")
            or not ruta.endswith("/ride.pdf")
        ):
            raise NotFoundError("La ruta del PDF RIDE no es válida.")

        try:
            contenido = self.cliente.storage.from_(self.bucket).download(ruta)
        except Exception:
            logger.error("No se pudo recuperar el RIDE desde Supabase Storage.")
            raise ServiceUnavailableError(
                "No fue posible recuperar el PDF de la factura.",
                code="RIDE_STORAGE_UNAVAILABLE",
            ) from None

        if not contenido:
            raise NotFoundError("El PDF RIDE no está disponible.")

        return contenido
