"""Consultas de gastos, categorías de gasto y proveedores: todas filtran por la empresa."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CategoriaGasto, Gasto, Proveedor
from app.repositories.comun import contiene_texto


class _DeLaEmpresa:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    def agregar(self, objeto) -> None:
        objeto.id_empresa = self._empresa_id
        self._db.add(objeto)
        self._db.flush()


class CategoriaGastoRepository(_DeLaEmpresa):
    def listar(self) -> list[CategoriaGasto]:
        stmt = (
            select(CategoriaGasto)
            .where(CategoriaGasto.id_empresa == self._empresa_id)
            .order_by(CategoriaGasto.nombre)
        )
        return list(self._db.scalars(stmt))

    def obtener(self, id_categoria: int) -> CategoriaGasto | None:
        return self._db.scalar(
            select(CategoriaGasto).where(
                CategoriaGasto.id_empresa == self._empresa_id,
                CategoriaGasto.id_categoria_gasto == id_categoria,
            )
        )

    def existe_nombre(self, nombre: str) -> bool:
        stmt = select(CategoriaGasto.id_categoria_gasto).where(
            CategoriaGasto.id_empresa == self._empresa_id,
            func.lower(CategoriaGasto.nombre) == nombre.lower(),
        )
        return self._db.scalar(stmt.limit(1)) is not None


class ProveedorRepository(_DeLaEmpresa):
    def _de_la_empresa(self):
        return select(Proveedor).where(Proveedor.id_empresa == self._empresa_id)

    def listar(self, *, buscar: str | None, offset: int, limit: int) -> tuple[list[Proveedor], int]:
        stmt = self._de_la_empresa()
        if buscar:
            stmt = stmt.where(
                contiene_texto(buscar, Proveedor.ruc_identificacion, Proveedor.razon_social)
            )
        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        filas = self._db.scalars(
            stmt.order_by(Proveedor.razon_social, Proveedor.id_proveedor)
            .offset(offset)
            .limit(limit)
        )
        return list(filas), total

    def obtener(self, id_proveedor: int) -> Proveedor | None:
        return self._db.scalar(self._de_la_empresa().where(Proveedor.id_proveedor == id_proveedor))

    def por_identificacion(self, identificacion: str) -> Proveedor | None:
        return self._db.scalar(
            self._de_la_empresa().where(Proveedor.ruc_identificacion == identificacion)
        )


class GastoRepository(_DeLaEmpresa):
    def _con_relaciones(self):
        return (
            select(Gasto, CategoriaGasto, Proveedor)
            .join(
                CategoriaGasto,
                (CategoriaGasto.id_categoria_gasto == Gasto.id_categoria_gasto)
                & (CategoriaGasto.id_empresa == Gasto.id_empresa),
            )
            .outerjoin(
                Proveedor,
                (Proveedor.id_proveedor == Gasto.id_proveedor)
                & (Proveedor.id_empresa == Gasto.id_empresa),
            )
            .where(Gasto.id_empresa == self._empresa_id)
        )

    def listar(
        self,
        *,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        id_categoria: int | None = None,
        id_proveedor: int | None = None,
        metodo_pago: str | None = None,
        monto_minimo: Decimal | None = None,
        monto_maximo: Decimal | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Gasto, CategoriaGasto, Proveedor | None]], int]:
        stmt = self._con_relaciones()
        filtros = [
            (desde, lambda v: Gasto.fecha >= v),
            (hasta, lambda v: Gasto.fecha < v),
            (id_categoria, lambda v: Gasto.id_categoria_gasto == v),
            (id_proveedor, lambda v: Gasto.id_proveedor == v),
            (metodo_pago, lambda v: Gasto.metodo_pago == v),
            (monto_minimo, lambda v: Gasto.monto >= v),
            (monto_maximo, lambda v: Gasto.monto <= v),
        ]
        for valor, condicion in filtros:
            if valor is not None:
                stmt = stmt.where(condicion(valor))
        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        filas = self._db.execute(
            stmt.order_by(Gasto.fecha.desc(), Gasto.id_gasto.desc()).offset(offset).limit(limit)
        ).all()
        return [(f[0], f[1], f[2]) for f in filas], total

    def obtener(self, id_gasto: int) -> tuple[Gasto, CategoriaGasto, Proveedor | None] | None:
        fila = self._db.execute(self._con_relaciones().where(Gasto.id_gasto == id_gasto)).first()
        return (fila[0], fila[1], fila[2]) if fila else None
