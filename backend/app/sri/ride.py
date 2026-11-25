"""RIDE (Representación Impresa del Documento Electrónico) de la factura, en PDF.

Se arma LEYENDO EL XML de la factura, no desde los datos originales: así el PDF
muestra exactamente lo que se envió al SRI. Devuelve los bytes del PDF (los
contenedores no guardan archivos; se almacenará en Supabase Storage).
"""

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from lxml import etree
from reportlab.graphics.barcode.code128 import Code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.sri.factura_xml import FormaPago

_FORMAS_PAGO = {
    FormaPago.SIN_SISTEMA_FINANCIERO: "SIN UTILIZACIÓN DEL SISTEMA FINANCIERO",
    FormaPago.COMPENSACION_DEUDAS: "COMPENSACIÓN DE DEUDAS",
    FormaPago.TARJETA_DEBITO: "TARJETA DE DÉBITO",
    FormaPago.DINERO_ELECTRONICO: "DINERO ELECTRÓNICO",
    FormaPago.TARJETA_PREPAGO: "TARJETA PREPAGO",
    FormaPago.TARJETA_CREDITO: "TARJETA DE CRÉDITO",
    FormaPago.OTROS_SISTEMA_FINANCIERO: "OTROS CON UTILIZACIÓN DEL SISTEMA FINANCIERO",
    FormaPago.ENDOSO_TITULOS: "ENDOSO DE TÍTULOS",
}
# codigoPorcentaje del IVA -> texto del subtotal en el RIDE (orden de presentación).
_SUBTOTALES = {"4": "SUBTOTAL 15%", "5": "SUBTOTAL 5%", "0": "SUBTOTAL 0%",
               "6": "SUBTOTAL NO OBJETO DE IVA", "7": "SUBTOTAL EXENTO DE IVA"}  # fmt: skip

_GRIS = colors.HexColor("#555555")
_BORDE = colors.HexColor("#999999")
_NORMAL = ParagraphStyle("normal", fontName="Helvetica", fontSize=8, leading=10)
_NEGRITA = ParagraphStyle("negrita", parent=_NORMAL, fontName="Helvetica-Bold")
_TITULO = ParagraphStyle("titulo", parent=_NEGRITA, fontSize=12, leading=15)
_PEQUENA = ParagraphStyle("pequena", parent=_NORMAL, fontSize=7, leading=9, textColor=_GRIS)


def _p(texto: str | None, estilo: ParagraphStyle = _NORMAL) -> Paragraph:
    # escape(): los datos vienen del usuario y Paragraph interpreta etiquetas tipo HTML.
    return Paragraph(escape(texto or ""), estilo)


def _etiqueta(nombre: str, valor: str | None) -> Paragraph:
    return Paragraph(f"<b>{escape(nombre)}:</b> {escape(valor or '')}", _NORMAL)


def _monto(texto: str | None) -> str:
    return f"{Decimal(texto or '0'):,.2f}"


def _cantidad(texto: str) -> str:
    """Cantidad sin ceros sobrantes: 2.000000 -> 2; 1.500000 -> 1.5."""
    valor = Decimal(texto).normalize()
    return f"{valor:f}"


def _precio(texto: str) -> str:
    """Precio con al menos 2 decimales y hasta 6: 4.500000 -> 4.50; 0.555000 -> 0.555."""
    valor = Decimal(texto).normalize()
    return f"{valor:.2f}" if -valor.as_tuple().exponent < 2 else f"{valor:f}"


def generar_ride(
    xml: bytes,
    *,
    numero_autorizacion: str | None = None,
    fecha_autorizacion: datetime | None = None,
) -> bytes:
    """PDF del RIDE a partir del XML de la factura. Sin autorización, lo indica en el documento."""
    raiz = etree.fromstring(xml, etree.XMLParser(no_network=True, resolve_entities=False))

    def t(ruta: str) -> str | None:
        return raiz.findtext(ruta)

    clave = t("infoTributaria/claveAcceso") or ""
    numero = (
        f"{t('infoTributaria/estab')}-{t('infoTributaria/ptoEmi')}-{t('infoTributaria/secuencial')}"
    )
    ambiente = "PRODUCCIÓN" if t("infoTributaria/ambiente") == "2" else "PRUEBAS"
    if fecha_autorizacion:
        autorizacion = numero_autorizacion or clave
        fecha_aut = fecha_autorizacion.strftime("%d/%m/%Y %H:%M:%S")
    else:
        autorizacion, fecha_aut = "PENDIENTE DE AUTORIZACIÓN", "—"

    ancho = A4[0] - 2.4 * cm
    historia = []

    # ---------- cabecera: emisor | comprobante ----------
    emisor = [
        _p(t("infoTributaria/razonSocial"), _TITULO),
        _p(t("infoTributaria/nombreComercial"), _NEGRITA),
        Spacer(1, 4),
        _etiqueta("Dirección matriz", t("infoTributaria/dirMatriz")),
    ]
    if t("infoFactura/dirEstablecimiento"):
        emisor.append(_etiqueta("Dirección establecimiento", t("infoFactura/dirEstablecimiento")))
    if t("infoFactura/contribuyenteEspecial"):
        emisor.append(
            _etiqueta("Contribuyente especial Nro.", t("infoFactura/contribuyenteEspecial"))
        )
    emisor.append(
        _etiqueta("Obligado a llevar contabilidad", t("infoFactura/obligadoContabilidad"))
    )
    if t("infoTributaria/contribuyenteRimpe"):
        emisor.append(_p(t("infoTributaria/contribuyenteRimpe"), _NEGRITA))

    comprobante = [
        _p(f"R.U.C.: {t('infoTributaria/ruc')}", _TITULO),
        _p("FACTURA", _TITULO),
        _etiqueta("No.", numero),
        _etiqueta("Número de autorización", autorizacion),
        _etiqueta("Fecha y hora de autorización", fecha_aut),
        _etiqueta("Ambiente", ambiente),
        _etiqueta("Emisión", "NORMAL"),
        _p("CLAVE DE ACCESO", _NEGRITA),
        Code128(clave, barHeight=1.1 * cm, barWidth=0.72, humanReadable=False),
        _p(clave, _PEQUENA),
    ]
    cabecera = Table([[emisor, comprobante]], colWidths=[ancho * 0.48, ancho * 0.52])
    cabecera.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.6, _BORDE),
                ("BOX", (1, 0), (1, 0), 0.6, _BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    historia += [cabecera, Spacer(1, 6)]

    # ---------- comprador ----------
    comprador = Table(
        [
            [
                _etiqueta("Razón social / Nombres", t("infoFactura/razonSocialComprador")),
                _etiqueta("Identificación", t("infoFactura/identificacionComprador")),
            ],
            [
                _etiqueta("Fecha de emisión", t("infoFactura/fechaEmision")),
                _etiqueta("Dirección", t("infoFactura/direccionComprador")),
            ],
        ],
        colWidths=[ancho * 0.6, ancho * 0.4],
    )
    comprador.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, _BORDE)]))
    historia += [comprador, Spacer(1, 6)]

    # ---------- detalle ----------
    filas = [["Código", "Cant.", "Descripción", "P. unitario", "Descuento", "Total"]]
    for d in raiz.iterfind("detalles/detalle"):
        filas.append(
            [
                _p(d.findtext("codigoPrincipal")),
                _cantidad(d.findtext("cantidad")),
                _p(d.findtext("descripcion")),
                _precio(d.findtext("precioUnitario")),
                _monto(d.findtext("descuento")),
                _monto(d.findtext("precioTotalSinImpuesto")),
            ]
        )
    detalle = Table(
        filas,
        colWidths=[ancho * f for f in (0.14, 0.08, 0.42, 0.12, 0.11, 0.13)],
        repeatRows=1,
    )
    detalle.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                ("GRID", (0, 0), (-1, -1), 0.4, _BORDE),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    historia += [detalle, Spacer(1, 6)]

    # ---------- información adicional y pagos | totales ----------
    adicional = [_p("Información adicional", _NEGRITA)]
    for campo in raiz.iterfind("infoAdicional/campoAdicional"):
        adicional.append(_etiqueta(campo.get("nombre"), campo.text))
    adicional += [Spacer(1, 6), _p("Forma de pago", _NEGRITA)]
    for pago in raiz.iterfind("infoFactura/pagos/pago"):
        forma = pago.findtext("formaPago")
        nombre = _FORMAS_PAGO.get(forma, forma)
        adicional.append(_p(f"{forma} - {nombre}: {_monto(pago.findtext('total'))}"))

    bases = {
        ti.findtext("codigoPorcentaje"): ti
        for ti in raiz.iterfind("infoFactura/totalConImpuestos/totalImpuesto")
        if ti.findtext("codigo") == "2"
    }
    totales = [
        [texto, _monto(bases[codigo].findtext("baseImponible"))]
        for codigo, texto in _SUBTOTALES.items()
        if codigo in bases
    ]
    totales += [
        ["SUBTOTAL SIN IMPUESTOS", _monto(t("infoFactura/totalSinImpuestos"))],
        ["TOTAL DESCUENTO", _monto(t("infoFactura/totalDescuento"))],
    ]
    for codigo, porcentaje in (("4", "15"), ("5", "5")):
        if codigo in bases:
            totales.append([f"IVA {porcentaje}%", _monto(bases[codigo].findtext("valor"))])
    totales.append(["VALOR TOTAL", _monto(t("infoFactura/importeTotal"))])

    tabla_totales = Table(totales, colWidths=[ancho * 0.26, ancho * 0.14])
    tabla_totales.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
                ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
                ("GRID", (0, 0), (-1, -1), 0.4, _BORDE),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    pie = Table([[adicional, tabla_totales]], colWidths=[ancho * 0.58, ancho * 0.42])
    pie.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (0, 0), 0.6, _BORDE),
                ("LEFTPADDING", (0, 0), (0, 0), 6),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    historia.append(pie)

    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=A4,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title=f"Factura {numero}",
        author=t("infoTributaria/razonSocial") or "",
    )
    documento.build(historia)
    return salida.getvalue()
