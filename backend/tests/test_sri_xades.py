"""Firma XAdES-BES verificada con una librería independiente (xmlsig).

Usa certificados autofirmados (tests/certificados.py): la estructura es la que exige
el SRI, pero solo el SRI de pruebas, con un .p12 real, confirma que la acepta.
"""

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import xmlsig
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

from app.sri.certificado import CertificadoInvalidoError, cargar_p12
from app.sri.emision import EstadoEmision, ServicioEmision
from app.sri.factura_xml import generar_factura_xml, validar_factura_xml
from app.sri.servicios_web import (
    EstadoAutorizacion,
    EstadoRecepcion,
    RespuestaAutorizacion,
    RespuestaRecepcion,
)
from app.sri.xades import C14N, DS, ETSI, RSA_SHA1, SHA1, FirmadorXadesBes
from tests.certificados import CLAVE_P12, crear_p12
from tests.datos_sri import FACTURA

NS = {"ds": DS, "etsi": ETSI}
HORA_FIRMA = datetime(2026, 10, 27, 11, 20, 30, tzinfo=ZoneInfo("America/Guayaquil"))
CERTIFICADO = cargar_p12(crear_p12(), CLAVE_P12)
XML = generar_factura_xml(FACTURA).xml


def _firmar(certificado=CERTIFICADO, xml: bytes = XML) -> bytes:
    return FirmadorXadesBes(certificado, reloj=lambda: HORA_FIRMA).firmar(xml)


def _verificar(firmado: bytes) -> None:
    """Verificación independiente con xmlsig (huellas y firma RSA con el certificado de
    KeyInfo). Lanza una excepción si la firma no es válida."""
    firma = etree.fromstring(firmado).find(f"{{{DS}}}Signature")
    contexto = xmlsig.SignatureContext()
    contexto.public_key = CERTIFICADO.certificado.public_key()
    contexto.verify(firma)


# ---------- La firma es válida ----------
def test_la_firma_es_valida_para_un_verificador_independiente():
    firmado = _firmar()
    _verificar(firmado)
    assert validar_factura_xml(firmado) == []  # sigue cumpliendo el esquema del SRI


def test_estructura_que_exige_el_sri():
    raiz = etree.fromstring(_firmar())
    firma = raiz[-1]
    assert firma.tag == f"{{{DS}}}Signature"  # al final del comprobante
    assert firma.find("ds:SignedInfo/ds:CanonicalizationMethod", NS).get("Algorithm") == C14N
    assert firma.find("ds:SignedInfo/ds:SignatureMethod", NS).get("Algorithm") == RSA_SHA1
    referencias = firma.findall("ds:SignedInfo/ds:Reference", NS)
    assert [r.get("URI") for r in referencias][2] == "#comprobante"
    assert referencias[0].get("Type") == "http://uri.etsi.org/01903#SignedProperties"
    assert {r.find("ds:DigestMethod", NS).get("Algorithm") for r in referencias} == {SHA1}
    # Las referencias apuntan a las propiedades firmadas y al certificado.
    ids = {e.get("Id") for e in firma.iter() if e.get("Id")}
    assert {referencias[0].get("URI")[1:], referencias[1].get("URI")[1:]} <= ids


def test_propiedades_firmadas_con_la_hora_de_ecuador_y_el_certificado():
    firma = etree.fromstring(_firmar())[-1]
    propiedades = firma.find(".//etsi:SignedSignatureProperties", NS)
    assert propiedades.findtext("etsi:SigningTime", namespaces=NS) == "2026-10-27T11:20:30-05:00"

    der = CERTIFICADO.certificado.public_bytes(serialization.Encoding.DER)
    huella = base64.b64encode(hashlib.sha1(der).digest()).decode()
    cert = propiedades.find("etsi:SigningCertificate/etsi:Cert", NS)
    assert cert.findtext("etsi:CertDigest/ds:DigestValue", namespaces=NS) == huella
    assert cert.findtext("etsi:IssuerSerial/ds:X509IssuerName", namespaces=NS) == (
        "CN=AUTORIDAD DE PRUEBA IONDU"
    )
    serie = cert.findtext("etsi:IssuerSerial/ds:X509SerialNumber", namespaces=NS)
    assert serie == str(CERTIFICADO.certificado.serial_number)

    referencia = firma.find("ds:SignedInfo/ds:Reference[@URI='#comprobante']", NS)
    formato = firma.find(".//etsi:DataObjectFormat", NS)
    assert formato.get("ObjectReference") == f"#{referencia.get('Id')}"
    assert formato.findtext("etsi:MimeType", namespaces=NS) == "text/xml"


def test_cada_firma_usa_identificadores_distintos():
    ids_a = etree.fromstring(_firmar())[-1].get("Id")
    ids_b = etree.fromstring(_firmar())[-1].get("Id")
    assert ids_a != ids_b


# ---------- La firma detecta trampas ----------
def test_cambiar_el_total_despues_de_firmar_invalida_la_firma():
    raiz = etree.fromstring(_firmar())
    raiz.find("infoFactura/importeTotal").text = "1.00"
    with pytest.raises(Exception):  # noqa: B017 (xmlsig lanza Exception genérica)
        _verificar(etree.tostring(raiz))


def test_alterar_la_firma_rsa_la_invalida():
    raiz = etree.fromstring(_firmar())
    valor = raiz.find(".//ds:SignatureValue", NS)
    valor.text = base64.b64encode(bytes(256)).decode()  # firma falsa del mismo largo
    with pytest.raises(Exception):  # noqa: B017
        _verificar(etree.tostring(raiz))


def test_la_firma_rsa_solo_cuadra_con_la_llave_del_firmante():
    # xmlsig usa el certificado incluido en la firma; aquí se verifica la firma RSA
    # de SignedInfo directamente, con la llave correcta y con la de otra persona.
    firma = etree.fromstring(_firmar())[-1]
    signed_info = etree.tostring(firma.find("ds:SignedInfo", NS), method="c14n")
    valor = base64.b64decode(firma.findtext("ds:SignatureValue", namespaces=NS))

    CERTIFICADO.certificado.public_key().verify(
        valor, signed_info, padding.PKCS1v15(), hashes.SHA1()
    )
    otro = cargar_p12(crear_p12(titular="OTRA PERSONA"), CLAVE_P12)
    with pytest.raises(InvalidSignature):
        otro.certificado.public_key().verify(valor, signed_info, padding.PKCS1v15(), hashes.SHA1())


# ---------- Validaciones antes de firmar ----------
def test_no_firma_con_un_certificado_vencido():
    vencido = cargar_p12(
        crear_p12(desde=datetime.now(UTC) - timedelta(days=730), dias_validez=365), CLAVE_P12
    )
    with pytest.raises(CertificadoInvalidoError, match="venció"):
        _firmar(vencido)


def test_no_firma_dos_veces():
    with pytest.raises(ValueError, match="ya está firmado"):
        _firmar(xml=_firmar())


def test_exige_el_id_comprobante():
    with pytest.raises(ValueError, match='id="comprobante"'):
        _firmar(xml=b"<factura><x/></factura>")


# ---------- Encaja en el flujo de emisión ----------
class SriQueAutoriza:
    def __init__(self):
        self.enviado: bytes | None = None

    def enviar(self, xml):
        self.enviado = xml
        return RespuestaRecepcion(EstadoRecepcion.RECIBIDA)

    def autorizar(self, clave):
        return RespuestaAutorizacion(EstadoAutorizacion.AUTORIZADO, clave, HORA_FIRMA)


def test_el_flujo_de_emision_envia_la_factura_firmada():
    sri = SriQueAutoriza()
    servicio = ServicioEmision(sri, FirmadorXadesBes(CERTIFICADO), dormir=lambda _s: None)
    resultado = servicio.emitir(FACTURA)
    assert resultado.estado == EstadoEmision.AUTORIZADA
    assert sri.enviado == resultado.xml_firmado
    _verificar(sri.enviado)  # lo que recibe el SRI tiene una firma válida
    assert resultado.ride.startswith(b"%PDF")
