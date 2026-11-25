"""Endpoints para administrar el certificado de firma electrónica."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import DbSession, SoloAdministrador
from app.core.errors import UnprocessableError
from app.services.certificado_empresa import (
    TAMANO_MAXIMO_P12,
    CertificadoEmpresaService,
)

router = APIRouter(tags=["Certificado electrónico"])


@router.put("/company/certificate")
async def guardar_certificado(
    db: DbSession,
    contexto: SoloAdministrador,
    archivo: Annotated[UploadFile, File(description="Archivo de firma electrónica .p12")],
    clave: Annotated[str, Form(min_length=1, max_length=1024)],
) -> dict[str, str | date]:
    """Valida y almacena el certificado cifrado de la empresa autenticada."""

    try:
        if not archivo.filename or not archivo.filename.lower().endswith(".p12"):
            raise UnprocessableError("El archivo debe tener extensión .p12.")

        contenido = await archivo.read(TAMANO_MAXIMO_P12 + 1)

        if len(contenido) > TAMANO_MAXIMO_P12:
            raise UnprocessableError("El archivo .p12 no puede superar los 5 MiB.")

        return CertificadoEmpresaService(db, contexto.empresa_id).guardar(contenido, clave)
    finally:
        await archivo.close()
