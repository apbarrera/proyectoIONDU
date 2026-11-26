"""Datos de la empresa y configuración de facturación (docs/API.md, sección 10).

Cualquier usuario de la empresa puede consultarlos; solo el Administrador los modifica.
"""

from fastapi import APIRouter

from app.api.deps import AuditorActual, ContextoActual, DbSession, SoloAdministrador
from app.schemas.empresa import BillingSettingsUpdate, Company, CompanyUpdate
from app.services.empresa import EmpresaService

router = APIRouter(tags=["Empresa"])


@router.get("/company", response_model=Company)
def get_company(contexto: ContextoActual, db: DbSession):
    return EmpresaService(db, contexto.empresa_id).obtener()


@router.put("/company", response_model=Company)
def update_company(
    datos: CompanyUpdate, contexto: SoloAdministrador, db: DbSession, auditor: AuditorActual
):
    empresa = EmpresaService(db, contexto.empresa_id).actualizar(datos)
    cambios = ", ".join(datos.model_dump(exclude_unset=True, by_alias=True))
    auditor.registrar(
        "configuracion", "Editó datos de la empresa", f"Campos: {cambios or 'sin cambios'}."
    )
    return empresa


@router.put("/company/billing-settings", response_model=Company)
def update_billing_settings(
    datos: BillingSettingsUpdate,
    contexto: SoloAdministrador,
    db: DbSession,
    auditor: AuditorActual,
):
    empresa = EmpresaService(db, contexto.empresa_id).configurar_facturacion(datos)
    auditor.registrar(
        "configuracion",
        "Cambió la configuración de facturación",
        f"Ambiente {datos.environment}, establecimiento {datos.establishment}, "
        f"punto de emisión {datos.emission_point}.",
    )
    return empresa
