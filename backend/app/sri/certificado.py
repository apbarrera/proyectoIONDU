"""Lectura del certificado de firma electrónica (.p12) de una empresa.

Comprueba la contraseña y obtiene la llave privada, el certificado, el titular y la
fecha de vencimiento (para la alerta de caducidad, RNF-25). Todo en memoria: el .p12
nunca se escribe en disco (CLAUDE.md).
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

DIAS_AVISO_VENCIMIENTO = 30


class CertificadoInvalidoError(Exception):
    """El .p12 no se puede usar (contraseña incorrecta, archivo dañado, vencido, etc.)."""


@dataclass(frozen=True)
class Certificado:
    llave_privada: RSAPrivateKey
    certificado: x509.Certificate
    cadena: list[x509.Certificate]
    titular: str
    emisor: str
    valido_desde: datetime
    vence: datetime

    def dias_para_vencer(self, ahora: datetime | None = None) -> int:
        return (self.vence - (ahora or datetime.now(UTC))).days

    def vencido(self, ahora: datetime | None = None) -> bool:
        return (ahora or datetime.now(UTC)) >= self.vence

    def por_vencer(self, ahora: datetime | None = None) -> bool:
        """Faltan DIAS_AVISO_VENCIMIENTO días o menos (RNF-25)."""
        return not self.vencido(ahora) and self.dias_para_vencer(ahora) <= DIAS_AVISO_VENCIMIENTO


def _nombre(nombre: x509.Name) -> str:
    atributos = nombre.get_attributes_for_oid(NameOID.COMMON_NAME)
    return str(atributos[0].value) if atributos else nombre.rfc4514_string()


def cargar_p12(contenido: bytes, clave: str) -> Certificado:
    """Abre el .p12 en memoria. Lanza CertificadoInvalidoError con un mensaje para el usuario."""
    try:
        llave, certificado, cadena = pkcs12.load_key_and_certificates(
            contenido, clave.encode("utf-8")
        )
    except ValueError as exc:
        raise CertificadoInvalidoError(
            "No se pudo abrir el certificado: la contraseña es incorrecta o el archivo está dañado."
        ) from exc
    if llave is None or certificado is None:
        raise CertificadoInvalidoError("El archivo no contiene una llave privada y su certificado.")
    if not isinstance(llave, RSAPrivateKey):
        raise CertificadoInvalidoError("La firma del SRI requiere un certificado con llave RSA.")
    return Certificado(
        llave_privada=llave,
        certificado=certificado,
        cadena=list(cadena or []),
        titular=_nombre(certificado.subject),
        emisor=_nombre(certificado.issuer),
        valido_desde=certificado.not_valid_before_utc,
        vence=certificado.not_valid_after_utc,
    )
