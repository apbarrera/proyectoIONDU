"""Pruebas unitarias del servicio de ventas sin acceso a PostgreSQL."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models import DetalleVenta, MovimientoInventario, Venta
from app.schemas.venta import SaleCreate
from app.services.venta import VentaService


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeVentaRepository:
    def __init__(self, productos):
        self.productos = productos
        self.venta = None
        self.lineas = []
        self.movimientos = []
        self.flushes = 0

    def bloquear_productos(self, ids):
        return {
            id_producto: self.productos[id_producto]
            for id_producto in ids
            if id_producto in self.productos
        }

    def agregar(self, objeto):
        if isinstance(objeto, Venta):
            self.venta = objeto
        elif isinstance(objeto, DetalleVenta):
            self.lineas.append(objeto)
        elif isinstance(objeto, MovimientoInventario):
            self.movimientos.append(objeto)
        else:
            raise AssertionError(f"Objeto inesperado: {type(objeto).__name__}")

    def guardar_pendientes(self):
        self.flushes += 1
        if self.venta is not None and self.venta.id_venta is None:
            self.venta.id_venta = 101
            self.venta.fecha = datetime(2026, 11, 9, 20, 0, tzinfo=UTC)

    def obtener(self, id_venta):
        if self.venta is None or self.venta.id_venta != id_venta:
            return None
        return self.venta, None, None, None  # venta, cliente, factura, quién la registró

    def detalles(self, ids_venta):
        resultado = {id_venta: [] for id_venta in ids_venta}
        for detalle in self.lineas:
            if detalle.id_venta in resultado:
                producto = self.productos.get(detalle.id_producto)
                resultado[detalle.id_venta].append((detalle, producto))
        return resultado


class FakeClienteRepository:
    def obtener(self, id_cliente):
        return None


def _servicio(monkeypatch, productos=None):
    repo = FakeVentaRepository(productos or {})
    session = FakeSession()

    monkeypatch.setattr(
        "app.services.venta.VentaRepository",
        lambda db, empresa_id: repo,
    )
    monkeypatch.setattr(
        "app.services.venta.ClienteRepository",
        lambda db, empresa_id: FakeClienteRepository(),
    )

    return VentaService(session, empresa_id=1), repo, session


def _producto():
    return SimpleNamespace(
        id_producto=1,
        codigo_principal="PROD-001",
        nombre="Producto de prueba",
        precio_venta=Decimal("10.00"),
        codigo_porcentaje_iva="4",
        stock_actual=Decimal("8"),
        activo=True,
        tipo="PRODUCTO",
    )


def test_venta_solo_servicios_no_modifica_inventario(monkeypatch):
    servicio, repo, session = _servicio(monkeypatch)
    datos = SaleCreate(
        items=[
            {
                "description": "Consultoría",
                "quantity": Decimal("1"),
                "unit_price": Decimal("25.00"),
                "vat_percentage_code": "5",
            }
        ],
        payment_method="efectivo",
    )

    resultado = servicio.crear(datos, uuid4())

    assert len(repo.lineas) == 1
    assert repo.lineas[0].id_producto is None
    assert repo.lineas[0].descripcion_libre == "Consultoría"
    assert repo.lineas[0].codigo_porcentaje_iva == "5"
    assert repo.lineas[0].porcentaje_iva == Decimal("5")
    assert repo.lineas[0].valor_iva == Decimal("1.25")
    assert resultado.items[0].product_name == "Consultoría"
    assert resultado.items[0].vat_percentage_code == "5"
    assert repo.movimientos == []
    assert repo.flushes == 2
    assert session.commits == 1
    assert session.rollbacks == 0


def test_venta_de_producto_descuenta_stock_y_registra_movimiento(monkeypatch):
    producto = _producto()
    servicio, repo, session = _servicio(monkeypatch, {1: producto})
    datos = SaleCreate(
        items=[{"product_id": 1, "quantity": Decimal("2")}],
        payment_method="efectivo",
    )

    resultado = servicio.crear(datos, uuid4())

    assert producto.stock_actual == Decimal("6")
    assert len(repo.lineas) == 1
    assert repo.lineas[0].id_producto == 1
    assert repo.lineas[0].descripcion_libre == producto.nombre
    assert repo.lineas[0].precio_unitario == Decimal("10.00")
    assert repo.lineas[0].codigo_porcentaje_iva == "4"
    assert repo.lineas[0].porcentaje_iva == Decimal("15")
    assert repo.lineas[0].valor_iva == Decimal("3.00")
    assert len(repo.movimientos) == 1
    assert repo.movimientos[0].tipo_movimiento == "VENTA"
    assert repo.movimientos[0].cantidad == Decimal("2")
    assert resultado.items[0].sku == "PROD-001"
    assert resultado.subtotal == Decimal("20.00")
    assert resultado.iva_amount == Decimal("3.00")
    assert resultado.total == Decimal("23.00")
    assert session.commits == 1
    assert session.rollbacks == 0


def test_venta_mixta_conserva_lineas_y_codigos_iva(monkeypatch):
    producto = _producto()
    servicio, repo, session = _servicio(monkeypatch, {1: producto})
    datos = SaleCreate(
        items=[
            {"product_id": 1, "quantity": Decimal("2")},
            {
                "description": "Consultoría",
                "quantity": Decimal("1"),
                "unit_price": Decimal("25.00"),
                "vat_percentage_code": "5",
            },
        ],
        payment_method="efectivo",
    )

    resultado = servicio.crear(datos, uuid4())

    assert len(repo.lineas) == 2
    assert [linea.id_producto for linea in repo.lineas] == [1, None]
    assert [linea.descripcion_libre for linea in repo.lineas] == [producto.nombre, "Consultoría"]
    assert [linea.codigo_porcentaje_iva for linea in repo.lineas] == ["4", "5"]
    assert [item.vat_percentage_code for item in resultado.items] == ["4", "5"]
    assert producto.stock_actual == Decimal("6")
    assert len(repo.movimientos) == 1
    assert resultado.subtotal == Decimal("45.00")
    assert resultado.iva_amount == Decimal("4.25")
    assert resultado.total == Decimal("49.25")
    assert session.commits == 1
    assert session.rollbacks == 0


def test_error_al_validar_producto_hace_rollback_sin_commit(monkeypatch):
    servicio, repo, session = _servicio(monkeypatch)
    datos = SaleCreate(
        items=[{"product_id": 999, "quantity": Decimal("1")}],
        payment_method="efectivo",
    )

    with pytest.raises(Exception) as error:
        servicio.crear(datos, uuid4())

    assert getattr(error.value, "code", None) == "PRODUCT_NOT_FOUND"
    assert repo.venta is None
    assert repo.lineas == []
    assert repo.movimientos == []
    assert session.commits == 0
    assert session.rollbacks == 1
