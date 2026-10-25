"""Consultas de categorías y productos (patrón Repositorio).

Cada repositorio recibe la empresa al crearse y TODAS sus consultas filtran por
ella: no existe forma de consultar sin empresa.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import CategoriaProducto, Producto


class CategoriaProductoRepository:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    def listar(self) -> list[CategoriaProducto]:
        stmt = (
            select(CategoriaProducto)
            .where(CategoriaProducto.id_empresa == self._empresa_id)
            .order_by(CategoriaProducto.nombre)
        )
        return list(self._db.scalars(stmt))

    def obtener(self, id_categoria: int) -> CategoriaProducto | None:
        stmt = select(CategoriaProducto).where(
            CategoriaProducto.id_empresa == self._empresa_id,
            CategoriaProducto.id_categoria_producto == id_categoria,
        )
        return self._db.scalar(stmt)

    def agregar(self, categoria: CategoriaProducto) -> CategoriaProducto:
        categoria.id_empresa = self._empresa_id
        self._db.add(categoria)
        self._db.flush()
        return categoria


class ProductoRepository:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    def _con_categoria(self):
        """Producto y nombre de su categoría, solo de esta empresa."""
        return (
            select(Producto, CategoriaProducto.nombre)
            .join(
                CategoriaProducto,
                CategoriaProducto.id_categoria_producto == Producto.id_categoria_producto,
            )
            .where(Producto.id_empresa == self._empresa_id)
        )

    def listar(
        self,
        *,
        buscar: str | None = None,
        id_categoria: int | None = None,
        tipo: str | None = None,
        solo_stock_bajo: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Producto, str]], int]:
        """Una página de productos (ordenados por nombre) y el total que cumple los filtros."""
        stmt = self._con_categoria()
        if buscar:
            # Escapa % y _ para que se busquen como texto y no como comodines.
            escapado = buscar.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
            patron = f"%{escapado}%"
            stmt = stmt.where(
                or_(
                    Producto.codigo_principal.ilike(patron, escape="\\"),
                    Producto.nombre.ilike(patron, escape="\\"),
                )
            )
        if id_categoria is not None:
            stmt = stmt.where(Producto.id_categoria_producto == id_categoria)
        if tipo is not None:
            stmt = stmt.where(Producto.tipo == tipo)
        if solo_stock_bajo:
            stmt = stmt.where(
                Producto.stock_minimo.is_not(None), Producto.stock_actual <= Producto.stock_minimo
            )

        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        filas = self._db.execute(
            stmt.order_by(Producto.nombre, Producto.id_producto).offset(offset).limit(limit)
        ).all()
        return [(fila[0], fila[1]) for fila in filas], total

    def obtener(self, id_producto: int) -> tuple[Producto, str] | None:
        fila = self._db.execute(
            self._con_categoria().where(Producto.id_producto == id_producto)
        ).first()
        return (fila[0], fila[1]) if fila else None

    def existe_codigo(self, codigo: str, *, excepto_id: int | None = None) -> bool:
        stmt = select(Producto.id_producto).where(
            Producto.id_empresa == self._empresa_id,
            func.lower(Producto.codigo_principal) == codigo.lower(),
        )
        if excepto_id is not None:
            stmt = stmt.where(Producto.id_producto != excepto_id)
        return self._db.scalar(stmt.limit(1)) is not None

    def agregar(self, producto: Producto) -> Producto:
        producto.id_empresa = self._empresa_id
        self._db.add(producto)
        self._db.flush()
        return producto
