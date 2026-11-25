"""Consultas de empresas y pertenencias del usuario autenticado."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Empresa, Rol, UsuarioEmpresa
from app.models.usuario_empresa import ACTIVO


@dataclass(frozen=True)
class Pertenencia:
    id_empresa: int
    rol: str
    nombre: str


@dataclass(frozen=True)
class EmpresaDisponible:
    id_empresa: int
    razon_social: str
    nombre_comercial: str | None
    ruc: str
    rol: str


def obtener_empresas_activas(
    db: Session,
    id_usuario: uuid.UUID,
) -> list[EmpresaDisponible]:
    """Devuelve las empresas con pertenencia activa del usuario."""

    filas = db.execute(
        select(
            Empresa.id_empresa,
            Empresa.razon_social,
            Empresa.nombre_comercial,
            Empresa.ruc,
            Rol.nombre,
        )
        .join(
            UsuarioEmpresa,
            UsuarioEmpresa.id_empresa == Empresa.id_empresa,
        )
        .join(Rol, Rol.id_rol == UsuarioEmpresa.id_rol)
        .where(
            UsuarioEmpresa.id_usuario == id_usuario,
            UsuarioEmpresa.estado == ACTIVO,
        )
        .order_by(Empresa.razon_social, Empresa.id_empresa)
    ).all()

    return [
        EmpresaDisponible(
            id_empresa=fila[0],
            razon_social=fila[1],
            nombre_comercial=fila[2],
            ruc=fila[3],
            rol=fila[4],
        )
        for fila in filas
    ]


def obtener_pertenencia_activa(
    db: Session,
    id_usuario: uuid.UUID,
    id_empresa: int | None = None,
) -> Pertenencia | None:
    """Obtiene una pertenencia activa, sin elegir arbitrariamente entre varias.

    Si no se especifica empresa, solo devuelve un resultado cuando existe
    exactamente una pertenencia activa.
    """

    consulta = (
        select(
            UsuarioEmpresa.id_empresa,
            Rol.nombre,
            UsuarioEmpresa.nombre_visible,
        )
        .join(Rol, Rol.id_rol == UsuarioEmpresa.id_rol)
        .where(
            UsuarioEmpresa.id_usuario == id_usuario,
            UsuarioEmpresa.estado == ACTIVO,
        )
    )

    if id_empresa is not None:
        consulta = consulta.where(UsuarioEmpresa.id_empresa == id_empresa)

    filas = db.execute(consulta.limit(2)).all()

    if len(filas) != 1:
        return None

    fila = filas[0]

    return Pertenencia(
        id_empresa=fila[0],
        rol=fila[1],
        nombre=fila[2] or "",
    )
