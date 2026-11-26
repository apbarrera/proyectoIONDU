"""Agente de IA, etapa 3: fotos de facturas, tickets y guías (RF-6.3)."""

import base64
import io
import uuid

import pytest
from PIL import Image
from sqlalchemy import select

from app.api.agente_ia import get_modelo_vision
from app.core.errors import UnprocessableError
from app.ia.agente import NO_ES_COMPROBANTE, esquema, metodo_pago_leido
from app.ia.imagen import LADO_MAXIMO, TAMANO_MAXIMO_BYTES, preparar_imagen
from app.main import app
from app.models import AccionIA, Empresa, Gasto
from tests.conftest import con_token
from tests.test_agente_ia import ModeloFalso, _gasto
from tests.test_agente_ia_inventario import CAFE, _inventario, cafe  # noqa: F401

pytestmark = pytest.mark.usefixtures("supabase_falso")


def _foto(ancho=2400, alto=1800, formato="JPEG") -> bytes:
    salida = io.BytesIO()
    Image.new("RGB", (ancho, alto), "white").save(salida, format=formato)
    return salida.getvalue()


def _con_lectura(datos: dict, lectura: str, tipo: str = "factura_o_ticket") -> dict:
    return {"lectura": lectura, "tipo_imagen": tipo, **datos}


@pytest.fixture
def vision():
    falso = ModeloFalso(
        _con_lectura(
            {
                "accion": "registrar_gasto",
                "respuesta": "",
                "gasto": _gasto(total=11.5, iva=1.5, proveedor="Distribuidora Andina"),
            },
            "Distribuidora Andina. Factura 001-001-123. Fundas x100. IVA 1.50. Total 11.50",
        )
    )
    app.dependency_overrides[get_modelo_vision] = lambda: falso
    yield falso
    app.dependency_overrides.pop(get_modelo_vision, None)


@pytest.fixture
def usuario(usuarios_empresa, empresas) -> uuid.UUID:
    return usuarios_empresa[empresas[0]]


# La fixture `cafe` de las pruebas de inventario la pide con el nombre `admin`.
@pytest.fixture
def admin(usuario) -> uuid.UUID:
    return usuario


def _subir(client, usuario, contenido=None, texto=None, nombre="ticket.jpg"):
    return client.post(
        "/api/ai/images",
        files={"image": (nombre, contenido if contenido is not None else _foto(), "image/jpeg")},
        data={"text": texto} if texto else None,
        headers=con_token(usuario),
    )


def _codigo(response):
    return response.json()["error"]["code"]


# ---------- Preparar la imagen ----------
def test_la_foto_se_reduce_y_se_envia_como_jpeg():
    url = preparar_imagen(_foto(4000, 3000, "PNG"))

    assert url.startswith("data:image/jpeg;base64,")
    imagen = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    assert imagen.format == "JPEG"
    assert max(imagen.size) == LADO_MAXIMO


def test_una_foto_pequena_no_se_agranda():
    url = preparar_imagen(_foto(600, 400, "WEBP"))
    imagen = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    assert imagen.size == (600, 400)


@pytest.mark.parametrize(
    "contenido",
    [b"", b"no soy una imagen", b"%PDF-1.7 documento", _foto(50, 50, "GIF")],
    ids=["vacio", "texto", "pdf", "gif"],
)
def test_lo_que_no_es_una_foto_se_rechaza(contenido):
    with pytest.raises(UnprocessableError) as error:
        preparar_imagen(contenido)
    assert error.value.code == "INVALID_IMAGE"


def test_una_imagen_demasiado_pesada_se_rechaza():
    with pytest.raises(UnprocessableError) as error:
        preparar_imagen(b"\xff" * (TAMANO_MAXIMO_BYTES + 1))
    assert error.value.code == "IMAGE_TOO_LARGE"


def test_el_esquema_de_imagen_pide_la_lectura():
    normal = esquema(["Empaque"], [])
    con_lectura = esquema(["Empaque"], [], con_lectura=True)
    assert "lectura" not in normal["properties"]
    assert con_lectura["required"][:2] == ["lectura", "tipo_imagen"]
    assert con_lectura["properties"]["gasto"] == normal["properties"]["gasto"]


@pytest.mark.parametrize(
    ("lectura", "metodo"),
    [
        ("Total 17.25. Forma de pago: Tarjeta de CRÉDITO", "tarjeta_credito"),
        ("Pago con tarjeta de débito", "tarjeta_debito"),
        ("TOTAL USD 20.00 EFECTIVO", "efectivo"),
        ("Total 20.00", None),
        ("Efectivo 10.00, tarjeta de crédito 5.00", None),  # pago mixto: decide el modelo
    ],
)
def test_el_metodo_de_pago_sale_de_lo_leido(lectura, metodo):
    assert metodo_pago_leido(lectura) == metodo


# ---------- Endpoint ----------
def test_una_factura_se_propone_como_gasto_sin_guardarse(client, db, vision, usuario):
    response = _subir(client, usuario, texto="Compra de fundas")

    assert response.status_code == 200
    cuerpo = response.json()
    gasto = cuerpo["proposal"]["expense"]
    assert (gasto["total"], gasto["ivaAmount"], gasto["supplierName"]) == (
        11.5,
        1.5,
        "Distribuidora Andina",
    )
    assert db.scalar(select(Gasto.id_gasto)) is None  # nada se guarda sin confirmar

    accion = db.get(AccionIA, cuerpo["actionId"])
    assert accion.instruccion_recibida == "[Imagen] Compra de fundas"
    assert accion.payload_json["entrada"] == "imagen"
    assert "Factura 001-001-123" in accion.payload_json["lectura"]
    # La foto no se guarda en ningún lado: solo lo que se leyó.
    assert "base64" not in str(accion.payload_json)


def test_la_foto_va_al_modelo_con_las_reglas_de_imagen(client, db, vision, usuario, empresas):
    _subir(client, usuario)

    sistema, mensaje = vision.mensajes
    empresa = db.get(Empresa, empresas[0])
    assert empresa.ruc in sistema["content"]
    assert "EMITIÓ esta" in sistema["content"]
    texto, imagen = mensaje["content"]
    assert texto == {"type": "text", "text": "Interpreta esta imagen."}
    assert imagen["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "lectura" in vision.esquema["properties"]


def test_confirmar_la_propuesta_de_una_foto_crea_el_gasto(client, db, vision, usuario):
    id_accion = _subir(client, usuario).json()["actionId"]

    response = client.post(
        f"/api/ai/actions/{id_accion}/confirm", json={}, headers=con_token(usuario)
    )

    assert response.status_code == 200
    gasto = db.get(Gasto, response.json()["expenseId"])
    assert (str(gasto.monto), str(gasto.iva)) == ("11.50", "1.50")


def test_el_historial_indica_que_vino_de_una_imagen(client, vision, usuario):
    _subir(client, usuario)

    items = client.get("/api/ai/actions", headers=con_token(usuario)).json()["items"]
    assert (items[0]["instruction"], items[0]["inputType"]) == ("[Imagen]", "imagen")


def test_el_producto_debe_leerse_en_la_foto(client, vision, usuario, cafe):  # noqa: F811
    vision.datos = _con_lectura(_inventario(CAFE, cantidad=4), "Guía de remisión: 4 bolsas café")
    assert _subir(client, usuario).json()["proposal"]["inventory"]["quantity"] == 4

    vision.datos = _con_lectura(_inventario(CAFE, cantidad=4), "Guía de remisión: 4 cajas té")
    cuerpo = _subir(client, usuario).json()
    assert cuerpo["proposal"] is None
    assert "qué producto" in cuerpo["reply"]


def test_un_archivo_que_no_es_imagen_no_llega_al_modelo(client, vision, usuario):
    response = _subir(client, usuario, contenido=b"%PDF-1.7", nombre="factura.pdf")

    assert response.status_code == 422
    assert _codigo(response) == "INVALID_IMAGE"
    assert vision.mensajes is None


def test_sin_modelo_de_vision_responde_que_no_esta_configurado(client, usuario):
    app.dependency_overrides[get_modelo_vision] = lambda: None
    try:
        response = _subir(client, usuario)
    finally:
        app.dependency_overrides.pop(get_modelo_vision, None)

    assert response.status_code == 503
    assert _codigo(response) == "AI_VISION_NOT_CONFIGURED"


def test_sin_sesion_no_se_puede_subir(client):
    response = client.post("/api/ai/images", files={"image": ("t.jpg", _foto(), "image/jpeg")})
    assert response.status_code == 401


def test_lo_leido_manda_sobre_el_metodo_que_eligio_el_modelo(client, vision, usuario):
    vision.datos = _con_lectura(
        {
            "accion": "registrar_gasto",
            "respuesta": "",
            "gasto": _gasto(metodo_pago="tarjeta_debito"),
        },
        "Distribuidora Andina. Total 25.00. Forma de pago: Tarjeta de crédito",
    )
    gasto = _subir(client, usuario).json()["proposal"]["expense"]
    assert gasto["paymentMethod"] == "tarjeta_credito"


def test_una_foto_que_no_es_comprobante_pide_otra(client, db, vision, usuario):
    vision.datos = _con_lectura(
        {"accion": "pedir_aclaracion", "respuesta": "No puedo ver imágenes.", "gasto": _gasto()},
        "Un paisaje con un sol amarillo.",
        tipo="otra_cosa",
    )
    cuerpo = _subir(client, usuario).json()

    assert (cuerpo["proposal"], cuerpo["reply"]) == (None, NO_ES_COMPROBANTE)
    accion = db.scalar(select(AccionIA).order_by(AccionIA.id_accion_ia.desc()))
    assert accion.estado == "SIN_PROPUESTA"
    assert accion.payload_json["lectura"] == "Un paisaje con un sol amarillo."


def test_una_factura_de_venta_se_rechaza(client, vision, usuario):
    vision.datos = _con_lectura(
        {"accion": "fuera_de_alcance", "respuesta": "Es una venta.", "gasto": _gasto()},
        "Factura de la empresa a Juan Pérez",
        tipo="otra_cosa",
    )
    cuerpo = _subir(client, usuario).json()
    assert (cuerpo["proposal"], cuerpo["reply"]) == (None, "Es una venta.")
