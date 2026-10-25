"""Categorías y productos contra PostgreSQL (necesitan TEST_DATABASE_URL, ver conftest.py)."""

import pytest


def _h(empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id)}


@pytest.fixture
def categoria_a(client, empresas) -> int:
    a, _ = empresas
    response = client.post("/api/product-categories", json={"name": "Bebidas"}, headers=_h(a))
    assert response.status_code == 201
    return response.json()["id"]


def _crear_producto(client, empresa_id: int, categoria_id: int, **extra):
    datos = {"sku": "CAF-250", "name": "Café molido 250 g", "categoryId": categoria_id} | extra
    return client.post("/api/products", json=datos, headers=_h(empresa_id))


# ---------- Crear y consultar ----------
def test_crear_producto_devuelve_el_contrato_de_la_api(client, empresas, categoria_a):
    a, _ = empresas
    response = _crear_producto(
        client, a, categoria_a, salePrice=4.5, cost=2.8, currentStock=18, minStock=5
    )

    assert response.status_code == 201
    producto = response.json()
    assert producto == {
        "id": producto["id"],
        "sku": "CAF-250",
        "name": "Café molido 250 g",
        "description": None,
        "categoryId": categoria_a,
        "categoryName": "Bebidas",
        "type": "venta",
        "unit": "UNIDAD",
        "salePrice": 4.5,
        "cost": 2.8,
        "appliesVat": True,
        "currentStock": 18.0,
        "minStock": 5.0,
        "lowStock": False,
    }
    assert client.get(f"/api/products/{producto['id']}", headers=_h(a)).json() == producto


def test_listar_con_paginas_y_filtros(client, empresas, categoria_a):
    a, _ = empresas
    _crear_producto(client, a, categoria_a, sku="A-1", name="Azúcar", currentStock=2, minStock=5)
    _crear_producto(client, a, categoria_a, sku="C-1", name="Café", currentStock=10, minStock=5)
    _crear_producto(client, a, categoria_a, sku="T-1", name="Té", type="insumo")

    pagina = client.get("/api/products?page=1&pageSize=2", headers=_h(a)).json()
    assert [p["name"] for p in pagina["items"]] == ["Azúcar", "Café"]
    assert (pagina["total"], pagina["page"], pagina["pageSize"]) == (3, 1, 2)

    def nombres(query: str) -> list[str]:
        return [
            p["name"] for p in client.get(f"/api/products?{query}", headers=_h(a)).json()["items"]
        ]

    assert nombres("search=caf") == ["Café"]
    assert nombres("search=t-1") == ["Té"]
    assert nombres("lowStock=true") == ["Azúcar"]
    assert nombres("type=insumo") == ["Té"]
    assert nombres("search=%25") == []  # "%" se busca como texto, no como comodín


def test_editar_solo_cambia_lo_enviado(client, empresas, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, a, categoria_a, salePrice=4.5).json()

    response = client.patch(
        f"/api/products/{producto['id']}", json={"salePrice": 5, "minStock": 30}, headers=_h(a)
    )
    assert response.status_code == 200
    editado = response.json()
    assert (editado["salePrice"], editado["minStock"], editado["lowStock"]) == (5.0, 30.0, True)
    assert editado["name"] == producto["name"]


# ---------- Reglas y validaciones ----------
def test_codigo_repetido_en_la_misma_empresa_responde_409(client, empresas, categoria_a):
    a, _ = empresas
    _crear_producto(client, a, categoria_a, sku="CAF-250")
    response = _crear_producto(client, a, categoria_a, sku="caf-250")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_SKU_TAKEN"


def test_categoria_inexistente_responde_422(client, empresas):
    a, _ = empresas
    response = _crear_producto(client, a, 999999)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"


def test_validacion_devuelve_el_campo_y_un_mensaje_en_espanol(client, empresas, categoria_a):
    a, _ = empresas
    response = _crear_producto(client, a, categoria_a, salePrice=-1, sku="")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {"field": "salePrice", "message": "Debe ser mayor o igual a 0."} in error["details"]
    assert {"field": "sku", "message": "Debe tener al menos 1 caracteres."} in error["details"]


def test_editar_no_permite_cambiar_el_stock(client, empresas, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, a, categoria_a).json()
    response = client.patch(
        f"/api/products/{producto['id']}", json={"currentStock": 100}, headers=_h(a)
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "currentStock"


def test_editar_no_permite_vaciar_un_campo_obligatorio(client, empresas, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, a, categoria_a).json()
    response = client.patch(f"/api/products/{producto['id']}", json={"name": None}, headers=_h(a))
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "name", "message": "No puede estar vacío."}
    ]


# ---------- Aislamiento entre empresas (multi-tenant) ----------
def test_una_empresa_no_ve_ni_modifica_los_productos_de_otra(client, empresas, categoria_a):
    a, b = empresas
    producto = _crear_producto(client, a, categoria_a).json()
    url = f"/api/products/{producto['id']}"

    assert client.get("/api/products", headers=_h(b)).json()["total"] == 0
    assert client.get("/api/product-categories", headers=_h(b)).json() == []
    assert client.get(url, headers=_h(b)).status_code == 404
    assert client.patch(url, json={"name": "Hackeado"}, headers=_h(b)).status_code == 404
    # B tampoco puede usar una categoría de A.
    assert _crear_producto(client, b, categoria_a).status_code == 422
    # Y el producto de A sigue intacto.
    assert client.get(url, headers=_h(a)).json()["name"] == "Café molido 250 g"


def test_el_mismo_codigo_puede_existir_en_empresas_distintas(client, empresas, categoria_a):
    a, b = empresas
    categoria_b = client.post(
        "/api/product-categories", json={"name": "Bebidas"}, headers=_h(b)
    ).json()["id"]
    assert _crear_producto(client, a, categoria_a, sku="CAF-250").status_code == 201
    assert _crear_producto(client, b, categoria_b, sku="CAF-250").status_code == 201
