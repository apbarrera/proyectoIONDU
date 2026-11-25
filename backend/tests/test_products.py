"""Categorías y productos contra PostgreSQL (necesitan TEST_DATABASE_URL, ver conftest.py)."""

import pytest

from tests.tokens import crear_token

pytestmark = pytest.mark.usefixtures("supabase_falso")


def _h(usuario, empresa_id: int) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {crear_token(usuario)}",
        "X-Empresa-Id": str(empresa_id),
    }


@pytest.fixture
def categoria_a(client, empresas, usuarios_empresa) -> int:
    a, _ = empresas
    response = client.post(
        "/api/product-categories",
        json={"name": "Bebidas"},
        headers=_h(usuarios_empresa[a], a),
    )
    assert response.status_code == 201
    return response.json()["id"]


def _crear_producto(client, usuario, empresa_id: int, categoria_id: int, **extra):
    datos = {
        "sku": "CAF-250",
        "name": "Café molido 250 g",
        "categoryId": categoria_id,
    } | extra
    return client.post(
        "/api/products",
        json=datos,
        headers=_h(usuario, empresa_id),
    )


# ---------- Crear y consultar ----------
def test_crear_producto_devuelve_el_contrato_de_la_api(
    client, empresas, usuarios_empresa, categoria_a
):
    a, _ = empresas
    response = _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        salePrice=4.5,
        cost=2.8,
        currentStock=18,
        minStock=5,
        vatPercentageCode="4",
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
        "vatPercentageCode": "4",
        "appliesVat": True,
        "currentStock": 18.0,
        "minStock": 5.0,
        "lowStock": False,
        "active": True,
    }
    assert (
        client.get(
            f"/api/products/{producto['id']}",
            headers=_h(usuarios_empresa[a], a),
        ).json()
        == producto
    )


def test_listar_con_paginas_y_filtros(client, empresas, usuarios_empresa, categoria_a):
    a, _ = empresas
    _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        sku="A-1",
        name="Azúcar",
        currentStock=2,
        minStock=5,
    )
    _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        sku="C-1",
        name="Café",
        currentStock=10,
        minStock=5,
    )
    _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        sku="T-1",
        name="Té",
        type="insumo",
    )

    pagina = client.get(
        "/api/products?page=1&pageSize=2",
        headers=_h(usuarios_empresa[a], a),
    ).json()
    assert [p["name"] for p in pagina["items"]] == ["Azúcar", "Café"]
    assert (pagina["total"], pagina["page"], pagina["pageSize"]) == (3, 1, 2)

    def nombres(query: str) -> list[str]:
        return [
            p["name"]
            for p in client.get(
                f"/api/products?{query}",
                headers=_h(usuarios_empresa[a], a),
            ).json()["items"]
        ]

    assert nombres("search=caf") == ["Café"]
    assert nombres("search=t-1") == ["Té"]
    assert nombres("lowStock=true") == ["Azúcar"]
    assert nombres("type=insumo") == ["Té"]
    assert nombres("search=%25") == []  # "%" se busca como texto, no como comodín


def test_editar_solo_cambia_lo_enviado(client, empresas, usuarios_empresa, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, usuarios_empresa[a], a, categoria_a, salePrice=4.5).json()

    response = client.patch(
        f"/api/products/{producto['id']}",
        json={"salePrice": 5, "minStock": 30},
        headers=_h(usuarios_empresa[a], a),
    )
    assert response.status_code == 200
    editado = response.json()
    assert (editado["salePrice"], editado["minStock"], editado["lowStock"]) == (5.0, 30.0, True)
    assert editado["name"] == producto["name"]


# ---------- Reglas y validaciones ----------
def test_codigo_repetido_en_la_misma_empresa_responde_409(
    client, empresas, usuarios_empresa, categoria_a
):
    a, _ = empresas
    _crear_producto(client, usuarios_empresa[a], a, categoria_a, sku="CAF-250")
    response = _crear_producto(client, usuarios_empresa[a], a, categoria_a, sku="caf-250")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_SKU_TAKEN"


def test_categoria_inexistente_responde_422(client, empresas, usuarios_empresa):
    a, _ = empresas
    response = _crear_producto(client, usuarios_empresa[a], a, 999999)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"


def test_validacion_devuelve_el_campo_y_un_mensaje_en_espanol(
    client, empresas, usuarios_empresa, categoria_a
):
    a, _ = empresas
    response = _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        salePrice=-1,
        sku="",
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {"field": "salePrice", "message": "Debe ser mayor o igual a 0."} in error["details"]
    assert {"field": "sku", "message": "Debe tener al menos 1 caracteres."} in error["details"]


def test_el_codigo_admite_como_maximo_25_caracteres(
    client, empresas, usuarios_empresa, categoria_a
):
    # Límite de codigoPrincipal en el XML de la factura del SRI.
    a, _ = empresas
    assert (
        _crear_producto(client, usuarios_empresa[a], a, categoria_a, sku="X" * 25).status_code
        == 201
    )
    response = _crear_producto(client, usuarios_empresa[a], a, categoria_a, sku="Y" * 26)
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "sku", "message": "Debe tener como máximo 25 caracteres."}
    ]


def test_editar_no_permite_cambiar_el_stock(client, empresas, usuarios_empresa, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, usuarios_empresa[a], a, categoria_a).json()
    response = client.patch(
        f"/api/products/{producto['id']}",
        json={"currentStock": 100},
        headers=_h(usuarios_empresa[a], a),
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "currentStock"


def test_editar_no_permite_vaciar_un_campo_obligatorio(
    client, empresas, usuarios_empresa, categoria_a
):
    a, _ = empresas
    producto = _crear_producto(client, usuarios_empresa[a], a, categoria_a).json()
    response = client.patch(
        f"/api/products/{producto['id']}",
        json={"name": None},
        headers=_h(usuarios_empresa[a], a),
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "name", "message": "No puede estar vacío."}
    ]


# ---------- Aislamiento entre empresas (multi-tenant) ----------
def test_una_empresa_no_ve_ni_modifica_los_productos_de_otra(
    client, empresas, usuarios_empresa, categoria_a
):
    a, b = empresas
    producto = _crear_producto(client, usuarios_empresa[a], a, categoria_a).json()
    url = f"/api/products/{producto['id']}"

    assert client.get("/api/products", headers=_h(usuarios_empresa[b], b)).json()["total"] == 0

    assert client.get("/api/product-categories", headers=_h(usuarios_empresa[b], b)).json() == []

    assert client.get(url, headers=_h(usuarios_empresa[b], b)).status_code == 404

    assert (
        client.patch(
            url,
            json={"name": "Hackeado"},
            headers=_h(usuarios_empresa[b], b),
        ).status_code
        == 404
    )

    # B tampoco puede usar una categoría de A.
    assert _crear_producto(client, usuarios_empresa[b], b, categoria_a).status_code == 422

    # Y el producto de A sigue intacto.
    assert client.get(url, headers=_h(usuarios_empresa[a], a)).json()["name"] == "Café molido 250 g"


def test_el_mismo_codigo_puede_existir_en_empresas_distintas(
    client, empresas, usuarios_empresa, categoria_a
):
    a, b = empresas
    categoria_b = client.post(
        "/api/product-categories",
        json={"name": "Bebidas"},
        headers=_h(usuarios_empresa[b], b),
    ).json()["id"]

    assert (
        _crear_producto(client, usuarios_empresa[a], a, categoria_a, sku="CAF-250").status_code
        == 201
    )

    assert (
        _crear_producto(client, usuarios_empresa[b], b, categoria_b, sku="CAF-250").status_code
        == 201
    )


# ---------- Código de porcentaje IVA ----------
@pytest.mark.parametrize("codigo", ["0", "4", "5", "6", "7"])
def test_crear_producto_acepta_codigos_tributarios(
    client, empresas, usuarios_empresa, categoria_a, codigo
):
    a, _ = empresas
    response = _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        vatPercentageCode=codigo,
    )

    assert response.status_code == 201
    assert response.json()["vatPercentageCode"] == codigo


def test_crear_producto_rechaza_codigo_tributario_invalido(
    client, empresas, usuarios_empresa, categoria_a
):
    a, _ = empresas
    response = _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        vatPercentageCode="15",
    )

    assert response.status_code == 422


def test_crear_producto_no_acepta_applies_vat_como_entrada(
    client, empresas, usuarios_empresa, categoria_a
):
    a, _ = empresas
    response = _crear_producto(
        client,
        usuarios_empresa[a],
        a,
        categoria_a,
        appliesVat=False,
    )

    assert response.status_code == 422


def test_editar_codigo_tributario(client, empresas, usuarios_empresa, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, usuarios_empresa[a], a, categoria_a).json()

    response = client.patch(
        f"/api/products/{producto['id']}",
        json={"vatPercentageCode": "5"},
        headers=_h(usuarios_empresa[a], a),
    )

    assert response.status_code == 200
    assert response.json()["vatPercentageCode"] == "5"


# ---------- Activación y desactivación ----------
def test_desactivar_y_reactivar_producto(client, empresas, usuarios_empresa, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, usuarios_empresa[a], a, categoria_a).json()
    url = f"/api/products/{producto['id']}"

    desactivado = client.patch(
        url,
        json={"active": False},
        headers=_h(usuarios_empresa[a], a),
    )
    assert desactivado.status_code == 200
    assert desactivado.json()["active"] is False

    consultado = client.get(url, headers=_h(usuarios_empresa[a], a))
    assert consultado.status_code == 200
    assert consultado.json()["active"] is False

    listado = client.get("/api/products", headers=_h(usuarios_empresa[a], a)).json()
    encontrado = next(p for p in listado["items"] if p["id"] == producto["id"])
    assert encontrado["active"] is False

    reactivado = client.patch(
        url,
        json={"active": True},
        headers=_h(usuarios_empresa[a], a),
    )
    assert reactivado.status_code == 200
    assert reactivado.json()["active"] is True


def test_editar_no_permite_active_null(client, empresas, usuarios_empresa, categoria_a):
    a, _ = empresas
    producto = _crear_producto(client, usuarios_empresa[a], a, categoria_a).json()

    response = client.patch(
        f"/api/products/{producto['id']}",
        json={"active": None},
        headers=_h(usuarios_empresa[a], a),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "active", "message": "No puede estar vacío."}
    ]
