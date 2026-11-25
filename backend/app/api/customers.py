"""Endpoints de clientes (docs/API.md, sección 7).

Solo reciben la petición y llaman al servicio; las reglas viven en app/services.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import DbSession, EmpresaId
from app.schemas.cliente import Customer, CustomerCreate, CustomerUpdate
from app.schemas.common import Page
from app.services.cliente import ClienteService

router = APIRouter(tags=["Clientes"])

CustomerId = Annotated[int, Path(gt=0)]


@router.get("/customers", response_model=Page[Customer])
def list_customers(
    empresa_id: EmpresaId,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    return ClienteService(db, empresa_id).listar(page=page, page_size=page_size, search=search)


# Va antes de /customers/{id} para que "lookup" no se lea como un id.
@router.get("/customers/lookup", response_model=Customer)
def lookup_customer(
    empresa_id: EmpresaId,
    db: DbSession,
    identification: Annotated[str, Query(min_length=1, max_length=20)],
):
    return ClienteService(db, empresa_id).buscar_por_identificacion(identification)


@router.get("/customers/{id}", response_model=Customer)
def get_customer(id: CustomerId, empresa_id: EmpresaId, db: DbSession):
    return ClienteService(db, empresa_id).obtener(id)


@router.post("/customers", response_model=Customer, status_code=201)
def create_customer(datos: CustomerCreate, empresa_id: EmpresaId, db: DbSession):
    return ClienteService(db, empresa_id).crear(datos)


@router.patch("/customers/{id}", response_model=Customer)
def update_customer(id: CustomerId, datos: CustomerUpdate, empresa_id: EmpresaId, db: DbSession):
    return ClienteService(db, empresa_id).actualizar(id, datos)
