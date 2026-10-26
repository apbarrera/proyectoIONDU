"""Cliente de los servicios web del SRI (esquema offline): recepción y autorización.

    1. enviar(xml_firmado)  -> RECIBIDA | DEVUELTA (con mensajes de error)
    2. autorizar(clave)     -> AUTORIZADO | NO AUTORIZADO | EN PROCESO

Son servicios SOAP; los mensajes se arman y leen con lxml. Si el SRI no responde
(red, tiempo de espera, error 5xx) se lanza SriNoDisponibleError para reintentar después.

Las respuestas se leen con no_network=True y resolve_entities=False: evita ataques
XXE (un XML que intente leer archivos del servidor o conectarse a otros sitios).
"""

import base64
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

import httpx2 as httpx
from lxml import etree

from app.sri.clave_acceso import Ambiente

_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
_NS_RECEPCION = "http://ec.gob.sri.ws.recepcion"
_NS_AUTORIZACION = "http://ec.gob.sri.ws.autorizacion"

_BASE = {
    Ambiente.PRUEBAS: "https://celcer.sri.gob.ec/comprobantes-electronicos-ws",
    Ambiente.PRODUCCION: "https://cel.sri.gob.ec/comprobantes-electronicos-ws",
}
URL_RECEPCION = {a: f"{u}/RecepcionComprobantesOffline" for a, u in _BASE.items()}
URL_AUTORIZACION = {a: f"{u}/AutorizacionComprobantesOffline" for a, u in _BASE.items()}

# Códigos de mensaje del SRI con un significado especial.
CLAVE_YA_REGISTRADA = "43"  # el SRI ya recibió este comprobante: pasar a autorización
CLAVE_EN_PROCESAMIENTO = "70"  # el SRI lo está procesando: consultar de nuevo más tarde

_TIEMPO_ESPERA = httpx.Timeout(30.0, connect=10.0)
_PARSER = etree.XMLParser(no_network=True, resolve_entities=False, huge_tree=False)


class SriNoDisponibleError(Exception):
    """El SRI no respondió o respondió con un error del servidor: reintentar más tarde."""


class EstadoRecepcion(StrEnum):
    RECIBIDA = "RECIBIDA"
    DEVUELTA = "DEVUELTA"


class EstadoAutorizacion(StrEnum):
    AUTORIZADO = "AUTORIZADO"
    NO_AUTORIZADO = "NO AUTORIZADO"
    EN_PROCESO = "EN PROCESO"  # el SRI aún no tiene una respuesta para esa clave


@dataclass(frozen=True)
class Mensaje:
    identificador: str
    mensaje: str
    informacion_adicional: str | None
    tipo: str  # ERROR | ADVERTENCIA | INFORMATIVO


@dataclass(frozen=True)
class RespuestaRecepcion:
    estado: EstadoRecepcion
    mensajes: list[Mensaje] = field(default_factory=list)

    @property
    def ya_registrada(self) -> bool:
        """DEVUELTA solo porque el SRI ya la tenía (p. ej., un envío anterior que se cortó)."""
        return any(m.identificador == CLAVE_YA_REGISTRADA for m in self.mensajes)

    @property
    def puede_consultar_autorizacion(self) -> bool:
        return self.estado == EstadoRecepcion.RECIBIDA or self.ya_registrada


@dataclass(frozen=True)
class RespuestaAutorizacion:
    estado: EstadoAutorizacion
    numero_autorizacion: str | None = None
    fecha_autorizacion: datetime | None = None
    comprobante: str | None = None  # el XML autorizado, tal como lo devuelve el SRI
    mensajes: list[Mensaje] = field(default_factory=list)


# ---------- lectura de XML sin depender de prefijos de espacio de nombres ----------
def _hijo(nodo: etree._Element, nombre: str) -> etree._Element | None:
    encontrados = nodo.xpath(f"./*[local-name()='{nombre}']")
    return encontrados[0] if encontrados else None


def _texto(nodo: etree._Element, nombre: str) -> str | None:
    hijo = _hijo(nodo, nombre)
    return hijo.text.strip() if hijo is not None and hijo.text else None


def _todos(nodo: etree._Element, nombre: str) -> list[etree._Element]:
    return nodo.xpath(f".//*[local-name()='{nombre}']")


def _mensajes(nodo: etree._Element) -> list[Mensaje]:
    return [
        Mensaje(
            identificador=_texto(m, "identificador") or "",
            mensaje=_texto(m, "mensaje") or "",
            informacion_adicional=_texto(m, "informacionAdicional"),
            tipo=_texto(m, "tipo") or "",
        )
        for m in _todos(nodo, "mensaje")
        if _hijo(m, "identificador") is not None
    ]


def _sobre(espacio: str, operacion: str, parametro: str, valor: str) -> bytes:
    """Sobre SOAP 1.1 con una operación y un parámetro."""
    sobre = etree.Element(f"{{{_SOAP}}}Envelope", nsmap={"soapenv": _SOAP, "ec": espacio})
    etree.SubElement(sobre, f"{{{_SOAP}}}Header")
    cuerpo = etree.SubElement(sobre, f"{{{_SOAP}}}Body")
    llamada = etree.SubElement(cuerpo, f"{{{espacio}}}{operacion}")
    etree.SubElement(llamada, parametro).text = valor
    return etree.tostring(sobre, xml_declaration=True, encoding="UTF-8")


class ClienteSri:
    def __init__(self, ambiente: Ambiente, *, http: httpx.Client | None = None):
        self.ambiente = Ambiente(ambiente)
        self._http = http or httpx.Client(timeout=_TIEMPO_ESPERA)

    def _llamar(self, url: str, sobre: bytes) -> etree._Element:
        try:
            respuesta = self._http.post(
                url,
                content=sobre,
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
            )
        except httpx.HTTPError as exc:
            raise SriNoDisponibleError(f"No se pudo conectar con el SRI: {exc}") from exc

        if respuesta.status_code >= 500 and b"Fault" not in respuesta.content:
            raise SriNoDisponibleError(f"El SRI respondió con error {respuesta.status_code}.")
        try:
            raiz = etree.fromstring(respuesta.content, _PARSER)
        except etree.XMLSyntaxError as exc:
            raise SriNoDisponibleError("El SRI devolvió una respuesta que no es XML.") from exc

        falla = raiz.xpath("//*[local-name()='Fault']")
        if falla:
            detalle = _texto(falla[0], "faultstring") or "sin detalle"
            raise SriNoDisponibleError(f"El SRI devolvió un error SOAP: {detalle}")
        return raiz

    def enviar(self, xml_firmado: bytes) -> RespuestaRecepcion:
        """Recepción: envía el comprobante FIRMADO (el SRI lo recibe en base64)."""
        sobre = _sobre(
            _NS_RECEPCION,
            "validarComprobante",
            "xml",
            base64.b64encode(xml_firmado).decode("ascii"),
        )
        raiz = self._llamar(URL_RECEPCION[self.ambiente], sobre)
        respuesta = _todos(raiz, "RespuestaRecepcionComprobante")
        if not respuesta:
            raise SriNoDisponibleError(
                "La respuesta de recepción del SRI no tiene el formato esperado."
            )
        estado = _texto(respuesta[0], "estado")
        if estado not in EstadoRecepcion._value2member_map_:
            raise SriNoDisponibleError(f"Estado de recepción desconocido: {estado!r}.")
        return RespuestaRecepcion(EstadoRecepcion(estado), _mensajes(respuesta[0]))

    def autorizar(self, clave_acceso: str) -> RespuestaAutorizacion:
        """Autorización: consulta el resultado del comprobante con su clave de acceso."""
        sobre = _sobre(
            _NS_AUTORIZACION,
            "autorizacionComprobante",
            "claveAccesoComprobante",
            clave_acceso,
        )
        raiz = self._llamar(URL_AUTORIZACION[self.ambiente], sobre)
        autorizaciones = _todos(raiz, "autorizacion")
        if not autorizaciones:
            return RespuestaAutorizacion(EstadoAutorizacion.EN_PROCESO)

        # Puede haber varias (intentos anteriores): vale la autorizada; si no hay, la primera.
        elegida = next(
            (a for a in autorizaciones if _texto(a, "estado") == EstadoAutorizacion.AUTORIZADO),
            autorizaciones[0],
        )
        estado = _texto(elegida, "estado")
        fecha = _texto(elegida, "fechaAutorizacion")
        return RespuestaAutorizacion(
            estado=EstadoAutorizacion(estado)
            if estado in EstadoAutorizacion._value2member_map_
            else EstadoAutorizacion.EN_PROCESO,
            numero_autorizacion=_texto(elegida, "numeroAutorizacion"),
            fecha_autorizacion=datetime.fromisoformat(fecha) if fecha else None,
            comprobante=_texto(elegida, "comprobante"),
            mensajes=_mensajes(elegida),
        )
