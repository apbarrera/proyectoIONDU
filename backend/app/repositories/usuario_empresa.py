"""Empresa y rol del usuario autenticado.

EXCEPCIÓN a la regla de filtrar por id_empresa: esta consulta es la que AVERIGUA la
empresa del usuario. Busca por el id que viene verificado en el token de Supabase,
así que nadie puede pedir la empresa de otro usuario.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Rol, UsuarioEmpresa
from app.models.usuario_empresa import ACTIVO


@dataclass(frozen=True)
class Pertenencia:
    id_empresa: int
    rol: str
    nombre: str


def obtener_pertenencia_activa(db: Session, id_usuario: uuid.UUID) -> Pertenencia | None:
    fila = db.execute(
        select(UsuarioEmpresa.id_empresa, Rol.nombre, UsuarioEmpresa.nombre)
        .join(Rol, Rol.id_rol == UsuarioEmpresa.id_rol)
        .where(UsuarioEmpresa.id_usuario == id_usuario, UsuarioEmpresa.estado == ACTIVO)
    ).first()
    return Pertenencia(id_empresa=fila[0], rol=fila[1], nombre=fila[2]) if fila else None
