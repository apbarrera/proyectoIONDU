"""Historial de inventario, entradas/salidas manuales y ajustes (necesitan TEST_DATABASE_URL)."""

import pytest

from app.core.config import get_settings
from app.models.rol import OPERATIVO
from tests.conftest import con_token


@pytest.fixture(autouse=True)
def _sesion(supabase_falso):
    """Mover el inventario exige un usuario con sesión: se usa el "Supabase falso"."""


def _h(empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id)}  # desarrollo: rol Administrador, sin usuario


def _producto(client, empresa_id: int, sku: str = "CAF-250", stock: float = 10) -> int:
    categoria = client.post(
        "/api/product-categories", json={"name": f"Cat {sku}"}, headers=_h(empresa_id)
    ).json()
    response = client.post(
        "/api/products",
        json={
            "sku": sku,
            "name": f"Producto {sku}",
            "categoryId": categoria["id"],
            "salePrice": 4.5,
            "currentStock": stock,
            "unit": "UNIDAD",
        },
        headers=_h(empresa_id),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _stock(client, empresa_id: int, id_producto: int) -> float:
    return client.get(f"/api/products/{id_producto}", headers=_h(empresa_id)).json()["currentStock"]


def _mover(client, usuario, id_producto: int, tipo: str, cantidad: float, motivo="Compra"):
    return client.post(
        "/api/inventory/movements",
        json={"productId": id_producto, "type": tipo, "quantity": cantidad, "reason": motivo},
        headers=con_token(usuario),
    )


def _ajustar(client, usuario, id_producto: int, nuevo: float, motivo="Conteo físico"):
    return client.post(
        "/api/inventory/adjustments",
        json={"productId": id_producto, "newStock": nuevo, "reason": motivo},
        headers=con_token(usuario),
    )


@pytest.fixture
def admin(empresas, nuevo_usuario):
    a, _ = empresas
    return nuevo_usuario(a)


def test_entrada_y_salida_cambian_el_stock(client, empresas, admin):
    a, _ = empresas
    cafe = _producto(client, a)

    entrada = _mover(client, admin, cafe, "entrada", 5, "Llegó el pedido")
    assert entrada.status_code == 201, entrada.text
    movimiento = entrada.json()
    assert (movimiento["type"], movimiento["quantity"], movimiento["resultingStock"]) == (
        "entrada",
        5,
        15,
    )
    assert (movimiento["reason"], movimiento["createdBy"]) == ("Llegó el pedido", "Ana Torres")
    assert movimiento["date"].endswith("-05:00")

    salida = _mover(client, admin, cafe, "salida", 2.5, "Merma").json()
    assert (salida["quantity"], salida["resultingStock"]) == (-2.5, 12.5)
    assert _stock(client, a, cafe) == 12.5


def test_salida_sin_stock_suficiente(client, empresas, admin):
    a, _ = empresas
    cafe = _producto(client, a, stock=3)
    response = _mover(client, admin, cafe, "salida", 4)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert _stock(client, a, cafe) == 3


def test_ajuste_al_conteo_fisico(client, empresas, admin):
    a, _ = empresas
    cafe = _producto(client, a, stock=10)

    response = _ajustar(client, admin, cafe, 7, "Conteo de fin de mes")
    assert response.status_code == 201, response.text
    ajuste = response.json()
    assert (ajuste["previousStock"], ajuste["newStock"], ajuste["quantityDelta"]) == (10, 7, -3)
    assert (ajuste["reason"], ajuste["createdBy"]) == ("Conteo de fin de mes", "Ana Torres")
    assert _stock(client, a, cafe) == 7

    sube = _ajustar(client, admin, cafe, 9).json()
    assert (sube["previousStock"], sube["newStock"], sube["quantityDelta"]) == (7, 9, 2)

    igual = _ajustar(client, admin, cafe, 9)
    assert (igual.status_code, igual.json()["error"]["code"]) == (422, "NO_STOCK_CHANGE")
    assert _ajustar(client, admin, cafe, -1).status_code == 422
    assert _ajustar(client, admin, cafe, 5, motivo="").status_code == 422


def test_solo_el_administrador_ajusta(client, empresas, nuevo_usuario):
    a, _ = empresas
    cafe = _producto(client, a)
    operador = nuevo_usuario(a, rol=OPERATIVO)
    response = _ajustar(client, operador, cafe, 1)
    assert (response.status_code, response.json()["error"]["code"]) == (403, "FORBIDDEN")
    # Pero sí registra entradas y salidas.
    assert _mover(client, operador, cafe, "entrada", 1).status_code == 201


def test_mover_exige_sesion(client, empresas, monkeypatch):
    a, _ = empresas
    cafe = _producto(client, a)
    cuerpo = {"productId": cafe, "type": "entrada", "quantity": 1, "reason": "X"}
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        response = client.post("/api/inventory/movements", json=cuerpo, headers=_h(a))
    finally:
        get_settings.cache_clear()
    assert (response.status_code, response.json()["error"]["code"]) == (
        401,
        "UNAUTHENTICATED",
    )


def test_historial_con_stock_resultante_y_filtros(client, empresas, admin):
    a, _ = empresas
    cafe, azucar = _producto(client, a, "CAF-250", 10), _producto(client, a, "AZU-1K", 5)
    _mover(client, admin, cafe, "entrada", 5)  # 15
    _mover(client, admin, azucar, "salida", 1)  # azúcar 4
    _ajustar(client, admin, cafe, 12)  # 12
    venta = client.post(
        "/api/sales",
        json={
            "items": [{"productId": cafe, "quantity": 2}],
            "paymentMethod": "efectivo",
        },
        headers=con_token(admin),
    )
    assert venta.status_code == 201, venta.text  # 10

    def historial(**filtros) -> list[tuple]:
        response = client.get("/api/inventory/movements", params=filtros, headers=_h(a))
        assert response.status_code == 200, response.text
        return [(m["type"], m["quantity"], m["resultingStock"]) for m in response.json()["items"]]

    # El más reciente primero; el stock resultante cuadra paso a paso.
    assert historial(productId=cafe) == [
        ("venta", -2, 10),
        ("ajuste", -3, 12),
        ("entrada", 5, 15),
    ]
    # Filtrar por tipo no cambia el stock que quedó después de cada movimiento.
    assert historial(type="ajuste") == [("ajuste", -3, 12)]
    assert historial(type="salida") == [("salida", -1, 4)]
    assert len(historial()) == 4


def test_producto_de_otra_empresa(client, empresas, admin):
    a, b = empresas
    ajeno = _producto(client, b)
    for response in (_mover(client, admin, ajeno, "entrada", 1), _ajustar(client, admin, ajeno, 1)):
        assert (response.status_code, response.json()["error"]["code"]) == (
            422,
            "PRODUCT_NOT_FOUND",
        )
    cafe = _producto(client, a)
    movimiento = _mover(client, admin, cafe, "entrada", 1).json()
    assert client.get("/api/inventory/movements", headers=_h(b)).json()["total"] == 0
    response = client.get(f"/api/inventory/movements/{movimiento['id']}", headers=_h(b))
    assert response.status_code == 404
