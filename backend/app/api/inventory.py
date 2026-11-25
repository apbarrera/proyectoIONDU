"""Endpoints de inventario: historial, entradas/salidas y ajustes (docs/API.md, sección 12).

Solo reciben la petición y llaman al servicio; las reglas viven en app/services.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import ContextoActual, DbSession, EmpresaId, SoloAdministrador
from app.core.errors import ForbiddenError
from app.schemas.common import Page
from app.schemas.inventario import (
    AdjustmentCreate,
    InventoryMovement,
    MovementCreate,
    MovementType,
    StockAdjustment,
)
from app.services.inventario import InventarioService

router = APIRouter(prefix="/inventory", tags=["Inventario"])


def _id_usuario(contexto):
    # El movimiento guarda quién lo hizo: el encabezado de desarrollo no tiene usuario.
    if contexto.usuario is None:
        raise ForbiddenError(
            "Para mover el inventario debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )
    return contexto.usuario.id


@router.get("/movements", response_model=Page[InventoryMovement])
def list_movements(
    empresa_id: EmpresaId,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    product_id: Annotated[int | None, Query(alias="productId", gt=0)] = None,
    type: Annotated[MovementType | None, Query()] = None,
    desde: Annotated[date | None, Query(alias="from")] = None,  # "from" es palabra reservada
    hasta: Annotated[date | None, Query(alias="to")] = None,
):
    return InventarioService(db, empresa_id).listar(
        page=page,
        page_size=page_size,
        product_id=product_id,
        type=type,
        desde=desde,
        hasta=hasta,
    )


@router.get("/movements/{id}", response_model=InventoryMovement)
def get_movement(id: Annotated[int, Path(gt=0)], empresa_id: EmpresaId, db: DbSession):
    return InventarioService(db, empresa_id).obtener(id)


@router.post("/movements", response_model=InventoryMovement, status_code=201)
def create_movement(datos: MovementCreate, contexto: ContextoActual, db: DbSession):
    id_usuario = _id_usuario(contexto)
    return InventarioService(db, contexto.empresa_id).registrar_movimiento(datos, id_usuario)


# RF-4.8: solo el Administrador corrige el stock contra el conteo físico.
@router.post("/adjustments", response_model=StockAdjustment, status_code=201)
def create_adjustment(datos: AdjustmentCreate, contexto: SoloAdministrador, db: DbSession):
    id_usuario = _id_usuario(contexto)
    return InventarioService(db, contexto.empresa_id).ajustar(datos, id_usuario)
