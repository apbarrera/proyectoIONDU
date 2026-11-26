"""Almacenamiento privado de los PDF RIDE por la API S3.

El mismo código sirve para SeaweedFS (desarrollo local), el endpoint S3 de Supabase
Storage o cualquier proveedor compatible: solo cambian las variables STORAGE_*.
Los contenedores no guardan archivos en disco.
"""

import logging
from pathlib import PurePosixPath
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.errors import NotFoundError, ServiceUnavailableError

logger = logging.getLogger(__name__)

BUCKET_RIDES = "rides"
CONTENT_TYPE_PDF = "application/pdf"
CODIGOS_NO_EXISTE = {"NoSuchKey", "404", "NotFound"}
BUCKET_YA_EXISTE = {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}


def crear_cliente_s3(settings) -> Any | None:
    """Cliente S3 según la configuración; None si falta el endpoint o las credenciales."""
    if not (
        settings.storage_endpoint_url
        and settings.storage_access_key_id
        and settings.storage_secret_access_key
    ):
        return None
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        region_name=settings.storage_region,
        aws_access_key_id=settings.storage_access_key_id,
        aws_secret_access_key=settings.storage_secret_access_key.get_secret_value(),
        # Rutas del tipo endpoint/bucket/clave: las que usan SeaweedFS y Supabase.
        config=Config(
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=20,
            retries={"max_attempts": 2},
        ),
    )


def crear_almacenamiento(settings, *, crear_bucket: bool = False):
    """Servicio listo para usar, o None si el almacenamiento no está configurado.

    Con `crear_bucket` (solo desarrollo) crea el bucket si no existe; en producción el
    bucket privado se crea al preparar el ambiente.
    """
    cliente = crear_cliente_s3(settings)
    if cliente is None:
        logger.warning("Almacenamiento S3 no configurado: los RIDE no estarán disponibles.")
        return None
    servicio = AlmacenamientoRideService(cliente, settings.storage_bucket)
    if crear_bucket:
        servicio.asegurar_bucket()
    return servicio


class AlmacenamientoRideService:
    """Gestiona los PDF RIDE en un bucket privado."""

    def __init__(self, cliente, bucket: str = BUCKET_RIDES):
        self.cliente = cliente
        self.bucket = bucket

    @staticmethod
    def construir_ruta(empresa_id: int, factura_id: int) -> str:
        """Genera una ruta determinista y aislada por empresa y factura."""

        if empresa_id <= 0 or factura_id <= 0:
            raise ValueError("Los identificadores deben ser positivos.")

        return f"empresas/{empresa_id}/facturas/{factura_id}/ride.pdf"

    def asegurar_bucket(self) -> None:
        """Crea el bucket si no existe. Un fallo aquí no detiene el arranque."""
        try:
            self.cliente.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.cliente.create_bucket(Bucket=self.bucket)
                logger.info("Bucket %s creado.", self.bucket)
            except ClientError as exc:
                # La API arranca con varios procesos: otro pudo crearlo un instante antes.
                if exc.response.get("Error", {}).get("Code") not in BUCKET_YA_EXISTE:
                    logger.exception("No se pudo crear el bucket %s.", self.bucket)
            except BotoCoreError:
                logger.exception("No se pudo crear el bucket %s.", self.bucket)
        except BotoCoreError:
            logger.error("El almacenamiento S3 no responde; se reintentará al usarlo.")

    def guardar(self, empresa_id: int, factura_id: int, contenido: bytes) -> str:
        """Sube o reemplaza el RIDE y devuelve su ruta privada."""

        if not isinstance(contenido, bytes) or not contenido:
            raise ValueError("El contenido del RIDE debe ser un PDF no vacío.")

        ruta = self.construir_ruta(empresa_id, factura_id)

        try:
            self.cliente.put_object(
                Bucket=self.bucket,
                Key=ruta,
                Body=contenido,
                ContentType=CONTENT_TYPE_PDF,
            )
        except (ClientError, BotoCoreError):
            logger.error("No se pudo almacenar el RIDE en el almacenamiento S3.")
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
            respuesta = self.cliente.get_object(Bucket=self.bucket, Key=ruta)
            contenido = respuesta["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in CODIGOS_NO_EXISTE:
                raise NotFoundError("El PDF RIDE no está disponible.") from None
            logger.error("No se pudo recuperar el RIDE desde el almacenamiento S3.")
            raise ServiceUnavailableError(
                "No fue posible recuperar el PDF de la factura.",
                code="RIDE_STORAGE_UNAVAILABLE",
            ) from None
        except BotoCoreError:
            logger.error("El almacenamiento S3 no responde.")
            raise ServiceUnavailableError(
                "No fue posible recuperar el PDF de la factura.",
                code="RIDE_STORAGE_UNAVAILABLE",
            ) from None

        if not contenido:
            raise NotFoundError("El PDF RIDE no está disponible.")

        return contenido
