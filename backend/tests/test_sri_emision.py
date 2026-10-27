"""Flujo de emisión: cada camino (autorizada, rechazada, por enviar, por autorizar)."""

from dataclasses import replace
from datetime import datetime
from io import BytesIO

import pytest
from pypdf import PdfReader

from app.sri.clave_acceso import Ambiente
from app.sri.emision import EstadoEmision, ServicioEmision
from app.sri.factura_xml import Comprador
from app.sri.firma import FirmadorSinFirma
from app.sri.identificacion import TipoIdentificacion
from app.sri.servicios_web import (
    EstadoAutorizacion,
    EstadoRecepcion,
    Mensaje,
    RespuestaAutorizacion,
    RespuestaRecepcion,
    SriNoDisponibleError,
)
from tests.datos_sri import CLAVE_FACTURA as CLAVE
from tests.datos_sri import FACTURA

FECHA = datetime(2026, 10, 27, 10, 15, 0)
RECIBIDA = RespuestaRecepcion(EstadoRecepcion.RECIBIDA)
EN_PROCESO = RespuestaAutorizacion(EstadoAutorizacion.EN_PROCESO)
AUTORIZADO = RespuestaAutorizacion(
    EstadoAutorizacion.AUTORIZADO, numero_autorizacion=CLAVE, fecha_autorizacion=FECHA
)
CAIDO = SriNoDisponibleError("sin conexión")


def _error(codigo: str, texto: str) -> Mensaje:
    return Mensaje(codigo, texto, None, "ERROR")


class SriFalso:
    """Devuelve (o lanza) las respuestas en el orden dado y cuenta las llamadas."""

    def __init__(self, recepciones=(), autorizaciones=()):
        self.recepciones = list(recepciones)
        self.autorizaciones = list(autorizaciones)
        self.enviados: list[bytes] = []
        self.consultas: list[str] = []

    @staticmethod
    def _siguiente(respuestas):
        respuesta = respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    def enviar(self, xml: bytes):
        self.enviados.append(xml)
        return self._siguiente(self.recepciones)

    def autorizar(self, clave: str):
        self.consultas.append(clave)
        return self._siguiente(self.autorizaciones)


def _servicio(sri: SriFalso, pausas: list[float]) -> ServicioEmision:
    return ServicioEmision(sri, FirmadorSinFirma(), dormir=pausas.append)


def test_camino_feliz_autoriza_y_genera_el_ride():
    sri, pausas = SriFalso([RECIBIDA], [AUTORIZADO]), []

    resultado = _servicio(sri, pausas).emitir(FACTURA)

    assert resultado.estado == EstadoEmision.AUTORIZADA
    assert not resultado.pendiente
    assert resultado.clave_acceso == CLAVE
    assert (resultado.numero_autorizacion, resultado.fecha_autorizacion) == (CLAVE, FECHA)
    assert sri.enviados == [resultado.xml_firmado]
    assert sri.consultas == [CLAVE]
    assert pausas == [3.0]  # espera una vez entre el envío y la consulta
    texto = PdfReader(BytesIO(resultado.ride)).pages[0].extract_text()
    assert "27/10/2026 10:15:00" in texto and "PENDIENTE" not in texto


def test_espera_mientras_el_sri_procesa():
    sri, pausas = SriFalso([RECIBIDA], [EN_PROCESO, EN_PROCESO, AUTORIZADO]), []
    resultado = _servicio(sri, pausas).emitir(FACTURA)
    assert resultado.estado == EstadoEmision.AUTORIZADA
    assert len(sri.consultas) == 3
    assert pausas == [3.0, 3.0, 3.0]


def test_si_no_hay_respuesta_queda_por_autorizar_y_el_worker_la_retoma():
    sri, pausas = SriFalso([RECIBIDA], [EN_PROCESO, CAIDO, EN_PROCESO]), []
    servicio = _servicio(sri, pausas)

    pendiente = servicio.emitir(FACTURA)
    assert pendiente.estado == EstadoEmision.POR_AUTORIZAR
    assert pendiente.pendiente

    # Más tarde, el worker solo vuelve a consultar (no reenvía).
    sri.autorizaciones = [AUTORIZADO]
    final = servicio.consultar(pendiente.xml_firmado, pendiente.clave_acceso)
    assert final.estado == EstadoEmision.AUTORIZADA
    assert len(sri.enviados) == 1


def test_si_el_sri_no_responde_al_enviar_queda_por_enviar_y_se_puede_reenviar():
    sri, pausas = SriFalso([CAIDO]), []
    servicio = _servicio(sri, pausas)

    pendiente = servicio.emitir(FACTURA)
    assert pendiente.estado == EstadoEmision.POR_ENVIAR
    assert sri.consultas == []  # sin recepción no se consulta la autorización

    # El reenvío es seguro: si el SRI ya la tenía (43), sigue con la autorización.
    ya_registrada = RespuestaRecepcion(
        EstadoRecepcion.DEVUELTA, [_error("43", "CLAVE ACCESO REGISTRADA")]
    )
    sri.recepciones, sri.autorizaciones = [ya_registrada], [AUTORIZADO]
    final = servicio.enviar(pendiente.xml_firmado, pendiente.clave_acceso)
    assert final.estado == EstadoEmision.AUTORIZADA


def test_devuelta_en_recepcion_queda_rechazada_con_los_motivos():
    devuelta = RespuestaRecepcion(
        EstadoRecepcion.DEVUELTA, [_error("35", "ARCHIVO NO CUMPLE ESTRUCTURA XML")]
    )
    sri, pausas = SriFalso([devuelta]), []
    resultado = _servicio(sri, pausas).emitir(FACTURA)
    assert resultado.estado == EstadoEmision.RECHAZADA
    assert [m.identificador for m in resultado.mensajes] == ["35"]
    assert sri.consultas == [] and resultado.ride is None


def test_no_autorizado_queda_rechazada_con_los_motivos():
    no_autorizado = RespuestaAutorizacion(
        EstadoAutorizacion.NO_AUTORIZADO, mensajes=[_error("39", "FIRMA INVALIDA")]
    )
    resultado = _servicio(SriFalso([RECIBIDA], [no_autorizado]), []).emitir(FACTURA)
    assert resultado.estado == EstadoEmision.RECHAZADA
    assert resultado.mensajes[0].mensaje == "FIRMA INVALIDA"


def test_datos_invalidos_se_detectan_antes_de_contactar_al_sri():
    sri = SriFalso()
    factura = replace(FACTURA, comprador=Comprador(TipoIdentificacion.CEDULA, "1710000008", "X"))
    with pytest.raises(ValueError, match="Identificación del comprador"):
        _servicio(sri, []).emitir(factura)
    assert sri.enviados == []


def test_el_firmador_de_prueba_nunca_procesa_facturas_de_produccion():
    sri = SriFalso()
    with pytest.raises(RuntimeError, match="solo acepta comprobantes del ambiente de pruebas"):
        _servicio(sri, []).emitir(replace(FACTURA, ambiente=Ambiente.PRODUCCION))
    assert sri.enviados == []
