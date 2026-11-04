"""Clientes contra PostgreSQL (necesitan TEST_DATABASE_URL, ver conftest.py).

Cédulas inventadas (verificador calculado a mano); RUC de sociedades públicos.
"""

import pytest

CEDULA = "1710000009"
RUC_SOCIEDAD = "1790016919001"  # Corporación Favorita


def _h(empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id)}


def _crear(client, empresa_id: int, **datos):
    cuerpo = {"identification": CEDULA, "name": "Juan Pérez"} | datos
    return client.post("/api/customers", json=cuerpo, headers=_h(empresa_id))


def _error(response) -> dict:
    return response.json()["error"]


# ---------- Crear ----------
def test_crear_con_cedula_deduce_el_tipo(client, empresas):
    a, _ = empresas
    response = _crear(client, a, email="juan@example.com", phone="0991234567")
    assert response.status_code == 201
    cliente = response.json()
    assert cliente == {
        "id": cliente["id"],
        "identificationType": "cedula",
        "identification": CEDULA,
        "name": "Juan Pérez",
        "address": None,
        "phone": "0991234567",
        "email": "juan@example.com",
        "identificationWarning": None,
    }


def test_crear_con_ruc_deduce_el_tipo(client, empresas):
    a, _ = empresas
    response = _crear(client, a, identification=RUC_SOCIEDAD, name="Corporación Favorita C.A.")
    assert response.json()["identificationType"] == "ruc"


def test_ruc_de_sociedad_con_verificador_distinto_se_acepta_con_aviso(client, empresas):
    a, _ = empresas
    response = _crear(client, a, identification="1790010938001", name="Sociedad X")
    assert response.status_code == 201
    assert "confirma el número" in response.json()["identificationWarning"]


def test_pasaporte_requiere_indicar_el_tipo(client, empresas):
    a, _ = empresas
    sin_tipo = _crear(client, a, identification="AB123456")
    assert sin_tipo.status_code == 422
    assert _error(sin_tipo)["details"][0]["field"] == "identificationType"

    con_tipo = _crear(client, a, identification="AB123456", identificationType="pasaporte")
    assert con_tipo.status_code == 201


def test_cedula_invalida_explica_el_motivo(client, empresas):
    a, _ = empresas
    response = _crear(client, a, identification="1710000008")
    assert response.status_code == 422
    assert _error(response)["code"] == "INVALID_IDENTIFICATION"
    assert _error(response)["details"] == [
        {"field": "identification", "message": "El dígito verificador de la cédula no es correcto."}
    ]


def test_el_consumidor_final_no_se_guarda_como_cliente(client, empresas):
    a, _ = empresas
    response = _crear(client, a, identification="9999999999999")
    assert response.status_code == 422
    assert _error(response)["code"] == "FINAL_CONSUMER_NOT_ALLOWED"


@pytest.mark.parametrize(("campo", "valor"), [("email", "sin-arroba.com"), ("phone", "099-abc")])
def test_formato_de_correo_y_telefono(client, empresas, campo, valor):
    a, _ = empresas
    response = _crear(client, a, **{campo: valor})
    assert response.status_code == 422
    assert {"field": campo, "message": "El formato no es válido."} in _error(response)["details"]


def test_identificacion_repetida_en_la_empresa_responde_409(client, empresas):
    a, b = empresas
    assert _crear(client, a).status_code == 201
    repetido = _crear(client, a, name="Otro nombre")
    assert repetido.status_code == 409
    assert _error(repetido)["code"] == "CUSTOMER_EXISTS"
    assert _crear(client, b).status_code == 201  # en otra empresa sí puede existir


# ---------- Buscar y listar ----------
def test_lookup_autocompleta_por_identificacion(client, empresas):
    a, _ = empresas
    creado = _crear(client, a).json()
    response = client.get(f"/api/customers/lookup?identification=%20{CEDULA}%20", headers=_h(a))
    assert response.status_code == 200
    assert response.json() == creado
    no_existe = client.get("/api/customers/lookup?identification=0102030400", headers=_h(a))
    assert no_existe.status_code == 404


def test_listar_con_busqueda(client, empresas):
    a, _ = empresas
    _crear(client, a, identification=CEDULA, name="Juan Pérez")
    _crear(client, a, identification="0102030400", name="María López")
    _crear(client, a, identification=RUC_SOCIEDAD, name="Corporación Favorita")

    def nombres(query: str = "") -> list[str]:
        items = client.get(f"/api/customers?{query}", headers=_h(a)).json()["items"]
        return [c["name"] for c in items]

    assert nombres() == ["Corporación Favorita", "Juan Pérez", "María López"]
    assert nombres("search=maría") == ["María López"]
    assert nombres("search=179001") == ["Corporación Favorita"]


# ---------- Editar ----------
def test_editar_solo_cambia_lo_enviado(client, empresas):
    a, _ = empresas
    cliente = _crear(client, a, email="juan@example.com").json()
    response = client.patch(
        f"/api/customers/{cliente['id']}", json={"address": "Av. Amazonas"}, headers=_h(a)
    )
    assert response.status_code == 200
    assert response.json()["address"] == "Av. Amazonas"
    assert response.json()["email"] == "juan@example.com"


def test_editar_valida_la_nueva_identificacion_y_que_no_este_repetida(client, empresas):
    a, _ = empresas
    juan = _crear(client, a).json()
    _crear(client, a, identification="0102030400", name="María")
    url = f"/api/customers/{juan['id']}"
    assert (
        client.patch(url, json={"identification": "1710000008"}, headers=_h(a)).status_code == 422
    )
    repetida = client.patch(url, json={"identification": "0102030400"}, headers=_h(a))
    assert repetida.status_code == 409
    assert client.patch(url, json={"name": None}, headers=_h(a)).status_code == 422


# ---------- Aislamiento entre empresas ----------
def test_una_empresa_no_ve_ni_modifica_los_clientes_de_otra(client, empresas):
    a, b = empresas
    cliente = _crear(client, a).json()
    url = f"/api/customers/{cliente['id']}"

    assert client.get("/api/customers", headers=_h(b)).json()["total"] == 0
    assert client.get(url, headers=_h(b)).status_code == 404
    assert client.patch(url, json={"name": "Hackeado"}, headers=_h(b)).status_code == 404
    lookup = client.get(f"/api/customers/lookup?identification={CEDULA}", headers=_h(b))
    assert lookup.status_code == 404
    assert client.get(url, headers=_h(a)).json()["name"] == "Juan Pérez"
