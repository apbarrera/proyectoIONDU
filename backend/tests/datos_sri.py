"""Factura de ejemplo para las pruebas del SRI (XML y RIDE).

Totales calculados a mano: 15 % sobre 18.00 (IVA 2.70) + 0 % sobre 3.30 = 24.00.
"""

from datetime import date
from decimal import Decimal as D  # noqa: N817 (alias corto: hay muchos montos)

from app.sri.clave_acceso import Ambiente
from app.sri.factura_xml import Comprador, DetalleFactura, Emisor, Factura, FormaPago, Pago
from app.sri.identificacion import TipoIdentificacion
from app.sri.totales import Linea, TarifaIva

CLAVE_FACTURA = "2510202601179001093700110010010000001231234567816"

EMISOR = Emisor(
    ruc="1790010937001",
    razon_social="CAFETERÍA DEMO S.A.",
    dir_matriz="Av. Amazonas N12-34, Quito",
    nombre_comercial="Café Demo",
    contribuyente_rimpe=True,
)
DETALLES = [
    DetalleFactura("CAF-250", "Café molido 250 g", Linea(D("2"), D("4.50"), TarifaIva.IVA_15)),
    DetalleFactura("AZU-1K", "Azúcar 1 kg", Linea(D("3"), D("1.10"), TarifaIva.IVA_0)),
    DetalleFactura(
        "SRV-01",
        "Servicio de entrega",
        Linea(D("1"), D("10.00"), TarifaIva.IVA_15, descuento=D("1.00")),
    ),
]
FACTURA = Factura(
    emisor=EMISOR,
    comprador=Comprador(
        TipoIdentificacion.CEDULA, "1710000009", "Juan Pérez", correo="juan@example.com"
    ),
    establecimiento="001",
    punto_emision="001",
    secuencial=123,
    ambiente=Ambiente.PRUEBAS,
    detalles=DETALLES,
    pagos=[Pago(FormaPago.SIN_SISTEMA_FINANCIERO, D("24.00"))],
    fecha_emision=date(2026, 10, 25),
    codigo_numerico="12345678",
)
