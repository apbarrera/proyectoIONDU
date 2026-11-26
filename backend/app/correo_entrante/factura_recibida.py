"""Lectura de la factura electrónica (XML del SRI) que un proveedor envía por correo.

Acepta el XML del comprobante (<factura>) o el de autorización que lo envuelve
(<autorizacion><comprobante><![CDATA[...]]>). Solo facturas (codDoc 01) dirigidas a
la empresa: el RUC (o la cédula) del comprador debe ser el de la empresa.
El XML viene de afuera: se lee sin red, sin entidades y con tamaño limitado.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from lxml import etree

TAMANO_MAXIMO = 1_000_000  # 1 MB por adjunto
_PARSER = etree.XMLParser(
    no_network=True, resolve_entities=False, huge_tree=False, remove_comments=True
)
CODIGO_IVA = "2"  # <codigo> del impuesto IVA en totalConImpuestos


@dataclass(frozen=True)
class FacturaRecibida:
    clave_acceso: str
    proveedor_ruc: str
    proveedor_nombre: str
    numero: str  # 001-001-000000123
    fecha_emision: date
    comprador_identificacion: str
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    detalle: list[dict] = field(default_factory=list)


def _decimal(texto: str | None) -> Decimal:
    try:
        return Decimal((texto or "0").strip()).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def _raiz_factura(contenido: bytes) -> etree._Element | None:
    if len(contenido) > TAMANO_MAXIMO:
        return None
    try:
        raiz = etree.fromstring(contenido, _PARSER)
    except etree.XMLSyntaxError:
        return None
    if raiz.tag == "autorizacion" or raiz.find("comprobante") is not None:
        if (raiz.findtext("estado") or "AUTORIZADO").strip().upper() != "AUTORIZADO":
            return None
        interno = (raiz.findtext("comprobante") or "").strip()
        if not interno:
            return None
        try:
            raiz = etree.fromstring(interno.encode("utf-8"), _PARSER)
        except etree.XMLSyntaxError:
            return None
    return raiz if raiz.tag == "factura" else None


def leer_factura(contenido: bytes) -> FacturaRecibida | None:
    """None si no es una factura del SRI válida (otro documento, XML dañado, etc.)."""
    raiz = _raiz_factura(contenido)
    if raiz is None or (raiz.findtext("infoTributaria/codDoc") or "").strip() != "01":
        return None
    t = raiz.findtext
    clave = (t("infoTributaria/claveAcceso") or "").strip()
    ruc = (t("infoTributaria/ruc") or "").strip()
    try:
        fecha = datetime.strptime((t("infoFactura/fechaEmision") or "").strip(), "%d/%m/%Y")
    except ValueError:
        return None
    if len(clave) != 49 or not clave.isdigit() or len(ruc) != 13 or not ruc.isdigit():
        return None

    iva = sum(
        (
            _decimal(imp.findtext("valor"))
            for imp in raiz.iterfind("infoFactura/totalConImpuestos/totalImpuesto")
            if (imp.findtext("codigo") or "").strip() == CODIGO_IVA
        ),
        Decimal("0.00"),
    )
    detalle = [
        {
            "descripcion": (d.findtext("descripcion") or "").strip()[:300],
            "cantidad": str(_decimal(d.findtext("cantidad"))),
            "total": str(_decimal(d.findtext("precioTotalSinImpuesto"))),
        }
        for d in list(raiz.iterfind("detalles/detalle"))[:50]
    ]
    return FacturaRecibida(
        clave_acceso=clave,
        proveedor_ruc=ruc,
        proveedor_nombre=(t("infoTributaria/razonSocial") or "").strip()[:300],
        numero=f"{t('infoTributaria/estab')}-{t('infoTributaria/ptoEmi')}-"
        f"{t('infoTributaria/secuencial')}",
        fecha_emision=fecha.date(),
        comprador_identificacion=(t("infoFactura/identificacionComprador") or "").strip(),
        subtotal=_decimal(t("infoFactura/totalSinImpuestos")),
        iva=iva,
        total=_decimal(t("infoFactura/importeTotal")),
        detalle=detalle,
    )


def es_para_la_empresa(factura: FacturaRecibida, ruc_empresa: str) -> bool:
    """El comprador es la empresa: su RUC, o la cédula de una persona natural (10 dígitos)."""
    comprador = factura.comprador_identificacion
    return comprador == ruc_empresa or (len(comprador) == 10 and ruc_empresa.startswith(comprador))
