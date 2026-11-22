"""Pruebas de los triggers que exigen pertenencia activa."""

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import (
    AccionIA,
    CategoriaGasto,
    CategoriaProducto,
    Gasto,
    MovimientoInventario,
    Producto,
    Venta,
)


@pytest.fixture(scope="module", autouse=True)
def triggers_membresia(engine):
    """Instala y retira los triggers usando la migración real."""
    ruta = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_11_19_2200-f3a8c1d72e90_validar_membresia_activa.py"
    )
    spec = importlib.util.spec_from_file_location(
        "migration_validar_membresia_activa",
        ruta,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar la migración: {ruta}")

    migracion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracion)

    with engine.begin() as conn:
        contexto = MigrationContext.configure(conn)
        with Operations.context(contexto):
            migracion.upgrade()

    yield

    with engine.begin() as conn:
        contexto = MigrationContext.configure(conn)
        with Operations.context(contexto):
            migracion.downgrade()


def test_venta_rechaza_usuario_con_pertenencia_inactiva(db, empresas, nuevo_usuario):
    id_empresa, _ = empresas
    usuario = nuevo_usuario(id_empresa, estado="INACTIVO")

    with pytest.raises(DBAPIError, match="membresia activa"), db.begin_nested():
        db.add(
            Venta(
                id_empresa=id_empresa,
                id_usuario=usuario,
                subtotal=10,
                iva=1.50,
                monto_total=11.50,
                tipo_origen="MANUAL",
                metodo_pago="EFECTIVO",
            )
        )
        db.flush()


def test_gasto_rechaza_usuario_con_pertenencia_inactiva(db, empresas, nuevo_usuario):
    id_empresa, _ = empresas
    usuario = nuevo_usuario(id_empresa, estado="INACTIVO")
    categoria = CategoriaGasto(
        id_empresa=id_empresa,
        nombre="Prueba trigger",
    )
    db.add(categoria)
    db.flush()

    with pytest.raises(DBAPIError, match="membresia activa"), db.begin_nested():
        db.add(
            Gasto(
                id_empresa=id_empresa,
                id_categoria_gasto=categoria.id_categoria_gasto,
                id_usuario=usuario,
                monto=10,
                concepto="Gasto de prueba",
                metodo_pago="EFECTIVO",
            )
        )
        db.flush()


def test_movimiento_rechaza_usuario_con_pertenencia_inactiva(db, empresas, nuevo_usuario):
    id_empresa, _ = empresas
    usuario = nuevo_usuario(id_empresa, estado="INACTIVO")
    categoria = CategoriaProducto(
        id_empresa=id_empresa,
        nombre="Prueba trigger",
    )
    db.add(categoria)
    db.flush()

    producto = Producto(
        id_empresa=id_empresa,
        id_categoria_producto=categoria.id_categoria_producto,
        codigo_principal="TRIGGER-001",
        nombre="Producto de prueba",
    )
    db.add(producto)
    db.flush()

    with pytest.raises(DBAPIError, match="membresia activa"), db.begin_nested():
        db.add(
            MovimientoInventario(
                id_empresa=id_empresa,
                id_producto=producto.id_producto,
                id_usuario=usuario,
                tipo_movimiento="ENTRADA",
                cantidad=1,
            )
        )
        db.flush()


def test_accion_ia_rechaza_usuario_con_pertenencia_inactiva(db, empresas, nuevo_usuario):
    id_empresa, _ = empresas
    usuario = nuevo_usuario(id_empresa, estado="INACTIVO")

    with pytest.raises(DBAPIError, match="membresia activa"), db.begin_nested():
        db.add(
            AccionIA(
                id_empresa=id_empresa,
                id_usuario=usuario,
                tipo_accion="CONSULTA",
                instruccion_recibida="Prueba de pertenencia inactiva",
            )
        )
        db.flush()


def test_accion_ia_permite_usuario_nulo_para_registro_historico(db, empresas):
    id_empresa, _ = empresas
    accion = AccionIA(
        id_empresa=id_empresa,
        id_usuario=None,
        tipo_accion="CONSULTA",
        instruccion_recibida="Registro histórico sin usuario",
    )
    db.add(accion)
    db.flush()

    assert accion.id_accion_ia is not None


def test_movimiento_rechaza_producto_de_otra_empresa(db, empresas, nuevo_usuario):
    empresa_a, empresa_b = empresas
    usuario_a = nuevo_usuario(empresa_a)

    categoria_b = CategoriaProducto(
        id_empresa=empresa_b,
        nombre="Categoria empresa B",
    )
    db.add(categoria_b)
    db.flush()

    producto_b = Producto(
        id_empresa=empresa_b,
        id_categoria_producto=categoria_b.id_categoria_producto,
        codigo_principal="PRODUCTO-EMPRESA-B",
        nombre="Producto de empresa B",
    )
    db.add(producto_b)
    db.flush()

    with (
        pytest.raises(
            IntegrityError,
            match="movimiento_inventario_empresa_producto_fkey",
        ),
        db.begin_nested(),
    ):
        db.add(
            MovimientoInventario(
                id_empresa=empresa_a,
                id_producto=producto_b.id_producto,
                id_usuario=usuario_a,
                tipo_movimiento="ENTRADA",
                cantidad=1,
            )
        )
        db.flush()
