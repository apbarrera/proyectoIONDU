"""Cliente de los servicios web del SRI con respuestas SIMULADAS (MockTransport).

Ninguna prueba se conecta al SRI. Las respuestas siguen la estructura de la ficha
técnica (esquema offline); falta confirmarlas contra el ambiente de pruebas real
cuando exista el certificado .p12.
"""

import base64
from datetime import datetime, timedelta, timezone

import httpx2 as httpx
import pytest
from lxml import etree

from app.sri.clave_acceso import Ambiente
from app.sri.servicios_web import (
    URL_AUTORIZACION,
    URL_RECEPCION,
    ClienteSri,
    EstadoAutorizacion,
    EstadoRecepcion,
    SriNoDisponibleError,
)
from tests.datos_sri import CLAVE_FACTURA as CLAVE


def _soap(cuerpo: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<soap:Body>{cuerpo}</soap:Body></soap:Envelope>"
    ).encode()


def _recepcion(estado: str, mensajes: str = "") -> bytes:
    return _soap(
        '<ns2:validarComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.recepcion">'
        f"<RespuestaRecepcionComprobante><estado>{estado}</estado><comprobantes>"
        f"<comprobante><claveAcceso>{CLAVE}</claveAcceso><mensajes>{mensajes}</mensajes>"
        "</comprobante></comprobantes></RespuestaRecepcionComprobante>"
        "</ns2:validarComprobanteResponse>"
    )


def _mensaje(identificador: str, texto: str, tipo: str = "ERROR") -> str:
    return (
        f"<mensaje><identificador>{identificador}</identificador><mensaje>{texto}</mensaje>"
        f"<informacionAdicional>Detalle {identificador}</informacionAdicional>"
        f"<tipo>{tipo}</tipo></mensaje>"
    )


def _autorizacion(*autorizaciones: str) -> bytes:
    return _soap(
        '<ns2:autorizacionComprobanteResponse xmlns:ns2="http://ec.gob.sri.ws.autorizacion">'
        f"<RespuestaAutorizacionComprobante><claveAccesoConsultada>{CLAVE}</claveAccesoConsultada>"
        f"<numeroComprobantes>{len(autorizaciones)}</numeroComprobantes>"
        f"<autorizaciones>{''.join(autorizaciones)}</autorizaciones>"
        "</RespuestaAutorizacionComprobante></ns2:autorizacionComprobanteResponse>"
    )


def _una_autorizacion(estado: str, fecha: str = "", mensajes: str = "") -> str:
    comprobante = '<![CDATA[<?xml version="1.0"?><factura id="comprobante"/>]]>'
    return (
        f"<autorizacion><estado>{estado}</estado><numeroAutorizacion>{CLAVE}</numeroAutorizacion>"
        f"<fechaAutorizacion>{fecha}</fechaAutorizacion><ambiente>PRUEBAS</ambiente>"
        f"<comprobante>{comprobante}</comprobante><mensajes>{mensajes}</mensajes></autorizacion>"
    )


class SriSimulado:
    """Responde siempre lo mismo y guarda las peticiones recibidas."""

    def __init__(self, contenido: bytes = b"", status: int = 200, error: Exception | None = None):
        self.contenido, self.status, self.error = contenido, status, error
        self.peticiones: list[httpx.Request] = []

    def cliente(self, ambiente: Ambiente = Ambiente.PRUEBAS) -> ClienteSri:
        def responder(peticion: httpx.Request) -> httpx.Response:
            self.peticiones.append(peticion)
            if self.error:
                raise self.error
            return httpx.Response(self.status, content=self.contenido)

        return ClienteSri(ambiente, http=httpx.Client(transport=httpx.MockTransport(responder)))


# ---------- Recepción ----------
def test_enviar_arma_el_sobre_soap_con_el_xml_en_base64():
    sri = SriSimulado(_recepcion("RECIBIDA"))
    xml = "<factura>Café</factura>".encode()

    respuesta = sri.cliente().enviar(xml)

    assert respuesta.estado == EstadoRecepcion.RECIBIDA
    assert respuesta.puede_consultar_autorizacion
    peticion = sri.peticiones[0]
    assert str(peticion.url) == URL_RECEPCION[Ambiente.PRUEBAS]
    assert peticion.url.host == "celcer.sri.gob.ec"  # ambiente de pruebas
    assert peticion.headers["Content-Type"].startswith("text/xml")
    sobre = etree.fromstring(peticion.content)
    enviado = sobre.xpath("//*[local-name()='validarComprobante']/xml/text()")[0]
    assert base64.b64decode(enviado) == xml


def test_devuelta_con_errores_no_permite_consultar_la_autorizacion():
    mensajes = _mensaje("35", "ARCHIVO NO CUMPLE ESTRUCTURA XML")
    respuesta = SriSimulado(_recepcion("DEVUELTA", mensajes)).cliente().enviar(b"<x/>")
    assert respuesta.estado == EstadoRecepcion.DEVUELTA
    assert not respuesta.puede_consultar_autorizacion
    assert respuesta.mensajes[0].identificador == "35"
    assert respuesta.mensajes[0].mensaje == "ARCHIVO NO CUMPLE ESTRUCTURA XML"
    assert respuesta.mensajes[0].informacion_adicional == "Detalle 35"
    assert respuesta.mensajes[0].tipo == "ERROR"


def test_devuelta_porque_ya_estaba_registrada_permite_seguir():
    mensajes = _mensaje("43", "CLAVE ACCESO REGISTRADA")
    respuesta = SriSimulado(_recepcion("DEVUELTA", mensajes)).cliente().enviar(b"<x/>")
    assert respuesta.ya_registrada
    assert respuesta.puede_consultar_autorizacion


def test_produccion_usa_el_servidor_de_produccion():
    sri = SriSimulado(_recepcion("RECIBIDA"))
    sri.cliente(Ambiente.PRODUCCION).enviar(b"<x/>")
    assert str(sri.peticiones[0].url) == URL_RECEPCION[Ambiente.PRODUCCION]
    assert sri.peticiones[0].url.host == "cel.sri.gob.ec"


# ---------- Autorización ----------
def test_autorizado_con_numero_fecha_y_comprobante():
    sri = SriSimulado(_autorizacion(_una_autorizacion("AUTORIZADO", "2026-10-25T14:30:05-05:00")))

    respuesta = sri.cliente().autorizar(CLAVE)

    assert respuesta.estado == EstadoAutorizacion.AUTORIZADO
    assert respuesta.numero_autorizacion == CLAVE
    assert respuesta.fecha_autorizacion == datetime(
        2026, 10, 25, 14, 30, 5, tzinfo=timezone(timedelta(hours=-5))
    )
    assert respuesta.comprobante.endswith('<factura id="comprobante"/>')
    assert str(sri.peticiones[0].url) == URL_AUTORIZACION[Ambiente.PRUEBAS]
    sobre = etree.fromstring(sri.peticiones[0].content)
    assert sobre.xpath("//claveAccesoComprobante/text()") == [CLAVE]


def test_no_autorizado_trae_los_motivos():
    mensajes = _mensaje("39", "FIRMA INVALIDA")
    sri = SriSimulado(_autorizacion(_una_autorizacion("NO AUTORIZADO", mensajes=mensajes)))
    respuesta = sri.cliente().autorizar(CLAVE)
    assert respuesta.estado == EstadoAutorizacion.NO_AUTORIZADO
    assert [m.mensaje for m in respuesta.mensajes] == ["FIRMA INVALIDA"]


def test_sin_autorizaciones_todavia_esta_en_proceso():
    respuesta = SriSimulado(_autorizacion()).cliente().autorizar(CLAVE)
    assert respuesta.estado == EstadoAutorizacion.EN_PROCESO
    assert respuesta.numero_autorizacion is None


def test_con_varios_intentos_vale_el_autorizado():
    sri = SriSimulado(
        _autorizacion(
            _una_autorizacion("NO AUTORIZADO", mensajes=_mensaje("39", "FIRMA INVALIDA")),
            _una_autorizacion("AUTORIZADO", "2026-10-25T15:00:00-05:00"),
        )
    )
    assert sri.cliente().autorizar(CLAVE).estado == EstadoAutorizacion.AUTORIZADO


# ---------- Cuando el SRI falla ----------
@pytest.mark.parametrize(
    ("sri", "error"),
    [
        (SriSimulado(error=httpx.ConnectTimeout("tiempo agotado")), "No se pudo conectar"),
        (SriSimulado(b"<html>Service Unavailable</html>", status=503), "error 503"),
        (SriSimulado(b"esto no es xml", status=200), "no es XML"),
        (
            SriSimulado(
                _soap(
                    "<soap:Fault><faultcode>soap:Server</faultcode>"
                    "<faultstring>Error interno</faultstring></soap:Fault>"
                ),  # fmt: skip
                status=500,
            ),
            "Error interno",
        ),
        (SriSimulado(_soap("<otra-cosa/>")), "formato esperado"),
        (SriSimulado(_recepcion("RARO")), "desconocido"),
    ],
)
def test_si_el_sri_falla_se_lanza_un_error_para_reintentar(sri, error):
    with pytest.raises(SriNoDisponibleError, match=error):
        sri.cliente().enviar(b"<x/>")


def test_una_respuesta_maliciosa_no_puede_leer_archivos_del_servidor(tmp_path):
    secreto = tmp_path / "secreto.txt"
    secreto.write_text("SECRETO-IONDU")
    ataque = (
        f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY xxe SYSTEM "{secreto.as_uri()}">]>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
        "<RespuestaRecepcionComprobante><estado>&xxe;</estado></RespuestaRecepcionComprobante>"
        "</soap:Body></soap:Envelope>"
    ).encode()

    with pytest.raises(SriNoDisponibleError) as error:
        SriSimulado(ataque).cliente().enviar(b"<x/>")
    assert "SECRETO-IONDU" not in str(error.value)
