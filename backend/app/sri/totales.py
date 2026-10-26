"""Totales e IVA de una factura según el SRI.

Reglas (ver docs/DECISIONES.md, 2.18):
- Todo con Decimal (nunca float) y redondeo comercial ROUND_HALF_UP a 2 decimales:
  2.665 -> 2.67 (el redondeo por defecto de Decimal daría 2.66).
- Por línea: subtotal = cantidad x precio unitario - descuento, redondeado.
- El IVA se calcula sobre la suma de las bases de cada tarifa (no sumando el IVA
  redondeado de cada línea, que acumula diferencias de centavos).
- Pendiente de confirmar en el ambiente de pruebas del SRI: la tolerancia con que
  compara el IVA de cada línea contra el total.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

CENTAVO = Decimal("0.01")
CODIGO_IMPUESTO_IVA = "2"  # código del impuesto IVA en el XML del SRI


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


class TarifaIva(Enum):
    """Código de porcentaje del SRI y tarifa en %."""

    IVA_15 = ("4", Decimal("15"))
    IVA_5 = ("5", Decimal("5"))
    IVA_0 = ("0", Decimal("0"))
    NO_OBJETO = ("6", Decimal("0"))
    EXENTO = ("7", Decimal("0"))

    def __init__(self, codigo: str, porcentaje: Decimal):
        self.codigo = codigo
        self.porcentaje = porcentaje


@dataclass(frozen=True)
class Linea:
    """Una línea de la factura tal como la ingresa el usuario."""

    cantidad: Decimal
    precio_unitario: Decimal
    tarifa: TarifaIva
    descuento: Decimal = Decimal("0")

    def __post_init__(self):
        for nombre in ("cantidad", "precio_unitario", "descuento"):
            if not isinstance(getattr(self, nombre), Decimal):
                raise TypeError(
                    f"{nombre} debe ser Decimal, no {type(getattr(self, nombre)).__name__}"
                )
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que 0.")
        if self.precio_unitario < 0 or self.descuento < 0:
            raise ValueError("El precio y el descuento no pueden ser negativos.")
        # La ficha técnica admite hasta 6 decimales en cantidad y precio unitario.
        for nombre in ("cantidad", "precio_unitario"):
            if -getattr(self, nombre).normalize().as_tuple().exponent > 6:
                raise ValueError(f"{nombre} admite como máximo 6 decimales.")
        if self.descuento > self.cantidad * self.precio_unitario:
            raise ValueError("El descuento no puede ser mayor que el valor de la línea.")


@dataclass(frozen=True)
class LineaCalculada:
    linea: Linea
    precio_total_sin_impuesto: Decimal  # base imponible de la línea
    iva: Decimal  # IVA de la línea (informativo en el detalle del XML)


@dataclass(frozen=True)
class TotalPorTarifa:
    tarifa: TarifaIva
    base_imponible: Decimal
    valor: Decimal


@dataclass(frozen=True)
class Totales:
    lineas: list[LineaCalculada]
    total_sin_impuestos: Decimal
    total_descuento: Decimal
    por_tarifa: list[TotalPorTarifa]  # en el orden de TarifaIva, solo las que aparecen
    total_iva: Decimal
    importe_total: Decimal


def calcular_totales(lineas: Iterable[Linea]) -> Totales:
    lineas = list(lineas)
    if not lineas:
        raise ValueError("La factura debe tener al menos una línea.")

    calculadas = []
    bases: dict[TarifaIva, Decimal] = {}
    for linea in lineas:
        base = redondear(linea.cantidad * linea.precio_unitario - linea.descuento)
        iva = redondear(base * linea.tarifa.porcentaje / 100)
        calculadas.append(LineaCalculada(linea, base, iva))
        bases[linea.tarifa] = bases.get(linea.tarifa, Decimal("0")) + base

    por_tarifa = [
        TotalPorTarifa(tarifa, bases[tarifa], redondear(bases[tarifa] * tarifa.porcentaje / 100))
        for tarifa in TarifaIva
        if tarifa in bases
    ]
    total_sin_impuestos = sum((c.precio_total_sin_impuesto for c in calculadas), Decimal("0"))
    total_iva = sum((t.valor for t in por_tarifa), Decimal("0"))
    return Totales(
        lineas=calculadas,
        total_sin_impuestos=total_sin_impuestos,
        total_descuento=redondear(sum((linea.descuento for linea in lineas), Decimal("0"))),
        por_tarifa=por_tarifa,
        total_iva=total_iva,
        importe_total=total_sin_impuestos + total_iva,
    )
