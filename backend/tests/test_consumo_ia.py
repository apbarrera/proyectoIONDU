"""Límite mensual de tokens del agente de IA (RF-6.1, RF-6.14, RNF-12)."""

# Los fixtures `modelo` y `usuario` vienen de test_agente_ia: pytest los inyecta por nombre.
# ruff: noqa: F811

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.models import Auditoria, ConsumoTokens, Empresa
from app.models.rol import OPERATIVO
from app.services.consumo_ia import inicio_de_mes
from tests.conftest import con_token
from tests.test_agente_ia import _codigo, _enviar, modelo, usuario  # noqa: F401

pytestmark = pytest.mark.usefixtures("supabase_falso")
ZONA = ZoneInfo("America/Guayaquil")


def _consumir(db, empresa_id, tokens, fecha=None):
    db.add(
        ConsumoTokens(
            id_empresa=empresa_id,
            modelo_ia="modelo-falso",
            tokens_prompt=tokens,
            tokens_completado=0,
            **({"fecha": fecha} if fecha else {}),
        )
    )
    db.flush()


def _limite(client, usuario, valor):
    return client.put(
        "/api/ai/usage/limit", json={"monthlyLimit": valor}, headers=con_token(usuario)
    )


def test_inicio_de_mes_en_ecuador_y_meses_atras():
    # 1 de diciembre a las 02:00 UTC todavía es 30 de noviembre en Ecuador.
    ahora = datetime(2026, 12, 1, 2, 0, tzinfo=ZoneInfo("UTC"))
    assert inicio_de_mes(ahora) == datetime(2026, 11, 1, tzinfo=ZONA)
    assert inicio_de_mes(ahora, 11) == datetime(2025, 12, 1, tzinfo=ZONA)


def test_sin_limite_el_agente_responde_y_el_resumen_lo_indica(client, modelo, usuario):  # noqa: F811
    assert _enviar(client, usuario).status_code == 200

    resumen = client.get("/api/ai/usage", headers=con_token(usuario)).json()
    assert resumen["monthlyLimit"] is None
    assert resumen["used"] == 150  # 120 de prompt + 30 de respuesta del modelo falso
    assert (resumen["remaining"], resumen["percentUsed"], resumen["limitReached"]) == (
        None,
        None,
        False,
    )
    assert len(resumen["history"]) == 6
    assert resumen["history"][-1]["used"] == 150


def test_con_el_limite_alcanzado_no_se_llama_al_modelo(  # noqa: F811
    client, db, modelo, usuario, empresas
):
    a, _ = empresas
    assert _limite(client, usuario, 1000).status_code == 200
    _consumir(db, a, 1000)
    modelo.mensajes = None

    response = _enviar(client, usuario)

    assert response.status_code == 429
    assert _codigo(response) == "AI_TOKEN_LIMIT_REACHED"
    assert modelo.mensajes is None  # el modelo no se llamó
    total = db.scalar(select(func.count()).select_from(ConsumoTokens))
    assert total == 1  # no se sumó consumo


def test_por_debajo_del_limite_responde_y_avisa_al_acercarse(  # noqa: F811
    client, db, modelo, usuario, empresas
):
    a, _ = empresas
    _limite(client, usuario, 1000)
    _consumir(db, a, 700)

    assert _enviar(client, usuario).status_code == 200  # 700 + 150 = 850
    resumen = client.get("/api/ai/usage", headers=con_token(usuario)).json()
    assert (resumen["used"], resumen["remaining"], resumen["percentUsed"]) == (850, 150, 85.0)
    assert (resumen["nearLimit"], resumen["limitReached"]) == (True, False)


def test_el_consumo_de_meses_anteriores_no_cuenta(  # noqa: F811
    client, db, modelo, usuario, empresas
):
    a, _ = empresas
    _limite(client, usuario, 1000)
    _consumir(db, a, 5000, fecha=datetime(2020, 1, 15, tzinfo=ZONA))

    assert _enviar(client, usuario).status_code == 200


def test_el_limite_es_por_empresa(client, db, modelo, usuario, empresas):  # noqa: F811
    a, b = empresas
    _limite(client, usuario, 100)
    _consumir(db, b, 10_000)  # lo que gasta otra empresa no cuenta

    assert _enviar(client, usuario).status_code == 200


def test_quitar_el_limite_y_queda_auditado(client, db, usuario, empresas):  # noqa: F811
    a, _ = empresas
    _limite(client, usuario, 500)
    response = _limite(client, usuario, None)

    assert response.status_code == 200
    assert response.json()["monthlyLimit"] is None
    assert db.get(Empresa, a).limite_tokens_ia_mensual is None
    acciones = db.scalars(select(Auditoria.descripcion).where(Auditoria.modulo == "ia")).all()
    assert any("sin límite" in d for d in acciones)
    assert any("500 tokens" in d for d in acciones)


def test_limite_negativo_no_se_acepta(client, usuario):  # noqa: F811
    assert _limite(client, usuario, -1).status_code == 422


def test_solo_el_administrador_ve_y_cambia_el_limite(client, empresas, nuevo_usuario):
    a, _ = empresas
    operativo = nuevo_usuario(a, rol=OPERATIVO)

    assert client.get("/api/ai/usage", headers=con_token(operativo)).status_code == 403
    assert _limite(client, operativo, 10).status_code == 403
