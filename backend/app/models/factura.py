from datetime import datetime
from decimal import Decimal

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class Factura(Base):
    __tablename__ = "factura"

    __table_args__ = (
        CheckConstraint(
            "impuestos >= 0",
            name=conv("factura_impuestos_check"),
        ),
        CheckConstraint(
            "numero_comprobante ~ '^[0-9]{3}-[0-9]{3}-[0-9]{9}$'",
            name=conv("factura_numero_formato_ck"),
        ),
        CheckConstraint(
            "subtotal >= 0",
            name=conv("factura_subtotal_check"),
        ),
        CheckConstraint(
            "total >= 0",
            name=conv("factura_total_check"),
        ),
        CheckConstraint(
            "intentos_envio >= 0",
            name=conv("factura_intentos_envio_check"),
        ),
        UniqueConstraint(
            "id_venta",
            name=conv("factura_id_venta_key"),
        ),
        UniqueConstraint(
            "id_empresa",
            "numero_comprobante",
            name="factura_empresa_numero_uq",
        ),
        UniqueConstraint(
            "clave_acceso",
            name=conv("factura_clave_acceso_key"),
        ),
        ForeignKeyConstraint(
            ["id_empresa", "id_venta"],
            ["venta.id_empresa", "venta.id_venta"],
            ondelete="CASCADE",
            name="factura_venta_empresa_fk",
        ),
        Index(
            "idx_factura_empresa_fecha",
            "id_empresa",
            text("fecha_emision DESC"),
        ),
    )

    id_factura: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="factura_id_empresa_fkey",
        ),
        nullable=False,
    )

    id_venta: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    numero_comprobante: Mapped[str] = mapped_column(
        String(17),
        nullable=False,
    )

    clave_acceso: Mapped[str | None] = mapped_column(String(49), nullable=True)

    estado_autorizacion: Mapped[str] = mapped_column(String(30), nullable=False)

    numero_autorizacion: Mapped[str | None] = mapped_column(String(49))

    fecha_autorizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    mensajes_sri: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    intentos_envio: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    impuestos: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    fecha_emision: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    xml_firmado: Mapped[str | None] = mapped_column(Text)

    xml_autorizado: Mapped[str | None] = mapped_column(Text)

    pdf_ride_path: Mapped[str | None] = mapped_column(String(255))
