"""Buzón de facturas de la empresa y borradores de gasto (RF-3.2, RF-3.3).

- El Administrador configura la cuenta IMAP. La clave se cifra al guardarla y nunca se
  devuelve; solo el worker la descifra en memoria para leer.
- Cualquier usuario de la empresa revisa los borradores: al confirmarlos se crea el gasto
  (con la clave de acceso, para no registrar dos veces la misma factura) y el proveedor
  si no existía; o los descarta.
"""

import base64
import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cifrado import get_cifrador
from app.core.config import TIMEZONE
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.correo_entrante.imap import BuzonInaccesibleError, LectorImap
from app.correo_entrante.procesar import contexto_clave
from app.models import BorradorGasto, BuzonCorreo
from app.models.correo import CONVERTIDO, DESCARTADO, PENDIENTE
from app.schemas.correo import (
    EmailInbox,
    EmailInboxTestResult,
    EmailInboxUpdate,
    ExpenseDraft,
    ExpenseDraftConfirm,
    ExpenseDraftLine,
)
from app.schemas.gasto import Expense, ExpenseCreate, SupplierCreate
from app.services.gasto import GastoService, ProveedorService

ZONA = ZoneInfo(TIMEZONE)
ESTADOS_API = {PENDIENTE: "pendiente", CONVERTIDO: "convertido", DESCARTADO: "descartado"}


def _a_buzon(buzon: BuzonCorreo) -> EmailInbox:
    return EmailInbox(
        server=buzon.servidor,
        port=buzon.puerto,
        security=buzon.seguridad,
        username=buzon.usuario,
        folder=buzon.carpeta,
        enabled=buzon.activo,
        last_read_at=buzon.ultima_lectura,
        last_error=buzon.ultimo_error,
    )


class BuzonCorreoService:
    def __init__(self, db: Session, empresa_id: int, *, crear_lector=None):
        self.db = db
        self.empresa_id = empresa_id
        # Se resuelve al usarlo para que las pruebas puedan reemplazar LectorImap.
        self._crear_lector = crear_lector

    def _cifrar(self, clave: str) -> str:
        cifrada = get_cifrador().cifrar(clave.encode("utf-8"), contexto_clave(self.empresa_id))
        return base64.b64encode(cifrada).decode("ascii")

    def _clave_guardada(self, buzon: BuzonCorreo) -> str:
        cifrada = base64.b64decode(buzon.clave_cifrada)
        return get_cifrador().descifrar(cifrada, contexto_clave(self.empresa_id)).decode()

    def obtener(self) -> EmailInbox | None:
        buzon = self.db.get(BuzonCorreo, self.empresa_id)
        return _a_buzon(buzon) if buzon else None

    def configurar(self, datos: EmailInboxUpdate) -> EmailInbox:
        buzon = self.db.get(BuzonCorreo, self.empresa_id)
        if buzon is None:
            if not datos.password:
                raise UnprocessableError(
                    "Escribe la clave del correo.",
                    code="VALIDATION_ERROR",
                    details=[{"field": "password", "message": "Obligatoria la primera vez."}],
                )
            buzon = BuzonCorreo(id_empresa=self.empresa_id, clave_cifrada="")
            self.db.add(buzon)
        cambia_cuenta = (buzon.servidor, buzon.usuario, buzon.carpeta) != (
            datos.server,
            datos.username,
            datos.folder,
        )
        buzon.servidor = datos.server
        buzon.puerto = datos.port
        buzon.seguridad = datos.security
        buzon.usuario = datos.username
        buzon.carpeta = datos.folder
        buzon.activo = datos.enabled
        if datos.password:
            buzon.clave_cifrada = self._cifrar(datos.password)
        if cambia_cuenta:  # otra cuenta o carpeta: se empieza a leer de nuevo
            buzon.uid_validity = None
            buzon.ultimo_uid = None
        buzon.ultimo_error = None
        buzon.actualizado_en = datetime.now(ZONA)
        self.db.commit()
        return _a_buzon(buzon)

    def eliminar(self) -> None:
        buzon = self.db.get(BuzonCorreo, self.empresa_id)
        if buzon is None:
            raise NotFoundError("La empresa no tiene un correo de facturas configurado.")
        self.db.delete(buzon)
        self.db.commit()

    def probar(self, datos: EmailInboxUpdate | None) -> EmailInboxTestResult:
        """Prueba la conexión con los datos escritos (o los guardados) sin guardar nada."""
        buzon = self.db.get(BuzonCorreo, self.empresa_id)
        if datos is None:
            if buzon is None:
                raise NotFoundError("La empresa no tiene un correo de facturas configurado.")
            servidor, puerto, seguridad = buzon.servidor, buzon.puerto, buzon.seguridad
            usuario, carpeta, clave = buzon.usuario, buzon.carpeta, self._clave_guardada(buzon)
        else:
            if not datos.password and buzon is None:
                raise UnprocessableError("Escribe la clave del correo.", code="VALIDATION_ERROR")
            servidor, puerto, seguridad = datos.server, datos.port, datos.security
            usuario, carpeta = datos.username, datos.folder
            clave = datos.password or self._clave_guardada(buzon)
        try:
            lector = self._crear_lector or LectorImap
            lector(servidor, puerto, seguridad, usuario, clave, carpeta).probar()
        except BuzonInaccesibleError as exc:
            return EmailInboxTestResult(ok=False, message=str(exc))
        return EmailInboxTestResult(ok=True, message="Conexión correcta: el buzón se puede leer.")


def _a_borrador(b: BorradorGasto) -> ExpenseDraft:
    return ExpenseDraft(
        id=b.id_borrador,
        received_at=b.recibido_en,
        from_address=b.remitente,
        subject=b.asunto,
        supplier_ruc=b.proveedor_ruc,
        supplier_name=b.proveedor_nombre,
        receipt_number=b.numero_comprobante,
        issue_date=b.fecha_emision,
        subtotal=b.subtotal,
        iva_amount=b.iva,
        total=b.total,
        lines=[
            ExpenseDraftLine(
                description=linea.get("descripcion", ""),
                quantity=linea.get("cantidad", "0"),
                total=linea.get("total", "0"),
            )
            for linea in (b.detalle or [])
        ],
        status=ESTADOS_API[b.estado],
        expense_id=b.id_gasto,
    )


class BorradorGastoService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def listar(self, estado: str | None = "pendiente") -> list[ExpenseDraft]:
        consulta = select(BorradorGasto).where(BorradorGasto.id_empresa == self.empresa_id)
        if estado:
            interno = {v: k for k, v in ESTADOS_API.items()}[estado]
            consulta = consulta.where(BorradorGasto.estado == interno)
        consulta = consulta.order_by(BorradorGasto.recibido_en.desc().nulls_last()).limit(200)
        return [_a_borrador(b) for b in self.db.scalars(consulta)]

    def _pendiente(self, id_borrador: int) -> BorradorGasto:
        borrador = self.db.scalar(
            select(BorradorGasto)
            .where(
                BorradorGasto.id_empresa == self.empresa_id,
                BorradorGasto.id_borrador == id_borrador,
            )
            .with_for_update()
        )
        if borrador is None:
            raise NotFoundError("El borrador no existe.")
        if borrador.estado != PENDIENTE:
            raise ConflictError(
                "Este borrador ya fue confirmado o descartado.", code="DRAFT_NOT_PENDING"
            )
        return borrador

    def _proveedor(self, borrador: BorradorGasto) -> int | None:
        if not borrador.proveedor_ruc:
            return None
        proveedores = ProveedorService(self.db, self.empresa_id)
        try:
            return proveedores.buscar_por_identificacion(borrador.proveedor_ruc).id
        except NotFoundError:
            nombre = borrador.proveedor_nombre or f"Proveedor {borrador.proveedor_ruc}"
            return proveedores.crear(
                SupplierCreate(identification=borrador.proveedor_ruc, name=nombre[:255])
            ).id

    def confirmar(
        self, id_borrador: int, datos: ExpenseDraftConfirm, id_usuario: uuid.UUID
    ) -> Expense:
        borrador = self._pendiente(id_borrador)
        total = datos.total or borrador.total
        if not total or total <= 0:
            raise UnprocessableError("El total del gasto debe ser mayor que 0.")
        iva = min(borrador.iva or 0, total)
        descripcion = datos.description or (
            f"Factura {borrador.numero_comprobante} de {borrador.proveedor_nombre}"
            if borrador.numero_comprobante
            else "Gasto recibido por correo"
        )
        fecha = (
            datetime.combine(borrador.fecha_emision, time(12), tzinfo=ZONA)
            if borrador.fecha_emision
            else None
        )
        gasto_nuevo = ExpenseCreate(
            category_id=datos.category_id,
            supplier_id=self._proveedor(borrador),
            total=total,
            iva_amount=iva,
            description=descripcion[:1000],
            payment_method=datos.payment_method,
            date=fecha,
            receipt_number=borrador.numero_comprobante,
        )
        try:
            gasto = GastoService(self.db, self.empresa_id).crear(
                gasto_nuevo,
                id_usuario,
                message_id_correo=borrador.message_id,
                clave_acceso=borrador.clave_acceso,
            )
        except IntegrityError as exc:
            raise ConflictError(
                "Esta factura ya está registrada como gasto.", code="EXPENSE_ALREADY_REGISTERED"
            ) from exc
        borrador = self.db.get(BorradorGasto, id_borrador)
        borrador.estado = CONVERTIDO
        borrador.id_gasto = gasto.id
        self.db.commit()
        return gasto

    def descartar(self, id_borrador: int) -> None:
        self._pendiente(id_borrador).estado = DESCARTADO
        self.db.commit()
