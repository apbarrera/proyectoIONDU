"""Endpoints de categorías y productos (docs/API.md, secciones 3 y 4).

Solo reciben la petición y llaman al servicio; las reglas viven en app/services.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import DbSession, EmpresaId
from app.schemas.common import Page
from app.schemas.producto import (
    Category,
    CategoryCreate,
    Product,
    ProductCreate,
    ProductType,
    ProductUpdate,
)
from app.services.producto import CategoriaProductoService, ProductoService

router = APIRouter(tags=["Productos"])

ProductId = Annotated[int, Path(gt=0)]


@router.get("/product-categories", response_model=list[Category])
def list_categories(empresa_id: EmpresaId, db: DbSession):
    return CategoriaProductoService(db, empresa_id).listar()


@router.post("/product-categories", response_model=Category, status_code=201)
def create_category(datos: CategoryCreate, empresa_id: EmpresaId, db: DbSession):
    return CategoriaProductoService(db, empresa_id).crear(datos)


@router.get("/products", response_model=Page[Product])
def list_products(
    empresa_id: EmpresaId,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    category_id: Annotated[int | None, Query(alias="categoryId", gt=0)] = None,
    type: ProductType | None = None,
    low_stock: Annotated[bool, Query(alias="lowStock")] = False,
):
    return ProductoService(db, empresa_id).listar(
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        type=type,
        low_stock=low_stock,
    )


@router.get("/products/{id}", response_model=Product)
def get_product(id: ProductId, empresa_id: EmpresaId, db: DbSession):
    return ProductoService(db, empresa_id).obtener(id)


@router.post("/products", response_model=Product, status_code=201)
def create_product(datos: ProductCreate, empresa_id: EmpresaId, db: DbSession):
    return ProductoService(db, empresa_id).crear(datos)


@router.patch("/products/{id}", response_model=Product)
def update_product(id: ProductId, datos: ProductUpdate, empresa_id: EmpresaId, db: DbSession):
    return ProductoService(db, empresa_id).actualizar(id, datos)
