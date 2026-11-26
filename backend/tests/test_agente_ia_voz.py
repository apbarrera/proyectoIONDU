"""Agente de IA, etapa 4: mensajes de voz (RF-6.4). El audio se transcribe y sigue como texto."""

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.api.agente_ia import get_modelo, get_transcriptor
from app.core.errors import ServiceUnavailableError, UnprocessableError
from app.ia import voz as modulo_voz
from app.ia.voz import (
    TAMANO_MAXIMO_AUDIO,
    Transcripcion,
    TranscriptorOpenAICompatible,
    detectar_formato,
)
from app.main import app
from app.models import AccionIA, Gasto
from tests.conftest import con_token
from tests.test_agente_ia import ModeloFalso, _gasto

pytestmark = pytest.mark.usefixtures("supabase_falso")

WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 2000


class TranscriptorFalso:
    def __init__(self, texto="Gasté 25 dólares en fundas"):
        self.texto = texto
        self.recibido = None

    def transcribir(self, audio, formato):
        self.recibido = (len(audio), formato)
        return Transcripcion(self.texto, "whisper-falso")


@pytest.fixture
def modelo():
    falso = ModeloFalso({"accion": "registrar_gasto", "respuesta": "", "gasto": _gasto()})
    app.dependency_overrides[get_modelo] = lambda: falso
    yield falso
    app.dependency_overrides.pop(get_modelo, None)


@pytest.fixture
def transcriptor():
    falso = TranscriptorFalso()
    app.dependency_overrides[get_transcriptor] = lambda: falso
    yield falso
    app.dependency_overrides.pop(get_transcriptor, None)


@pytest.fixture
def usuario(usuarios_empresa, empresas) -> uuid.UUID:
    return usuarios_empresa[empresas[0]]


def _enviar(client, usuario, audio=WEBM):
    return client.post(
        "/api/ai/audio",
        files={"audio": ("mensaje.webm", audio, "audio/webm")},
        headers=con_token(usuario),
    )


def _codigo(response):
    return response.json()["error"]["code"]


# ---------- Formato del audio ----------
@pytest.mark.parametrize(
    ("cabecera", "formato"),
    [
        (b"\x1a\x45\xdf\xa3", "webm"),
        (b"OggS", "ogg"),
        (b"\x00\x00\x00\x20ftypM4A ", "mp4"),
        (b"RIFF\x00\x00\x00\x00WAVE", "wav"),
        (b"ID3\x04", "mp3"),
    ],
)
def test_el_formato_sale_de_los_primeros_bytes(cabecera, formato):
    assert detectar_formato(cabecera + b"\x00" * 2000) == formato


@pytest.mark.parametrize(
    "audio",
    [b"", b"\x1a\x45\xdf\xa3", b"%PDF-1.7" + b"\x00" * 2000, b"\x89PNG" + b"\x00" * 2000],
    ids=["vacio", "cortado", "pdf", "png"],
)
def test_lo_que_no_es_audio_se_rechaza(audio):
    with pytest.raises(UnprocessableError) as error:
        detectar_formato(audio)
    assert error.value.code == "INVALID_AUDIO"


def test_un_audio_demasiado_pesado_se_rechaza():
    with pytest.raises(UnprocessableError) as error:
        detectar_formato(WEBM[:4] + b"\x00" * TAMANO_MAXIMO_AUDIO)
    assert error.value.code == "AUDIO_TOO_LARGE"


# ---------- Endpoint ----------
def test_la_voz_se_transcribe_y_se_propone_como_texto(client, db, modelo, transcriptor, usuario):
    response = _enviar(client, usuario)

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["transcript"] == "Gasté 25 dólares en fundas"
    assert cuerpo["proposal"]["expense"]["total"] == 25.0
    assert transcriptor.recibido == (len(WEBM), "webm")
    # El modelo de texto recibe la transcripción como si se hubiera escrito.
    assert modelo.mensajes[1] == {"role": "user", "content": "Gasté 25 dólares en fundas"}
    assert db.scalar(select(Gasto.id_gasto)) is None  # nada se guarda sin confirmar

    accion = db.get(AccionIA, cuerpo["actionId"])
    assert accion.instruccion_recibida == "[Voz] Gasté 25 dólares en fundas"
    assert accion.payload_json["entrada"] == "voz"


def test_el_historial_indica_que_vino_de_un_audio(client, modelo, transcriptor, usuario):
    _enviar(client, usuario)
    items = client.get("/api/ai/actions", headers=con_token(usuario)).json()["items"]
    assert items[0]["inputType"] == "voz"


def test_un_audio_sin_palabras_no_llega_al_modelo(client, db, modelo, transcriptor, usuario):
    transcriptor.texto = ""
    cuerpo = _enviar(client, usuario).json()

    assert (cuerpo["actionId"], cuerpo["proposal"], cuerpo["transcript"]) == (None, None, "")
    assert "No logré entender" in cuerpo["reply"]
    assert modelo.mensajes is None
    assert db.scalar(select(AccionIA.id_accion_ia)) is None


def test_un_archivo_que_no_es_audio_no_se_transcribe(client, modelo, transcriptor, usuario):
    response = _enviar(client, usuario, b"no soy audio" * 200)

    assert (response.status_code, _codigo(response)) == (422, "INVALID_AUDIO")
    assert transcriptor.recibido is None


def test_sin_servicio_de_voz_responde_que_no_esta_configurado(client, modelo, usuario):
    app.dependency_overrides[get_transcriptor] = lambda: None
    try:
        response = _enviar(client, usuario)
    finally:
        app.dependency_overrides.pop(get_transcriptor, None)
    assert (response.status_code, _codigo(response)) == (503, "AI_VOICE_NOT_CONFIGURED")


def test_sin_modelo_de_texto_no_se_transcribe(client, transcriptor, usuario):
    app.dependency_overrides[get_modelo] = lambda: None
    try:
        response = _enviar(client, usuario)
    finally:
        app.dependency_overrides.pop(get_modelo, None)
    assert (response.status_code, _codigo(response)) == (503, "AI_NOT_CONFIGURED")
    assert transcriptor.recibido is None


def test_sin_sesion_no_se_puede_enviar(client):
    response = client.post("/api/ai/audio", files={"audio": ("m.webm", WEBM, "audio/webm")})
    assert response.status_code == 401


# ---------- Cliente de transcripción ----------
def _respuesta(url, status=200, cuerpo=b'{"text": "  Llegaron   20\\n croissants "}'):
    return httpx.Response(status, request=httpx.Request("POST", url), content=cuerpo)


def test_el_cliente_pide_espanol_y_limpia_el_texto(monkeypatch):
    enviado = {}

    def post(url, **kwargs):
        enviado.update(url=url, **kwargs)
        return _respuesta(url)

    monkeypatch.setattr(modulo_voz.httpx, "post", post)
    cliente = TranscriptorOpenAICompatible("http://stt:8000/v1/", "whisper-small", "clave", 30)

    resultado = cliente.transcribir(WEBM, "webm")

    assert resultado == Transcripcion("Llegaron 20 croissants", "whisper-small")
    assert enviado["url"] == "http://stt:8000/v1/audio/transcriptions"
    assert enviado["data"] == {
        "model": "whisper-small",
        "language": "es",
        "response_format": "json",
    }
    assert enviado["files"]["file"] == ("mensaje.webm", WEBM, "audio/webm")
    assert enviado["headers"] == {"Authorization": "Bearer clave"}


def _sin_conexion(url):
    raise httpx.ConnectError("sin conexión", request=httpx.Request("POST", url))


@pytest.mark.parametrize(
    "respuesta",
    [
        lambda url: _respuesta(url, 500, b"error"),
        lambda url: _respuesta(url, 200, b"no es json"),
        lambda url: _respuesta(url, 200, b'{"detail": "sin texto"}'),
        _sin_conexion,
    ],
    ids=["500", "no-json", "sin-text", "sin-conexion"],
)
def test_si_la_transcripcion_falla_es_503(monkeypatch, respuesta):
    monkeypatch.setattr(modulo_voz.httpx, "post", lambda url, **_: respuesta(url))
    with pytest.raises(ServiceUnavailableError) as error:
        TranscriptorOpenAICompatible("http://x/v1", "m", None, 5).transcribir(WEBM, "webm")
    assert error.value.code == "AI_UNAVAILABLE"
