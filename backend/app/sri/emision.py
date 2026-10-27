"""Flujo de emisión de una factura electrónica.

    generar XML -> firmar -> enviar (recepción) -> consultar autorización -> RIDE

Resultados:
    AUTORIZADA     el SRI la autorizó; incluye el RIDE.
    RECHAZADA      DEVUELTA en recepción o NO AUTORIZADO; incluye los motivos del SRI.
    POR_ENVIAR     el SRI no respondió al enviar: el worker debe reenviarla (enviar()).
    POR_AUTORIZAR  recibida, pero sin respuesta todavía: el worker vuelve a consultar (consultar()).

El cliente del SRI, el firmador y la pausa se reciben desde fuera (inyección de
dependencias): el mismo flujo sirve en producción y en las pruebas.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.sri.factura_xml import Factura, generar_factura_xml
from app.sri.firma import Firmador
from app.sri.ride import generar_ride
from app.sri.servicios_web import (
    ClienteSri,
    EstadoAutorizacion,
    Mensaje,
    SriNoDisponibleError,
)

logger = logging.getLogger("iondu.sri")


class EstadoEmision(StrEnum):
    AUTORIZADA = "autorizada"
    RECHAZADA = "rechazada"
    POR_ENVIAR = "por_enviar"
    POR_AUTORIZAR = "por_autorizar"


@dataclass(frozen=True)
class ResultadoEmision:
    estado: EstadoEmision
    clave_acceso: str
    xml_firmado: bytes
    numero_autorizacion: str | None = None
    fecha_autorizacion: datetime | None = None
    xml_autorizado: bytes | None = None
    ride: bytes | None = None
    mensajes: list[Mensaje] = field(default_factory=list)

    @property
    def pendiente(self) -> bool:
        """El worker debe retomarla más tarde."""
        return self.estado in (EstadoEmision.POR_ENVIAR, EstadoEmision.POR_AUTORIZAR)


class ServicioEmision:
    def __init__(
        self,
        cliente: ClienteSri,
        firmador: Firmador,
        *,
        intentos_autorizacion: int = 3,
        pausa_segundos: float = 3.0,
        dormir: Callable[[float], None] = time.sleep,
    ):
        self._cliente = cliente
        self._firmador = firmador
        self._intentos = intentos_autorizacion
        self._pausa = pausa_segundos
        self._dormir = dormir

    def emitir(self, factura: Factura) -> ResultadoEmision:
        """Todo el flujo desde los datos de la factura.

        Lanza ValueError si los datos de la factura no son válidos (antes de contactar al SRI).
        """
        generada = generar_factura_xml(factura)
        firmado = self._firmador.firmar(generada.xml)
        return self.enviar(firmado, generada.clave_acceso)

    def enviar(self, xml_firmado: bytes, clave_acceso: str) -> ResultadoEmision:
        """Recepción y luego autorización. Es seguro repetirlo: si el SRI ya la tenía
        (mensaje 43), continúa con la autorización."""
        try:
            recepcion = self._cliente.enviar(xml_firmado)
        except SriNoDisponibleError as exc:
            logger.warning("factura %s por enviar: %s", clave_acceso, exc)
            return ResultadoEmision(EstadoEmision.POR_ENVIAR, clave_acceso, xml_firmado)

        if not recepcion.puede_consultar_autorizacion:
            logger.warning("factura %s devuelta: %s", clave_acceso, recepcion.mensajes)
            return ResultadoEmision(
                EstadoEmision.RECHAZADA, clave_acceso, xml_firmado, mensajes=recepcion.mensajes
            )

        self._dormir(self._pausa)  # el SRI tarda unos segundos en procesar lo recibido
        return self.consultar(xml_firmado, clave_acceso)

    def consultar(self, xml_firmado: bytes, clave_acceso: str) -> ResultadoEmision:
        """Consulta la autorización hasta `intentos_autorizacion` veces."""
        for intento in range(self._intentos):
            if intento:
                self._dormir(self._pausa)
            try:
                autorizacion = self._cliente.autorizar(clave_acceso)
            except SriNoDisponibleError as exc:
                logger.warning("autorización de %s sin respuesta: %s", clave_acceso, exc)
                continue

            if autorizacion.estado == EstadoAutorizacion.AUTORIZADO:
                # El RIDE se arma con el comprobante que devuelve el SRI (o el enviado).
                xml_autorizado = (
                    autorizacion.comprobante.encode("utf-8")
                    if autorizacion.comprobante
                    else xml_firmado
                )
                return ResultadoEmision(
                    EstadoEmision.AUTORIZADA,
                    clave_acceso,
                    xml_firmado,
                    numero_autorizacion=autorizacion.numero_autorizacion,
                    fecha_autorizacion=autorizacion.fecha_autorizacion,
                    xml_autorizado=xml_autorizado,
                    ride=generar_ride(
                        xml_autorizado,
                        numero_autorizacion=autorizacion.numero_autorizacion,
                        fecha_autorizacion=autorizacion.fecha_autorizacion,
                    ),
                    mensajes=autorizacion.mensajes,
                )
            if autorizacion.estado == EstadoAutorizacion.NO_AUTORIZADO:
                logger.warning("factura %s no autorizada: %s", clave_acceso, autorizacion.mensajes)
                return ResultadoEmision(
                    EstadoEmision.RECHAZADA,
                    clave_acceso,
                    xml_firmado,
                    mensajes=autorizacion.mensajes,
                )

        return ResultadoEmision(EstadoEmision.POR_AUTORIZAR, clave_acceso, xml_firmado)
