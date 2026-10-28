
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class Gasto(Base):
    __tablename__ = "gasto"

    __table_args__ = (
        UniqueConstraint(
            "id_empresa",
            "message_id_correo",
            name="gasto_empresa_message_id_correo_uq",
        ),
        UniqueConstraint(
            "id_empresa",
            "clave_acceso",
            name="gasto_empresa_clave_acceso_uq",
        ),
        CheckConstraint(
            "monto >= 0",
            name=conv("gasto_monto_check"),
        ),
        ForeignKeyConstraint(
            ["id_empresa", "id_categoria_gasto"],
            [
                "categoria_gasto.id_empresa",
                "categoria_gasto.id_categoria_gasto",
            ],
            ondelete="RESTRICT",
            name="gasto_categoria_empresa_fk",
        ),
        ForeignKeyConstraint(
            ["id_empresa", "id_proveedor"],
            ["proveedor.id_empresa", "proveedor.id_proveedor"],
            ondelete="SET NULL (id_proveedor)",
            name="gasto_proveedor_empresa_fk",
        ),
        ForeignKeyConstraint(
            ["id_usuario", "id_empresa"],
            [
                "usuario_empresa.id_usuario",
                "usuario_empresa.id_empresa",
            ],
            ondelete="RESTRICT",
            name="gasto_usuario_empresa_fk",
        ),
        Index(
            "idx_gasto_empresa_fecha",
            "id_empresa",
            text("fecha DESC"),
        ),
        Index("idx_gasto_proveedor", "id_proveedor"),
        Index("idx_gasto_usuario", "id_usuario"),
    )

    id_gasto: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="gasto_id_empresa_fkey",
        ),
        nullable=False,
    )

    id_categoria_gasto: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    id_usuario: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    id_proveedor: Mapped[int | None] = mapped_column(Integer)

    monto: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    numero_comprobante: Mapped[str | None] = mapped_column(String(50))

    # Identificadores opcionales de origen para hacer idempotentes las importaciones.
    # PostgreSQL permite múltiples NULL en una restricción UNIQUE, así que los gastos
    # manuales no requieren estos valores.
    message_id_correo: Mapped[str | None] = mapped_column(String(998))
    clave_acceso: Mapped[str | None] = mapped_column(String(49))

    concepto: Mapped[str] = mapped_column(Text, nullable=False)

    metodo_pago: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'CONFIRMADO'"),
    )
