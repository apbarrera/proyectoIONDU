"""Firma XAdES-BES de los comprobantes, como la exige el SRI.

- Firma XML envuelta (enveloped) al final de <factura id="comprobante">.
- XAdES 1.3.2, firma RSA-SHA1, resúmenes SHA-1 y canonicalización C14N inclusiva.
  SHA-1 hoy se considera débil, pero es lo que exige la ficha técnica del SRI; con
  SHA-256 el SRI rechaza el comprobante. Solo se usa aquí, por obligación.
- Tres referencias firmadas: las propiedades firmadas (hora y certificado), el
  certificado (KeyInfo) y el comprobante sin la firma.

La llave privada se usa solo en memoria (viene del .p12 descifrado, ver certificado.py).
Verificación independiente en las pruebas con la librería xmlsig.
"""

import base64
import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

from app.core.config import TIMEZONE
from app.sri.certificado import Certificado, CertificadoInvalidoError, cargar_p12

DS = "http://www.w3.org/2000/09/xmldsig#"
ETSI = "http://uri.etsi.org/01903/v1.3.2#"
C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
RSA_SHA1 = f"{DS}rsa-sha1"
SHA1 = f"{DS}sha1"
ENVELOPED = f"{DS}enveloped-signature"
TIPO_SIGNED_PROPERTIES = "http://uri.etsi.org/01903#SignedProperties"


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def _c14n(elemento: etree._Element) -> bytes:
    """C14N inclusiva (incluye los espacios de nombres heredados de los ancestros)."""
    return etree.tostring(elemento, method="c14n")


def _sha1(datos: bytes) -> str:
    return _b64(hashlib.sha1(datos).digest())  # exigido por el SRI


def _entero_b64(numero: int) -> str:
    return _b64(numero.to_bytes((numero.bit_length() + 7) // 8, "big"))


def _ds(padre: etree._Element, nombre: str, texto: str | None = None, **atributos):
    elemento = etree.SubElement(padre, f"{{{DS}}}{nombre}", **atributos)
    elemento.text = texto
    return elemento


def _etsi(padre: etree._Element, nombre: str, texto: str | None = None, **atributos):
    elemento = etree.SubElement(padre, f"{{{ETSI}}}{nombre}", **atributos)
    elemento.text = texto
    return elemento


def _referencia(signed_info, uri: str, digest: str | None = None, **atributos):
    referencia = _ds(signed_info, "Reference", URI=uri, **atributos)
    if uri == "#comprobante":
        _ds(_ds(referencia, "Transforms"), "Transform", Algorithm=ENVELOPED)
    _ds(referencia, "DigestMethod", Algorithm=SHA1)
    return _ds(referencia, "DigestValue", digest)


class FirmadorXadesBes:
    """Firmador real (implementa el protocolo Firmador de firma.py)."""

    def __init__(
        self,
        certificado: Certificado,
        *,
        reloj: Callable[[], datetime] = lambda: datetime.now(ZoneInfo(TIMEZONE)),
    ):
        self._cert = certificado
        self._reloj = reloj

    @classmethod
    def desde_p12(cls, contenido: bytes, clave: str) -> "FirmadorXadesBes":
        return cls(cargar_p12(contenido, clave))

    def firmar(self, xml: bytes) -> bytes:
        ahora = self._reloj()
        if self._cert.vencido(ahora):
            raise CertificadoInvalidoError(
                f"El certificado de firma venció el {self._cert.vence:%d/%m/%Y}."
            )
        raiz = etree.fromstring(xml, etree.XMLParser(no_network=True, resolve_entities=False))
        if raiz.get("id") != "comprobante":
            raise ValueError('El comprobante debe tener el atributo id="comprobante".')
        if raiz.find(f"{{{DS}}}Signature") is not None:
            raise ValueError("El comprobante ya está firmado.")

        n = secrets.randbelow(900_000) + 100_000
        id_firma = f"Signature{n}"
        id_propiedades = f"{id_firma}-SignedProperties{n}"
        id_certificado = f"Certificate{n}"
        id_ref_comprobante = f"Reference-ID-{n}"

        # 1. Huella del comprobante SIN la firma (transformación "enveloped").
        digest_comprobante = _sha1(_c14n(raiz))

        # 2. Estructura de la firma, ya dentro del comprobante.
        firma = etree.SubElement(
            raiz, f"{{{DS}}}Signature", nsmap={"ds": DS, "etsi": ETSI}, Id=id_firma
        )
        signed_info = _ds(firma, "SignedInfo", Id=f"Signature-SignedInfo{n}")
        _ds(signed_info, "CanonicalizationMethod", Algorithm=C14N)
        _ds(signed_info, "SignatureMethod", Algorithm=RSA_SHA1)
        digest_propiedades = _referencia(
            signed_info,
            f"#{id_propiedades}",
            Id=f"SignedPropertiesID{n}",
            Type=TIPO_SIGNED_PROPERTIES,
        )
        digest_certificado = _referencia(signed_info, f"#{id_certificado}")
        _referencia(signed_info, "#comprobante", digest_comprobante, Id=id_ref_comprobante)

        valor_firma = _ds(firma, "SignatureValue", Id=f"SignatureValue{n}")

        certificado_der = self._cert.certificado.public_bytes(serialization.Encoding.DER)
        numeros = self._cert.llave_privada.public_key().public_numbers()
        key_info = _ds(firma, "KeyInfo", Id=id_certificado)
        _ds(_ds(key_info, "X509Data"), "X509Certificate", _b64(certificado_der))
        rsa_key = _ds(_ds(key_info, "KeyValue"), "RSAKeyValue")
        _ds(rsa_key, "Modulus", _entero_b64(numeros.n))
        _ds(rsa_key, "Exponent", _entero_b64(numeros.e))

        objeto = _ds(firma, "Object", Id=f"{id_firma}-Object{n}")
        calificadoras = _etsi(objeto, "QualifyingProperties", Target=f"#{id_firma}")
        propiedades = _etsi(calificadoras, "SignedProperties", Id=id_propiedades)
        de_la_firma = _etsi(propiedades, "SignedSignatureProperties")
        _etsi(de_la_firma, "SigningTime", ahora.isoformat(timespec="seconds"))
        cert = _etsi(_etsi(de_la_firma, "SigningCertificate"), "Cert")
        huella = _etsi(cert, "CertDigest")
        _ds(huella, "DigestMethod", Algorithm=SHA1)
        _ds(huella, "DigestValue", _sha1(certificado_der))
        emisor_serie = _etsi(cert, "IssuerSerial")
        _ds(emisor_serie, "X509IssuerName", self._cert.certificado.issuer.rfc4514_string())
        _ds(emisor_serie, "X509SerialNumber", str(self._cert.certificado.serial_number))
        formato = _etsi(
            _etsi(propiedades, "SignedDataObjectProperties"),
            "DataObjectFormat",
            ObjectReference=f"#{id_ref_comprobante}",
        )
        _etsi(formato, "Description", "contenido comprobante")
        _etsi(formato, "MimeType", "text/xml")

        # 3. Huellas de las propiedades y del certificado, ya en su lugar.
        digest_propiedades.text = _sha1(_c14n(propiedades))
        digest_certificado.text = _sha1(_c14n(key_info))

        # 4. Firma RSA-SHA1 de SignedInfo.
        firma_rsa = self._cert.llave_privada.sign(
            _c14n(signed_info), padding.PKCS1v15(), hashes.SHA1()
        )
        valor_firma.text = _b64(firma_rsa)
        return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")
