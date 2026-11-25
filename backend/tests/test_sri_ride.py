"""RIDE (PDF) de la factura: se lee el texto del PDF y se comprueba su contenido."""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal as D  # noqa: N817 (alias corto: hay muchos montos)
from io import BytesIO

from pypdf import PdfReader

from app.sri.factura_xml import Comprador, DetalleFactura, Pago, generar_factura_xml
from app.sri.identificacion import TipoIdentificacion
from app.sri.ride import generar_ride
from app.sri.totales import Linea, TarifaIva
from tests.datos_sri import CLAVE_FACTURA as CLAVE
from tests.datos_sri import FACTURA


def _texto(pdf: bytes) -> str:
    return "\n".join(pagina.extract_text() for pagina in PdfReader(BytesIO(pdf)).pages)


def test_ride_pendiente_muestra_los_datos_de_la_factura():
    pdf = generar_ride(generar_factura_xml(FACTURA).xml)
    assert pdf.startswith(b"%PDF")
    texto = _texto(pdf)
    for esperado in (
        "CAFETERÍA DEMO S.A.",
        "R.U.C.: 1790010937001",
        "FACTURA",
        "001-001-000000123",
        "PENDIENTE DE AUTORIZACIÓN",
        "PRUEBAS",
        CLAVE,
        "Juan Pérez",
        "1710000009",
        "25/10/2026",
        "Café molido 250 g",
        "4.50",
        "SUBTOTAL 15%",
        "18.00",
        "SUBTOTAL 0%",
        "3.30",
        "IVA 15%",
        "2.70",
        "VALOR TOTAL",
        "24.00",
        "SIN UTILIZACIÓN DEL SISTEMA FINANCIERO",
        "juan@example.com",
    ):
        assert esperado in texto, f"falta «{esperado}» en el RIDE"


def test_ride_autorizado_muestra_el_numero_y_la_fecha_de_autorizacion():
    xml = generar_factura_xml(FACTURA).xml
    texto = _texto(generar_ride(xml, fecha_autorizacion=datetime(2026, 10, 25, 14, 30, 5)))
    assert "PENDIENTE" not in texto
    assert "25/10/2026 14:30:05" in texto
    assert texto.count(CLAVE) == 2  # número de autorización y clave de acceso


def test_los_datos_del_usuario_se_muestran_tal_cual_sin_interpretarse():
    comprador = Comprador(TipoIdentificacion.RUC, "1790016919001", "Pérez & Hijos <S.A.>")
    texto = _texto(generar_ride(generar_factura_xml(replace(FACTURA, comprador=comprador)).xml))
    assert "Pérez & Hijos <S.A.>" in texto


def test_una_factura_larga_ocupa_varias_paginas():
    detalles = [
        DetalleFactura(f"P-{i:03d}", f"Producto {i}", Linea(D("1"), D("1.00"), TarifaIva.IVA_0))
        for i in range(80)
    ]
    factura = replace(FACTURA, detalles=detalles, pagos=[Pago(FACTURA.pagos[0].forma, D("80.00"))])
    pdf = generar_ride(generar_factura_xml(factura).xml)
    assert len(PdfReader(BytesIO(pdf)).pages) > 1
    assert "Producto 79" in _texto(pdf)
