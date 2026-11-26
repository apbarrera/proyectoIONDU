"""Agente de IA, etapa 2: entradas, salidas y ajustes de inventario propuestos por texto."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.api.agente_ia import get_modelo
from app.ia.agente import menciona_producto
from app.main import app
from app.models import Auditoria, MovimientoInventario, Producto
from app.models.rol import OPERATIVO
from tests.conftest import con_token
from tests.test_agente_ia import ModeloFalso, _gasto

pytestmark = pytest.mark.usefixtures("supabase_falso")

CAFE = "Café en grano [CAF-1]"


def _inventario(producto=CAFE, tipo="entrada", cantidad=10, motivo="Llegó pedido"):
    return {
        "accion": "movimiento_inventario",
        "respuesta": "",
        "gasto": _gasto(total=0),
        "inventario": {"producto": producto, "tipo": tipo, "cantidad": cantidad, "motivo": motivo},
    }


@pytest.fixture
def modelo():
    falso = ModeloFalso(_inventario())
    app.dependency_overrides[get_modelo] = lambda: falso
    yield falso
    app.dependency_overrides.pop(get_modelo, None)


@pytest.fixture
def admin(usuarios_empresa, empresas) -> uuid.UUID:
    return usuarios_empresa[empresas[0]]


@pytest.fixture
def operador(empresas, nuevo_usuario) -> uuid.UUID:
    return nuevo_usuario(empresas[0], rol=OPERATIVO)


@pytest.fixture
def cafe(client, admin) -> int:
    """Producto con 5 unidades en la empresa A."""
    categoria = client.post(
        "/api/product-categories", json={"name": "Cafés"}, headers=con_token(admin)
    ).json()["id"]
    return client.post(
        "/api/products",
        json={
            "sku": "CAF-1",
            "name": "Café en grano",
            "categoryId": categoria,
            "salePrice": 8.5,
            "currentStock": 5,
        },
        headers=con_token(admin),
    ).json()["id"]


def _enviar(client, usuario, texto="Llegaron 10 bolsas de café"):
    return client.post("/api/ai/messages", json={"text": texto}, headers=con_token(usuario)).json()


def _confirmar(client, usuario, id_accion, cuerpo=None):
    return client.post(
        f"/api/ai/actions/{id_accion}/confirm", json=cuerpo or {}, headers=con_token(usuario)
    )


def _stock(db, id_producto) -> Decimal:
    db.expire_all()
    return db.get(Producto, id_producto).stock_actual


# ---------- Propuestas ----------
def test_una_entrada_se_propone_con_el_stock_resultante(client, db, modelo, admin, cafe):
    cuerpo = _enviar(client, admin)

    propuesta = cuerpo["proposal"]
    assert propuesta["type"] == "inventory"
    assert propuesta["inventory"] == {
        "productId": cafe,
        "productName": "Café en grano",
        "type": "entrada",
        "quantity": 10.0,
        "unit": "UNIDAD",
        "currentStock": 5.0,
        "resultingStock": 15.0,
        "reason": "Llegó pedido",
    }
    assert "stock: 5 → 15" in cuerpo["reply"]
    assert _stock(db, cafe) == Decimal("5")  # nada cambia sin confirmar


def test_el_modelo_solo_puede_elegir_productos_activos(client, db, modelo, admin, cafe):
    db.get(Producto, cafe).activo = False
    db.flush()
    _enviar(client, admin)
    productos = modelo.esquema["properties"]["inventario"]["properties"]["producto"]["enum"]
    assert productos == ["(otro producto)"]


def test_el_prompt_lleva_el_catalogo_con_su_stock(client, modelo, admin, cafe):
    _enviar(client, admin)
    assert "Café en grano [CAF-1]: unidad UNIDAD, stock actual 5" in modelo.mensajes[0]["content"]


def test_una_salida_mayor_al_stock_se_convierte_en_pregunta(client, modelo, admin, cafe):
    modelo.datos = _inventario(tipo="salida", cantidad=8)
    cuerpo = _enviar(client, admin, "Se dañaron 8 bolsas de café")
    assert cuerpo["proposal"] is None
    assert "Solo hay 5" in cuerpo["reply"]


def test_un_producto_que_no_esta_en_el_catalogo_se_pregunta(client, modelo, admin, cafe):
    modelo.datos = _inventario(producto="Té verde [TE-9]")
    cuerpo = _enviar(client, admin, "Llegaron 3 cajas de té")
    assert cuerpo["proposal"] is None
    assert "¿De qué producto" in cuerpo["reply"]


def test_un_operativo_no_recibe_propuestas_de_ajuste(client, modelo, operador, cafe):
    modelo.datos = _inventario(tipo="ajuste", cantidad=20, motivo="Conteo")
    cuerpo = _enviar(client, operador, "Conté 20 bolsas de café")
    assert cuerpo["proposal"] is None
    assert "Administrador" in cuerpo["reply"]


# ---------- Confirmar ----------
def test_confirmar_una_entrada_mueve_el_stock_y_lo_audita(client, db, modelo, admin, cafe):
    id_accion = _enviar(client, admin)["actionId"]

    response = _confirmar(client, admin, id_accion)

    assert response.status_code == 200
    assert response.json()["expenseId"] is None
    movimiento = db.get(MovimientoInventario, response.json()["movementId"])
    assert movimiento.motivo == "Llegó pedido"
    assert _stock(db, cafe) == Decimal("15")
    registro = db.scalar(select(Auditoria).where(Auditoria.modulo == "ia"))
    assert registro.descripcion.startswith("Movimiento de inventario #")


def test_corregir_la_cantidad_de_una_salida(client, db, modelo, operador, cafe):
    modelo.datos = _inventario(tipo="salida", cantidad=3, motivo="Producto dañado")
    id_accion = _enviar(client, operador, "Se dañaron 3 bolsas de café")["actionId"]

    response = _confirmar(client, operador, id_accion, {"quantity": 2})

    assert response.json()["status"] == "corregido"
    assert _stock(db, cafe) == Decimal("3")


def test_el_administrador_ajusta_por_conteo(client, db, modelo, admin, cafe):
    modelo.datos = _inventario(tipo="ajuste", cantidad=12, motivo="Conteo físico")
    cuerpo = _enviar(client, admin, "Conté 12 bolsas de café")
    assert "de 5 a 12" in cuerpo["reply"]

    assert _confirmar(client, admin, cuerpo["actionId"]).status_code == 200
    assert _stock(db, cafe) == Decimal("12")


def test_un_operativo_no_puede_confirmar_un_ajuste(client, db, modelo, admin, operador, cafe):
    modelo.datos = _inventario(tipo="ajuste", cantidad=12, motivo="Conteo físico")
    id_accion = _enviar(client, admin, "Conté 12 bolsas de café")["actionId"]

    response = _confirmar(client, operador, id_accion)

    assert (response.status_code, response.json()["error"]["code"]) == (403, "ADMIN_REQUIRED")
    assert _stock(db, cafe) == Decimal("5")


def test_el_historial_guarda_el_movimiento(client, modelo, admin, cafe):
    id_accion = _enviar(client, admin)["actionId"]
    _confirmar(client, admin, id_accion)

    [accion] = client.get("/api/ai/actions", headers=con_token(admin)).json()["items"]
    assert accion["proposal"]["type"] == "inventory"
    assert accion["movementId"] is not None


def test_el_modelo_siempre_tiene_la_opcion_otro_producto(client, modelo, admin, cafe):
    _enviar(client, admin)
    productos = modelo.esquema["properties"]["inventario"]["properties"]["producto"]["enum"]
    assert productos == [CAFE, "(otro producto)"]


def test_otro_producto_se_convierte_en_pregunta(client, modelo, admin, cafe):
    modelo.datos = _inventario(producto="(otro producto)")
    cuerpo = _enviar(client, admin, "Llegaron 5 cajas de té verde")
    assert cuerpo["proposal"] is None
    assert "¿De qué producto" in cuerpo["reply"]


@pytest.mark.parametrize(
    ("texto", "nombre", "esperado"),
    [
        ("Llegaron 20 croissants", "Croissant", True),
        ("Se rompieron 2 aguas", "Agua sin gas 500 ml", True),
        ("Sacamos 1 kilo de azúcar", "Azúcar 1 kg", True),
        ("Llegaron 5 cajas de té verde", "Café en grano 500 g", False),
        ("Llegaron 3 cajas", "Café en grano 500 g", False),
    ],
)
def test_el_producto_debe_mencionarse_en_el_mensaje(texto, nombre, esperado):
    assert menciona_producto(texto, nombre) is esperado


def test_si_el_modelo_elige_un_producto_que_no_se_menciono_se_pregunta(client, modelo, admin, cafe):
    # El modelo (obligado a elegir de la lista) propone café cuando el usuario habló de té.
    cuerpo = _enviar(client, admin, "Llegaron 5 cajas de té verde")
    assert cuerpo["proposal"] is None
    assert "¿De qué producto" in cuerpo["reply"]
