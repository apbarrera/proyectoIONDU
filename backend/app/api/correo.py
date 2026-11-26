"""Correo de facturas de proveedores (RF-3.2, RF-3.3).

- /company/email-inbox: la cuenta IMAP de la empresa (solo el Administrador).
- /expense-drafts: facturas encontradas en el correo, para confirmar o descartar.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Body, Path, Query, Response

from app.api.deps import AuditorActual, ContextoActual, DbSession, EmpresaId, SoloAdministrador
from app.api.expenses import _id_usuario
from app.core.errors import NotFoundError
from app.schemas.correo import (
    EmailInbox,
    EmailInboxTestResult,
    EmailInboxUpdate,
    ExpenseDraft,
    ExpenseDraftConfirm,
)
from app.schemas.gasto import Expense
from app.services.correo import BorradorGastoService, BuzonCorreoService

router = APIRouter(tags=["Correo de facturas"])
Id = Annotated[int, Path(gt=0)]


@router.get("/company/email-inbox", response_model=EmailInbox)
def get_email_inbox(contexto: SoloAdministrador, db: DbSession):
    buzon = BuzonCorreoService(db, contexto.empresa_id).obtener()
    if buzon is None:
        raise NotFoundError("La empresa no tiene un correo de facturas configurado.")
    return buzon


@router.put("/company/email-inbox", response_model=EmailInbox)
def set_email_inbox(
    datos: EmailInboxUpdate, contexto: SoloAdministrador, db: DbSession, auditor: AuditorActual
):
    buzon = BuzonCorreoService(db, contexto.empresa_id).configurar(datos)
    auditor.registrar(
        "configuracion",
        "Configuró el correo de facturas",
        f"{datos.username} en {datos.server}:{datos.port}, carpeta {datos.folder}"
        f"{'' if datos.enabled else ' (desactivado)'}.",
    )
    return buzon


@router.delete("/company/email-inbox", status_code=204)
def delete_email_inbox(contexto: SoloAdministrador, db: DbSession, auditor: AuditorActual):
    BuzonCorreoService(db, contexto.empresa_id).eliminar()
    auditor.registrar("configuracion", "Quitó el correo de facturas", "Se dejó de leer el correo.")
    return Response(status_code=204)


@router.post("/company/email-inbox/test", response_model=EmailInboxTestResult)
def test_email_inbox(
    contexto: SoloAdministrador,
    db: DbSession,
    datos: Annotated[EmailInboxUpdate | None, Body()] = None,
):
    """Prueba la conexión con los datos del formulario (o los guardados) sin guardar nada."""
    return BuzonCorreoService(db, contexto.empresa_id).probar(datos)


@router.get("/expense-drafts", response_model=list[ExpenseDraft])
def list_expense_drafts(
    empresa_id: EmpresaId,
    db: DbSession,
    status: Annotated[
        Literal["pendiente", "convertido", "descartado"] | None, Query()
    ] = "pendiente",
):
    return BorradorGastoService(db, empresa_id).listar(status)


@router.post("/expense-drafts/{id}/confirm", response_model=Expense, status_code=201)
def confirm_expense_draft(
    id: Id,
    datos: ExpenseDraftConfirm,
    contexto: ContextoActual,
    db: DbSession,
    auditor: AuditorActual,
):
    gasto = BorradorGastoService(db, contexto.empresa_id).confirmar(
        id, datos, _id_usuario(contexto)
    )
    auditor.registrar(
        "gastos",
        "Registró gasto desde el correo",
        f"Gasto #{gasto.id} por ${gasto.total:.2f}: {gasto.description}",
        entidad="gasto",
        id_entidad=gasto.id,
    )
    return gasto


@router.post("/expense-drafts/{id}/discard", status_code=204)
def discard_expense_draft(id: Id, contexto: ContextoActual, db: DbSession, auditor: AuditorActual):
    BorradorGastoService(db, contexto.empresa_id).descartar(id)
    auditor.registrar("gastos", "Descartó un borrador del correo", f"Borrador #{id}.")
    return Response(status_code=204)
