"""Dashboard financiero (necesitan TEST_DATABASE_URL)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models import Venta
from app.models.rol import OPERATIVO
from tests.conftest import con_token

ZONA = ZoneInfo("America/Guayaquil")


@pytest.fixture(autouse=True)
def _sesion(supabase_falso):
    """Registrar ventas y gastos exige un usuario: se usa el "Supabase falso"."""


def _h(empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id)}  # desarrollo: rol Administrador


def _dashboard(client, empresa_id: int, **periodo):
    response = client.get("/api/dashboard", params=periodo, headers=_h(empresa_id))
    assert response.status_code == 200, response.text
    return response.json()


def _producto(client, empresa_id, sku, nombre, precio, costo, stock, minimo=None) -> int:
    categoria = client.post(
        "/api/product-categories", json={"name": f"Cat {sku}"}, headers=_h(empresa_id)
    ).json()
    cuerpo = {
        "sku": sku,
        "name": nombre,
        "categoryId": categoria["id"],
        "salePrice": precio,
        "cost": costo,
        "vatPercentageCode": "0",  # sin IVA: el total es igual al subtotal
        "currentStock": stock,
        "minStock": minimo,
    }
    response = client.post("/api/products", json=cuerpo, headers=_h(empresa_id))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _vender(client, usuario, items) -> int:
    response = client.post(
        "/api/sales",
        json={
            "paymentMethod": "efectivo",
            "items": [{"productId": p, "quantity": q} for p, q in items],
        },
        headers=con_token(usuario),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _gastar(client, usuario, empresa_id, categoria, total, fecha=None):
    categorias = client.get("/api/expense-categories", headers=_h(empresa_id)).json()
    cuerpo = {
        "categoryId": next(c["id"] for c in categorias if c["name"] == categoria),
        "total": total,
        "description": "Gasto",
        "paymentMethod": "efectivo",
    }
    if fecha:
        cuerpo["date"] = fecha.isoformat()
    response = client.post("/api/expenses", json=cuerpo, headers=con_token(usuario))
    assert response.status_code == 201, response.text


@pytest.fixture
def admin(empresas, nuevo_usuario):
    a, _ = empresas
    return nuevo_usuario(a)


def test_empresa_sin_movimientos(client, empresas):
    a, _ = empresas
    resumen = _dashboard(client, a, **{"from": "2026-11-01", "to": "2026-11-07"})
    assert (resumen["from"], resumen["to"]) == ("2026-11-01", "2026-11-07")
    assert (resumen["income"], resumen["expenses"], resumen["profit"]) == (0, 0, 0)
    assert (resumen["salesCount"], resumen["averageTicket"]) == (0, 0)
    assert resumen["topProducts"] == resumen["expensesByCategory"] == []
    # Un punto por día, también los días sin ventas (para el gráfico).
    assert [p["date"] for p in resumen["dailySeries"]] == [f"2026-11-0{d}" for d in range(1, 8)]
    assert resumen["inventory"] == {
        "activeProducts": 0,
        "lowStockCount": 0,
        "inventoryValue": 0,
        "lowStockProducts": [],
    }


def test_por_defecto_es_el_mes_en_curso(client, empresas):
    a, _ = empresas
    hoy = datetime.now(ZONA).date()
    resumen = _dashboard(client, a)
    assert (resumen["from"], resumen["to"]) == (str(hoy.replace(day=1)), str(hoy))


def test_indicadores_del_periodo(client, db, empresas, admin):
    a, _ = empresas
    cafe = _producto(client, a, "CAF", "Café", 5, 3, 20, minimo=5)
    pan = _producto(client, a, "PAN", "Pan", 1, 0.4, 10, minimo=10)
    _vender(client, admin, [(cafe, 2), (pan, 3)])  # 13
    _vender(client, admin, [(cafe, 1)])  # 5
    anulada = _vender(client, admin, [(cafe, 1)])  # no cuenta
    db.get(Venta, anulada).estado = "ANULADA"
    db.flush()
    _gastar(client, admin, a, "Arriendo", 10)
    _gastar(client, admin, a, "Servicios", 2.5)
    _gastar(client, admin, a, "Arriendo", 4)

    hoy = str(datetime.now(ZONA).date())
    resumen = _dashboard(client, a, **{"from": hoy, "to": hoy})
    assert (resumen["income"], resumen["salesCount"], resumen["averageTicket"]) == (18, 2, 9)
    assert (resumen["expenses"], resumen["expensesCount"], resumen["profit"]) == (16.5, 3, 1.5)
    assert resumen["topProducts"] == [
        {"productId": cafe, "name": "Café", "unitsSold": 3, "revenue": 15},
        {"productId": pan, "name": "Pan", "unitsSold": 3, "revenue": 3},
    ]
    assert [(c["name"], c["total"]) for c in resumen["expensesByCategory"]] == [
        ("Arriendo", 14),
        ("Servicios", 2.5),
    ]
    assert resumen["dailySeries"] == [{"date": hoy, "income": 18, "expenses": 16.5}]

    inventario = resumen["inventory"]
    # Stock: café 20-2-1-1 = 16, pan 10-3 = 7 (bajo su mínimo de 10).
    assert (inventario["activeProducts"], inventario["lowStockCount"]) == (2, 1)
    assert inventario["inventoryValue"] == 16 * 3 + 7 * 0.4
    assert inventario["lowStockProducts"] == [
        {"productId": pan, "name": "Pan", "unit": "UNIDAD", "currentStock": 7, "minStock": 10}
    ]


def test_los_dias_son_de_ecuador(client, db, empresas, admin):
    a, _ = empresas
    cafe = _producto(client, a, "CAF", "Café", 5, 3, 20)
    venta = _vender(client, admin, [(cafe, 1)])
    # 23:30 del 10 de noviembre en Ecuador (04:30 del 11 en UTC) es del día 10.
    db.get(Venta, venta).fecha = datetime(2026, 11, 10, 23, 30, tzinfo=ZONA)
    db.flush()
    _gastar(client, admin, a, "Servicios", 7, datetime(2026, 11, 11, 0, 15, tzinfo=ZONA))

    resumen = _dashboard(client, a, **{"from": "2026-11-10", "to": "2026-11-11"})
    assert resumen["dailySeries"] == [
        {"date": "2026-11-10", "income": 5, "expenses": 0},
        {"date": "2026-11-11", "income": 0, "expenses": 7},
    ]
    solo_el_10 = _dashboard(client, a, **{"from": "2026-11-10", "to": "2026-11-10"})
    assert (solo_el_10["income"], solo_el_10["expenses"]) == (5, 0)


def test_periodo_invalido(client, empresas):
    a, _ = empresas
    hoy = date(2026, 11, 20)
    for desde, hasta in ((hoy, hoy - timedelta(days=1)), (hoy - timedelta(days=366), hoy)):
        response = client.get(
            "/api/dashboard", params={"from": str(desde), "to": str(hasta)}, headers=_h(a)
        )
        assert response.status_code == 422, (desde, hasta)


def test_solo_el_administrador(client, empresas, nuevo_usuario):
    a, _ = empresas
    operador = nuevo_usuario(a, rol=OPERATIVO)
    response = client.get("/api/dashboard", headers=con_token(operador))
    assert (response.status_code, response.json()["error"]["code"]) == (403, "FORBIDDEN")


def test_cada_empresa_ve_sus_indicadores(client, empresas, admin):
    a, b = empresas
    cafe = _producto(client, a, "CAF", "Café", 5, 3, 20, minimo=50)
    _vender(client, admin, [(cafe, 1)])
    _gastar(client, admin, a, "Arriendo", 10)
    resumen_b = _dashboard(client, b)
    assert (resumen_b["income"], resumen_b["expenses"], resumen_b["salesCount"]) == (0, 0, 0)
    assert resumen_b["inventory"]["activeProducts"] == 0
