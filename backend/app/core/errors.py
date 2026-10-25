"""Errores de la API con un formato único (ver docs/API.md, sección 2).

Toda respuesta de error tiene la forma:
    {"error": {"code": "...", "message": "...", "details": [...]}}

Los servicios lanzan `AppError` (o sus subclases) y estos manejadores la
convierten en la respuesta HTTP correspondiente.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("iondu.errors")


class AppError(Exception):
    """Error esperado de la aplicación: lleva su código HTTP y su `code` fijo."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None, details: list | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or []


class UnauthenticatedError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class UnprocessableError(AppError):
    """Datos con formato correcto pero que no se pueden usar (ej.: una categoría inexistente)."""

    status_code = 422
    code = "VALIDATION_ERROR"


def _error_body(code: str, message: str, details: list | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or []}}


# Mensajes en español para los errores de validación más comunes de Pydantic.
_VALIDATION_MESSAGES = {
    "missing": "Campo obligatorio.",
    "string_too_short": "Debe tener al menos {min_length} caracteres.",
    "string_too_long": "Debe tener como máximo {max_length} caracteres.",
    "greater_than_equal": "Debe ser mayor o igual a {ge}.",
    "greater_than": "Debe ser mayor que {gt}.",
    "less_than_equal": "Debe ser menor o igual a {le}.",
    "int_parsing": "Debe ser un número entero.",
    "decimal_parsing": "Debe ser un número.",
    "float_parsing": "Debe ser un número.",
    "bool_parsing": "Debe ser verdadero o falso.",
    "literal_error": "Valor no permitido. Opciones: {expected}.",
    "decimal_max_places": "Debe tener como máximo {decimal_places} decimales.",
    "extra_forbidden": "Este campo no se puede enviar.",
}


def _validation_details(exc: RequestValidationError) -> list[dict[str, str]]:
    details = []
    for err in exc.errors():
        # loc = ("body", "salePrice") o ("query", "page"): se muestra solo el campo.
        field = ".".join(str(part) for part in err["loc"][1:]) or str(err["loc"][0])
        template = _VALIDATION_MESSAGES.get(err["type"])
        message = template.format(**err.get("ctx", {})) if template else err["msg"]
        details.append({"field": field, "message": message})
    return details


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # JSON mal escrito: es una petición rota, no un dato inválido (igual que el texto
        # mal codificado, que FastAPI ya responde con 400).
        if any(err["type"] == "json_invalid" for err in exc.errors()):
            return JSONResponse(
                status_code=400,
                content=_error_body("BAD_REQUEST", "La petición no tiene un formato válido."),
            )
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "VALIDATION_ERROR", "Revisa los datos enviados.", _validation_details(exc)
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Rutas inexistentes, JSON mal formado, métodos no permitidos, etc.
        if exc.status_code == 404:
            return JSONResponse(status_code=404, content=_error_body("NOT_FOUND", "No existe."))
        if exc.status_code == 400:
            return JSONResponse(
                status_code=400,
                content=_error_body("BAD_REQUEST", "La petición no tiene un formato válido."),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("HTTP_ERROR", str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(OperationalError)
    async def _database_down(_: Request, exc: OperationalError) -> JSONResponse:
        logger.error("la base de datos no responde: %s", exc.orig)
        return JSONResponse(
            status_code=503,
            content=_error_body(
                "DATABASE_UNAVAILABLE", "El servicio no está disponible. Intenta en un momento."
            ),
        )

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        # El detalle va a los registros del servidor, nunca al usuario.
        logger.exception("error inesperado")
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "Ocurrió un error inesperado."),
        )
