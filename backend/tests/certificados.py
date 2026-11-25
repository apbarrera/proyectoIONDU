"""Certificados .p12 AUTOFIRMADOS para las pruebas (no sirven ante el SRI).

Imitan la estructura de un certificado de firma electrónica: llave RSA y certificado
con titular y fechas de validez, protegidos con contraseña.
"""

from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509.oid import NameOID

CLAVE_P12 = "clave-de-prueba"


def crear_p12(
    *,
    titular: str = "CAFETERIA DEMO S.A.",
    clave: str = CLAVE_P12,
    dias_validez: int = 365,
    desde: datetime | None = None,
    llave_ec: bool = False,
) -> bytes:
    llave = (
        ec.generate_private_key(ec.SECP256R1())
        if llave_ec
        else rsa.generate_private_key(public_exponent=65537, key_size=2048)
    )
    inicio = desde or datetime.now(UTC) - timedelta(days=1)
    nombre = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, titular),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "EC"),
        ]
    )
    emisor = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AUTORIDAD DE PRUEBA IONDU")])
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(emisor)
        .public_key(llave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(inicio)
        .not_valid_after(inicio + timedelta(days=dias_validez))
        .sign(llave, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"firma", llave, certificado, None, BestAvailableEncryption(clave.encode())
    )
