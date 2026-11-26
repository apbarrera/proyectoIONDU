"""Worker de IONDU: procesos periódicos y reintentos de emisión SRI."""

import logging
import threading
import time
from pathlib import Path

from sqlalchemy import and_, or_, select

from app.core.cifrado import get_cifrador
from app.core.config import get_settings
from app.correo_entrante.procesar import procesar_buzones
from app.models.empresa import Empresa
from app.models.factura import Factura
from app.services.almacenamiento import crear_almacenamiento
from app.sri.clave_acceso import Ambiente
from app.sri.emision import EstadoEmision, ServicioEmision
from app.sri.ride import generar_ride
from app.sri.servicios_web import ClienteSri
from app.sri.simulado import ClienteSriSimulado, es_autorizacion_simulada, usa_sri_simulado
from app.worker.database import (
    bloqueo_factura,
    dispose_worker_engine,
    get_worker_engine,
    get_worker_session_factory,
)

logger = logging.getLogger("iondu.worker")
stop = threading.Event()

TAMANO_LOTE = 20
ESTADOS_PENDIENTES = ("por_enviar", "por_autorizar")


# Cursor en memoria para repartir los lotes entre todas las facturas pendientes.
# No requiere columnas ni cambios en la base de datos.
_ultimo_pendiente: tuple | None = None


def _obtener_pendientes(session_factory) -> list[tuple[int, int]]:
    """Obtiene un lote acotado y continúa circularmente desde el lote anterior."""
    global _ultimo_pendiente

    def consultar(session, cursor):
        sentencia = select(
            Factura.fecha_emision,
            Factura.id_empresa,
            Factura.id_factura,
        ).where(Factura.estado_autorizacion.in_(ESTADOS_PENDIENTES))

        if cursor is not None:
            fecha, empresa_id, factura_id = cursor
            sentencia = sentencia.where(
                or_(
                    Factura.fecha_emision > fecha,
                    and_(
                        Factura.fecha_emision == fecha,
                        Factura.id_empresa > empresa_id,
                    ),
                    and_(
                        Factura.fecha_emision == fecha,
                        Factura.id_empresa == empresa_id,
                        Factura.id_factura > factura_id,
                    ),
                )
            )

        return session.execute(
            sentencia.order_by(
                Factura.fecha_emision,
                Factura.id_empresa,
                Factura.id_factura,
            ).limit(TAMANO_LOTE)
        ).all()

    with session_factory() as session:
        filas = consultar(session, _ultimo_pendiente)

        # Al llegar al final, vuelve al principio para continuar la rotación.
        if not filas and _ultimo_pendiente is not None:
            filas = consultar(session, None)

        if not filas:
            _ultimo_pendiente = None
            return []

        ultima = filas[-1]
        _ultimo_pendiente = (
            ultima[0],
            int(ultima[1]),
            int(ultima[2]),
        )

        return [(int(fila[1]), int(fila[2])) for fila in filas]


def _serializar_mensajes(mensajes) -> list[dict]:
    """Convierte los mensajes SRI en datos compatibles con JSONB."""
    return [
        {
            "identificador": mensaje.identificador,
            "mensaje": mensaje.mensaje,
            "informacion_adicional": mensaje.informacion_adicional,
            "tipo": mensaje.tipo,
        }
        for mensaje in mensajes
    ]


def _guardar_ruta_ride(session_factory, empresa_id: int, factura_id: int, ruta: str):
    """Registra la ruta del RIDE sin modificar el resultado de autorización."""
    with session_factory() as session, session.begin():
        factura = session.scalar(
            select(Factura).where(
                Factura.id_empresa == empresa_id,
                Factura.id_factura == factura_id,
                Factura.estado_autorizacion == EstadoEmision.AUTORIZADA.value,
            )
        )

        if factura is not None:
            factura.pdf_ride_path = ruta


def _procesar_factura(
    session_factory,
    empresa_id: int,
    factura_id: int,
    almacenamiento,
) -> None:
    # Procesa la factura con bloqueo de sesión y transacciones cortas.
    try:
        with bloqueo_factura(empresa_id, factura_id) as bloqueada:
            if not bloqueada:
                return

            # Primera transacción: validar y persistir el intento antes del SRI.
            with session_factory() as session, session.begin():
                factura = session.scalar(
                    select(Factura)
                    .where(
                        Factura.id_empresa == empresa_id,
                        Factura.id_factura == factura_id,
                    )
                    .with_for_update()
                )

                if factura is None or factura.estado_autorizacion not in ESTADOS_PENDIENTES:
                    return

                if not factura.clave_acceso or not factura.xml_firmado:
                    raise ValueError("La factura pendiente no tiene XML o clave de acceso.")

                resultado_empresa = session.execute(
                    select(
                        Empresa.id_empresa,
                        Empresa.datos_facturacion_electronica,
                    ).where(Empresa.id_empresa == empresa_id)
                )
                fila_empresa = resultado_empresa.one_or_none()
                if fila_empresa is None:
                    raise ValueError("No existe la empresa asociada a la factura.")

                _, configuracion_empresa = fila_empresa
                configuracion = configuracion_empresa or {}
                ambiente_configurado = configuracion.get("ambiente")

                if ambiente_configurado not in ("1", "2"):
                    raise ValueError("El ambiente SRI de la empresa no es válido.")

                ambiente = Ambiente(ambiente_configurado)
                estado_anterior = factura.estado_autorizacion
                clave_acceso = factura.clave_acceso
                xml_firmado_texto = factura.xml_firmado
                xml_firmado = xml_firmado_texto.encode("utf-8")

                if estado_anterior == EstadoEmision.POR_ENVIAR.value:
                    factura.intentos_envio = (factura.intentos_envio or 0) + 1

            # La transacción de negocio ya terminó. El advisory lock de sesión
            # permanece adquirido durante toda la comunicación con el SRI.
            try:
                cliente = (
                    ClienteSriSimulado
                    if usa_sri_simulado(empresa_id, ambiente, get_settings().sri_simulado_empresas)
                    else ClienteSri
                )
                with cliente(ambiente) as cliente_sri:
                    servicio = ServicioEmision(
                        cliente_sri,
                        firmador=None,
                    )

                    if estado_anterior == EstadoEmision.POR_ENVIAR.value:
                        resultado = servicio.enviar(
                            xml_firmado,
                            clave_acceso,
                        )
                    else:
                        # Una factura por autorizar nunca se reenvía.
                        resultado = servicio.consultar(
                            xml_firmado,
                            clave_acceso,
                        )
            except Exception as exc:
                accion = (
                    "enviar" if estado_anterior == EstadoEmision.POR_ENVIAR.value else "consultar"
                )
                logger.error(
                    "Error al %s factura %s de empresa %s. tipo=%s",
                    accion,
                    factura_id,
                    empresa_id,
                    type(exc).__name__,
                )
                return

            datos_ride = None

            # Segunda transacción: releer, verificar y persistir la respuesta.
            with session_factory() as session, session.begin():
                factura = session.scalar(
                    select(Factura)
                    .where(
                        Factura.id_empresa == empresa_id,
                        Factura.id_factura == factura_id,
                    )
                    .with_for_update()
                )

                if (
                    factura is None
                    or factura.estado_autorizacion != estado_anterior
                    or factura.clave_acceso != clave_acceso
                    or factura.xml_firmado != xml_firmado_texto
                ):
                    logger.warning(
                        "La factura %s de empresa %s cambió durante "
                        "la consulta al SRI; no se aplicará la respuesta.",
                        factura_id,
                        empresa_id,
                    )
                    return

                factura.estado_autorizacion = resultado.estado.value

                factura.mensajes_sri = _serializar_mensajes(resultado.mensajes or [])

                if resultado.estado == EstadoEmision.AUTORIZADA:
                    factura.numero_autorizacion = resultado.numero_autorizacion
                    factura.fecha_autorizacion = resultado.fecha_autorizacion

                    if resultado.xml_autorizado:
                        factura.xml_autorizado = resultado.xml_autorizado.decode("utf-8")

                    xml_para_ride = resultado.xml_autorizado or xml_firmado
                    if resultado.numero_autorizacion and resultado.fecha_autorizacion:
                        datos_ride = (
                            xml_para_ride,
                            resultado.numero_autorizacion,
                            resultado.fecha_autorizacion,
                        )

            # La autorización ya está confirmada. Un fallo de RIDE o Storage
            # no puede revertirla.
            if datos_ride is not None and almacenamiento is not None:
                try:
                    (
                        xml_ride,
                        numero_autorizacion,
                        fecha_autorizacion,
                    ) = datos_ride
                    ride = generar_ride(
                        xml_ride,
                        numero_autorizacion=numero_autorizacion,
                        fecha_autorizacion=fecha_autorizacion,
                        simulado=es_autorizacion_simulada(
                            _serializar_mensajes(resultado.mensajes or [])
                        ),
                    )
                    ruta = almacenamiento.guardar(
                        empresa_id,
                        factura_id,
                        ride,
                    )
                    _guardar_ruta_ride(
                        session_factory,
                        empresa_id,
                        factura_id,
                        ruta,
                    )
                except Exception as exc:
                    logger.error(
                        "No se pudo almacenar o registrar el RIDE de factura "
                        "%s de empresa %s. tipo=%s",
                        factura_id,
                        empresa_id,
                        type(exc).__name__,
                    )

    except Exception as exc:
        logger.error(
            "Error procesando factura %s de empresa %s. tipo=%s",
            factura_id,
            empresa_id,
            type(exc).__name__,
        )


_proxima_lectura_correo = 0.0


def leer_correo_si_toca(ahora: float | None = None) -> None:
    """RF-3.2: cada IMAP_INTERVALO_SEGUNDOS lee los buzones activos y guarda borradores."""
    global _proxima_lectura_correo
    ahora = time.monotonic() if ahora is None else ahora
    if ahora < _proxima_lectura_correo:
        return
    settings = get_settings()
    _proxima_lectura_correo = ahora + settings.imap_intervalo_segundos
    try:
        cifrador = get_cifrador()
    except Exception as exc:
        logger.warning("Sin llave de cifrado: no se leen buzones. tipo=%s", type(exc).__name__)
        return
    encontradas = procesar_buzones(get_worker_session_factory(), cifrador.descifrar)
    if encontradas:
        logger.info("correo: %s facturas leídas (las repetidas no se duplican)", encontradas)


def run_cycle() -> None:
    """Procesa un lote de facturas pendientes de envío o autorización."""
    settings = get_settings()
    session_factory = get_worker_session_factory()

    pendientes = _obtener_pendientes(session_factory)
    if not pendientes:
        return

    try:
        almacenamiento = crear_almacenamiento(settings)
    except Exception as exc:
        # Sin almacenamiento la factura se autoriza igual; el RIDE se genera al descargarlo.
        logger.error("No se pudo inicializar el almacenamiento. tipo=%s", type(exc).__name__)
        almacenamiento = None

    for empresa_id, factura_id in pendientes:
        _procesar_factura(
            session_factory,
            empresa_id,
            factura_id,
            almacenamiento,
        )


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    import signal

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())

    # Fallar al inicio si falta WORKER_DATABASE_URL.
    # No se utiliza DATABASE_URL como alternativa.
    get_worker_engine()

    heartbeat = Path(settings.worker_heartbeat_file)
    logger.info("worker iniciado")

    try:
        while not stop.is_set():
            try:
                run_cycle()
            except Exception:
                logger.exception("error en el ciclo del worker")
            try:
                leer_correo_si_toca()
            except Exception:
                logger.exception("error en el ciclo del worker")

            heartbeat.touch()
            stop.wait(settings.worker_tick_seconds)
    finally:
        dispose_worker_engine()

    logger.info("worker detenido")


if __name__ == "__main__":
    main()
