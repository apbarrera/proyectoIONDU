"""Datos de la empresa y configuración de facturación (docs/API.md, sección 10).

Cualquier usuario de la empresa puede consultarlos; solo el Administrador los modifica.
"""

from fastapi import APIRouter

from app.api.deps import ContextoActual, DbSession, SoloAdministrador
from app.schemas.empresa import BillingSettingsUpdate, Company, CompanyUpdate
from app.services.empresa import EmpresaService

router = APIRouter(tags=["Empresa"])


@router.get("/company", response_model=Company)
def get_company(contexto: ContextoActual, db: DbSession):
    return EmpresaService(db, contexto.empresa_id).obtener()


@router.put("/company", response_model=Company)
def update_company(datos: CompanyUpdate, contexto: SoloAdministrador, db: DbSession):
    return EmpresaService(db, contexto.empresa_id).actualizar(datos)


@router.put("/company/billing-settings", response_model=Company)
def update_billing_settings(
    datos: BillingSettingsUpdate, contexto: SoloAdministrador, db: DbSession
):
    return EmpresaService(db, contexto.empresa_id).configurar_facturacion(datos)
