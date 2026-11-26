"""Schemas de la auditoría (docs/API.md, sección 14)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.common import ApiModel

AuditModule = Literal[
    "auth", "ventas", "facturacion", "gastos", "inventario", "ia", "configuracion", "usuarios"
]


class AuditEntry(ApiModel):
    """Mismos nombres que `AuditEntry` del frontend."""

    id: int
    timestamp: datetime
    user_id: UUID | None
    user_name: str
    module: AuditModule
    action: str
    description: str
    entity: str | None = None
    entity_id: str | None = None
