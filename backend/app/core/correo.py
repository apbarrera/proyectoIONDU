"""Envío de correos por SMTP (recuperación de contraseña e invitaciones).

Cualquier servidor SMTP sirve: en local, Mailpit (docker-compose.override.yml); en
producción, el proveedor que se contrate. Sin SMTP_HOST, `crear_enviador` devuelve None
y el sistema sigue funcionando sin correos (los usuarios reciben contraseña temporal).
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger("iondu.correo")
TIEMPO_ESPERA = 15  # segundos


class Enviador(Protocol):
    def enviar(self, destinatario: str, asunto: str, texto: str, html: str | None = None) -> None:
        """Lanza una excepción si no pudo entregar el mensaje al servidor."""
        ...


class EnviadorSMTP:
    def __init__(
        self,
        host: str,
        port: int,
        remitente: str,
        *,
        usuario: str | None = None,
        clave: str | None = None,
        starttls: bool = True,
    ):
        self.host = host
        self.port = port
        self.remitente = remitente
        self.usuario = usuario
        self.clave = clave
        self.starttls = starttls

    def enviar(self, destinatario: str, asunto: str, texto: str, html: str | None = None) -> None:
        mensaje = EmailMessage()
        mensaje["From"] = self.remitente
        mensaje["To"] = destinatario
        mensaje["Subject"] = asunto
        mensaje.set_content(texto)
        if html:
            mensaje.add_alternative(html, subtype="html")

        with smtplib.SMTP(self.host, self.port, timeout=TIEMPO_ESPERA) as smtp:
            if self.starttls:
                smtp.starttls(context=ssl.create_default_context())
            if self.usuario and self.clave:
                smtp.login(self.usuario, self.clave)
            smtp.send_message(mensaje)


def crear_enviador(settings: Settings) -> Enviador | None:
    if not settings.smtp_host:
        return None
    return EnviadorSMTP(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_from,
        usuario=settings.smtp_username,
        clave=settings.smtp_password.get_secret_value() if settings.smtp_password else None,
        starttls=settings.smtp_starttls,
    )


def enviar_sin_fallar(enviador: Enviador, destinatario: str, asunto: str, texto: str, html: str):
    """Para tareas en segundo plano: un fallo del correo se registra, no rompe la petición.

    No se registra el destinatario ni el contenido (llevan el enlace de un solo uso).
    """
    try:
        enviador.enviar(destinatario, asunto, texto, html)
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de red o SMTP
        logger.error("No se pudo enviar el correo '%s'. tipo=%s", asunto, type(exc).__name__)
