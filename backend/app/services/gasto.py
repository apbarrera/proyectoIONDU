"""Reglas de negocio de gastos, categorías de gasto y proveedores (RF-3.1, 3.5, 3.6, 3.7).

- Las 7 categorías predefinidas de RF-3.5 se crean solas la primera vez que se piden.
- El RUC o la cédula del proveedor se validan con las reglas del SRI.
- Registrar o editar un gasto exige sesión: el gasto guarda qué usuario lo registró.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import CategoriaGasto, Gasto, Proveedor
from app.repositories.gasto import CategoriaGastoRepository, GastoRepository, ProveedorRepository
from app.schemas.common import Page
from app.schemas.gasto import (
    Expense,
    ExpenseCategory,
    ExpenseCategoryCreate,
    ExpenseCreate,
    ExpensePaymentMethod,
    ExpenseUpdate,
    Supplier,
    SupplierCreate,
    SupplierUpdate,
)
from app.services.venta import _rango_del_dia
from app.sri.identificacion import CONSUMIDOR_FINAL, TipoIdentificacion, validar_identificacion

PREDEFINIDA = "PREDEFINIDA"
ANULADO = "ANULADO"
DEL_USUARIO = "USUARIO"
CATEGORIAS_PREDEFINIDAS = (  # RF-3.5
    "Materia prima",
    "Servicios",
    "Transporte",
    "Empaque",
    "Mantenimiento",
    "Arriendo",
    "Otros gastos operativos",
)
_ZONA = ZoneInfo(TIMEZONE)


def _error(campo: str, mensaje: str, code: str = "VALIDATION_ERROR") -> UnprocessableError:
    return UnprocessableError(mensaje, code=code, details=[{"field": campo, "message": mensaje}])


def _vacio_no_permitido(cambios: dict, campos: dict[str, str]) -> None:
    for campo, alias in campos.items():
        if campo in cambios and cambios[campo] is None:
            raise _error(alias, "No puede estar vacío.")


def _confirmar(db: Session, mensaje: str, code: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:  # restricción única de la base (dos peticiones a la vez)
        db.rollback()
        raise ConflictError(mensaje, code=code) from exc


# ---------- Categorías ----------
def _a_categoria(c: CategoriaGasto) -> ExpenseCategory:
    return ExpenseCategory(
        id=c.id_categoria_gasto,
        name=c.nombre,
        description=c.descripcion,
        predefined=c.origen == PREDEFINIDA,
    )


class CategoriaGastoService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._repo = CategoriaGastoRepository(db, empresa_id)

    def _asegurar_predefinidas(self) -> list[CategoriaGasto]:
        categorias = self._repo.listar()
        if not categorias:
            for nombre in CATEGORIAS_PREDEFINIDAS:
                self._repo.agregar(CategoriaGasto(nombre=nombre, origen=PREDEFINIDA))
            try:
                self._db.commit()
            except IntegrityError:  # otra petición las sembró a la vez: basta con leerlas
                self._db.rollback()
            categorias = self._repo.listar()
        return categorias

    def listar(self) -> list[ExpenseCategory]:
        return [_a_categoria(c) for c in self._asegurar_predefinidas()]

    def crear(self, datos: ExpenseCategoryCreate) -> ExpenseCategory:
        self._asegurar_predefinidas()
        if self._repo.existe_nombre(datos.name):
            raise ConflictError(f"Ya existe la categoría {datos.name}.", code="CATEGORY_EXISTS")
        categoria = CategoriaGasto(
            nombre=datos.name, descripcion=datos.description or None, origen=DEL_USUARIO
        )
        self._repo.agregar(categoria)
        _confirmar(self._db, f"Ya existe la categoría {datos.name}.", "CATEGORY_EXISTS")
        return _a_categoria(categoria)


# ---------- Proveedores ----------
def _validar_identificacion(identificacion: str) -> str | None:
    """Valida un RUC (13 dígitos) o una cédula (10); devuelve la advertencia, si la hay."""
    if identificacion == CONSUMIDOR_FINAL or not identificacion.isdigit():
        raise _error(
            "identification",
            "Ingresa el RUC (13 dígitos) o la cédula (10 dígitos) del proveedor.",
            "INVALID_IDENTIFICATION",
        )
    tipos = {10: TipoIdentificacion.CEDULA, 13: TipoIdentificacion.RUC}
    if len(identificacion) not in tipos:
        raise _error(
            "identification",
            "Ingresa el RUC (13 dígitos) o la cédula (10 dígitos) del proveedor.",
            "INVALID_IDENTIFICATION",
        )
    resultado = validar_identificacion(tipos[len(identificacion)], identificacion)
    if not resultado.valida:
        raise _error("identification", resultado.error, "INVALID_IDENTIFICATION")
    return resultado.advertencia


def _a_proveedor(p: Proveedor) -> Supplier:
    advertencia = None
    if p.ruc_identificacion.isdigit() and len(p.ruc_identificacion) == 13:
        advertencia = validar_identificacion(
            TipoIdentificacion.RUC, p.ruc_identificacion
        ).advertencia
    return Supplier(
        id=p.id_proveedor,
        identification=p.ruc_identificacion,
        name=p.razon_social,
        phone=p.telefono,
        email=p.correo_electronico,
        address=p.direccion,
        identification_warning=advertencia,
    )


class ProveedorService:
    _COLUMNAS = {
        "identification": "ruc_identificacion",
        "name": "razon_social",
        "phone": "telefono",
        "email": "correo_electronico",
        "address": "direccion",
    }

    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._repo = ProveedorRepository(db, empresa_id)

    def listar(self, *, page: int, page_size: int, search: str | None) -> Page[Supplier]:
        filas, total = self._repo.listar(
            buscar=search.strip() if search else None,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page[Supplier](
            items=[_a_proveedor(p) for p in filas], total=total, page=page, page_size=page_size
        )

    def _obtener_o_404(self, id_proveedor: int) -> Proveedor:
        proveedor = self._repo.obtener(id_proveedor)
        if proveedor is None:
            raise NotFoundError("El proveedor no existe.")
        return proveedor

    def obtener(self, id_proveedor: int) -> Supplier:
        return _a_proveedor(self._obtener_o_404(id_proveedor))

    def buscar_por_identificacion(self, identificacion: str) -> Supplier:
        proveedor = self._repo.por_identificacion(identificacion.strip())
        if proveedor is None:
            raise NotFoundError("No hay un proveedor con esa identificación.")
        return _a_proveedor(proveedor)

    def _validar_libre(self, identificacion: str, excepto_id: int | None = None) -> None:
        existente = self._repo.por_identificacion(identificacion)
        if existente is not None and existente.id_proveedor != excepto_id:
            raise ConflictError(
                f"Ya existe un proveedor con la identificación {identificacion}.",
                code="SUPPLIER_EXISTS",
            )

    def crear(self, datos: SupplierCreate) -> Supplier:
        _validar_identificacion(datos.identification)
        self._validar_libre(datos.identification)
        proveedor = Proveedor(
            ruc_identificacion=datos.identification,
            razon_social=datos.name,
            telefono=datos.phone or None,
            correo_electronico=datos.email or None,
            direccion=datos.address or None,
        )
        self._repo.agregar(proveedor)
        _confirmar(self._db, "Ya existe un proveedor con esa identificación.", "SUPPLIER_EXISTS")
        return _a_proveedor(proveedor)

    def actualizar(self, id_proveedor: int, datos: SupplierUpdate) -> Supplier:
        proveedor = self._obtener_o_404(id_proveedor)
        cambios = datos.model_dump(exclude_unset=True)
        _vacio_no_permitido(cambios, {"identification": "identification", "name": "name"})
        if "identification" in cambios:
            _validar_identificacion(cambios["identification"])
            self._validar_libre(cambios["identification"], excepto_id=id_proveedor)
        for campo, valor in cambios.items():
            setattr(proveedor, self._COLUMNAS[campo], valor or None)
        _confirmar(self._db, "Ya existe un proveedor con esa identificación.", "SUPPLIER_EXISTS")
        return _a_proveedor(proveedor)


# ---------- Gastos ----------
def _a_gasto(gasto: Gasto, categoria: CategoriaGasto, proveedor: Proveedor | None) -> Expense:
    return Expense(
        id=gasto.id_gasto,
        date=gasto.fecha.astimezone(_ZONA),
        category_id=categoria.id_categoria_gasto,
        category_name=categoria.nombre,
        supplier_id=proveedor.id_proveedor if proveedor else None,
        supplier_name=proveedor.razon_social if proveedor else None,
        supplier_identification=proveedor.ruc_identificacion if proveedor else None,
        total=gasto.monto,
        description=gasto.concepto,
        payment_method=gasto.metodo_pago.lower(),
        receipt_number=gasto.numero_comprobante,
        status=gasto.estado.lower(),
        source="correo" if gasto.message_id_correo else "manual",
    )


def _en_ecuador(fecha: datetime | None) -> datetime:
    """Sin fecha: ahora. Una fecha sin zona horaria se toma como hora de Ecuador."""
    if fecha is None:
        return datetime.now(_ZONA)
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=_ZONA)


class GastoService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._repo = GastoRepository(db, empresa_id)
        self._categorias = CategoriaGastoRepository(db, empresa_id)
        self._proveedores = ProveedorRepository(db, empresa_id)

    def listar(
        self,
        *,
        page: int,
        page_size: int,
        desde: date | None = None,
        hasta: date | None = None,
        category_id: int | None = None,
        supplier_id: int | None = None,
        payment_method: ExpensePaymentMethod | None = None,
        min_total: Decimal | None = None,
        max_total: Decimal | None = None,
    ) -> Page[Expense]:
        inicio, fin = _rango_del_dia(desde, hasta)
        filas, total = self._repo.listar(
            desde=inicio,
            hasta=fin,
            id_categoria=category_id,
            id_proveedor=supplier_id,
            metodo_pago=payment_method.upper() if payment_method else None,
            monto_minimo=min_total,
            monto_maximo=max_total,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page[Expense](
            items=[_a_gasto(*fila) for fila in filas], total=total, page=page, page_size=page_size
        )

    def obtener(self, id_gasto: int) -> Expense:
        encontrado = self._repo.obtener(id_gasto)
        if encontrado is None:
            raise NotFoundError("El gasto no existe.")
        return _a_gasto(*encontrado)

    def _validar_relaciones(self, category_id: int | None, supplier_id: int | None) -> None:
        if category_id is not None and self._categorias.obtener(category_id) is None:
            raise _error("categoryId", "La categoría no existe.", "CATEGORY_NOT_FOUND")
        if supplier_id is not None and self._proveedores.obtener(supplier_id) is None:
            raise _error("supplierId", "El proveedor no existe.", "SUPPLIER_NOT_FOUND")

    def crear(self, datos: ExpenseCreate, id_usuario: uuid.UUID) -> Expense:
        self._validar_relaciones(datos.category_id, datos.supplier_id)
        gasto = Gasto(
            id_categoria_gasto=datos.category_id,
            id_proveedor=datos.supplier_id,
            id_usuario=id_usuario,
            monto=datos.total,
            fecha=_en_ecuador(datos.date),
            concepto=datos.description,
            metodo_pago=datos.payment_method.upper(),
            numero_comprobante=datos.receipt_number,
            estado="CONFIRMADO",
        )
        self._repo.agregar(gasto)
        self._db.commit()
        return self.obtener(gasto.id_gasto)

    def actualizar(self, id_gasto: int, datos: ExpenseUpdate) -> Expense:
        encontrado = self._repo.obtener(id_gasto)
        if encontrado is None:
            raise NotFoundError("El gasto no existe.")
        gasto = encontrado[0]
        if gasto.estado == ANULADO:
            raise ConflictError("Un gasto anulado no se puede editar.", code="EXPENSE_VOIDED")
        cambios = datos.model_dump(exclude_unset=True)
        _vacio_no_permitido(
            cambios,
            {
                "category_id": "categoryId",
                "total": "total",
                "description": "description",
                "payment_method": "paymentMethod",
                "date": "date",
            },
        )
        self._validar_relaciones(cambios.get("category_id"), cambios.get("supplier_id"))
        columnas = {
            "category_id": ("id_categoria_gasto", lambda v: v),
            "supplier_id": ("id_proveedor", lambda v: v),
            "total": ("monto", lambda v: v),
            "description": ("concepto", lambda v: v),
            "payment_method": ("metodo_pago", lambda v: v.upper()),
            "date": ("fecha", _en_ecuador),
            "receipt_number": ("numero_comprobante", lambda v: v),
        }
        for campo, valor in cambios.items():
            columna, convertir = columnas[campo]
            setattr(gasto, columna, convertir(valor) if valor is not None else None)
        self._db.commit()
        return self.obtener(id_gasto)

    def anular(self, id_gasto: int, motivo: str, quien: str | None) -> Expense:
        """RF-3.7: el gasto no se borra; queda `anulado`, con el motivo, y deja de contar."""
        encontrado = self._repo.obtener(id_gasto)
        if encontrado is None:
            raise NotFoundError("El gasto no existe.")
        gasto = encontrado[0]
        if gasto.estado == ANULADO:
            raise ConflictError("El gasto ya está anulado.", code="EXPENSE_ALREADY_VOIDED")
        fecha = datetime.now(_ZONA).strftime("%d/%m/%Y %H:%M")
        nota = f"[ANULADO el {fecha} por {quien or 'usuario'}: {motivo}]"
        gasto.concepto = f"{gasto.concepto} {nota}"
        gasto.estado = ANULADO
        self._db.commit()
        return self.obtener(id_gasto)
