"""Auditoría: la API registra las acciones y solo el Administrador las consulta."""

import uuid

import pytest
from sqlalchemy import select, text

from app.models import Auditoria
from app.models.rol import OPERATIVO
from app.services import auditoria as modulo_auditoria
from tests.conftest import con_token

pytestmark = pytest.mark.usefixtures("supabase_falso")


@pytest.fixture
def admin_a(usuarios_empresa, empresas) -> uuid.UUID:
    return usuarios_empresa[empresas[0]]


def _crear_producto(client, usuario, sku="CAF-1"):
    categoria = client.post(
        "/api/product-categories", json={"name": f"Categoría {sku}"}, headers=con_token(usuario)
    ).json()["id"]
    return client.post(
        "/api/products",
        json={"sku": sku, "name": "Café", "categoryId": categoria, "salePrice": 2.5},
        headers=con_token(usuario),
    )


def test_crear_un_producto_queda_en_la_auditoria(client, admin_a):
    assert _crear_producto(client, admin_a).status_code == 201

    response = client.get("/api/audit", headers=con_token(admin_a))

    assert response.status_code == 200
    [registro] = response.json()["items"]
    assert registro["module"] == "inventario"
    assert registro["action"] == "Creó producto"
    assert "CAF-1" in registro["description"]
    assert registro["userId"] == str(admin_a)
    assert registro["userName"] == "Ana Torres"
    assert registro["entity"] == "producto"


def test_las_acciones_de_un_operativo_tambien_se_registran(
    client, db, admin_a, empresas, nuevo_usuario
):
    operador = nuevo_usuario(empresas[0], rol=OPERATIVO)
    assert _crear_producto(client, operador).status_code == 201

    autores = db.scalars(select(Auditoria.id_usuario)).all()
    assert autores == [operador]


def test_un_operativo_no_puede_ver_la_auditoria(client, empresas, nuevo_usuario):
    operador = nuevo_usuario(empresas[0], rol=OPERATIVO)
    assert client.get("/api/audit", headers=con_token(operador)).status_code == 403


def test_cada_empresa_ve_solo_su_auditoria(client, empresas, usuarios_empresa):
    a, b = empresas
    _crear_producto(client, usuarios_empresa[a], sku="DE-A")
    _crear_producto(client, usuarios_empresa[b], sku="DE-B")

    items = client.get("/api/audit", headers=con_token(usuarios_empresa[a])).json()["items"]

    assert [i["description"] for i in items] == ["DE-A · Café."]


def test_filtra_por_modulo_y_ordena_de_lo_mas_reciente(client, admin_a):
    _crear_producto(client, admin_a, sku="P-1")
    client.post(
        "/api/users",
        json={"email": "luis@empresa.ec", "fullName": "Luis", "role": "operator"},
        headers=con_token(admin_a),
    )
    _crear_producto(client, admin_a, sku="P-2")

    todos = client.get("/api/audit", headers=con_token(admin_a)).json()
    solo_inventario = client.get(
        "/api/audit", params={"module": "inventario"}, headers=con_token(admin_a)
    ).json()

    assert todos["total"] == 3
    assert todos["items"][0]["description"].startswith("P-2")
    assert [i["module"] for i in solo_inventario["items"]] == ["inventario", "inventario"]


def test_restablecer_una_contrasena_no_guarda_la_contrasena_temporal(
    client, db, admin_a, empresas, nuevo_usuario
):
    operador = nuevo_usuario(empresas[0], rol=OPERATIVO)
    temporal = client.post(
        f"/api/users/{operador}/reset-password", headers=con_token(admin_a)
    ).json()["temporaryPassword"]

    registro = db.scalar(select(Auditoria).where(Auditoria.accion == "Restableció contraseña"))
    assert registro is not None
    assert temporal not in registro.descripcion


def test_si_la_auditoria_falla_la_accion_igual_se_completa(client, admin_a, monkeypatch, caplog):
    monkeypatch.setattr(
        modulo_auditoria, "SQL_INSERTAR", text("INSERT INTO tabla_que_no_existe VALUES (1)")
    )

    response = _crear_producto(client, admin_a)

    assert response.status_code == 201
    assert "No se pudo registrar la auditoría" in caplog.text


def test_un_filtro_de_modulo_invalido_responde_422(client, admin_a):
    response = client.get("/api/audit", params={"module": "otro"}, headers=con_token(admin_a))
    assert response.status_code == 422
