"""SRI simulado: facturación de demostración mientras no llega el certificado .p12.

Para las empresas de SRI_SIMULADO_EMPRESAS, y SOLO si están en ambiente de PRUEBAS:
- la factura se firma de verdad (XAdES-BES) con un certificado autofirmado generado en
  memoria, en lugar del .p12 de la empresa;
- en lugar de llamar al SRI, `ClienteSriSimulado` responde "RECIBIDA" y "AUTORIZADO".

Todo lo demás es el flujo real: XML validado, clave de acceso, totales, secuencial,
worker, RIDE y almacenamiento. La autorización queda marcada con el mensaje
MENSAJE_SIMULADO en mensajes_sri y el RIDE dice "SIMULADO - SIN VALIDEZ TRIBUTARIA".

En producción (ambiente 2) nunca se simula: sin .p12 la emisión falla como siempre.
"""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree

from app.core.config import TIMEZONE
from app.sri.certificado import Certificado
from app.sri.clave_acceso import Ambiente
from app.sri.servicios_web import (
    EstadoAutorizacion,
    EstadoRecepcion,
    Mensaje,
    RespuestaAutorizacion,
    RespuestaRecepcion,
)
from app.sri.xades import FirmadorXadesBes

IDENTIFICADOR_SIMULADO = "SIMULADO"
MENSAJE_SIMULADO = Mensaje(
    identificador=IDENTIFICADOR_SIMULADO,
    mensaje="Autorización simulada para demostración: el comprobante no tiene validez tributaria.",
    informacion_adicional="Se emitió sin certificado .p12 y sin enviarlo al SRI.",
    tipo="INFORMATIVO",
)
TITULAR_PRUEBA = "IONDU - CERTIFICADO DE PRUEBA (SIN VALIDEZ)"
_PARSER = etree.XMLParser(no_network=True, resolve_entities=False)


def usa_sri_simulado(empresa_id: int, ambiente: str | Ambiente, empresas: Iterable[int]) -> bool:
    """La empresa está en la lista y en ambiente de pruebas. En producción, nunca."""
    return empresa_id in set(empresas) and str(ambiente) == Ambiente.PRUEBAS.value


def es_autorizacion_simulada(mensajes_sri: Iterable[dict] | None) -> bool:
    """Si la autorización guardada de una factura fue simulada (para marcar el RIDE)."""
    return any(
        isinstance(m, dict) and m.get("identificador") == IDENTIFICADOR_SIMULADO
        for m in mensajes_sri or []
    )


@lru_cache(maxsize=1)
def _certificado_de_prueba() -> Certificado:
    """Certificado autofirmado, solo en memoria; se genera una vez por proceso."""
    llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, TITULAR_PRUEBA),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "EC"),
        ]
    )
    desde = datetime.now(UTC) - timedelta(days=1)
    hasta = desde + timedelta(days=365)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(llave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(desde)
        .not_valid_after(hasta)
        .sign(llave, hashes.SHA256())
    )
    return Certificado(
        llave_privada=llave,
        certificado=certificado,
        cadena=[],
        titular=TITULAR_PRUEBA,
        emisor=TITULAR_PRUEBA,
        valido_desde=desde,
        vence=hasta,
    )


def firmador_de_prueba() -> FirmadorXadesBes:
    """La firma XAdES-BES real, con el certificado de prueba en lugar del .p12."""
    return FirmadorXadesBes(_certificado_de_prueba())


class ClienteSriSimulado:
    """Misma interfaz que ClienteSri (enviar, autorizar y context manager), sin red.

    Se niega a procesar comprobantes de producción: es la segunda barrera, además de
    `usa_sri_simulado`, para que nunca se "autorice" una factura real.
    """

    def __init__(self, ambiente: Ambiente, *, reloj=lambda: datetime.now(ZoneInfo(TIMEZONE))):
        if ambiente != Ambiente.PRUEBAS:
            raise ValueError("El SRI simulado solo funciona en el ambiente de pruebas.")
        self._reloj = reloj
        self._recibidos: dict[str, bytes] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def close(self) -> None:
        return None

    def enviar(self, xml_firmado: bytes) -> RespuestaRecepcion:
        raiz = etree.fromstring(xml_firmado, _PARSER)
        if raiz.findtext("infoTributaria/ambiente") != Ambiente.PRUEBAS.value:
            raise ValueError("El SRI simulado solo acepta comprobantes del ambiente de pruebas.")
        clave = raiz.findtext("infoTributaria/claveAcceso") or ""
        self._recibidos[clave] = xml_firmado
        return RespuestaRecepcion(EstadoRecepcion.RECIBIDA)

    def autorizar(self, clave_acceso: str) -> RespuestaAutorizacion:
        xml = self._recibidos.get(clave_acceso)
        return RespuestaAutorizacion(
            estado=EstadoAutorizacion.AUTORIZADO,
            # Como el SRI en línea: el número de autorización es la clave de acceso.
            numero_autorizacion=clave_acceso,
            fecha_autorizacion=self._reloj(),
            comprobante=xml.decode("utf-8") if xml else None,
            mensajes=[MENSAJE_SIMULADO],
        )
