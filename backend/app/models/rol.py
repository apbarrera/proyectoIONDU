from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Igual que database/schema.sql. Roles mínimos (RF-1.2): Administrador y Operativo.
ADMINISTRADOR = "Administrador"
OPERATIVO = "Operativo"


class Rol(Base):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))
