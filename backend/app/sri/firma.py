"""Firma electrónica de los comprobantes (pieza intercambiable).

El flujo de emisión solo necesita algo con `firmar(xml) -> xml firmado`:
- `FirmadorXadesBes` (app/sri/xades.py): la firma real que exige el SRI, con el
  certificado .p12 de la empresa descifrado solo en memoria.
- `FirmadorSinFirma`: NO firma; solo para pruebas del flujo.
"""

from typing import Protocol

from lxml import etree

from app.sri.clave_acceso import Ambiente


class Firmador(Protocol):
    def firmar(self, xml: bytes) -> bytes:
        """Devuelve el comprobante firmado. Lanza una excepción si no puede firmarlo."""
        ...


class FirmadorSinFirma:
    """SOLO PARA PRUEBAS: devuelve el XML sin firmar.

    Se niega a procesar comprobantes del ambiente de producción, para que nunca se
    use por error con facturas reales.
    """

    def firmar(self, xml: bytes) -> bytes:
        parser = etree.XMLParser(no_network=True, resolve_entities=False)
        ambiente = etree.fromstring(xml, parser).findtext("infoTributaria/ambiente")
        if ambiente != Ambiente.PRUEBAS:
            raise RuntimeError("FirmadorSinFirma solo acepta comprobantes del ambiente de pruebas.")
        return xml
