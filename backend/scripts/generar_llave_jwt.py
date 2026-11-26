"""Genera la llave privada EC P-256 para AUTH_JWT_PRIVATE_KEY.

Imprime la línea lista para pegar en .env (o en el panel del despliegue). No guarda
nada en disco. Cada ambiente usa su propia llave.

Uso:  python -m scripts.generar_llave_jwt
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generar() -> str:
    pem = (
        ec.generate_private_key(ec.SECP256R1())
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
    )
    return pem.strip().replace("\n", "\\n")


if __name__ == "__main__":
    print(f"AUTH_JWT_PRIVATE_KEY={generar()}")
