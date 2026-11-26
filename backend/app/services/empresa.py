"""Datos de la empresa y su configuración de facturación electrónica.

La configuración del emisor se guarda en `empresa.datos_facturacion_electronica` con el
mismo validador que usa la facturación (ConfiguracionFacturacion): nunca se guarda una
configuración que luego haga fallar la emisión.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE, get_settings
from app.core.errors import NotFoundError, UnprocessableError
from app.models import Empresa
from app.schemas.configuracion_facturacion import ConfiguracionFacturacion
from app.schemas.empresa import (
    BillingSettings,
    BillingSettingsUpdate,
    Company,
    CompanyUpdate,
    ElectronicSignature,
)
from app.sri.certificado import DIAS_AVISO_VENCIMIENTO
from app.sri.simulado import usa_sri_simulado

_AMBIENTES = {"pruebas": "1", "produccion": "2"}
_COLUMNAS = {
    "business_name": "razon_social",
    "trade_name": "nombre_comercial",
    "economic_activity": "actividad_economica",
    "address": "direccion",
    "email": "correo_electronico",
}


def _firma(empresa: Empresa) -> ElectronicSignature:
    vence = empresa.certificado_fecha_vencimiento
    configurada = bool(empresa.certificado_p12_cifrado) and vence is not None
    dias = (vence - datetime.now(ZoneInfo(TIMEZONE)).date()).days if vence else None
    ambiente = (empresa.datos_facturacion_electronica or {}).get("ambiente")
    return ElectronicSignature(
        configured=configurada,
        expires_at=vence,
        expires_soon=configurada and 0 <= dias <= DIAS_AVISO_VENCIMIENTO,
        expired=configurada and dias < 0,
        simulated=usa_sri_simulado(
            empresa.id_empresa, ambiente or "", get_settings().sri_simulado_empresas
        ),
    )


def _facturacion(empresa: Empresa) -> BillingSettings | None:
    if not empresa.datos_facturacion_electronica:
        return None
    try:
        config = ConfiguracionFacturacion.model_validate(empresa.datos_facturacion_electronica)
    except ValidationError:
        return None  # configuración antigua o incompleta: se pide configurarla de nuevo
    return BillingSettings(
        environment="pruebas" if config.ambiente == "1" else "produccion",
        establishment=config.establecimiento,
        emission_point=config.punto_emision,
        required_to_keep_accounts=config.obligado_contabilidad,
        rimpe=config.contribuyente_rimpe,
        special_taxpayer=config.contribuyente_especial,
    )


def _a_company(empresa: Empresa) -> Company:
    return Company(
        id=empresa.id_empresa,
        ruc=empresa.ruc,
        business_name=empresa.razon_social,
        trade_name=empresa.nombre_comercial,
        economic_activity=empresa.actividad_economica,
        address=empresa.direccion,
        email=empresa.correo_electronico,
        electronic_signature=_firma(empresa),
        billing=_facturacion(empresa),
    )


class EmpresaService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    def _empresa(self) -> Empresa:
        empresa = self._db.get(Empresa, self._empresa_id)
        if empresa is None:
            raise NotFoundError("La empresa no existe.")
        return empresa

    def obtener(self) -> Company:
        return _a_company(self._empresa())

    def actualizar(self, datos: CompanyUpdate) -> Company:
        empresa = self._empresa()
        cambios = datos.model_dump(exclude_unset=True)
        for campo, alias in (("business_name", "businessName"), ("email", "email")):
            if campo in cambios and not cambios[campo]:
                raise UnprocessableError(
                    "Revisa los datos enviados.",
                    details=[{"field": alias, "message": "No puede estar vacío."}],
                )
        for campo, valor in cambios.items():
            texto = valor.strip() if isinstance(valor, str) else valor
            setattr(empresa, _COLUMNAS[campo], texto or None)
        self._db.commit()
        return _a_company(empresa)

    def configurar_facturacion(self, datos: BillingSettingsUpdate) -> Company:
        empresa = self._empresa()
        config = ConfiguracionFacturacion(
            ambiente=_AMBIENTES[datos.environment],
            establecimiento=datos.establishment,
            punto_emision=datos.emission_point,
            obligado_contabilidad=datos.required_to_keep_accounts,
            contribuyente_especial=datos.special_taxpayer,
            contribuyente_rimpe=datos.rimpe,
        )
        empresa.datos_facturacion_electronica = config.model_dump()
        self._db.commit()
        return _a_company(empresa)
