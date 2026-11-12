"""Pruebas unitarias de los esquemas de ventas, sin acceso a PostgreSQL."""

import pytest
from pydantic import ValidationError

from app.schemas.venta import SaleItemCreate


def test_linea_producto_valida():
    item = SaleItemCreate(product_id=1, quantity=2)

    assert item.product_id == 1
    assert item.description is None
    assert item.unit_price is None
    assert item.vat_percentage_code is None


def test_linea_servicio_valida():
    item = SaleItemCreate(
        description="Consultoria",
        quantity=1,
        unit_price="25.00",
        vat_percentage_code="4",
    )

    assert item.product_id is None
    assert item.description == "Consultoria"
    assert item.unit_price == 25
    assert item.vat_percentage_code == "4"


@pytest.mark.parametrize(
    "campo",
    ["description", "unit_price", "vat_percentage_code"],
)
def test_linea_servicio_requiere_todos_los_datos(campo):
    datos = {
        "description": "Consultoria",
        "quantity": 1,
        "unit_price": "25.00",
        "vat_percentage_code": "4",
    }
    datos.pop(campo)

    with pytest.raises(ValidationError):
        SaleItemCreate(**datos)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("description", "Producto manual"),
        ("unit_price", "25.00"),
        ("vat_percentage_code", "4"),
    ],
)
def test_linea_producto_rechaza_datos_manuales(campo, valor):
    datos = {"product_id": 1, "quantity": 1, campo: valor}

    with pytest.raises(ValidationError):
        SaleItemCreate(**datos)


def test_linea_rechaza_ausencia_de_producto_y_datos_de_servicio():
    with pytest.raises(ValidationError):
        SaleItemCreate(quantity=1)
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.venta import _a_sale


def test_a_sale_reconstruye_venta_mixta_y_conserva_iva_por_linea():
    fecha = datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc)

    venta = SimpleNamespace(
        id_venta=10,
        fecha=fecha,
        id_cliente=None,
        subtotal=Decimal("75.00"),
        iva=Decimal("11.25"),
        monto_total=Decimal("86.25"),
        metodo_pago="EFECTIVO",
        estado="COMPLETADA",
        observacion=None,
    )

    detalle_producto = SimpleNamespace(
        id_producto=1,
        descripcion_libre=None,
        cantidad=Decimal("2"),
        precio_unitario=Decimal("25.00"),
        descuento=Decimal("0.00"),
        codigo_porcentaje_iva="4",
        subtotal=Decimal("50.00"),
    )

    producto = SimpleNamespace(
        codigo_principal="PROD-001",
        nombre="Producto de prueba",
    )

    detalle_servicio = SimpleNamespace(
        id_producto=None,
        descripcion_libre="Consultoria",
        cantidad=Decimal("1"),
        precio_unitario=Decimal("25.00"),
        descuento=Decimal("0.00"),
        codigo_porcentaje_iva="5",
        subtotal=Decimal("25.00"),
    )

    resultado = _a_sale(
        venta,
        None,
        [
            (detalle_producto, producto),
            (detalle_servicio, None),
        ],
    )

    assert len(resultado.items) == 2

    linea_producto, linea_servicio = resultado.items

    assert linea_producto.product_id == 1
    assert linea_producto.sku == "PROD-001"
    assert linea_producto.product_name == "Producto de prueba"
    assert linea_producto.vat_percentage_code == "4"

    assert linea_servicio.product_id is None
    assert linea_servicio.sku is None
    assert linea_servicio.product_name == "Consultoria"
    assert linea_servicio.vat_percentage_code == "5"

    assert resultado.customer_name == "CONSUMIDOR FINAL"
    assert resultado.payment_method == "efectivo"
    assert resultado.status == "completada"
