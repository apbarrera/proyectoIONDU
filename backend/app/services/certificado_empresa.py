"""Gestión segura del certificado de firma electrónica de una empresa."""

import base64

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cifrado import get_cifrador
from app.core.errors import NotFoundError, UnprocessableError
from app.models.empresa import Empresa
from app.sri.certificado import CertificadoInvalidoError, cargar_p12

TAMANO_MAXIMO_P12 = 5 * 1024 * 1024  # 5 MiB


class CertificadoEmpresaService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def guardar(self, contenido: bytes, clave: str) -> dict:
        """Valida y cifra el certificado antes de persistirlo."""

        if not contenido:
            raise UnprocessableError("Debes seleccionar un archivo .p12.")

        if len(contenido) > TAMANO_MAXIMO_P12:
            raise UnprocessableError("El archivo .p12 no puede superar los 5 MiB.")

        if not clave or not clave.strip():
            raise UnprocessableError("Debes indicar la contraseña del certificado.")

        # Se comprueba el certificado en memoria, sin escribirlo en disco.
        try:
            certificado = cargar_p12(contenido, clave)
        except CertificadoInvalidoError as exc:
            raise UnprocessableError(
                "No se pudo validar el certificado. Comprueba el archivo y su contraseña."
            ) from exc

        # No aceptar certificados vencidos.
        if certificado.vencido():
            raise UnprocessableError("El certificado electrónico está vencido.")

        empresa = self.db.scalar(select(Empresa).where(Empresa.id_empresa == self.empresa_id))
        if empresa is None:
            raise NotFoundError("No se encontró la empresa del usuario.")

        cifrador = get_cifrador()

        certificado_cifrado = cifrador.cifrar(
            contenido,
            f"empresa:{self.empresa_id}:p12",
        )
        clave_cifrada = cifrador.cifrar(
            clave.encode("utf-8"),
            f"empresa:{self.empresa_id}:p12_password",
        )

        # Las columnas TEXT contienen Base64 del sobre cifrado completo.
        empresa.certificado_p12_cifrado = base64.b64encode(certificado_cifrado).decode("ascii")
        empresa.certificado_password_cifrada = base64.b64encode(clave_cifrada).decode("ascii")
        empresa.certificado_fecha_vencimiento = certificado.vence.date()

        # Las columnas separadas de nonce/tag no se utilizan: el sobre
        # de Cifrador ya contiene versión, nonce y etiqueta de autenticación.
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "mensaje": "Certificado electrónico guardado correctamente.",
            "fecha_vencimiento": empresa.certificado_fecha_vencimiento,
        }
