"""SRI simulado: demostración sin .p12, nunca en producción."""

from dataclasses import replace
from datetime import datetime
from io import BytesIO

import pytest
import xmlsig
from lxml import etree
from pypdf import PdfReader

from app.core.config import Settings
from app.sri.clave_acceso import Ambiente
from app.sri.emision import EstadoEmision, ServicioEmision
from app.sri.factura_xml import generar_factura_xml, validar_factura_xml
from app.sri.ride import AVISO_SIMULADO, generar_ride
from app.sri.simulado import (
    IDENTIFICADOR_SIMULADO,
    ClienteSriSimulado,
    _certificado_de_prueba,
    es_autorizacion_simulada,
    firmador_de_prueba,
    usa_sri_simulado,
)
from app.sri.xades import DS
from tests.datos_sri import FACTURA


def _texto(pdf: bytes) -> str:
    return "\n".join(pagina.extract_text() for pagina in PdfReader(BytesIO(pdf)).pages)


@pytest.mark.parametrize(
    ("empresa", "ambiente", "lista", "esperado"),
    [
        (1, "1", {1}, True),
        (1, Ambiente.PRUEBAS, {1, 3}, True),
        (2, "1", {1}, False),  # otra empresa: SRI real
        (1, "2", {1}, False),  # producción: nunca se simula
        (1, Ambiente.PRODUCCION, {1}, False),
        (1, "1", set(), False),  # sin la variable: SRI real
    ],
)
def test_solo_se_simula_en_pruebas_y_para_las_empresas_indicadas(
    empresa, ambiente, lista, esperado
):
    assert usa_sri_simulado(empresa, ambiente, lista) is esperado


def test_la_variable_se_lee_separada_por_comas():
    assert Settings(sri_simulado_empresas="1, 4").sri_simulado_empresas == {1, 4}
    assert Settings(sri_simulado_empresas="").sri_simulado_empresas == frozenset()


def test_la_firma_de_prueba_es_xades_valida_y_cumple_el_esquema():
    firmado = firmador_de_prueba().firmar(generar_factura_xml(FACTURA).xml)

    contexto = xmlsig.SignatureContext()
    contexto.public_key = _certificado_de_prueba().certificado.public_key()
    contexto.verify(etree.fromstring(firmado).find(f"{{{DS}}}Signature"))
    assert validar_factura_xml(firmado) == []


def test_el_flujo_completo_queda_autorizado_y_marcado_como_simulado():
    generada = generar_factura_xml(FACTURA)
    with ClienteSriSimulado(Ambiente.PRUEBAS) as cliente:
        servicio = ServicioEmision(cliente, firmador_de_prueba(), dormir=lambda _: None)
        resultado = servicio.emitir(FACTURA)

    assert resultado.estado == EstadoEmision.AUTORIZADA
    assert resultado.numero_autorizacion == generada.clave_acceso
    assert resultado.fecha_autorizacion is not None
    assert resultado.xml_autorizado == resultado.xml_firmado
    assert [m.identificador for m in resultado.mensajes] == [IDENTIFICADOR_SIMULADO]


def test_nunca_autoriza_comprobantes_de_produccion():
    with pytest.raises(ValueError, match="ambiente de pruebas"):
        ClienteSriSimulado(Ambiente.PRODUCCION)

    produccion = generar_factura_xml(replace(FACTURA, ambiente=Ambiente.PRODUCCION)).xml
    with pytest.raises(ValueError, match="ambiente de pruebas"):
        ClienteSriSimulado(Ambiente.PRUEBAS).enviar(produccion)


def test_la_marca_se_reconoce_en_los_mensajes_guardados():
    assert es_autorizacion_simulada([{"identificador": "SIMULADO", "mensaje": "..."}])
    assert not es_autorizacion_simulada([{"identificador": "43", "mensaje": "..."}])
    assert not es_autorizacion_simulada(None)


def test_el_ride_simulado_lleva_el_aviso_y_el_real_no():
    xml = generar_factura_xml(FACTURA).xml
    fecha = datetime(2026, 11, 26, 9, 0, 0)
    simulado = _texto(generar_ride(xml, fecha_autorizacion=fecha, simulado=True))
    real = _texto(generar_ride(xml, fecha_autorizacion=fecha))

    assert "SIN VALIDEZ TRIBUTARIA" in simulado
    assert AVISO_SIMULADO.split(".")[0] in " ".join(simulado.split())
    assert "SIN VALIDEZ TRIBUTARIA" not in real
