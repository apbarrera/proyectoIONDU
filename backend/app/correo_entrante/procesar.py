"""Proceso del worker: leer los buzones activos y guardar borradores de gasto (RF-3.2).

Por cada empresa con buzón activo:
1. descifra la clave del correo solo en memoria;
2. lee los mensajes nuevos y sus adjuntos XML;
3. guarda como borrador cada factura del SRI dirigida a la empresa. Si el correo o la
   clave de acceso ya existen, no se duplica (ON CONFLICT DO NOTHING);
4. anota hasta qué UID leyó o, si falló, un error apto para mostrar al Administrador.
Un buzón que falla no detiene a los demás.
"""

import base64
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import TIMEZONE
from app.correo_entrante.factura_recibida import es_para_la_empresa, leer_factura
from app.correo_entrante.imap import BuzonInaccesibleError, LectorImap, Lectura
from app.models import BorradorGasto, BuzonCorreo, Empresa

logger = logging.getLogger("iondu.correo_entrante")
ZONA = ZoneInfo(TIMEZONE)
DIAS_PRIMERA_LECTURA = 30
CONTEXTO_CLAVE = "empresa:{}:imap_password"


def contexto_clave(empresa_id: int) -> str:
    """Contexto del cifrado de la clave del buzón (la ata a la empresa)."""
    return CONTEXTO_CLAVE.format(empresa_id)


def guardar_borradores(session, empresa_id: int, ruc_empresa: str, lectura: Lectura) -> int:
    encontradas = 0
    for mensaje in lectura.mensajes:
        for adjunto in mensaje.adjuntos_xml:
            factura = leer_factura(adjunto)
            if factura is None or not es_para_la_empresa(factura, ruc_empresa):
                continue
            # Si ya existía (mismo correo o misma clave de acceso), no hace nada.
            session.connection().execute(
                insert(BorradorGasto.__table__)
                .values(
                    id_empresa=empresa_id,
                    # Un correo puede traer varias facturas: el message_id se completa con la clave.
                    message_id=f"{mensaje.message_id}#{factura.clave_acceso}"[:998],
                    clave_acceso=factura.clave_acceso,
                    remitente=(mensaje.remitente or "")[:254] or None,
                    asunto=mensaje.asunto,
                    recibido_en=mensaje.recibido_en,
                    proveedor_ruc=factura.proveedor_ruc,
                    proveedor_nombre=factura.proveedor_nombre,
                    numero_comprobante=factura.numero[:20],
                    fecha_emision=factura.fecha_emision,
                    subtotal=factura.subtotal,
                    iva=factura.iva,
                    total=factura.total,
                    detalle=factura.detalle,
                )
                .on_conflict_do_nothing()
            )
            encontradas += 1
    return encontradas


def procesar_buzones(
    session_factory,
    descifrar: Callable[[bytes, str], bytes],
    *,
    crear_lector: Callable[..., LectorImap] = LectorImap,
    reloj: Callable[[], datetime] = lambda: datetime.now(ZONA),
) -> int:
    """Devuelve cuántas facturas válidas para la empresa se encontraron (las repetidas
    se ignoran en la base: el worker no puede leer la tabla, solo insertar)."""
    with session_factory() as session:
        buzones = session.execute(
            select(BuzonCorreo, Empresa.ruc).join(
                Empresa, Empresa.id_empresa == BuzonCorreo.id_empresa
            )
        ).all()
        pendientes = [
            (
                b.id_empresa,
                ruc,
                b.servidor,
                b.puerto,
                b.seguridad,
                b.usuario,
                b.clave_cifrada,
                b.carpeta,
                b.uid_validity,
                b.ultimo_uid,
            )
            for b, ruc in buzones
        ]

    total = 0
    for (
        empresa_id,
        ruc,
        servidor,
        puerto,
        seguridad,
        usuario,
        cifrada,
        carpeta,
        uid_validity,
        ultimo_uid,
    ) in pendientes:
        ahora = reloj()
        error = None
        lectura = None
        try:
            clave = descifrar(base64.b64decode(cifrada), contexto_clave(empresa_id)).decode()
            lector = crear_lector(servidor, puerto, seguridad, usuario, clave, carpeta)
            lectura = lector.leer_nuevos(
                uid_validity, ultimo_uid, (ahora - timedelta(days=DIAS_PRIMERA_LECTURA)).date()
            )
        except BuzonInaccesibleError as exc:
            error = str(exc)
        except Exception as exc:  # noqa: BLE001 - un buzón no detiene a los demás
            logger.error(
                "Fallo al leer el buzón de la empresa %s. tipo=%s", empresa_id, type(exc).__name__
            )
            error = "No se pudo leer el correo. Revisa la configuración del buzón."

        try:
            total += _registrar(
                session_factory, empresa_id, ruc, ahora, error, lectura, uid_validity
            )
        except Exception as exc:  # noqa: BLE001 - el siguiente ciclo vuelve a intentar
            logger.error(
                "No se pudieron guardar los borradores de la empresa %s. tipo=%s",
                empresa_id,
                type(exc).__name__,
            )
            _registrar(
                session_factory, empresa_id, ruc, ahora, ERROR_AL_GUARDAR, None, uid_validity
            )
    return total


ERROR_AL_GUARDAR = "Se leyó el correo, pero no se pudieron guardar las facturas. Se reintentará."


def _registrar(session_factory, empresa_id, ruc, ahora, error, lectura, uid_validity) -> int:
    """Guarda los borradores y hasta dónde se leyó, en una sola transacción."""
    encontradas = 0
    with session_factory() as session, session.begin():
        buzon = session.get(BuzonCorreo, empresa_id, with_for_update=True)
        if buzon is None:
            return 0
        buzon.ultima_lectura = ahora
        buzon.ultimo_error = error[:300] if error else None
        if lectura is not None:
            encontradas = guardar_borradores(session, empresa_id, ruc, lectura)
            buzon.uid_validity = lectura.uid_validity
            if lectura.mensajes:
                buzon.ultimo_uid = max(m.uid for m in lectura.mensajes)
            elif buzon.uid_validity != uid_validity:
                buzon.ultimo_uid = None
    return encontradas
