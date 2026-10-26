"""XML de la factura validado contra el esquema oficial del SRI (factura_V2.1.0.xsd)."""

from dataclasses import replace
from decimal import Decimal as D  # noqa: N817 (alias corto: hay muchos montos)

import pytest
from lxml import etree

from app.sri.factura_xml import (
    Comprador,
    DetalleFactura,
    FormaPago,
    Pago,
    generar_factura_xml,
    validar_factura_xml,
)
from app.sri.identificacion import TipoIdentificacion
from app.sri.totales import Linea, TarifaIva
from tests.datos_sri import CLAVE_FACTURA, FACTURA


def _texto(xml: bytes, ruta: str) -> list[str]:
    return etree.fromstring(xml).xpath(f"{ruta}/text()")


def test_factura_completa_es_valida_y_tiene_los_valores_esperados():
    generada = generar_factura_xml(FACTURA)
    xml = generada.xml

    assert validar_factura_xml(xml) == []
    assert generada.clave_acceso == CLAVE_FACTURA
    assert _texto(xml, "/factura/infoTributaria/claveAcceso") == [generada.clave_acceso]
    assert _texto(xml, "/factura/infoTributaria/secuencial") == ["000000123"]
    assert _texto(xml, "/factura/infoFactura/fechaEmision") == ["25/10/2026"]
    assert _texto(xml, "/factura/infoFactura/importeTotal") == ["24.00"]
    # Un totalImpuesto por tarifa: 15 % sobre 18.00 y 0 % sobre 3.30.
    assert _texto(xml, "//totalImpuesto/codigoPorcentaje") == ["4", "0"]
    assert _texto(xml, "//totalImpuesto/baseImponible") == ["18.00", "3.30"]
    assert _texto(xml, "//totalImpuesto/valor") == ["2.70", "0.00"]
    assert len(etree.fromstring(xml).xpath("//detalle")) == 3
    assert _texto(xml, "//campoAdicional[@nombre='Email']") == ["juan@example.com"]
    assert xml.startswith(b"<?xml version='1.0' encoding='UTF-8'?>")
    assert "Café molido".encode() in xml  # UTF-8, sin entidades


def test_consumidor_final_es_valido():
    factura = replace(FACTURA, comprador=Comprador.consumidor_final())
    xml = generar_factura_xml(factura).xml
    assert _texto(xml, "//tipoIdentificacionComprador") == ["07"]
    assert _texto(xml, "//identificacionComprador") == ["9999999999999"]


def test_varias_formas_de_pago_que_suman_el_total():
    pagos = [
        Pago(FormaPago.TARJETA_CREDITO, D("20.00")),
        Pago(FormaPago.SIN_SISTEMA_FINANCIERO, D("4.00")),
    ]
    xml = generar_factura_xml(replace(FACTURA, pagos=pagos)).xml
    assert _texto(xml, "//pago/formaPago") == ["19", "01"]


@pytest.mark.parametrize(
    ("cambios", "error"),
    [
        (
            {"comprador": Comprador(TipoIdentificacion.CEDULA, "1710000008", "X")},
            "Identificación del comprador inválida",
        ),
        ({"pagos": [Pago(FormaPago.SIN_SISTEMA_FINANCIERO, D("23.99"))]}, "pagos suman 23.99"),
        ({"pagos": []}, "al menos una forma de pago"),
        ({"detalles": []}, "al menos un detalle"),
    ],
)
def test_errores_detectados_antes_de_armar_el_xml(cambios, error):
    with pytest.raises(ValueError, match=error):
        generar_factura_xml(replace(FACTURA, **cambios))


def test_nunca_devuelve_un_xml_que_el_esquema_rechace():
    # codigoPrincipal admite máximo 25 caracteres en el esquema.
    largo = DetalleFactura("X" * 26, "Producto", Linea(D("1"), D("24.00"), TarifaIva.IVA_0))
    with pytest.raises(ValueError, match="no cumple el esquema"):
        generar_factura_xml(replace(FACTURA, detalles=[largo]))


def test_el_validador_detecta_un_xml_alterado():
    xml = generar_factura_xml(FACTURA).xml
    raiz = etree.fromstring(xml)
    clave = raiz.find("infoTributaria/claveAcceso")
    clave.getparent().remove(clave)
    errores = validar_factura_xml(etree.tostring(raiz))
    assert errores and "claveAcceso" in errores[0]


def test_el_validador_no_acepta_xml_mal_formado():
    assert validar_factura_xml(b"<factura><sin-cerrar></factura>")[0].startswith("XML mal formado")
