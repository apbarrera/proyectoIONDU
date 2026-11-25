"""Consultas de clientes (patrón Repositorio): todas filtran por la empresa."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Cliente
from app.repositories.comun import contiene_texto


class ClienteRepository:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    def _de_la_empresa(self):
        return select(Cliente).where(Cliente.id_empresa == self._empresa_id)

    def listar(
        self, *, buscar: str | None = None, offset: int = 0, limit: int = 20
    ) -> tuple[list[Cliente], int]:
        stmt = self._de_la_empresa()
        if buscar:
            stmt = stmt.where(
                contiene_texto(buscar, Cliente.identificacion, Cliente.nombre_razon_social)
            )
        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        clientes = self._db.scalars(
            stmt.order_by(Cliente.nombre_razon_social, Cliente.id_cliente)
            .offset(offset)
            .limit(limit)
        )
        return list(clientes), total

    def obtener(self, id_cliente: int) -> Cliente | None:
        return self._db.scalar(self._de_la_empresa().where(Cliente.id_cliente == id_cliente))

    def buscar_por_identificacion(self, identificacion: str) -> Cliente | None:
        stmt = self._de_la_empresa().where(Cliente.identificacion == identificacion)
        return self._db.scalar(stmt.order_by(Cliente.id_cliente).limit(1))

    def existe(self, tipo: str, identificacion: str, *, excepto_id: int | None = None) -> bool:
        stmt = select(Cliente.id_cliente).where(
            Cliente.id_empresa == self._empresa_id,
            Cliente.tipo_identificacion == tipo,
            Cliente.identificacion == identificacion,
        )
        if excepto_id is not None:
            stmt = stmt.where(Cliente.id_cliente != excepto_id)
        return self._db.scalar(stmt.limit(1)) is not None

    def agregar(self, cliente: Cliente) -> Cliente:
        cliente.id_empresa = self._empresa_id
        self._db.add(cliente)
        self._db.flush()
        return cliente
