"""Agente de IA: interpreta mensajes, guarda la propuesta y la ejecuta al confirmarla.

- La propuesta queda guardada en `accion_ia` (estado PENDIENTE). Al confirmar se ejecuta
  esa misma propuesta, con las correcciones permitidas, por el servicio de gastos: el
  navegador no puede pedirle al agente que haga otra cosa (RF-6.9).
- Cada llamada al modelo suma sus tokens en `consumo_tokens` (RF-6.14).
- Cualquier usuario de la empresa puede confirmar o cancelar (RF-6.11).
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.errors import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    UnprocessableError,
)
from app.ia.agente import PropuestaGasto, esquema, interpretar, prompt_sistema
from app.ia.cliente import ModeloLenguaje
from app.models import AccionIA, ConsumoTokens, Usuario, UsuarioEmpresa
from app.schemas.agente_ia import (
    AiAction,
    AiConfirm,
    AiExpenseProposal,
    AiProposal,
    AiReply,
)
from app.schemas.common import Page
from app.schemas.gasto import ExpenseCreate
from app.services.gasto import CategoriaGastoService, GastoService

ZONA = ZoneInfo(TIMEZONE)
PENDIENTE = "PENDIENTE"
CONFIRMADO = "CONFIRMADO"
CORREGIDO = "CORREGIDO"
CANCELADO = "CANCELADO"
SIN_PROPUESTA = "SIN_PROPUESTA"
ESTADOS_API = {
    PENDIENTE: "pendiente",
    CONFIRMADO: "confirmado",
    CORREGIDO: "corregido",
    CANCELADO: "cancelado",
    SIN_PROPUESTA: "sin_propuesta",
}


class ServicioAgente:
    def __init__(
        self,
        db: Session,
        empresa_id: int,
        usuario_id: uuid.UUID | None,
        modelo: ModeloLenguaje | None = None,
    ):
        self.db = db
        self.empresa_id = empresa_id
        self.usuario_id = usuario_id
        self.modelo = modelo

    # ---------- Interpretar ----------
    def interpretar(self, texto: str) -> AiReply:
        if self.modelo is None:
            raise ServiceUnavailableError(
                "El agente de IA no está configurado en este servidor.", code="AI_NOT_CONFIGURED"
            )
        categorias = self._categorias()
        hoy = datetime.now(ZONA).date()
        respuesta = self.modelo.completar_json(
            [
                {"role": "system", "content": prompt_sistema(list(categorias), hoy)},
                {"role": "user", "content": texto},
            ],
            esquema(list(categorias)),
        )
        self.db.add(
            ConsumoTokens(
                id_empresa=self.empresa_id,
                modelo_ia=respuesta.modelo,
                tokens_prompt=respuesta.tokens_prompt,
                tokens_completado=respuesta.tokens_completado,
            )
        )

        interpretacion = interpretar(respuesta.datos, list(categorias), hoy)
        gasto = interpretacion.gasto
        accion = AccionIA(
            id_empresa=self.empresa_id,
            id_usuario=self.usuario_id,
            tipo_accion="registrar_gasto" if gasto else interpretacion.tipo,
            instruccion_recibida=texto,
            payload_json={
                "respuesta": interpretacion.respuesta,
                "propuesta": gasto.como_json() if gasto else None,
                "modelo": respuesta.modelo,
            },
            estado=PENDIENTE if gasto else SIN_PROPUESTA,
        )
        self.db.add(accion)
        self.db.commit()

        return AiReply(
            action_id=accion.id_accion_ia if gasto else None,
            reply=interpretacion.respuesta,
            proposal=self._propuesta_api(gasto, categorias) if gasto else None,
        )

    # ---------- Confirmar y cancelar ----------
    def confirmar(self, id_accion: int, correcciones: AiConfirm) -> tuple[AccionIA, int]:
        accion = self._pendiente(id_accion)
        propuesta = PropuestaGasto.desde_json(accion.payload_json["propuesta"])
        categorias = self._categorias()
        cambios = correcciones.model_dump(exclude_unset=True, exclude_none=True)

        id_categoria = cambios.get("category_id") or categorias.get(propuesta.categoria)
        if id_categoria not in categorias.values():
            raise UnprocessableError("La categoría no existe.", code="CATEGORY_NOT_FOUND")
        total = Decimal(cambios.get("total", propuesta.total))
        iva = Decimal(cambios.get("iva_amount", propuesta.iva))
        descripcion = cambios.get("description", propuesta.descripcion)
        if propuesta.proveedor and "description" not in cambios:
            descripcion = f"{descripcion} ({propuesta.proveedor})"
        fecha: date | None = cambios.get("date", propuesta.fecha)

        datos = ExpenseCreate(
            category_id=id_categoria,
            total=total,
            iva_amount=iva,
            description=descripcion,
            payment_method=cambios.get("payment_method", propuesta.metodo_pago),
            date=datetime.combine(fecha, time(12, 0), ZONA) if fecha else None,
        )

        # El estado cambia en la misma transacción que crea el gasto: no se puede
        # confirmar dos veces aunque lleguen dos peticiones a la vez (fila bloqueada).
        accion.estado = CORREGIDO if cambios else CONFIRMADO
        gasto = GastoService(self.db, self.empresa_id).crear(datos, self.usuario_id)
        accion.payload_json = {**accion.payload_json, "id_gasto": gasto.id}
        self.db.commit()
        return accion, gasto.id

    def cancelar(self, id_accion: int) -> AccionIA:
        accion = self._pendiente(id_accion)
        accion.estado = CANCELADO
        self.db.commit()
        return accion

    # ---------- Historial ----------
    def historial(self, *, page: int, page_size: int) -> Page[AiAction]:
        filtro = AccionIA.id_empresa == self.empresa_id
        total = self.db.scalar(select(func.count()).select_from(AccionIA).where(filtro))
        filas = self.db.execute(
            select(AccionIA, UsuarioEmpresa.nombre_visible, Usuario.email)
            .outerjoin(Usuario, Usuario.id == AccionIA.id_usuario)
            .outerjoin(
                UsuarioEmpresa,
                (UsuarioEmpresa.id_usuario == AccionIA.id_usuario)
                & (UsuarioEmpresa.id_empresa == AccionIA.id_empresa),
            )
            .where(filtro)
            .order_by(AccionIA.fecha.desc(), AccionIA.id_accion_ia.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        categorias = self._categorias()
        items = []
        for accion, nombre, email in filas:
            datos = accion.payload_json or {}
            propuesta = (
                PropuestaGasto.desde_json(datos["propuesta"]) if datos.get("propuesta") else None
            )
            items.append(
                AiAction(
                    id=accion.id_accion_ia,
                    timestamp=accion.fecha,
                    user_name=nombre or email or "Usuario",
                    instruction=accion.instruccion_recibida,
                    reply=datos.get("respuesta", ""),
                    proposal=self._propuesta_api(propuesta, categorias) if propuesta else None,
                    status=ESTADOS_API.get(accion.estado, "sin_propuesta"),
                    expense_id=datos.get("id_gasto"),
                )
            )
        return Page(items=items, total=total, page=page, page_size=page_size)

    # ---------- Internos ----------
    def _categorias(self) -> dict[str, int]:
        return {c.name: c.id for c in CategoriaGastoService(self.db, self.empresa_id).listar()}

    def _pendiente(self, id_accion: int) -> AccionIA:
        accion = self.db.scalar(
            select(AccionIA)
            .where(AccionIA.id_accion_ia == id_accion, AccionIA.id_empresa == self.empresa_id)
            .with_for_update()
        )
        if accion is None:
            raise NotFoundError("La propuesta no existe.", code="AI_ACTION_NOT_FOUND")
        if accion.estado != PENDIENTE:
            raise ConflictError(
                "Esta propuesta ya fue confirmada o cancelada.", code="AI_ACTION_RESOLVED"
            )
        return accion

    @staticmethod
    def _propuesta_api(gasto: PropuestaGasto, categorias: dict[str, int]) -> AiProposal:
        return AiProposal(
            summary=gasto.resumen(),
            expense=AiExpenseProposal(
                total=gasto.total,
                iva_amount=gasto.iva,
                category_id=categorias.get(gasto.categoria, 0),
                category_name=gasto.categoria,
                description=gasto.descripcion,
                supplier_name=gasto.proveedor,
                payment_method=gasto.metodo_pago,
                date=gasto.fecha,
            ),
        )
