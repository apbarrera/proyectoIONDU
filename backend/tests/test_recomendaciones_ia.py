"""Recomendaciones con IA (RF-7): datos reales, validación y solo para el Administrador."""

# Los fixtures `usuario` vienen de test_agente_ia: pytest los inyecta por nombre.
# ruff: noqa: F811
import pytest
from sqlalchemy import func, select

from app.api.agente_ia import get_modelo
from app.ia.cliente import RespuestaModelo
from app.ia.recomendaciones import DATOS, _variacion, esquema, interpretar
from app.main import app
from app.models import ConsumoTokens
from app.models.rol import OPERATIVO
from tests.conftest import con_token
from tests.test_agente_ia import usuario  # noqa: F401
from tests.test_consumo_ia import _consumir, _limite

pytestmark = pytest.mark.usefixtures("supabase_falso")

RESPUESTA = {
    "analisis": "Este mes vendiste menos que el anterior y tus gastos subieron.",
    "recomendaciones": [
        {
            "titulo": "Revisa tus gastos de empaque",
            "descripcion": "Los gastos de empaque subieron; compara proveedores.",
            "categoria": "Gastos",
            "prioridad": "alta",
            "datos_utilizados": ["gastos_mes_actual", "gastos_por_categoria"],
        }
    ],
}


class ModeloRecomendaciones:
    def __init__(self, datos=RESPUESTA):
        self.datos = datos
        self.mensajes = None

    def completar_json(self, mensajes, esquema):
        self.mensajes = mensajes
        return RespuestaModelo(self.datos, "modelo-falso", 400, 120)


@pytest.fixture
def modelo_rec():
    falso = ModeloRecomendaciones()
    app.dependency_overrides[get_modelo] = lambda: falso
    yield falso
    app.dependency_overrides.pop(get_modelo, None)


def _generar(client, usuario):
    return client.post("/api/recommendations/ai", headers=con_token(usuario))


def test_genera_el_analisis_con_los_datos_del_dashboard(client, db, modelo_rec, usuario):
    response = _generar(client, usuario)

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["analysis"].startswith("Este mes vendiste menos")
    [rec] = cuerpo["recommendations"]
    assert (rec["category"], rec["priority"]) == ("Gastos", "alta")
    assert rec["dataUsed"] == ["Gastos de este mes", "Gastos por categoría"]
    # Al modelo solo le llegan indicadores calculados, con las claves de la lista cerrada.
    contenido = modelo_rec.mensajes[1]["content"]
    assert '"ventas_mes_actual"' in contenido and '"stock_bajo"' in contenido
    consumo = db.scalar(select(func.sum(ConsumoTokens.tokens_prompt)))
    assert consumo == 400


def test_respeta_el_limite_de_tokens(client, db, modelo_rec, usuario, empresas):
    a, _ = empresas
    _limite(client, usuario, 100)
    _consumir(db, a, 100)

    response = _generar(client, usuario)

    assert response.status_code == 429
    assert modelo_rec.mensajes is None


def test_solo_el_administrador(client, empresas, nuevo_usuario, modelo_rec):
    operativo = nuevo_usuario(empresas[0], rol=OPERATIVO)
    assert _generar(client, operativo).status_code == 403


def test_descarta_lo_que_no_cumple():
    analisis = interpretar(
        {
            "analisis": "  Bien  ",
            "recomendaciones": [
                {"titulo": "", "descripcion": "sin título"},
                {
                    "titulo": "Stock",
                    "descripcion": "Repón café.",
                    "categoria": "Otra",
                    "prioridad": "urgente",
                    "datos_utilizados": ["stock_bajo", "inventado", "stock_bajo"],
                },
                {"titulo": "stock", "descripcion": "Repetida."},
                "no es un objeto",
            ],
        }
    )
    assert analisis.resumen == "Bien"
    [rec] = analisis.recomendaciones
    assert (rec.categoria, rec.prioridad) == ("Finanzas", "media")
    assert rec.datos_utilizados == ["Productos con stock bajo"]


def test_la_comparacion_la_calcula_el_backend():
    # El modelo real decía "los gastos aumentaron de $630 a $310": ahora recibe la dirección.
    assert _variacion(310, 630) == {
        "actual": 310.0,
        "anterior": 630.0,
        "direccion": "bajó",
        "cambio_pct": -50.8,
    }
    assert _variacion(-50, -100)["direccion"] == "subió"
    assert _variacion(10, 0)["cambio_pct"] is None  # sin base no hay porcentaje
    assert _variacion(5, 5)["direccion"] == "igual"


def test_el_esquema_solo_admite_datos_de_la_lista_cerrada():
    item = esquema()["properties"]["recomendaciones"]["items"]
    assert item["properties"]["datos_utilizados"]["items"]["enum"] == list(DATOS)
    assert esquema()["properties"]["recomendaciones"]["maxItems"] == 5
