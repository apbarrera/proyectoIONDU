"""Totales e IVA de la factura. Los valores esperados están calculados a mano."""

from decimal import Decimal as D  # noqa: N817 (alias corto: hay decenas de montos)

import pytest

from app.sri.totales import Linea, TarifaIva, calcular_totales


def test_factura_con_varias_tarifas_y_descuento():
    totales = calcular_totales(
        [
            Linea(D("2"), D("4.50"), TarifaIva.IVA_15),  # 9.00 -> IVA 1.35
            Linea(D("3"), D("1.10"), TarifaIva.IVA_0),  # 3.30 -> IVA 0
            Linea(D("1"), D("10.00"), TarifaIva.IVA_15, descuento=D("1.00")),  # 9.00 -> IVA 1.35
        ]
    )
    assert [c.precio_total_sin_impuesto for c in totales.lineas] == [
        D("9.00"),
        D("3.30"),
        D("9.00"),
    ]
    assert [c.iva for c in totales.lineas] == [D("1.35"), D("0.00"), D("1.35")]
    # Bases por tarifa, en el orden del SRI: 15% = 9 + 9 = 18.00 (IVA 2.70); 0% = 3.30.
    assert [(t.tarifa, t.base_imponible, t.valor) for t in totales.por_tarifa] == [
        (TarifaIva.IVA_15, D("18.00"), D("2.70")),
        (TarifaIva.IVA_0, D("3.30"), D("0.00")),
    ]
    assert totales.total_sin_impuestos == D("21.30")
    assert totales.total_descuento == D("1.00")
    assert totales.total_iva == D("2.70")
    assert totales.importe_total == D("24.00")


def test_redondeo_comercial_hacia_arriba_desde_5():
    # 3 x 0.555 = 1.665 -> 1.67 (el redondeo por defecto de Decimal daría 1.66).
    # IVA: 1.67 x 15% = 0.2505 -> 0.25.
    totales = calcular_totales([Linea(D("3"), D("0.555"), TarifaIva.IVA_15)])
    assert totales.lineas[0].precio_total_sin_impuesto == D("1.67")
    assert totales.total_iva == D("0.25")
    assert totales.importe_total == D("1.92")


def test_el_iva_total_se_calcula_sobre_la_base_y_no_sumando_lineas():
    # Cada línea: 0.10 x 15% = 0.015 -> 0.02; sumando líneas serían 0.06.
    # Sobre la base: 0.30 x 15% = 0.045 -> 0.05, que es el IVA correcto.
    totales = calcular_totales([Linea(D("1"), D("0.10"), TarifaIva.IVA_15)] * 3)
    assert sum(c.iva for c in totales.lineas) == D("0.06")
    assert totales.total_iva == D("0.05")
    assert totales.importe_total == D("0.35")


def test_tarifa_de_5_por_ciento():
    totales = calcular_totales([Linea(D("10"), D("2.00"), TarifaIva.IVA_5)])  # 20.00 -> 1.00
    assert (totales.por_tarifa[0].tarifa.codigo, totales.total_iva) == ("5", D("1.00"))


def test_codigos_de_tarifa_del_sri():
    assert {t.name: (t.codigo, t.porcentaje) for t in TarifaIva} == {
        "IVA_15": ("4", D("15")),
        "IVA_5": ("5", D("5")),
        "IVA_0": ("0", D("0")),
        "NO_OBJETO": ("6", D("0")),
        "EXENTO": ("7", D("0")),
    }


@pytest.mark.parametrize(
    ("crear", "error"),
    [
        (lambda: Linea(D("0"), D("1"), TarifaIva.IVA_15), "cantidad debe ser mayor"),
        (lambda: Linea(D("1"), D("-1"), TarifaIva.IVA_15), "no pueden ser negativos"),
        (lambda: Linea(D("1"), D("5"), TarifaIva.IVA_15, descuento=D("6")), "descuento no puede"),
        (lambda: Linea(D("1"), D("1.1234567"), TarifaIva.IVA_15), "6 decimales"),
    ],
)
def test_lineas_invalidas(crear, error):
    with pytest.raises(ValueError, match=error):
        crear()


def test_no_acepta_float():
    with pytest.raises(TypeError, match="Decimal"):
        Linea(1.5, D("1"), TarifaIva.IVA_15)


def test_factura_sin_lineas():
    with pytest.raises(ValueError, match="al menos una línea"):
        calcular_totales([])
