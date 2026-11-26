"""Endpoints de gastos, categorías de gasto y proveedores (docs/API.md, sección 11).

Solo reciben la petición y llaman al servicio; las reglas viven en app/services.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import AuditorActual, ContextoActual, DbSession, EmpresaId, SoloAdministrador
from app.core.errors import ForbiddenError
from app.schemas.common import Page, VoidRequest
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
from app.services.gasto import CategoriaGastoService, GastoService, ProveedorService

router = APIRouter(tags=["Gastos"])

Id = Annotated[int, Path(gt=0)]


def _id_usuario(contexto: ContextoActual):
    # El gasto guarda qué usuario lo registró: el encabezado de desarrollo no tiene usuario.
    if contexto.usuario is None:
        raise ForbiddenError(
            "Para registrar gastos debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )
    return contexto.usuario.id


# ---------- Categorías ----------
@router.get("/expense-categories", response_model=list[ExpenseCategory])
def list_expense_categories(empresa_id: EmpresaId, db: DbSession):
    return CategoriaGastoService(db, empresa_id).listar()


@router.post("/expense-categories", response_model=ExpenseCategory, status_code=201)
def create_expense_category(datos: ExpenseCategoryCreate, empresa_id: EmpresaId, db: DbSession):
    return CategoriaGastoService(db, empresa_id).crear(datos)


# ---------- Proveedores ----------
@router.get("/suppliers", response_model=Page[Supplier])
def list_suppliers(
    empresa_id: EmpresaId,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    return ProveedorService(db, empresa_id).listar(page=page, page_size=page_size, search=search)


# Va antes de /suppliers/{id} para que "lookup" no se lea como un id.
@router.get("/suppliers/lookup", response_model=Supplier)
def lookup_supplier(
    empresa_id: EmpresaId,
    db: DbSession,
    identification: Annotated[str, Query(min_length=1, max_length=20)],
):
    return ProveedorService(db, empresa_id).buscar_por_identificacion(identification)


@router.get("/suppliers/{id}", response_model=Supplier)
def get_supplier(id: Id, empresa_id: EmpresaId, db: DbSession):
    return ProveedorService(db, empresa_id).obtener(id)


@router.post("/suppliers", response_model=Supplier, status_code=201)
def create_supplier(
    datos: SupplierCreate, empresa_id: EmpresaId, db: DbSession, auditor: AuditorActual
):
    proveedor = ProveedorService(db, empresa_id).crear(datos)
    auditor.registrar(
        "gastos",
        "Registró proveedor",
        f"{proveedor.name} ({proveedor.identification}).",
        entidad="proveedor",
        id_entidad=proveedor.id,
    )
    return proveedor


@router.patch("/suppliers/{id}", response_model=Supplier)
def update_supplier(
    id: Id, datos: SupplierUpdate, empresa_id: EmpresaId, db: DbSession, auditor: AuditorActual
):
    proveedor = ProveedorService(db, empresa_id).actualizar(id, datos)
    auditor.registrar(
        "gastos",
        "Editó proveedor",
        f"{proveedor.name}: {_campos(datos)}.",
        entidad="proveedor",
        id_entidad=id,
    )
    return proveedor


def _campos(datos) -> str:
    """Campos que se cambiaron, con los nombres del contrato (camelCase)."""
    return ", ".join(datos.model_dump(exclude_unset=True, by_alias=True)) or "sin cambios"


# ---------- Gastos ----------
@router.get("/expenses", response_model=Page[Expense])
def list_expenses(
    empresa_id: EmpresaId,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    desde: Annotated[date | None, Query(alias="from")] = None,  # "from" es palabra reservada
    hasta: Annotated[date | None, Query(alias="to")] = None,
    category_id: Annotated[int | None, Query(alias="categoryId", gt=0)] = None,
    supplier_id: Annotated[int | None, Query(alias="supplierId", gt=0)] = None,
    payment_method: Annotated[ExpensePaymentMethod | None, Query(alias="paymentMethod")] = None,
    min_total: Annotated[Decimal | None, Query(alias="minTotal", ge=0)] = None,
    max_total: Annotated[Decimal | None, Query(alias="maxTotal", ge=0)] = None,
):
    return GastoService(db, empresa_id).listar(
        page=page,
        page_size=page_size,
        desde=desde,
        hasta=hasta,
        category_id=category_id,
        supplier_id=supplier_id,
        payment_method=payment_method,
        min_total=min_total,
        max_total=max_total,
    )


@router.get("/expenses/{id}", response_model=Expense)
def get_expense(id: Id, empresa_id: EmpresaId, db: DbSession):
    return GastoService(db, empresa_id).obtener(id)


@router.post("/expenses", response_model=Expense, status_code=201)
def create_expense(
    datos: ExpenseCreate, contexto: ContextoActual, db: DbSession, auditor: AuditorActual
):
    id_usuario = _id_usuario(contexto)
    gasto = GastoService(db, contexto.empresa_id).crear(datos, id_usuario)
    auditor.registrar(
        "gastos",
        "Registró gasto",
        f"Gasto #{gasto.id} por ${gasto.total:.2f}: {gasto.description}",
        entidad="gasto",
        id_entidad=gasto.id,
    )
    return gasto


@router.patch("/expenses/{id}", response_model=Expense)
def update_expense(
    id: Id,
    datos: ExpenseUpdate,
    contexto: ContextoActual,
    db: DbSession,
    auditor: AuditorActual,
):
    _id_usuario(contexto)
    gasto = GastoService(db, contexto.empresa_id).actualizar(id, datos)
    auditor.registrar(
        "gastos",
        "Editó gasto",
        f"Gasto #{id}: {_campos(datos)}.",
        entidad="gasto",
        id_entidad=id,
    )
    return gasto


# RF-3.7: solo el Administrador anula; el gasto queda en el historial como "anulado".
@router.post("/expenses/{id}/void", response_model=Expense)
def void_expense(
    id: Id,
    datos: VoidRequest,
    contexto: SoloAdministrador,
    db: DbSession,
    auditor: AuditorActual,
):
    id_usuario = _id_usuario(contexto)
    gasto = GastoService(db, contexto.empresa_id).anular(
        id, datos.reason, contexto.nombre, id_usuario
    )
    auditor.registrar(
        "gastos",
        "Anuló gasto",
        f"Gasto #{id} por ${gasto.total:.2f}. Motivo: {datos.reason}",
        entidad="gasto",
        id_entidad=id,
    )
    return gasto
