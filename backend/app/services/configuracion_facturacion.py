from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, UnprocessableError
from app.models.empresa import Empresa
from app.schemas.configuracion_facturacion import ConfiguracionFacturacion


class ConfiguracionFacturacionService:
    """Gestiona la configuración tributaria de la empresa autenticada."""

    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def obtener(self) -> ConfiguracionFacturacion | None:
        """Devuelve la configuración existente, si fue registrada."""

        empresa = self._obtener_empresa()
        datos = empresa.datos_facturacion_electronica

        if datos is None:
            return None

        if not isinstance(datos, dict):
            raise UnprocessableError(
                "La configuración de facturación almacenada no tiene un formato válido."
            )

        return self._validar_datos(datos)

    def actualizar(
        self,
        configuracion: ConfiguracionFacturacion,
    ) -> ConfiguracionFacturacion:
        """Actualiza los campos tributarios sin eliminar otras claves JSONB."""

        empresa = self._obtener_empresa()
        existentes = empresa.datos_facturacion_electronica

        if existentes is None:
            datos = {}
        elif isinstance(existentes, dict):
            datos = dict(existentes)
        else:
            raise UnprocessableError(
                "La configuración de facturación almacenada no tiene un formato válido."
            )

        datos.update(configuracion.model_dump())
        empresa.datos_facturacion_electronica = datos

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return configuracion

    @staticmethod
    def _validar_datos(datos: dict) -> ConfiguracionFacturacion:
        """Valida los campos propios sin rechazar otras claves JSONB."""

        campos = ConfiguracionFacturacion.model_fields
        conocidos = {}

        for nombre, campo in campos.items():
            if nombre in datos:
                conocidos[nombre] = datos[nombre]
            elif campo.alias and campo.alias in datos:
                conocidos[nombre] = datos[campo.alias]

        try:
            return ConfiguracionFacturacion.model_validate(conocidos)
        except Exception as exc:
            raise UnprocessableError(
                "La configuración de facturación almacenada no es válida."
            ) from exc

    def _obtener_empresa(self) -> Empresa:
        empresa = self.db.scalar(select(Empresa).where(Empresa.id_empresa == self.empresa_id))

        if empresa is None:
            raise NotFoundError("No se encontró la empresa del usuario.")

        return empresa
