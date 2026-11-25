"""Reglas de negocio de clientes.

- La identificación se valida con las reglas del SRI (app/sri/identificacion.py).
- Si no se indica el tipo, se deduce: 10 dígitos = cédula, 13 dígitos = RUC.
- El consumidor final no se guarda como cliente: se usa directamente en la venta.
- Una identificación no se repite dentro de la empresa (también lo exige la base).
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import Cliente
from app.repositories.cliente import ClienteRepository
from app.schemas.cliente import Customer, CustomerCreate, CustomerUpdate, IdentificationType
from app.schemas.common import Page
from app.sri.identificacion import CONSUMIDOR_FINAL, TipoIdentificacion, validar_identificacion

# Tipo en la API <-> código del SRI guardado en la base.
_CODIGOS: dict[str, TipoIdentificacion] = {
    "cedula": TipoIdentificacion.CEDULA,
    "ruc": TipoIdentificacion.RUC,
    "pasaporte": TipoIdentificacion.PASAPORTE,
    "exterior": TipoIdentificacion.EXTERIOR,
}
_TIPOS = {codigo: tipo for tipo, codigo in _CODIGOS.items()}

_COLUMNAS = {
    "name": "nombre_razon_social",
    "address": "direccion",
    "phone": "telefono",
    "email": "correo_electronico",
}


def _error(campo: str, mensaje: str, code: str = "VALIDATION_ERROR") -> UnprocessableError:
    return UnprocessableError(mensaje, code=code, details=[{"field": campo, "message": mensaje}])


def _a_customer(cliente: Cliente) -> Customer:
    resultado = validar_identificacion(cliente.tipo_identificacion, cliente.identificacion)
    return Customer(
        id=cliente.id_cliente,
        identification_type=_TIPOS[TipoIdentificacion(cliente.tipo_identificacion)],
        identification=cliente.identificacion,
        name=cliente.nombre_razon_social,
        address=cliente.direccion,
        phone=cliente.telefono,
        email=cliente.correo_electronico,
        identification_warning=resultado.advertencia,
    )


def _tipo_validado(tipo: IdentificationType | None, identificacion: str) -> TipoIdentificacion:
    """Deduce el tipo si no viene y valida la identificación con las reglas del SRI."""
    if identificacion == CONSUMIDOR_FINAL:
        raise _error(
            "identification",
            "El consumidor final no se registra como cliente.",
            code="FINAL_CONSUMER_NOT_ALLOWED",
        )
    if tipo is None:
        if identificacion.isdigit() and len(identificacion) == 10:
            tipo = "cedula"
        elif identificacion.isdigit() and len(identificacion) == 13:
            tipo = "ruc"
        else:
            raise _error(
                "identificationType", "Indica el tipo de identificación (pasaporte o exterior)."
            )
    codigo = _CODIGOS[tipo]
    resultado = validar_identificacion(codigo, identificacion)
    if not resultado.valida:
        raise _error("identification", resultado.error, code="INVALID_IDENTIFICATION")
    return codigo


class ClienteService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._repo = ClienteRepository(db, empresa_id)

    def listar(self, *, page: int, page_size: int, search: str | None) -> Page[Customer]:
        clientes, total = self._repo.listar(
            buscar=search.strip() if search else None,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page[Customer](
            items=[_a_customer(c) for c in clientes], total=total, page=page, page_size=page_size
        )

    def obtener(self, id_cliente: int) -> Customer:
        return _a_customer(self._obtener_o_404(id_cliente))

    def buscar_por_identificacion(self, identificacion: str) -> Customer:
        cliente = self._repo.buscar_por_identificacion(identificacion.strip())
        if cliente is None:
            raise NotFoundError("No hay un cliente con esa identificación.")
        return _a_customer(cliente)

    def crear(self, datos: CustomerCreate) -> Customer:
        codigo = _tipo_validado(datos.identification_type, datos.identification)
        self._validar_libre(codigo, datos.identification)
        cliente = self._repo.agregar(
            Cliente(
                tipo_identificacion=codigo.value,
                identificacion=datos.identification,
                nombre_razon_social=datos.name,
                direccion=datos.address or None,
                telefono=datos.phone or None,
                correo_electronico=datos.email or None,
            )
        )
        self._confirmar()
        return _a_customer(cliente)

    def actualizar(self, id_cliente: int, datos: CustomerUpdate) -> Customer:
        cliente = self._obtener_o_404(id_cliente)
        cambios = datos.model_dump(exclude_unset=True)
        for campo, alias in (("identification", "identification"), ("name", "name")):
            if campo in cambios and cambios[campo] is None:
                raise _error(alias, "No puede estar vacío.")

        if "identification" in cambios or "identification_type" in cambios:
            identificacion = cambios.get("identification") or cliente.identificacion
            tipo = (
                cambios["identification_type"]
                if "identification_type" in cambios
                else _TIPOS[TipoIdentificacion(cliente.tipo_identificacion)]
            )
            codigo = _tipo_validado(tipo, identificacion)
            self._validar_libre(codigo, identificacion, excepto_id=id_cliente)
            cliente.tipo_identificacion = codigo.value
            cliente.identificacion = identificacion

        for campo, columna in _COLUMNAS.items():
            if campo in cambios:
                setattr(cliente, columna, cambios[campo] or None)
        self._confirmar()
        return _a_customer(cliente)

    # ---------- reglas ----------
    def _obtener_o_404(self, id_cliente: int) -> Cliente:
        cliente = self._repo.obtener(id_cliente)  # de otra empresa también es 404
        if cliente is None:
            raise NotFoundError("El cliente no existe.")
        return cliente

    def _validar_libre(self, codigo, identificacion: str, *, excepto_id: int | None = None):
        if self._repo.existe(codigo.value, identificacion, excepto_id=excepto_id):
            raise ConflictError(
                f"Ya existe un cliente con la identificación {identificacion}.",
                code="CUSTOMER_EXISTS",
            )

    def _confirmar(self) -> None:
        # La base también exige identificación única por empresa: cubre dos
        # peticiones simultáneas que pasaron la validación a la vez.
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "Ya existe un cliente con esa identificación.", code="CUSTOMER_EXISTS"
            ) from exc
