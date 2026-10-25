"""Reglas de negocio de categorías y productos.

Traduce entre la API (docs/API.md, en inglés) y la base (en español), valida las
reglas que dependen de los datos guardados y confirma cada operación (commit).
"""

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import CategoriaProducto, Producto
from app.repositories.producto import CategoriaProductoRepository, ProductoRepository
from app.schemas.common import Page
from app.schemas.producto import (
    Category,
    CategoryCreate,
    Product,
    ProductCreate,
    ProductType,
    ProductUpdate,
)

# Campo de la API -> columna de la base (los que se pueden escribir).
_COLUMNAS = {
    "sku": "codigo_principal",
    "name": "nombre",
    "description": "descripcion",
    "category_id": "id_categoria_producto",
    "type": "tipo",
    "unit": "unidad_medida",
    "sale_price": "precio_venta",
    "cost": "precio_compra",
    "applies_vat": "aplica_iva",
    "current_stock": "stock_actual",
    "min_stock": "stock_minimo",
}
# Columnas NOT NULL: al editar, no se pueden enviar vacías (null).
_OBLIGATORIOS = {"sku", "name", "category_id", "type", "unit", "sale_price", "cost", "applies_vat"}
# Nombre del campo en el JSON (sale_price -> salePrice), para los mensajes de error.
_ALIAS = {campo: info.alias for campo, info in ProductUpdate.model_fields.items()}


def _a_category(categoria: CategoriaProducto) -> Category:
    return Category(
        id=categoria.id_categoria_producto,
        name=categoria.nombre,
        description=categoria.descripcion,
    )


def _a_product(producto: Producto, nombre_categoria: str) -> Product:
    stock_bajo = (
        producto.stock_minimo is not None and producto.stock_actual <= producto.stock_minimo
    )
    return Product(
        id=producto.id_producto,
        sku=producto.codigo_principal,
        name=producto.nombre,
        description=producto.descripcion,
        category_id=producto.id_categoria_producto,
        category_name=nombre_categoria,
        type=producto.tipo.lower(),
        unit=producto.unidad_medida,
        sale_price=producto.precio_venta,
        cost=producto.precio_compra,
        applies_vat=producto.aplica_iva,
        current_stock=producto.stock_actual,
        min_stock=producto.stock_minimo,
        low_stock=stock_bajo,
    )


def _a_columnas(campos: dict) -> dict:
    """Pasa {campo_api: valor} a {columna: valor}; el tipo se guarda en mayúsculas."""
    columnas = {_COLUMNAS[campo]: valor for campo, valor in campos.items()}
    if "tipo" in columnas:
        columnas["tipo"] = columnas["tipo"].upper()
    return columnas


class CategoriaProductoService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._repo = CategoriaProductoRepository(db, empresa_id)

    def listar(self) -> list[Category]:
        return [_a_category(c) for c in self._repo.listar()]

    def crear(self, datos: CategoryCreate) -> Category:
        categoria = self._repo.agregar(
            CategoriaProducto(nombre=datos.name, descripcion=datos.description or None)
        )
        self._db.commit()
        return _a_category(categoria)


class ProductoService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._repo = ProductoRepository(db, empresa_id)
        self._categorias = CategoriaProductoRepository(db, empresa_id)

    def listar(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        category_id: int | None,
        type: ProductType | None,
        low_stock: bool,
    ) -> Page[Product]:
        filas, total = self._repo.listar(
            buscar=search.strip() if search else None,
            id_categoria=category_id,
            tipo=type.upper() if type else None,
            solo_stock_bajo=low_stock,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page[Product](
            items=[_a_product(p, cat) for p, cat in filas],
            total=total,
            page=page,
            page_size=page_size,
        )

    def obtener(self, id_producto: int) -> Product:
        return _a_product(*self._obtener_o_404(id_producto))

    def crear(self, datos: ProductCreate) -> Product:
        self._validar_categoria(datos.category_id)
        self._validar_codigo_libre(datos.sku)
        producto = self._repo.agregar(Producto(**_a_columnas(datos.model_dump())))
        self._db.commit()
        return self.obtener(producto.id_producto)

    def actualizar(self, id_producto: int, datos: ProductUpdate) -> Product:
        producto, _ = self._obtener_o_404(id_producto)
        cambios = datos.model_dump(exclude_unset=True)  # solo lo que se envió

        vacios = sorted(c for c in _OBLIGATORIOS if c in cambios and cambios[c] is None)
        if vacios:
            raise UnprocessableError(
                "Revisa los datos enviados.",
                details=[{"field": _ALIAS[c], "message": "No puede estar vacío."} for c in vacios],
            )
        if "category_id" in cambios:
            self._validar_categoria(cambios["category_id"])
        if "sku" in cambios:
            self._validar_codigo_libre(cambios["sku"], excepto_id=id_producto)

        for columna, valor in _a_columnas(cambios).items():
            setattr(producto, columna, valor)
        self._db.commit()
        return self.obtener(id_producto)

    # ---------- reglas ----------
    def _obtener_o_404(self, id_producto: int) -> tuple[Producto, str]:
        # Si es de otra empresa, también es 404: no se revela que existe.
        encontrado = self._repo.obtener(id_producto)
        if encontrado is None:
            raise NotFoundError("El producto no existe.")
        return encontrado

    def _validar_categoria(self, id_categoria: int) -> None:
        if self._categorias.obtener(id_categoria) is None:
            raise UnprocessableError(
                "La categoría no existe.",
                code="CATEGORY_NOT_FOUND",
                details=[{"field": "categoryId", "message": "La categoría no existe."}],
            )

    def _validar_codigo_libre(self, codigo: str, *, excepto_id: int | None = None) -> None:
        # Mientras la tabla no tenga UNIQUE (id_empresa, codigo_principal), esta es la única
        # protección; con la restricción en la base quedará cubierto también ante dos
        # peticiones simultáneas.
        if self._repo.existe_codigo(codigo, excepto_id=excepto_id):
            raise ConflictError(
                f"Ya existe un producto con el código {codigo}.", code="PRODUCT_SKU_TAKEN"
            )
