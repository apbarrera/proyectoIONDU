
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class DashboardFinanciero(Base):
    __tablename__ = "dashboard_financiero"

    __table_args__ = (
        CheckConstraint(
            "productos_stock_bajo >= 0",
            name="productos_stock_bajo",
        ),
        CheckConstraint(
            "ventas_registradas >= 0",
            name="ventas_registradas",
        ),
        CheckConstraint(
            "periodo ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'",
            name=conv("dashboard_periodo_formato_ck"),
        ),
        UniqueConstraint(
            "id_empresa",
            "periodo",
            name="dashboard_empresa_periodo_uq",
        ),
    )

    id_dashboard: Mapped[int] = mapped_column(
        Integer,
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "empresa.id_empresa",
            name="dashboard_financiero_id_empresa_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    periodo: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
    )

    ingresos_totales: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0"),
    )

    gastos_totales: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0"),
    )

    utilidad_neta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0"),
    )

    ventas_registradas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    gastos_por_categoria: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    estado_inventario: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    productos_stock_bajo: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    fecha_calculo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
