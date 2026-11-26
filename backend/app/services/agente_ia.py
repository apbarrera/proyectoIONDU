"""Agente de IA: interpreta mensajes, guarda la propuesta y la ejecuta al confirmarla.

- La propuesta queda guardada en `accion_ia` (estado PENDIENTE). Al confirmar se ejecuta
  esa misma propuesta, con las correcciones permitidas, por el servicio de gastos o de
  inventario: el navegador no puede pedirle al agente que haga otra cosa (RF-6.9).
- Cada llamada al modelo suma sus tokens en `consumo_tokens` (RF-6.14).
- Cualquier usuario de la empresa puede confirmar o cancelar (RF-6.11), salvo los
  ajustes por conteo, que son solo del Administrador (RF-4.8).
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
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnprocessableError,
)
from app.ia.agente import (
    Interpretacion,
    ProductoDisponible,
    PropuestaGasto,
    PropuestaInventario,
    esquema,
    interpretar,
    interpretar_imagen,
    prompt_imagen,
    prompt_sistema,
)
from app.ia.cliente import ModeloLenguaje, RespuestaModelo
from app.models import AccionIA, ConsumoTokens, Empresa, Producto, Usuario, UsuarioEmpresa
from app.schemas.agente_ia import (
    AiAction,
    AiConfirm,
    AiExpenseProposal,
    AiInventoryProposal,
    AiProposal,
    AiReply,
)
from app.schemas.common import Page
from app.schemas.gasto import ExpenseCreate
from app.schemas.inventario import AdjustmentCreate, MovementCreate
from app.services.gasto import CategoriaGastoService, GastoService
from app.services.inventario import InventarioService

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
# Productos que se le muestran al modelo (los activos de la empresa, por nombre).
MAX_PRODUCTOS = 300
SOLO_ADMIN_AJUSTA = (
    "Los ajustes por conteo físico los confirma un Administrador. Si llegó o salió "
    "mercadería, dímelo como entrada o salida."
)


class ServicioAgente:
    def __init__(
        self,
        db: Session,
        empresa_id: int,
        usuario_id: uuid.UUID | None,
        modelo: ModeloLenguaje | None = None,
        *,
        es_administrador: bool = False,
    ):
        self.db = db
        self.empresa_id = empresa_id
        self.usuario_id = usuario_id
        self.modelo = modelo
        self.es_administrador = es_administrador

    # ---------- Interpretar ----------
    def interpretar(self, texto: str) -> AiReply:
        self._exigir_modelo()
        categorias = self._categorias()
        productos = self._productos()
        hoy = datetime.now(ZONA).date()
        respuesta = self.modelo.completar_json(
            [
                {"role": "system", "content": prompt_sistema(list(categorias), productos, hoy)},
                {"role": "user", "content": texto},
            ],
            esquema(list(categorias), productos),
        )
        interpretacion = interpretar(respuesta.datos, list(categorias), hoy, productos, texto)
        return self._proponer(respuesta, interpretacion, categorias, texto)

    def interpretar_imagen(self, imagen: str, texto: str | None = None) -> AiReply:
        """`imagen` es la foto ya validada y reducida, como data URL (app.ia.imagen)."""
        self._exigir_modelo(vision=True)
        categorias = self._categorias()
        productos = self._productos()
        hoy = datetime.now(ZONA).date()
        empresa = self.db.get(Empresa, self.empresa_id)
        sistema = prompt_sistema(list(categorias), productos, hoy, con_imagen=True) + prompt_imagen(
            empresa.razon_social, empresa.ruc
        )
        indicacion = texto or "Interpreta esta imagen."
        respuesta = self.modelo.completar_json(
            [
                {"role": "system", "content": sistema},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": indicacion},
                        {"type": "image_url", "image_url": {"url": imagen}},
                    ],
                },
            ],
            esquema(list(categorias), productos, con_lectura=True),
        )
        interpretacion, lectura = interpretar_imagen(
            respuesta.datos, list(categorias), hoy, productos, texto
        )
        return self._proponer(
            respuesta,
            interpretacion,
            categorias,
            f"[Imagen] {texto}" if texto else "[Imagen]",
            extra={"entrada": "imagen", "lectura": lectura},
        )

    def _exigir_modelo(self, *, vision: bool = False) -> None:
        if self.modelo is None:
            if vision:
                raise ServiceUnavailableError(
                    "La lectura de imágenes no está configurada en este servidor.",
                    code="AI_VISION_NOT_CONFIGURED",
                )
            raise ServiceUnavailableError(
                "El agente de IA no está configurado en este servidor.", code="AI_NOT_CONFIGURED"
            )

    def _proponer(
        self,
        respuesta: RespuestaModelo,
        interpretacion: Interpretacion,
        categorias: dict[str, int],
        instruccion: str,
        extra: dict | None = None,
    ) -> AiReply:
        self.db.add(
            ConsumoTokens(
                id_empresa=self.empresa_id,
                modelo_ia=respuesta.modelo,
                tokens_prompt=respuesta.tokens_prompt,
                tokens_completado=respuesta.tokens_completado,
            )
        )

        inventario = interpretacion.inventario
        if inventario and inventario.tipo == "ajuste" and not self.es_administrador:
            interpretacion = Interpretacion("aclaracion", SOLO_ADMIN_AJUSTA)

        gasto, inventario = interpretacion.gasto, interpretacion.inventario
        hay_propuesta = gasto is not None or inventario is not None
        accion = AccionIA(
            id_empresa=self.empresa_id,
            id_usuario=self.usuario_id,
            tipo_accion=(
                "registrar_gasto"
                if gasto
                else "movimiento_inventario"
                if inventario
                else interpretacion.tipo
            ),
            instruccion_recibida=instruccion,
            payload_json={
                "respuesta": interpretacion.respuesta,
                "propuesta": gasto.como_json() if gasto else None,
                "propuesta_inventario": inventario.como_json() if inventario else None,
                "modelo": respuesta.modelo,
                **(extra or {}),
            },
            estado=PENDIENTE if hay_propuesta else SIN_PROPUESTA,
        )
        self.db.add(accion)
        self.db.commit()

        return AiReply(
            action_id=accion.id_accion_ia if hay_propuesta else None,
            reply=interpretacion.respuesta,
            proposal=self._propuesta_api(gasto, inventario, categorias) if hay_propuesta else None,
        )

    # ---------- Confirmar y cancelar ----------
    def confirmar(
        self, id_accion: int, correcciones: AiConfirm
    ) -> tuple[AccionIA, int | None, int | None]:
        """Ejecuta la propuesta. Devuelve la acción, el id del gasto y el del movimiento."""
        accion = self._pendiente(id_accion)
        cambios = correcciones.model_dump(exclude_unset=True, exclude_none=True)
        datos = accion.payload_json
        if datos.get("propuesta_inventario"):
            return accion, None, self._confirmar_inventario(accion, datos, cambios)
        return accion, self._confirmar_gasto(accion, datos, cambios), None

    def _confirmar_gasto(self, accion: AccionIA, datos: dict, cambios: dict) -> int:
        propuesta = PropuestaGasto.desde_json(datos["propuesta"])
        categorias = self._categorias()

        id_categoria = cambios.get("category_id") or categorias.get(propuesta.categoria)
        if id_categoria not in categorias.values():
            raise UnprocessableError("La categoría no existe.", code="CATEGORY_NOT_FOUND")
        total = Decimal(cambios.get("total", propuesta.total))
        iva = Decimal(cambios.get("iva_amount", propuesta.iva))
        descripcion = cambios.get("description", propuesta.descripcion)
        if propuesta.proveedor and "description" not in cambios:
            descripcion = f"{descripcion} ({propuesta.proveedor})"
        fecha: date | None = cambios.get("date", propuesta.fecha)

        gasto_nuevo = ExpenseCreate(
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
        gasto = GastoService(self.db, self.empresa_id).crear(gasto_nuevo, self.usuario_id)
        accion.payload_json = {**datos, "id_gasto": gasto.id}
        self.db.commit()
        return gasto.id

    def _confirmar_inventario(self, accion: AccionIA, datos: dict, cambios: dict) -> int:
        propuesta = PropuestaInventario.desde_json(datos["propuesta_inventario"])
        if propuesta.tipo == "ajuste" and not self.es_administrador:
            raise ForbiddenError(
                "Los ajustes por conteo físico los confirma un Administrador.",
                code="ADMIN_REQUIRED",
            )
        cantidad = Decimal(cambios.get("quantity", propuesta.cantidad))
        if propuesta.tipo != "ajuste" and cantidad <= 0:
            raise UnprocessableError("La cantidad debe ser mayor que 0.", code="INVALID_QUANTITY")

        # Mismo patrón que el gasto: el estado y el movimiento se guardan juntos.
        accion.estado = CORREGIDO if cambios else CONFIRMADO
        servicio = InventarioService(self.db, self.empresa_id)
        if propuesta.tipo == "ajuste":
            resultado = servicio.ajustar(
                AdjustmentCreate(
                    product_id=propuesta.id_producto, new_stock=cantidad, reason=propuesta.motivo
                ),
                self.usuario_id,
            )
        else:
            resultado = servicio.registrar_movimiento(
                MovementCreate(
                    product_id=propuesta.id_producto,
                    type=propuesta.tipo,
                    quantity=cantidad,
                    reason=propuesta.motivo,
                ),
                self.usuario_id,
            )
        accion.payload_json = {**datos, "id_movimiento": resultado.id}
        self.db.commit()
        return resultado.id

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
            gasto = (
                PropuestaGasto.desde_json(datos["propuesta"]) if datos.get("propuesta") else None
            )
            inventario = (
                PropuestaInventario.desde_json(datos["propuesta_inventario"])
                if datos.get("propuesta_inventario")
                else None
            )
            items.append(
                AiAction(
                    id=accion.id_accion_ia,
                    timestamp=accion.fecha,
                    user_name=nombre or email or "Usuario",
                    instruction=accion.instruccion_recibida,
                    reply=datos.get("respuesta", ""),
                    proposal=(
                        self._propuesta_api(gasto, inventario, categorias)
                        if gasto or inventario
                        else None
                    ),
                    status=ESTADOS_API.get(accion.estado, "sin_propuesta"),
                    expense_id=datos.get("id_gasto"),
                    movement_id=datos.get("id_movimiento"),
                    input_type="imagen" if datos.get("entrada") == "imagen" else "texto",
                )
            )
        return Page(items=items, total=total, page=page, page_size=page_size)

    # ---------- Internos ----------
    def _categorias(self) -> dict[str, int]:
        return {c.name: c.id for c in CategoriaGastoService(self.db, self.empresa_id).listar()}

    def _productos(self) -> list[ProductoDisponible]:
        filas = self.db.execute(
            select(
                Producto.id_producto,
                Producto.nombre,
                Producto.codigo_principal,
                Producto.unidad_medida,
                Producto.stock_actual,
            )
            .where(Producto.id_empresa == self.empresa_id, Producto.activo.is_(True))
            .order_by(Producto.nombre)
            .limit(MAX_PRODUCTOS)
        ).all()
        return [ProductoDisponible(*fila) for fila in filas]

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
    def _propuesta_api(
        gasto: PropuestaGasto | None,
        inventario: PropuestaInventario | None,
        categorias: dict[str, int],
    ) -> AiProposal:
        if inventario is not None:
            return AiProposal(
                type="inventory",
                summary=inventario.resumen(),
                inventory=AiInventoryProposal(
                    product_id=inventario.id_producto,
                    product_name=inventario.producto,
                    type=inventario.tipo,
                    quantity=inventario.cantidad,
                    unit=inventario.unidad,
                    current_stock=inventario.stock_actual,
                    resulting_stock=inventario.stock_resultante,
                    reason=inventario.motivo,
                ),
            )
        return AiProposal(
            type="expense",
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
