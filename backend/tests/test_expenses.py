"""Gastos, categorías de gasto y proveedores (necesitan TEST_DATABASE_URL)."""

import pytest

from app.core.config import get_settings
from app.services.gasto import CATEGORIAS_PREDEFINIDAS
from tests.conftest import con_token

RUC_SOCIEDAD = "1790016919001"  # Corporación Favorita
CEDULA = "1710000009"


@pytest.fixture(autouse=True)
def _sesion(supabase_falso):
    """Registrar gastos exige un usuario con sesión: se usa el "Supabase falso"."""


def _h(empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id)}  # desarrollo: rol Administrador, sin usuario


def _categoria(client, empresa_id: int, nombre: str = "Servicios") -> int:
    categorias = client.get("/api/expense-categories", headers=_h(empresa_id)).json()
    return next(c["id"] for c in categorias if c["name"] == nombre)


def _proveedor(client, empresa_id: int, **datos) -> dict:
    cuerpo = {"identification": RUC_SOCIEDAD, "name": "Corporación Favorita"} | datos
    response = client.post("/api/suppliers", json=cuerpo, headers=_h(empresa_id))
    assert response.status_code == 201, response.text
    return response.json()


def _gasto(client, usuario, categoria_id: int, **datos):
    cuerpo = {
        "categoryId": categoria_id,
        "total": 25.5,
        "description": "Pago de internet",
        "paymentMethod": "transferencia",
    } | datos
    return client.post("/api/expenses", json=cuerpo, headers=con_token(usuario))


@pytest.fixture
def usuario(empresas, nuevo_usuario):
    a, _ = empresas
    return nuevo_usuario(a)


# ---------- Categorías ----------
def test_las_categorias_predefinidas_se_crean_una_sola_vez(client, empresas):
    a, _ = empresas
    primera = client.get("/api/expense-categories", headers=_h(a)).json()
    segunda = client.get("/api/expense-categories", headers=_h(a)).json()
    assert sorted(c["name"] for c in primera) == sorted(CATEGORIAS_PREDEFINIDAS)
    assert all(c["predefined"] for c in primera)
    assert segunda == primera


def test_crear_categoria_propia_y_no_repetir_nombre(client, empresas):
    a, b = empresas
    response = client.post(
        "/api/expense-categories",
        json={"name": "Publicidad", "description": "Redes sociales"},
        headers=_h(a),
    )
    assert response.status_code == 201
    assert (response.json()["name"], response.json()["predefined"]) == ("Publicidad", False)

    repetida = client.post("/api/expense-categories", json={"name": "publicidad"}, headers=_h(a))
    assert repetida.status_code == 409
    assert repetida.json()["error"]["code"] == "CATEGORY_EXISTS"
    # La otra empresa no ve la categoría y puede crear una con el mismo nombre.
    nombres_b = [c["name"] for c in client.get("/api/expense-categories", headers=_h(b)).json()]
    assert "Publicidad" not in nombres_b
    otra = client.post("/api/expense-categories", json={"name": "Publicidad"}, headers=_h(b))
    assert otra.status_code == 201


# ---------- Proveedores ----------
def test_crear_buscar_y_editar_proveedor(client, empresas):
    a, _ = empresas
    proveedor = _proveedor(client, a, phone="022345678", email="compras@favorita.ec")
    assert proveedor["identification"] == RUC_SOCIEDAD
    assert proveedor["email"] == "compras@favorita.ec"

    encontrado = client.get(
        "/api/suppliers/lookup", params={"identification": RUC_SOCIEDAD}, headers=_h(a)
    )
    assert encontrado.json()["id"] == proveedor["id"]
    lista = client.get("/api/suppliers", params={"search": "favorita"}, headers=_h(a)).json()
    assert [p["id"] for p in lista["items"]] == [proveedor["id"]]

    editado = client.patch(
        f"/api/suppliers/{proveedor['id']}", json={"address": "Quito"}, headers=_h(a)
    )
    assert editado.status_code == 200
    assert (editado.json()["address"], editado.json()["name"]) == ("Quito", "Corporación Favorita")
    vacio = client.patch(f"/api/suppliers/{proveedor['id']}", json={"name": None}, headers=_h(a))
    assert vacio.status_code == 422


def test_proveedor_con_identificacion_invalida_o_repetida(client, empresas):
    a, _ = empresas
    for identificacion in ("1710000008", "123", "9999999999999", "17100000AB"):
        response = client.post(
            "/api/suppliers", json={"identification": identificacion, "name": "X"}, headers=_h(a)
        )
        assert response.status_code == 422, identificacion
        assert response.json()["error"]["code"] == "INVALID_IDENTIFICATION"

    _proveedor(client, a)
    repetido = client.post(
        "/api/suppliers", json={"identification": RUC_SOCIEDAD, "name": "Otro"}, headers=_h(a)
    )
    assert repetido.status_code == 409
    assert repetido.json()["error"]["code"] == "SUPPLIER_EXISTS"


def test_cada_empresa_ve_solo_sus_proveedores(client, empresas):
    a, b = empresas
    proveedor = _proveedor(client, a)
    assert client.get(f"/api/suppliers/{proveedor['id']}", headers=_h(b)).status_code == 404
    assert client.get("/api/suppliers", headers=_h(b)).json()["total"] == 0
    # La misma identificación sí se puede registrar en otra empresa.
    assert _proveedor(client, b)["identification"] == RUC_SOCIEDAD


# ---------- Gastos ----------
def test_registrar_un_gasto(client, empresas, usuario):
    a, _ = empresas
    categoria = _categoria(client, a)
    proveedor = _proveedor(client, a)
    response = _gasto(
        client, usuario, categoria, supplierId=proveedor["id"], receiptNumber="001-001-000000123"
    )
    assert response.status_code == 201, response.text
    gasto = response.json()
    assert gasto["categoryName"] == "Servicios"
    assert (gasto["supplierName"], gasto["supplierIdentification"]) == (
        "Corporación Favorita",
        RUC_SOCIEDAD,
    )
    assert (gasto["total"], gasto["paymentMethod"]) == (25.5, "transferencia")
    assert (gasto["status"], gasto["source"]) == ("confirmado", "manual")
    assert gasto["receiptNumber"] == "001-001-000000123"
    assert gasto["date"].endswith("-05:00")  # hora de Ecuador

    assert client.get(f"/api/expenses/{gasto['id']}", headers=_h(a)).json() == gasto


def test_registrar_gasto_exige_sesion(client, empresas, monkeypatch):
    a, _ = empresas
    cuerpo = {
        "categoryId": _categoria(client, a),
        "total": 10,
        "description": "Gasolina",
        "paymentMethod": "efectivo",
    }
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        response = client.post("/api/expenses", json=cuerpo, headers=_h(a))
    finally:
        get_settings.cache_clear()
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_gasto_invalido(client, empresas, usuario):
    a, b = empresas
    categoria = _categoria(client, a)
    for cambio in ({"total": 0}, {"total": -5}, {"paymentMethod": "bitcoin"}, {"description": ""}):
        assert _gasto(client, usuario, categoria, **cambio).status_code == 422, cambio

    # Categoría y proveedor de otra empresa: como si no existieran.
    ajena = _categoria(client, b)
    response = _gasto(client, usuario, ajena)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "CATEGORY_NOT_FOUND")
    proveedor_b = _proveedor(client, b)
    response = _gasto(client, usuario, categoria, supplierId=proveedor_b["id"])
    assert (response.status_code, response.json()["error"]["code"]) == (422, "SUPPLIER_NOT_FOUND")


def test_filtrar_gastos(client, empresas, usuario):
    a, _ = empresas
    servicios, transporte = _categoria(client, a), _categoria(client, a, "Transporte")
    _gasto(client, usuario, servicios, total=100, date="2026-10-01T10:00:00-05:00")
    _gasto(
        client,
        usuario,
        transporte,
        total=8,
        paymentMethod="efectivo",
        date="2026-10-15T23:30:00-05:00",
    )
    _gasto(client, usuario, servicios, total=40, date="2026-11-02T08:00:00-05:00")

    def totales(**filtros) -> list[float]:
        response = client.get("/api/expenses", params=filtros, headers=_h(a))
        assert response.status_code == 200, response.text
        return [g["total"] for g in response.json()["items"]]

    assert totales() == [40, 8, 100]  # el más reciente primero
    # Las 23:30 del 15 de octubre en Ecuador siguen siendo ese día.
    assert totales(**{"from": "2026-10-15", "to": "2026-10-15"}) == [8]
    assert totales(categoryId=servicios) == [40, 100]
    assert totales(paymentMethod="efectivo") == [8]
    assert totales(minTotal=10, maxTotal=50) == [40]


def test_editar_un_gasto(client, empresas, usuario, monkeypatch):
    a, _ = empresas
    proveedor = _proveedor(client, a)
    gasto = _gasto(client, usuario, _categoria(client, a), supplierId=proveedor["id"]).json()
    url = f"/api/expenses/{gasto['id']}"

    response = client.patch(url, json={"total": 30, "supplierId": None}, headers=con_token(usuario))
    assert response.status_code == 200, response.text
    editado = response.json()
    assert (editado["total"], editado["supplierId"]) == (30, None)
    assert editado["description"] == gasto["description"]

    for vacio in ({"description": None}, {"categoryId": None}, {"total": None}):
        assert client.patch(url, json=vacio, headers=con_token(usuario)).status_code == 422
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        sin_sesion = client.patch(url, json={"total": 1}, headers=_h(a))
    finally:
        get_settings.cache_clear()
    assert sin_sesion.status_code == 401
    assert sin_sesion.json()["error"]["code"] == "UNAUTHENTICATED"


def test_cada_empresa_ve_solo_sus_gastos(client, empresas, usuario):
    a, b = empresas
    gasto = _gasto(client, usuario, _categoria(client, a)).json()
    assert client.get(f"/api/expenses/{gasto['id']}", headers=_h(b)).status_code == 404
    assert client.get("/api/expenses", headers=_h(b)).json()["total"] == 0


# ---------- Anular (RF-3.7) ----------
def test_anular_un_gasto(client, empresas, usuario, nuevo_usuario):
    from app.models.rol import OPERATIVO

    a, _ = empresas
    gasto = _gasto(client, usuario, _categoria(client, a), total=40).json()
    url = f"/api/expenses/{gasto['id']}"

    operador = nuevo_usuario(a, rol=OPERATIVO)
    no = client.post(f"{url}/void", json={"reason": "Duplicado"}, headers=con_token(operador))
    assert (no.status_code, no.json()["error"]["code"]) == (403, "FORBIDDEN")
    assert (
        client.post(f"{url}/void", json={"reason": ""}, headers=con_token(usuario)).status_code
        == 422
    )

    response = client.post(f"{url}/void", json={"reason": "Duplicado"}, headers=con_token(usuario))
    assert response.status_code == 200, response.text
    anulado = response.json()
    assert anulado["status"] == "anulado"
    assert "ANULADO" in anulado["description"] and "Duplicado" in anulado["description"]

    otra_vez = client.post(f"{url}/void", json={"reason": "X"}, headers=con_token(usuario))
    assert (otra_vez.status_code, otra_vez.json()["error"]["code"]) == (
        409,
        "EXPENSE_ALREADY_VOIDED",
    )
    editar = client.patch(url, json={"total": 1}, headers=con_token(usuario))
    assert (editar.status_code, editar.json()["error"]["code"]) == (409, "EXPENSE_VOIDED")
    # Sigue en el historial, pero ya no cuenta en el dashboard.
    assert client.get("/api/expenses", headers=_h(a)).json()["total"] == 1
    assert client.get("/api/dashboard", headers=_h(a)).json()["expenses"] == 0
