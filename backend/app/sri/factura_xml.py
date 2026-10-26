"""XML de la factura electrónica (esquema factura_V2.1.0.xsd del SRI), sin firmar.

`generar_factura_xml` valida la identificación del comprador, calcula los totales,
arma la clave de acceso, comprueba que los pagos sumen el total y, al final, valida
el XML contra el esquema oficial: nunca devuelve un XML que el esquema rechace.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from lxml import etree

from app.sri.clave_acceso import (
    TIPO_EMISION_NORMAL,
    Ambiente,
    TipoComprobante,
    generar_clave_acceso,
    hoy_en_ecuador,
)
from app.sri.identificacion import CONSUMIDOR_FINAL, TipoIdentificacion, validar_identificacion
from app.sri.totales import CODIGO_IMPUESTO_IVA, Linea, Totales, calcular_totales

VERSION_FACTURA = "2.1.0"
ESQUEMA = Path(__file__).parent / "xsd" / "factura_V2.1.0.xsd"
CONTRIBUYENTE_RIMPE = "CONTRIBUYENTE RÉGIMEN RIMPE"  # texto fijo exigido por el esquema
MAX_CAMPOS_ADICIONALES = 15


class FormaPago(StrEnum):
    """Tabla de formas de pago de la ficha técnica del SRI."""

    SIN_SISTEMA_FINANCIERO = "01"  # efectivo
    COMPENSACION_DEUDAS = "15"
    TARJETA_DEBITO = "16"
    DINERO_ELECTRONICO = "17"
    TARJETA_PREPAGO = "18"
    TARJETA_CREDITO = "19"
    OTROS_SISTEMA_FINANCIERO = "20"  # transferencia, cheque, etc.
    ENDOSO_TITULOS = "21"


@dataclass(frozen=True)
class Emisor:
    ruc: str
    razon_social: str
    dir_matriz: str
    nombre_comercial: str | None = None
    dir_establecimiento: str | None = None
    obligado_contabilidad: bool = False
    contribuyente_especial: str | None = None  # número de resolución, si lo es
    contribuyente_rimpe: bool = False


@dataclass(frozen=True)
class Comprador:
    tipo_identificacion: TipoIdentificacion
    identificacion: str
    razon_social: str
    direccion: str | None = None
    correo: str | None = None  # va en infoAdicional como "Email"

    @classmethod
    def consumidor_final(cls) -> "Comprador":
        return cls(TipoIdentificacion.CONSUMIDOR_FINAL, CONSUMIDOR_FINAL, "CONSUMIDOR FINAL")


@dataclass(frozen=True)
class DetalleFactura:
    codigo_principal: str
    descripcion: str
    linea: Linea
    unidad_medida: str | None = None


@dataclass(frozen=True)
class Pago:
    forma: FormaPago
    total: Decimal


@dataclass(frozen=True)
class Factura:
    emisor: Emisor
    comprador: Comprador
    establecimiento: str
    punto_emision: str
    secuencial: int
    ambiente: Ambiente
    detalles: Sequence[DetalleFactura]
    pagos: Sequence[Pago]
    fecha_emision: date | None = None  # por defecto, hoy en Ecuador
    info_adicional: dict[str, str] = field(default_factory=dict)
    codigo_numerico: str | None = None  # por defecto, al azar


@dataclass(frozen=True)
class FacturaGenerada:
    xml: bytes
    clave_acceso: str
    totales: Totales


# ---------- formato de los valores ----------
def _monto(valor: Decimal) -> str:
    return f"{valor:.2f}"


def _seis_decimales(valor: Decimal) -> str:
    return f"{valor:.6f}"


def _tarifa(valor: Decimal) -> str:
    return f"{valor.normalize():f}"


def _sub(padre: etree._Element, nombre: str, texto: str | None = None) -> etree._Element:
    elemento = etree.SubElement(padre, nombre)
    if texto is not None:
        elemento.text = texto
    return elemento


# ---------- generación ----------
def generar_factura_xml(factura: Factura) -> FacturaGenerada:
    comprador = factura.comprador
    identificacion = validar_identificacion(comprador.tipo_identificacion, comprador.identificacion)
    if not identificacion.valida:
        raise ValueError(f"Identificación del comprador inválida: {identificacion.error}")
    if not factura.detalles:
        raise ValueError("La factura debe tener al menos un detalle.")
    if not factura.pagos:
        raise ValueError("La factura debe indicar al menos una forma de pago.")

    totales = calcular_totales(d.linea for d in factura.detalles)
    suma_pagos = sum((p.total for p in factura.pagos), Decimal("0"))
    if suma_pagos != totales.importe_total:
        raise ValueError(
            f"Los pagos suman {_monto(suma_pagos)} y el total de la factura es "
            f"{_monto(totales.importe_total)}."
        )
    info_adicional = dict(factura.info_adicional)
    if comprador.correo:
        info_adicional.setdefault("Email", comprador.correo)
    if len(info_adicional) > MAX_CAMPOS_ADICIONALES:
        raise ValueError(f"Máximo {MAX_CAMPOS_ADICIONALES} campos adicionales.")

    fecha = factura.fecha_emision or hoy_en_ecuador()
    emisor = factura.emisor
    clave = generar_clave_acceso(
        ruc_emisor=emisor.ruc,
        establecimiento=factura.establecimiento,
        punto_emision=factura.punto_emision,
        secuencial=factura.secuencial,
        ambiente=factura.ambiente,
        tipo_comprobante=TipoComprobante.FACTURA,
        fecha_emision=fecha,
        codigo_numerico=factura.codigo_numerico,
    )

    # El orden de los elementos es el del esquema: cambiarlo invalida el XML.
    raiz = etree.Element("factura", id="comprobante", version=VERSION_FACTURA)

    info_tributaria = _sub(raiz, "infoTributaria")
    _sub(info_tributaria, "ambiente", str(factura.ambiente))
    _sub(info_tributaria, "tipoEmision", TIPO_EMISION_NORMAL)
    _sub(info_tributaria, "razonSocial", emisor.razon_social)
    if emisor.nombre_comercial:
        _sub(info_tributaria, "nombreComercial", emisor.nombre_comercial)
    _sub(info_tributaria, "ruc", emisor.ruc)
    _sub(info_tributaria, "claveAcceso", clave)
    _sub(info_tributaria, "codDoc", TipoComprobante.FACTURA)
    _sub(info_tributaria, "estab", factura.establecimiento)
    _sub(info_tributaria, "ptoEmi", factura.punto_emision)
    _sub(info_tributaria, "secuencial", f"{factura.secuencial:09d}")
    _sub(info_tributaria, "dirMatriz", emisor.dir_matriz)
    if emisor.contribuyente_rimpe:
        _sub(info_tributaria, "contribuyenteRimpe", CONTRIBUYENTE_RIMPE)

    info_factura = _sub(raiz, "infoFactura")
    _sub(info_factura, "fechaEmision", f"{fecha:%d/%m/%Y}")
    if emisor.dir_establecimiento:
        _sub(info_factura, "dirEstablecimiento", emisor.dir_establecimiento)
    if emisor.contribuyente_especial:
        _sub(info_factura, "contribuyenteEspecial", emisor.contribuyente_especial)
    _sub(info_factura, "obligadoContabilidad", "SI" if emisor.obligado_contabilidad else "NO")
    _sub(info_factura, "tipoIdentificacionComprador", str(comprador.tipo_identificacion))
    _sub(info_factura, "razonSocialComprador", comprador.razon_social)
    _sub(info_factura, "identificacionComprador", comprador.identificacion.strip())
    if comprador.direccion:
        _sub(info_factura, "direccionComprador", comprador.direccion)
    _sub(info_factura, "totalSinImpuestos", _monto(totales.total_sin_impuestos))
    _sub(info_factura, "totalDescuento", _monto(totales.total_descuento))
    total_con_impuestos = _sub(info_factura, "totalConImpuestos")
    for total in totales.por_tarifa:
        total_impuesto = _sub(total_con_impuestos, "totalImpuesto")
        _sub(total_impuesto, "codigo", CODIGO_IMPUESTO_IVA)
        _sub(total_impuesto, "codigoPorcentaje", total.tarifa.codigo)
        _sub(total_impuesto, "baseImponible", _monto(total.base_imponible))
        _sub(total_impuesto, "tarifa", _tarifa(total.tarifa.porcentaje))
        _sub(total_impuesto, "valor", _monto(total.valor))
    _sub(info_factura, "importeTotal", _monto(totales.importe_total))
    _sub(info_factura, "moneda", "DOLAR")
    pagos = _sub(info_factura, "pagos")
    for pago in factura.pagos:
        nodo_pago = _sub(pagos, "pago")
        _sub(nodo_pago, "formaPago", str(pago.forma))
        _sub(nodo_pago, "total", _monto(pago.total))

    detalles = _sub(raiz, "detalles")
    for detalle, calculada in zip(factura.detalles, totales.lineas, strict=True):
        linea = detalle.linea
        nodo = _sub(detalles, "detalle")
        _sub(nodo, "codigoPrincipal", detalle.codigo_principal)
        _sub(nodo, "descripcion", detalle.descripcion)
        if detalle.unidad_medida:
            _sub(nodo, "unidadMedida", detalle.unidad_medida)
        _sub(nodo, "cantidad", _seis_decimales(linea.cantidad))
        _sub(nodo, "precioUnitario", _seis_decimales(linea.precio_unitario))
        _sub(nodo, "descuento", _monto(linea.descuento))
        _sub(nodo, "precioTotalSinImpuesto", _monto(calculada.precio_total_sin_impuesto))
        impuesto = _sub(_sub(nodo, "impuestos"), "impuesto")
        _sub(impuesto, "codigo", CODIGO_IMPUESTO_IVA)
        _sub(impuesto, "codigoPorcentaje", linea.tarifa.codigo)
        _sub(impuesto, "tarifa", _tarifa(linea.tarifa.porcentaje))
        _sub(impuesto, "baseImponible", _monto(calculada.precio_total_sin_impuesto))
        _sub(impuesto, "valor", _monto(calculada.iva))

    if info_adicional:
        nodo_adicional = _sub(raiz, "infoAdicional")
        for nombre, valor in info_adicional.items():
            campo = _sub(nodo_adicional, "campoAdicional", valor)
            campo.set("nombre", nombre)

    xml = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")
    errores = validar_factura_xml(xml)
    if errores:
        raise ValueError("El XML no cumple el esquema del SRI: " + "; ".join(errores))
    return FacturaGenerada(xml=xml, clave_acceso=clave, totales=totales)


# ---------- validación ----------
@lru_cache
def _esquema() -> etree.XMLSchema:
    # no_network: el esquema (y el reemplazo de xmldsig) se leen solo del disco.
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    return etree.XMLSchema(etree.parse(str(ESQUEMA), parser))


def validar_factura_xml(xml: bytes) -> list[str]:
    """Errores del XML contra factura_V2.1.0.xsd; lista vacía si es válido."""
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    try:
        documento = etree.fromstring(xml, parser)
    except etree.XMLSyntaxError as exc:
        return [f"XML mal formado: {exc}"]
    esquema = _esquema()
    if esquema.validate(documento):
        return []
    return [f"línea {e.line}: {e.message}" for e in esquema.error_log]
