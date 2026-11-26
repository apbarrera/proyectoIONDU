"""Lectura del buzón IMAP de la empresa: mensajes nuevos y sus adjuntos XML.

Se avanza por UID: se guarda el último leído y UIDVALIDITY. Si el servidor cambia
UIDVALIDITY (buzón recreado), se vuelve a leer desde una fecha; la base evita duplicados.
Nunca se marcan, mueven ni borran mensajes (la carpeta se abre en solo lectura).
"""

import contextlib
import email
import imaplib
import re
import ssl
from dataclasses import dataclass, field
from datetime import date, datetime
from email.message import Message
from email.policy import default as politica_por_defecto
from email.utils import parsedate_to_datetime

TIEMPO_ESPERA = 30  # segundos
MAX_MENSAJES_POR_LECTURA = 50
MAX_ADJUNTOS = 5
CLAVE_RECHAZADA = "El servidor rechazó el usuario o la clave del correo."
TIPOS_XML = {"application/xml", "text/xml"}
_UIDVALIDITY = re.compile(rb"UIDVALIDITY (\d+)")


class BuzonInaccesibleError(Exception):
    """No se pudo leer el buzón. El mensaje es apto para mostrar al Administrador."""


@dataclass(frozen=True)
class MensajeRecibido:
    uid: int
    message_id: str
    remitente: str | None
    asunto: str | None
    recibido_en: datetime | None
    adjuntos_xml: list[bytes] = field(default_factory=list)


@dataclass(frozen=True)
class Lectura:
    uid_validity: int
    mensajes: list[MensajeRecibido]


def _conectar(servidor: str, puerto: int, seguridad: str) -> imaplib.IMAP4:
    try:
        if seguridad == "ssl":
            return imaplib.IMAP4_SSL(
                servidor, puerto, ssl_context=ssl.create_default_context(), timeout=TIEMPO_ESPERA
            )
        conexion = imaplib.IMAP4(servidor, puerto, timeout=TIEMPO_ESPERA)
        if seguridad == "starttls":
            conexion.starttls(ssl_context=ssl.create_default_context())
        return conexion
    except (OSError, imaplib.IMAP4.error) as exc:
        raise BuzonInaccesibleError(f"No se pudo conectar con {servidor}:{puerto}.") from exc


def adjuntos_xml(mensaje: Message) -> list[bytes]:
    encontrados = []
    for parte in mensaje.walk():
        if parte.is_multipart():
            continue
        nombre = (parte.get_filename() or "").lower()
        if parte.get_content_type() in TIPOS_XML or nombre.endswith(".xml"):
            contenido = parte.get_payload(decode=True)
            if contenido:
                encontrados.append(contenido)
        if len(encontrados) >= MAX_ADJUNTOS:
            break
    return encontrados


def leer_mensaje(uid: int, crudo: bytes) -> MensajeRecibido:
    mensaje = email.message_from_bytes(crudo, policy=politica_por_defecto)
    try:
        recibido = parsedate_to_datetime(mensaje["Date"]) if mensaje["Date"] else None
    except (TypeError, ValueError):
        recibido = None
    message_id = (mensaje["Message-ID"] or "").strip() or f"<uid-{uid}@iondu.sin-message-id>"
    return MensajeRecibido(
        uid=uid,
        message_id=message_id[:998],
        remitente=(str(mensaje["From"]) if mensaje["From"] else None),
        asunto=(str(mensaje["Subject"])[:300] if mensaje["Subject"] else None),
        recibido_en=recibido,
        adjuntos_xml=adjuntos_xml(mensaje),
    )


class LectorImap:
    def __init__(
        self,
        servidor: str,
        puerto: int,
        seguridad: str,
        usuario: str,
        clave: str,
        carpeta: str = "INBOX",
    ):
        self.servidor = servidor
        self.puerto = puerto
        self.seguridad = seguridad
        self.usuario = usuario
        self.clave = clave
        self.carpeta = carpeta

    def _abrir(self) -> tuple[imaplib.IMAP4, int]:
        conexion = _conectar(self.servidor, self.puerto, self.seguridad)
        try:
            conexion.login(self.usuario, self.clave)
        except imaplib.IMAP4.error as exc:
            conexion.logout()
            raise BuzonInaccesibleError(CLAVE_RECHAZADA) from exc
        estado, _ = conexion.select(self.carpeta, readonly=True)
        if estado != "OK":
            conexion.logout()
            raise BuzonInaccesibleError(f"No existe la carpeta «{self.carpeta}» en el correo.")
        respuesta = conexion.response("UIDVALIDITY")[1]
        valor = _UIDVALIDITY.search(b" ".join(r for r in respuesta if r) or b"")
        uid_validity = int(valor.group(1)) if valor else 0
        if not uid_validity and respuesta and respuesta[0] and respuesta[0].isdigit():
            uid_validity = int(respuesta[0])
        return conexion, uid_validity

    def probar(self) -> None:
        """Conecta, inicia sesión y abre la carpeta. Lanza BuzonInaccesibleError si algo falla."""
        conexion, _ = self._abrir()
        conexion.logout()

    def leer_nuevos(self, uid_validity: int | None, ultimo_uid: int | None, desde: date) -> Lectura:
        conexion, validez = self._abrir()
        try:
            if uid_validity == validez and ultimo_uid:
                criterio = ("UID", f"{ultimo_uid + 1}:*")
            else:  # primera lectura o buzón recreado: desde una fecha
                criterio = ("SINCE", desde.strftime("%d-%b-%Y"))
            estado, datos = conexion.uid("SEARCH", *criterio)
            if estado != "OK":
                raise BuzonInaccesibleError("El servidor de correo no respondió la búsqueda.")
            uids = sorted(int(u) for u in (datos[0] or b"").split())
            # "N:*" devuelve el último aunque sea menor que N: se descartan los ya leídos.
            uids = [u for u in uids if not ultimo_uid or uid_validity != validez or u > ultimo_uid]
            mensajes = []
            for uid in uids[:MAX_MENSAJES_POR_LECTURA]:
                estado, partes = conexion.uid("FETCH", str(uid), "(BODY.PEEK[])")
                crudo = next(
                    (p[1] for p in partes or [] if isinstance(p, tuple) and len(p) > 1), None
                )
                if estado == "OK" and crudo:
                    mensajes.append(leer_mensaje(uid, crudo))
            return Lectura(validez, mensajes)
        except (OSError, imaplib.IMAP4.error) as exc:
            raise BuzonInaccesibleError("Se cortó la conexión con el servidor de correo.") from exc
        finally:
            with contextlib.suppress(OSError, imaplib.IMAP4.error):
                conexion.logout()
