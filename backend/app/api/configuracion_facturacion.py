"""Endpoints para administrar la configuración de facturación."""

from fastapi import APIRouter

from app.api.deps import DbSession, SoloAdministrador
from app.schemas.configuracion_facturacion import ConfiguracionFacturacion
from app.services.configuracion_facturacion import ConfiguracionFacturacionService

router = APIRouter(tags=["Configuración de facturación"])


@router.get(
    "/company/billing-config",
    response_model=ConfiguracionFacturacion | None,
)
def obtener_configuracion_facturacion(
    db: DbSession,
    contexto: SoloAdministrador,
) -> ConfiguracionFacturacion | None:
    servicio = ConfiguracionFacturacionService(db, contexto.empresa_id)
    return servicio.obtener()


@router.put(
    "/company/billing-config",
    response_model=ConfiguracionFacturacion,
)
def actualizar_configuracion_facturacion(
    datos: ConfiguracionFacturacion,
    db: DbSession,
    contexto: SoloAdministrador,
) -> ConfiguracionFacturacion:
    servicio = ConfiguracionFacturacionService(db, contexto.empresa_id)
    return servicio.actualizar(datos)
