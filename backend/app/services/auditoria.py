"""Auditoría: quién hizo qué y cuándo, por empresa.

`Auditor.registrar` se llama desde los endpoints después de que la acción terminó bien.
Inserta en una transacción aparte: si fallara, la acción del usuario ya quedó guardada
y no se deshace; el fallo se registra en el log del servidor (no se oculta).
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.models import Auditoria, Usuario, UsuarioEmpresa
from app.schemas.auditoria import AuditEntry
from app.schemas.common import Page

logger = logging.getLogger("iondu.auditoria")
ZONA = ZoneInfo(TIMEZONE)
LONGITUD_DESCRIPCION = 1000

# INSERT explícito, sin RETURNING ni nextval(): un Operativo puede registrar en la
# auditoría pero no leerla (RLS), y con RETURNING PostgreSQL exigiría la política de
# lectura. Si SQLAlchemy generara el INSERT, pediría la clave nueva con RETURNING o con
# nextval() sobre la secuencia, que iondu_app tampoco necesita tener.
SQL_INSERTAR = text(
    """
    INSERT INTO auditoria (id_empresa, id_usuario, modulo, accion, descripcion, entidad, id_entidad)
    VALUES (:id_empresa, :id_usuario, :modulo, :accion, :descripcion, :entidad, :id_entidad)
    """
)


class Auditor:
    def __init__(self, db: Session, empresa_id: int, usuario_id: uuid.UUID | None):
        self.db = db
        self.empresa_id = empresa_id
        self.usuario_id = usuario_id

    def registrar(
        self,
        modulo: str,
        accion: str,
        descripcion: str,
        *,
        entidad: str | None = None,
        id_entidad: object | None = None,
    ) -> None:
        try:
            self.db.execute(
                SQL_INSERTAR,
                {
                    "id_empresa": self.empresa_id,
                    "id_usuario": self.usuario_id,
                    "modulo": modulo,
                    "accion": accion[:100],
                    "descripcion": descripcion[:LONGITUD_DESCRIPCION],
                    "entidad": entidad,
                    "id_entidad": str(id_entidad) if id_entidad is not None else None,
                },
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception(
                "No se pudo registrar la auditoría. empresa=%s modulo=%s accion=%s",
                self.empresa_id,
                modulo,
                accion,
            )


class AuditoriaService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def listar(
        self,
        *,
        page: int,
        page_size: int,
        modulo: str | None = None,
        id_usuario: uuid.UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> Page[AuditEntry]:
        filtros = [Auditoria.id_empresa == self.empresa_id]
        if modulo:
            filtros.append(Auditoria.modulo == modulo)
        if id_usuario:
            filtros.append(Auditoria.id_usuario == id_usuario)
        # Los días se cuentan en hora de Ecuador.
        if desde:
            filtros.append(Auditoria.fecha >= datetime.combine(desde, time.min, ZONA))
        if hasta:
            filtros.append(
                Auditoria.fecha < datetime.combine(hasta + timedelta(days=1), time.min, ZONA)
            )

        total = self.db.scalar(select(func.count()).select_from(Auditoria).where(*filtros))
        filas = self.db.execute(
            select(Auditoria, UsuarioEmpresa.nombre_visible, Usuario.email)
            .outerjoin(Usuario, Usuario.id == Auditoria.id_usuario)
            .outerjoin(
                UsuarioEmpresa,
                and_(
                    UsuarioEmpresa.id_usuario == Auditoria.id_usuario,
                    UsuarioEmpresa.id_empresa == Auditoria.id_empresa,
                ),
            )
            .where(*filtros)
            .order_by(Auditoria.fecha.desc(), Auditoria.id_auditoria.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return Page(
            items=[
                AuditEntry(
                    id=registro.id_auditoria,
                    timestamp=registro.fecha,
                    user_id=registro.id_usuario,
                    user_name=nombre or email or "Sistema",
                    module=registro.modulo,
                    action=registro.accion,
                    description=registro.descripcion,
                    entity=registro.entidad,
                    entity_id=registro.id_entidad,
                )
                for registro, nombre, email in filas
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
