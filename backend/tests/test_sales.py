"""Ventas contra PostgreSQL (necesitan TEST_DATABASE_URL, ver conftest.py).

Totales calculados a mano: café 2 x 4.50 = 9.00 (IVA 15 % = 1.35) y azúcar
3 x 1.10 = 3.30 (IVA 0 %) -> subtotal 12.30, IVA 1.35, total 13.65.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import DetalleVenta, MovimientoInventario, Producto, Venta
from tests.conftest import con_token


@pytest.fixture(autouse=True)
def _sesion(supabase_falso):
    """Las ventas exigen un usuario con sesión: se usa el "Supabase falso"."""


def _h(empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id)}


@pytest.fixture
def catalogo(client, empresas) -> dict[str, int]:
    """Categoría, productos y un cliente en la empresa A (creados por la API)."""
    a, _ = empresas
    cat = client.post(
        "/api/product-categories",
        json={"name": "Abarrotes"},
        headers=_h(a),
    ).json()

    def producto(
        sku: str,
        nombre: str,
        precio: float,
        iva: bool,
        stock: float,
        tipo: str = "venta",
    ) -> int:
        cuerpo = {
            "sku": sku,
            "name": nombre,
            "categoryId": cat["id"],
            "salePrice": precio,
            "vatPercentageCode": "4" if iva else "0",
            "currentStock": stock,
            "type": tipo,
        }
        respuesta = client.post(
            "/api/products",
            json=cuerpo,
            headers=_h(a),
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()["id"]

    cliente_response = client.post(
        "/api/customers",
        json={"identification": "1710000009", "name": "Juan Pérez"},
        headers=_h(a),
    )
    assert cliente_response.status_code == 201, cliente_response.text
    cliente = cliente_response.json()

    return {
        "cafe": producto("CAF-250", "Café molido 250 g", 4.5, True, 10),
        "azucar": producto("AZU-1K", "Azúcar 1 kg", 1.1, False, 5),
        "harina": producto("HAR-INS", "Harina (insumo)", 0.8, False, 50, tipo="insumo"),
        "cliente": cliente["id"],
    }


@pytest.fixture
def vendedor(empresas, nuevo_usuario):
    a, _ = empresas
    return nuevo_usuario(a)


def _vender(client, usuario, items, **extra):
    cuerpo = {"items": items, "paymentMethod": "efectivo"} | extra
    return client.post("/api/sales", json=cuerpo, headers=con_token(usuario))


def _stock(db, id_producto) -> float:
    db.expire_all()
    return float(db.get(Producto, id_producto).stock_actual)


# ---------- Registrar ----------
def test_venta_completa_calcula_totales_y_descuenta_stock(client, db, catalogo, vendedor):
    response = _vender(
        client,
        vendedor,
        [
            {"productId": catalogo["cafe"], "quantity": 2},
            {"productId": catalogo["azucar"], "quantity": 3},
        ],
        customerId=catalogo["cliente"],
        observation="Entrega a domicilio",
    )
    assert response.status_code == 201
    venta = response.json()
    assert (venta["subtotal"], venta["ivaAmount"], venta["total"]) == (12.3, 1.35, 13.65)
    assert (venta["customerName"], venta["customerIdentification"]) == ("Juan Pérez", "1710000009")
    assert (venta["paymentMethod"], venta["status"]) == ("efectivo", "completada")
    assert venta["date"].endswith("-05:00")  # hora de Ecuador
    assert [(i["sku"], i["quantity"], i["unitPrice"], i["subtotal"]) for i in venta["items"]] == [
        ("CAF-250", 2.0, 4.5, 9.0),
        ("AZU-1K", 3.0, 1.1, 3.3),
    ]

    assert (_stock(db, catalogo["cafe"]), _stock(db, catalogo["azucar"])) == (8.0, 2.0)
    movimientos = db.scalars(
        select(MovimientoInventario).order_by(MovimientoInventario.id_movimiento)
    ).all()
    assert [(m.tipo_movimiento, float(m.cantidad), m.id_usuario) for m in movimientos] == [
        ("VENTA", 2.0, vendedor),
        ("VENTA", 3.0, vendedor),
    ]
    assert movimientos[0].motivo == f"Venta #{venta['id']}"


def test_sin_cliente_es_consumidor_final(client, catalogo, vendedor):
    venta = _vender(
        client,
        vendedor,
        [{"productId": catalogo["cafe"], "quantity": 1}],
    ).json()
    assert (venta["customerId"], venta["customerName"]) == (None, "CONSUMIDOR FINAL")


def test_el_descuento_se_resta_de_la_linea(client, catalogo, vendedor):
    venta = _vender(
        client,
        vendedor,
        [{"productId": catalogo["cafe"], "quantity": 2, "discount": 1}],
    ).json()
    # 2 x 4.50 - 1.00 = 8.00; IVA 15 % = 1.20
    assert (venta["subtotal"], venta["ivaAmount"], venta["total"]) == (8.0, 1.2, 9.2)


def test_sin_sesion_de_usuario_no_se_puede_registrar(client, empresas, catalogo, monkeypatch):
    from app.core.config import get_settings

    a, _ = empresas
    cuerpo = {
        "items": [{"productId": catalogo["cafe"], "quantity": 1}],
        "paymentMethod": "efectivo",
    }
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        response = client.post("/api/sales", json=cuerpo, headers=_h(a))
    finally:
        get_settings.cache_clear()
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


# ---------- Stock ----------
def test_sin_stock_suficiente_no_se_guarda_nada(client, db, catalogo, vendedor):
    response = _vender(
        client,
        vendedor,
        [
            {"productId": catalogo["cafe"], "quantity": 1},
            {"productId": catalogo["azucar"], "quantity": 6},
        ],
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INSUFFICIENT_STOCK"
    assert error["details"] == [
        {
            "field": "items[1].quantity",
            "message": "Stock disponible de Azúcar 1 kg: 5.",
        }
    ]
    assert (_stock(db, catalogo["cafe"]), _stock(db, catalogo["azucar"])) == (10.0, 5.0)
    assert db.scalar(select(Venta.id_venta).limit(1)) is None


def test_se_puede_vender_exactamente_todo_el_stock(client, db, catalogo, vendedor):
    assert (
        _vender(
            client,
            vendedor,
            [{"productId": catalogo["azucar"], "quantity": 5}],
        ).status_code
        == 201
    )
    assert _stock(db, catalogo["azucar"]) == 0.0
    otra = _vender(
        client,
        vendedor,
        [{"productId": catalogo["azucar"], "quantity": 1}],
    )
    assert otra.status_code == 409


# ---------- Validaciones ----------
@pytest.mark.parametrize(
    ("items", "code"),
    [
        ([{"productId": 999999, "quantity": 1}], "PRODUCT_NOT_FOUND"),
        ([{"productId": "harina", "quantity": 1}], "PRODUCT_NOT_SELLABLE"),
        (
            [
                {"productId": "cafe", "quantity": 1},
                {"productId": "cafe", "quantity": 2},
            ],
            "DUPLICATE_PRODUCT",
        ),
        ([{"productId": "cafe", "quantity": 1, "discount": 5}], "VALIDATION_ERROR"),
    ],
)
def test_productos_invalidos(client, catalogo, vendedor, items, code):
    items = [i | {"productId": catalogo.get(i["productId"], i["productId"])} for i in items]
    response = _vender(client, vendedor, items)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_producto_desactivado_no_se_vende(client, db, catalogo, vendedor):
    db.get(Producto, catalogo["cafe"]).activo = False
    db.flush()
    response = _vender(
        client,
        vendedor,
        [{"productId": catalogo["cafe"], "quantity": 1}],
    )
    assert response.json()["error"]["code"] == "PRODUCT_INACTIVE"


def test_lista_vacia_y_metodo_de_pago_desconocido(client, catalogo, vendedor):
    assert _vender(client, vendedor, []).status_code == 422
    item = [{"productId": catalogo["cafe"], "quantity": 1}]
    assert _vender(client, vendedor, item, paymentMethod="bitcoin").status_code == 422


# ---------- Consultar ----------
def test_historial_con_filtros(client, empresas, catalogo, vendedor):
    a, _ = empresas
    primera = _vender(
        client,
        vendedor,
        [{"productId": catalogo["cafe"], "quantity": 1}],
    ).json()
    segunda = _vender(
        client,
        vendedor,
        [{"productId": catalogo["azucar"], "quantity": 1}],
        customerId=catalogo["cliente"],
        paymentMethod="transferencia",
    ).json()

    def ids(query: str = "") -> list[int]:
        return [v["id"] for v in client.get(f"/api/sales?{query}", headers=_h(a)).json()["items"]]

    assert ids() == [segunda["id"], primera["id"]]  # la más reciente primero
    assert ids("paymentMethod=transferencia") == [segunda["id"]]
    assert ids(f"customerId={catalogo['cliente']}") == [segunda["id"]]
    hoy = datetime.now(ZoneInfo("America/Guayaquil")).date()
    assert len(ids(f"from={hoy}&to={hoy}")) == 2
    assert ids(f"from={hoy + timedelta(days=1)}") == []
    detalle = client.get(f"/api/sales/{segunda['id']}", headers=_h(a)).json()
    assert detalle == segunda


# ---------- Aislamiento entre empresas ----------
def test_una_empresa_no_ve_las_ventas_ni_usa_productos_o_clientes_de_otra(
    client, empresas, catalogo, vendedor, nuevo_usuario
):
    a, b = empresas
    venta = _vender(
        client,
        vendedor,
        [{"productId": catalogo["cafe"], "quantity": 1}],
    ).json()
    assert client.get("/api/sales", headers=_h(b)).json()["total"] == 0
    assert client.get(f"/api/sales/{venta['id']}", headers=_h(b)).status_code == 404

    vendedor_b = nuevo_usuario(b)
    con_producto_de_a = _vender(
        client,
        vendedor_b,
        [{"productId": catalogo["cafe"], "quantity": 1}],
    )
    assert con_producto_de_a.json()["error"]["code"] == "PRODUCT_NOT_FOUND"

    con_cliente_de_a = _vender(
        client,
        vendedor_b,
        [{"productId": catalogo["cafe"], "quantity": 1}],
        customerId=catalogo["cliente"],
    )
    assert con_cliente_de_a.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


def test_detalle_rechaza_producto_de_otra_empresa(client, db, empresas, catalogo, vendedor):
    a, b = empresas
    venta = _vender(
        client,
        vendedor,
        [{"productId": catalogo["cafe"], "quantity": 1}],
    ).json()

    categoria_b = client.post(
        "/api/product-categories",
        json={"name": "Categoría B"},
        headers=_h(b),
    )
    assert categoria_b.status_code == 201, categoria_b.text

    producto_b = client.post(
        "/api/products",
        json={
            "sku": "PROD-B",
            "name": "Producto empresa B",
            "categoryId": categoria_b.json()["id"],
            "salePrice": 1,
            "vatPercentageCode": "0",
            "currentStock": 5,
            "type": "venta",
        },
        headers=_h(b),
    )
    assert producto_b.status_code == 201, producto_b.text

    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            DetalleVenta(
                id_empresa=a,
                id_venta=venta["id"],
                id_producto=producto_b.json()["id"],
                descripcion_libre="Producto empresa B",
                cantidad=1,
                precio_unitario=1,
                descuento=0,
                codigo_porcentaje_iva="0",
                subtotal=1,
                porcentaje_iva=0,
                valor_iva=0,
            )
        )
        db.flush()


def test_eliminar_producto_conserva_nombre_en_detalle_historico(
    client, db, empresas, catalogo, vendedor
):
    a, _ = empresas
    producto = db.get(Producto, catalogo["cafe"])
    nombre_historico = producto.nombre

    venta = Venta(
        id_empresa=a,
        id_usuario=vendedor,
        subtotal=4.50,
        iva=0.68,
        monto_total=5.18,
        tipo_origen="MANUAL",
        metodo_pago="EFECTIVO",
        estado="COMPLETADA",
    )
    db.add(venta)
    db.flush()

    detalle = DetalleVenta(
        id_empresa=a,
        id_venta=venta.id_venta,
        id_producto=producto.id_producto,
        descripcion_libre=nombre_historico,
        cantidad=1,
        precio_unitario=4.50,
        descuento=0,
        codigo_porcentaje_iva="4",
        subtotal=4.50,
        porcentaje_iva=15,
        valor_iva=0.68,
    )
    db.add(detalle)
    db.flush()
    id_venta = venta.id_venta
    id_detalle = detalle.id_detalle_venta

    db.delete(producto)
    db.flush()
    db.expire_all()

    detalle_guardado = db.get(DetalleVenta, id_detalle)
    assert detalle_guardado.id_producto is None
    assert detalle_guardado.descripcion_libre == nombre_historico

    respuesta = client.get(
        f"/api/sales/{id_venta}",
        headers=_h(a),
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["items"][0]["productId"] is None
    assert respuesta.json()["items"][0]["productName"] == nombre_historico
