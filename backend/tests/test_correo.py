"""Facturas de proveedores por correo (RF-3.2, RF-3.3): lectura, worker y API."""

# Fixtures `admin_a` vienen de test_usuarios: pytest los inyecta por nombre.
# ruff: noqa: F811
import base64
from dataclasses import replace
from datetime import date
from decimal import Decimal
from email.message import EmailMessage

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cifrado import Cifrador, generar_llave_maestra, leer_llave_maestra
from app.correo_entrante import procesar as modulo_procesar
from app.correo_entrante.factura_recibida import es_para_la_empresa, leer_factura
from app.correo_entrante.imap import (
    CLAVE_RECHAZADA,
    BuzonInaccesibleError,
    LectorImap,
    Lectura,
    MensajeRecibido,
    leer_mensaje,
)
from app.correo_entrante.procesar import contexto_clave, procesar_buzones
from app.models import BorradorGasto, BuzonCorreo, Empresa, Gasto, Proveedor
from app.services import correo as servicio_correo
from app.sri.factura_xml import Comprador, generar_factura_xml
from app.sri.identificacion import TipoIdentificacion
from tests.conftest import con_token
from tests.datos_sri import FACTURA
from tests.test_usuarios import admin_a  # noqa: F401

pytestmark = pytest.mark.usefixtures("supabase_falso")

RUC_EMPRESA = "1710000009001"
CIFRADOR = Cifrador(leer_llave_maestra(generar_llave_maestra()))
XML = generar_factura_xml(
    replace(FACTURA, comprador=Comprador(TipoIdentificacion.RUC, RUC_EMPRESA, "Empresa A"))
).xml


def _autorizacion(xml: bytes, estado="AUTORIZADO") -> bytes:
    return (
        f"<autorizacion><estado>{estado}</estado><comprobante><![CDATA["
        f"{xml.decode()}]]></comprobante></autorizacion>"
    ).encode()


# ---------- Lectura del XML ----------
def test_lee_la_factura_del_proveedor():
    factura = leer_factura(XML)
    assert factura is not None
    assert len(factura.clave_acceso) == 49
    assert factura.proveedor_nombre == "CAFETERÍA DEMO S.A."
    assert factura.numero == "001-001-000000123"
    assert factura.fecha_emision == date(2026, 10, 25)
    assert (factura.subtotal, factura.iva, factura.total) == (
        Decimal("21.30"),
        Decimal("2.70"),
        Decimal("24.00"),
    )
    assert factura.detalle[0]["descripcion"] == "Café molido 250 g"


def test_lee_la_factura_dentro_del_xml_de_autorizacion():
    autorizada = leer_factura(_autorizacion(XML))
    directa = leer_factura(XML)

    assert autorizada is not None
    assert directa is not None
    assert autorizada.clave_acceso == directa.clave_acceso
    assert leer_factura(_autorizacion(XML, "NO AUTORIZADO")) is None


@pytest.mark.parametrize(
    "contenido",
    [
        b"no es xml",
        b"<notaCredito/>",
        XML.replace(b"<codDoc>01</codDoc>", b"<codDoc>04</codDoc>"),
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>',
        pytest.param(
            b"<factura>" + b"x" * 1_000_001 + b"</factura>",
            id="xml_mayor_a_1mb",
        ),
    ],
)
def test_descarta_lo_que_no_es_una_factura_valida(contenido):
    assert leer_factura(contenido) is None


def test_solo_acepta_facturas_dirigidas_a_la_empresa():
    factura = leer_factura(XML)
    assert factura is not None
    assert es_para_la_empresa(factura, RUC_EMPRESA)
    assert not es_para_la_empresa(factura, "0990000000001")
    cedula = replace(factura, comprador_identificacion="1710000009")
    assert es_para_la_empresa(cedula, RUC_EMPRESA)  # persona natural: su cédula


def test_lee_los_adjuntos_xml_del_correo():
    correo = EmailMessage()
    correo["Message-ID"] = "<abc@proveedor.ec>"
    correo["From"] = "facturas@proveedor.ec"
    correo["Subject"] = "Factura 001-001-123"
    correo["Date"] = "Wed, 25 Nov 2026 10:00:00 -0500"
    correo.set_content("Adjuntamos su factura.")
    correo.add_attachment(XML, maintype="application", subtype="xml", filename="factura.xml")
    correo.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename="ride.pdf")

    mensaje = leer_mensaje(7, correo.as_bytes())

    assert (mensaje.uid, mensaje.message_id) == (7, "<abc@proveedor.ec>")
    assert mensaje.adjuntos_xml == [XML]
    assert mensaje.recibido_en is not None
    assert mensaje.recibido_en.year == 2026


# ---------- Proceso del worker ----------
class LectorFalso(LectorImap):
    lectura: Lectura | None = None
    error: Exception | None = None
    llamadas: list[tuple[str, str, str, str]] = []

    def __init__(
        self,
        servidor: str,
        puerto: int,
        seguridad: str,
        usuario: str,
        clave: str,
        carpeta: str = "INBOX",
    ):
        LectorFalso.llamadas.append((servidor, usuario, clave, carpeta))

    def leer_nuevos(
        self,
        uid_validity: int | None,
        ultimo_uid: int | None,
        desde: date,
    ) -> Lectura:
        if LectorFalso.error:
            raise LectorFalso.error
        assert LectorFalso.lectura is not None
        return LectorFalso.lectura

    def probar(self) -> None:
        if LectorFalso.error:
            raise LectorFalso.error


@pytest.fixture
def buzon(db, empresas):
    a, _ = empresas
    db.get(Empresa, a).ruc = RUC_EMPRESA
    cifrada = CIFRADOR.cifrar(b"clave-del-correo", contexto_clave(a))
    db.add(
        BuzonCorreo(
            id_empresa=a,
            servidor="imap.empresa.ec",
            puerto=993,
            seguridad="ssl",
            usuario="facturas@empresa.ec",
            clave_cifrada=base64.b64encode(cifrada).decode(),
            carpeta="INBOX",
        )
    )
    db.flush()
    LectorFalso.lectura, LectorFalso.error, LectorFalso.llamadas = None, None, []
    return a


def _fabrica(db):
    return lambda: Session(bind=db.connection(), join_transaction_mode="create_savepoint")


def _mensaje(uid, *adjuntos, message_id=None):
    return MensajeRecibido(
        uid, message_id or f"<m{uid}@p.ec>", "p@p.ec", "Factura", None, list(adjuntos)
    )


def _procesar(db):
    return procesar_buzones(_fabrica(db), CIFRADOR.descifrar, crear_lector=LectorFalso)


def test_el_worker_guarda_un_borrador_por_factura_sin_duplicar(db, buzon):
    # Dirigida a consumidor final, no a la empresa: se ignora.
    otra = generar_factura_xml(replace(FACTURA, comprador=Comprador.consumidor_final())).xml
    LectorFalso.lectura = Lectura(900, [_mensaje(5, XML, otra), _mensaje(6, b"no es xml")])

    assert _procesar(db) == 1
    assert db.scalar(select(func.count()).select_from(BorradorGasto)) == 1
    assert LectorFalso.llamadas[0][2] == "clave-del-correo"  # se descifró en memoria
    registro = db.get(BuzonCorreo, buzon)
    assert (registro.uid_validity, registro.ultimo_uid, registro.ultimo_error) == (900, 6, None)

    # El mismo correo reenviado (otro UID) con la misma factura no duplica.
    LectorFalso.lectura = Lectura(900, [_mensaje(7, XML, message_id="<reenvio@p.ec>")])
    _procesar(db)
    assert db.scalar(select(func.count()).select_from(BorradorGasto)) == 1


def test_un_error_del_buzon_queda_registrado(db, buzon):
    LectorFalso.error = BuzonInaccesibleError(CLAVE_RECHAZADA)
    assert _procesar(db) == 0
    registro = db.get(BuzonCorreo, buzon)
    assert registro.ultimo_error.startswith("El servidor rechazó")
    assert registro.ultima_lectura is not None


# ---------- API ----------
@pytest.fixture(autouse=True)
def cifrador_de_prueba(monkeypatch):
    monkeypatch.setattr(servicio_correo, "get_cifrador", lambda: CIFRADOR)
    monkeypatch.setattr(modulo_procesar, "LectorImap", LectorFalso)
    monkeypatch.setattr(servicio_correo, "LectorImap", LectorFalso)


CONFIG = {
    "server": "imap.gmail.com",
    "port": 993,
    "security": "ssl",
    "username": "facturas@empresa.ec",
    "password": "clave-de-aplicacion",
    "folder": "INBOX",
}


def test_configurar_el_buzon_cifra_la_clave_y_no_la_devuelve(client, db, admin_a, empresas):
    a, _ = empresas
    respuesta = client.put("/api/company/email-inbox", json=CONFIG, headers=con_token(admin_a))

    assert respuesta.status_code == 200
    assert "password" not in respuesta.json()
    guardado = db.get(BuzonCorreo, a)
    assert "clave-de-aplicacion" not in guardado.clave_cifrada
    descifrada = CIFRADOR.descifrar(base64.b64decode(guardado.clave_cifrada), contexto_clave(a))
    assert descifrada == b"clave-de-aplicacion"

    # Editar sin clave conserva la guardada.
    sin_clave = {k: v for k, v in CONFIG.items() if k != "password"} | {"folder": "Facturas"}
    editado = client.put("/api/company/email-inbox", json=sin_clave, headers=con_token(admin_a))
    assert editado.is_success
    assert db.get(BuzonCorreo, a).clave_cifrada == guardado.clave_cifrada


def test_la_primera_vez_la_clave_es_obligatoria(client, admin_a):
    sin_clave = {k: v for k, v in CONFIG.items() if k != "password"}
    respuesta = client.put("/api/company/email-inbox", json=sin_clave, headers=con_token(admin_a))
    assert respuesta.status_code == 422


def test_probar_la_conexion(client, admin_a):
    LectorFalso.error = None
    ok = client.post("/api/company/email-inbox/test", json=CONFIG, headers=con_token(admin_a))
    assert ok.json() == {"ok": True, "message": "Conexión correcta: el buzón se puede leer."}

    LectorFalso.error = BuzonInaccesibleError(CLAVE_RECHAZADA)
    mal = client.post("/api/company/email-inbox/test", json=CONFIG, headers=con_token(admin_a))
    assert mal.json()["ok"] is False
    LectorFalso.error = None


def test_confirmar_un_borrador_crea_el_gasto_y_el_proveedor(client, db, buzon, admin_a):
    LectorFalso.lectura = Lectura(1, [_mensaje(1, XML)])
    _procesar(db)
    [borrador] = client.get("/api/expense-drafts", headers=con_token(admin_a)).json()
    assert (borrador["supplierName"], borrador["total"]) == ("CAFETERÍA DEMO S.A.", 24.0)
    categoria = client.get("/api/expense-categories", headers=con_token(admin_a)).json()[0]["id"]

    respuesta = client.post(
        f"/api/expense-drafts/{borrador['id']}/confirm",
        json={"categoryId": categoria},
        headers=con_token(admin_a),
    )

    assert respuesta.status_code == 201
    gasto = db.get(Gasto, respuesta.json()["id"])
    assert gasto is not None
    assert (gasto.monto, gasto.iva) == (Decimal("24.00"), Decimal("2.70"))

    factura_xml = leer_factura(XML)
    assert factura_xml is not None
    assert gasto.clave_acceso == factura_xml.clave_acceso
    assert db.scalar(select(Proveedor.razon_social)) == "CAFETERÍA DEMO S.A."
    assert client.get("/api/expense-drafts", headers=con_token(admin_a)).json() == []

    otra_vez = client.post(
        f"/api/expense-drafts/{borrador['id']}/confirm",
        json={"categoryId": categoria},
        headers=con_token(admin_a),
    )
    assert otra_vez.status_code == 409


def test_descartar_un_borrador(client, db, buzon, admin_a):
    LectorFalso.lectura = Lectura(1, [_mensaje(1, XML)])
    _procesar(db)
    [borrador] = client.get("/api/expense-drafts", headers=con_token(admin_a)).json()

    respuesta = client.post(
        f"/api/expense-drafts/{borrador['id']}/discard", headers=con_token(admin_a)
    )

    assert respuesta.status_code == 204
    descartados = client.get(
        "/api/expense-drafts", params={"status": "descartado"}, headers=con_token(admin_a)
    ).json()
    assert [d["id"] for d in descartados] == [borrador["id"]]
    assert db.scalar(select(func.count()).select_from(Gasto)) == 0
