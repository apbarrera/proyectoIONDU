from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnprocessableError
from app.models import Empresa, SecuenciaComprobante
from app.services.secuencia_comprobante import SecuenciaComprobanteService


def _reservar(servicio, empresa_id, establecimiento="001", punto_emision="001"):
    return servicio.reservar(
        id_empresa=empresa_id,
        establecimiento=establecimiento,
        punto_emision=punto_emision,
        tipo_comprobante="01",
    )


def test_primer_secuencial_comienza_en_uno(db, empresas):
    servicio = SecuenciaComprobanteService(db)

    assert _reservar(servicio, empresas[0]) == 1


def test_reservas_consecutivas_incrementan_el_contador(db, empresas):
    servicio = SecuenciaComprobanteService(db)

    assert _reservar(servicio, empresas[0]) == 1
    assert _reservar(servicio, empresas[0]) == 2
    assert _reservar(servicio, empresas[0]) == 3


def test_empresas_y_configuraciones_tienen_contadores_independientes(db, empresas):
    servicio = SecuenciaComprobanteService(db)
    empresa_a, empresa_b = empresas

    assert _reservar(servicio, empresa_a) == 1
    assert _reservar(servicio, empresa_a, punto_emision="002") == 1
    assert _reservar(servicio, empresa_b) == 1
    assert _reservar(servicio, empresa_a) == 2


def test_no_permite_superar_nueve_digitos(db, empresas):
    empresa_id = empresas[0]

    db.add(
        SecuenciaComprobante(
            id_empresa=empresa_id,
            establecimiento="001",
            punto_emision="001",
            tipo_comprobante="01",
            ultimo_secuencial=999_999_999,
        )
    )
    db.flush()

    servicio = SecuenciaComprobanteService(db)

    with pytest.raises(ConflictError):
        _reservar(servicio, empresa_id)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("establecimiento", "1"),
        ("establecimiento", "0001"),
        ("establecimiento", "ABC"),
        ("punto_emision", "12"),
        ("punto_emision", "A01"),
        ("tipo_comprobante", "1"),
        ("tipo_comprobante", "ABC"),
    ],
)
def test_rechaza_formatos_invalidos(db, empresas, campo, valor):
    servicio = SecuenciaComprobanteService(db)
    argumentos = {
        "id_empresa": empresas[0],
        "establecimiento": "001",
        "punto_emision": "001",
        "tipo_comprobante": "01",
    }
    argumentos[campo] = valor

    with pytest.raises(UnprocessableError):
        servicio.reservar(**argumentos)


def test_rechaza_empresa_no_valida(db):
    servicio = SecuenciaComprobanteService(db)

    with pytest.raises(UnprocessableError):
        _reservar(servicio, 0)


def test_reservas_concurrentes_no_generan_secuenciales_duplicados(engine):
    with Session(engine) as session:
        empresa = Empresa(
            razon_social="Empresa concurrencia",
            ruc="0990000000003",
            correo_electronico="concurrencia@test.ec",
        )
        session.add(empresa)
        session.commit()
        empresa_id = empresa.id_empresa

    def reservar_independientemente(_):
        with Session(engine) as session:
            servicio = SecuenciaComprobanteService(session)
            secuencial = _reservar(servicio, empresa_id)
            session.commit()
            return secuencial

    with ThreadPoolExecutor(max_workers=8) as executor:
        resultados = list(executor.map(reservar_independientemente, range(8)))

    assert sorted(resultados) == list(range(1, 9))
