"""Pruebas unitarias de la orquestación de facturas sin PostgreSQL."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models.empresa import Empresa
from app.services.factura import FacturaService
from app.sri.firma import FirmadorSinFirma


class FakeSession:
    def __init__(self, resultados):
        self.resultados = iter(resultados)
        self.rollbacks = 0
        self.commits = 0
        self.ejecutadas = []

    def execute(self, consulta):
        self.ejecutadas.append(consulta)

    def scalar(self, consulta):
        return next(self.resultados)

    def rollback(self):
        self.rollbacks += 1

    def commit(self):
        self.commits += 1


def _servicio(monkeypatch, resultados):
    session = FakeSession(resultados)
    servicio = FacturaService(cast(Session, session), empresa_id=1)

    reservas = []
    monkeypatch.setattr(
        servicio.secuencias,
        "reservar",
        lambda **kwargs: reservas.append(kwargs) or 1,
    )

    return servicio, session, reservas


def test_venta_inexistente_no_emite_factura(monkeypatch):
    servicio, session, reservas = _servicio(monkeypatch, [None])

    with pytest.raises(NotFoundError):
        servicio.emitir(999)

    assert session.rollbacks == 1
    assert session.commits == 0
    assert reservas == []
    assert len(session.ejecutadas) == 1


def test_venta_ya_facturada_no_reserva_otro_secuencial(monkeypatch):
    venta = SimpleNamespace(
        id_venta=101,
        id_empresa=1,
        estado="COMPLETADA",
    )
    factura_existente = SimpleNamespace(id_factura=50, estado_autorizacion="autorizada")

    servicio, session, reservas = _servicio(
        monkeypatch,
        [venta, factura_existente],
    )

    with pytest.raises(ConflictError):
        servicio.emitir(101)

    assert session.rollbacks == 1
    assert session.commits == 0
    assert reservas == []
    assert len(session.ejecutadas) == 1


def test_venta_anulada_no_emite_factura(monkeypatch):
    venta = SimpleNamespace(
        id_venta=101,
        id_empresa=1,
        estado="ANULADA",
    )

    servicio, session, reservas = _servicio(monkeypatch, [venta, None])

    with pytest.raises(ConflictError, match="ventas completadas"):
        servicio.emitir(101)

    assert session.rollbacks == 1
    assert session.commits == 0
    assert reservas == []
    assert len(session.ejecutadas) == 1


def test_empresa_sin_configuracion_tributaria_no_puede_facturar(monkeypatch):
    servicio, _, _ = _servicio(monkeypatch, [])
    empresa = SimpleNamespace(datos_facturacion_electronica=None)

    with pytest.raises(UnprocessableError, match="configurada su facturación electrónica"):
        servicio._obtener_configuracion(cast(Empresa, empresa))


def test_configuracion_tributaria_incompleta_no_puede_facturar(monkeypatch):
    servicio, _, _ = _servicio(monkeypatch, [])
    empresa = SimpleNamespace(
        datos_facturacion_electronica={
            "ambiente": "1",
            "establecimiento": "01",
            "punto_emision": "001",
        },
        ruc="1790012345001",
        razon_social="Empresa de prueba",
        direccion="Quito",
    )

    with pytest.raises(UnprocessableError, match="incompleta o es inválida"):
        servicio._obtener_configuracion(cast(Empresa, empresa))


def test_empresa_sin_certificado_no_puede_facturar(monkeypatch):
    servicio, _, _ = _servicio(monkeypatch, [])
    empresa = SimpleNamespace(
        certificado_p12_cifrado=None,
        certificado_password_cifrada=None,
    )

    with pytest.raises(UnprocessableError, match="no tiene un certificado electrónico"):
        servicio._obtener_firmador(cast(Empresa, empresa))


class FakeSessionCompleta:
    def __init__(self, resultados, empresa):
        self.resultados = iter(resultados)
        self.empresa = empresa
        self.rollbacks = 0
        self.commits = 0
        self.ejecutadas = []
        self.added = []

    def execute(self, consulta):
        self.ejecutadas.append(consulta)

    def scalar(self, consulta):
        return next(self.resultados)

    def get(self, modelo, identificador):
        return self.empresa

    def add(self, objeto):
        self.added.append(objeto)

    def flush(self):
        pass

    def commit(self):
        self.commits += 1

    def refresh(self, objeto):
        pass

    def rollback(self):
        self.rollbacks += 1


def _preparar_emision_con_detalle(
    monkeypatch,
    detalle,
    *,
    subtotal,
    iva,
    total,
    sin_producto=False,
):
    venta = SimpleNamespace(
        id_venta=103,
        id_empresa=1,
        estado="COMPLETADA",
        subtotal=subtotal,
        iva=iva,
        monto_total=total,
        metodo_pago="EFECTIVO",
    )
    empresa = SimpleNamespace(
        datos_facturacion_electronica={
            "ambiente": "1",
            "establecimiento": "001",
            "punto_emision": "001",
            "obligado_contabilidad": False,
            "contribuyente_especial": None,
            "contribuyente_rimpe": False,
            "direccion_establecimiento": "Av. Amazonas 123, Quito",
        },
        ruc="1790010937001",
        razon_social="Empresa de prueba",
        nombre_comercial="Empresa de prueba",
        direccion="Quito, Ecuador",
    )
    producto = SimpleNamespace(
        codigo_principal="PROD-001",
        nombre="Producto de prueba",
        unidad_medida="UNIDAD",
    )

    session = FakeSessionCompleta([venta, None], empresa)
    servicio = FacturaService(cast(Session, session), empresa_id=1)
    reservas = []

    monkeypatch.setattr(
        servicio.secuencias,
        "reservar",
        lambda **kwargs: reservas.append(kwargs) or 3,
    )
    monkeypatch.setattr(
        servicio,
        "_obtener_firmador",
        lambda empresa: FirmadorSinFirma(),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "obtener",
        lambda id_venta: (venta, None),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "detalles",
        lambda ids: {103: [(detalle, None if sin_producto else producto)]},
    )

    return servicio, session, reservas


def test_emision_conserva_porcentaje_historico_de_iva(monkeypatch):
    detalle = SimpleNamespace(
        cantidad=Decimal("1"),
        precio_unitario=Decimal("10.00"),
        descuento=Decimal("0"),
        codigo_porcentaje_iva="4",
        porcentaje_iva=Decimal("12.00"),
        valor_iva=Decimal("1.20"),
        descripcion_libre=None,
    )
    servicio, session, reservas = _preparar_emision_con_detalle(
        monkeypatch,
        detalle,
        subtotal=Decimal("10.00"),
        iva=Decimal("1.20"),
        total=Decimal("11.20"),
    )

    factura = servicio.emitir(103)

    assert factura.xml_firmado is not None
    assert factura.total == Decimal("11.20")
    assert "<tarifa>12</tarifa>" in factura.xml_firmado
    assert "<valor>1.20</valor>" in factura.xml_firmado
    assert session.commits == 1
    assert session.rollbacks == 0
    assert len(reservas) == 1


def test_emision_conserva_servicio_sin_producto_y_su_iva_historico(monkeypatch):
    detalle = SimpleNamespace(
        cantidad=Decimal("2"),
        precio_unitario=Decimal("10.00"),
        descuento=Decimal("0"),
        codigo_porcentaje_iva="4",
        porcentaje_iva=Decimal("12.00"),
        valor_iva=Decimal("2.40"),
        descripcion_libre="Servicio de consultoria",
    )
    servicio, session, reservas = _preparar_emision_con_detalle(
        monkeypatch,
        detalle,
        subtotal=Decimal("20.00"),
        iva=Decimal("2.40"),
        total=Decimal("22.40"),
        sin_producto=True,
    )

    factura = servicio.emitir(103)

    assert factura.xml_firmado is not None
    assert "<codigoPrincipal>SIN-CODIGO</codigoPrincipal>" in factura.xml_firmado
    assert "<descripcion>Servicio de consultoria</descripcion>" in factura.xml_firmado
    assert "<tarifa>12</tarifa>" in factura.xml_firmado
    assert "<valor>2.40</valor>" in factura.xml_firmado
    assert factura.total == Decimal("22.40")
    assert session.commits == 1
    assert session.rollbacks == 0
    assert len(reservas) == 1


def test_emision_rechaza_iva_almacenado_distinto_del_historico(monkeypatch):
    detalle = SimpleNamespace(
        cantidad=Decimal("1"),
        precio_unitario=Decimal("10.00"),
        descuento=Decimal("0"),
        codigo_porcentaje_iva="4",
        porcentaje_iva=Decimal("12.00"),
        valor_iva=Decimal("1.50"),
        descripcion_libre=None,
    )
    servicio, session, reservas = _preparar_emision_con_detalle(
        monkeypatch,
        detalle,
        subtotal=Decimal("10.00"),
        iva=Decimal("1.20"),
        total=Decimal("11.20"),
    )

    with pytest.raises(ConflictError, match="c\u00e1lculo hist\u00f3rico"):
        servicio.emitir(103)

    assert session.rollbacks == 1
    assert session.commits == 0
    assert session.added == []
    assert reservas == []


def test_emision_persiste_factura_pendiente_para_worker(monkeypatch):
    venta = SimpleNamespace(
        id_venta=101,
        id_empresa=1,
        estado="COMPLETADA",
        subtotal=Decimal("10.00"),
        iva=Decimal("1.50"),
        monto_total=Decimal("11.50"),
        metodo_pago="EFECTIVO",
    )
    empresa = SimpleNamespace(
        datos_facturacion_electronica={
            "ambiente": "1",
            "establecimiento": "001",
            "punto_emision": "001",
            "obligado_contabilidad": False,
            "contribuyente_especial": None,
            "contribuyente_rimpe": False,
            "direccion_establecimiento": "Av. Amazonas 123, Quito",
        },
        ruc="1790010937001",
        razon_social="Empresa de prueba",
        nombre_comercial="Empresa de prueba",
        direccion="Quito, Ecuador",
    )
    detalle = SimpleNamespace(
        cantidad=Decimal("1"),
        precio_unitario=Decimal("10"),
        descuento=Decimal("0"),
        codigo_porcentaje_iva="4",
        descripcion_libre=None,
    )
    producto = SimpleNamespace(
        codigo_principal="PROD-001",
        nombre="Producto de prueba",
        unidad_medida="UNIDAD",
    )

    session = FakeSessionCompleta([venta, None], empresa)
    servicio = FacturaService(cast(Session, session), empresa_id=1)
    reservas = []

    monkeypatch.setattr(
        servicio.secuencias,
        "reservar",
        lambda **kwargs: reservas.append(kwargs) or 1,
    )
    monkeypatch.setattr(
        servicio,
        "_obtener_firmador",
        lambda empresa: FirmadorSinFirma(),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "obtener",
        lambda id_venta: (venta, None),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "detalles",
        lambda ids: {101: [(detalle, producto)]},
    )

    factura = servicio.emitir(101)

    assert len(session.added) == 1
    assert session.commits == 1
    assert session.rollbacks == 0
    assert len(reservas) == 1
    assert factura.estado_autorizacion == "por_enviar"
    assert factura.intentos_envio == 0
    assert factura.clave_acceso
    assert factura.xml_firmado is not None
    assert "<factura" in factura.xml_firmado
    assert "<dirEstablecimiento>Av. Amazonas 123, Quito</dirEstablecimiento>" in factura.xml_firmado
    assert factura.xml_autorizado is None
    assert factura.numero_autorizacion is None
    assert factura.numero_comprobante == "001-001-000000001"
    assert factura.total == Decimal("11.50")


def test_factura_rechazada_se_reemite_con_secuencial_nuevo(monkeypatch):
    """Tras un rechazo del SRI se vuelve a emitir en la MISMA fila, con número y clave nuevos."""
    venta = SimpleNamespace(
        id_venta=101,
        id_empresa=1,
        estado="COMPLETADA",
        subtotal=Decimal("10.00"),
        iva=Decimal("1.50"),
        monto_total=Decimal("11.50"),
        metodo_pago="EFECTIVO",
    )
    empresa = SimpleNamespace(
        datos_facturacion_electronica={
            "ambiente": "1",
            "establecimiento": "001",
            "punto_emision": "001",
            "obligado_contabilidad": False,
            "contribuyente_especial": None,
            "contribuyente_rimpe": False,
            "direccion_establecimiento": "Av. Amazonas 123, Quito",
        },
        ruc="1790010937001",
        razon_social="Empresa de prueba",
        nombre_comercial="Empresa de prueba",
        direccion="Quito, Ecuador",
    )
    detalle = SimpleNamespace(
        cantidad=Decimal("1"),
        precio_unitario=Decimal("10"),
        descuento=Decimal("0"),
        codigo_porcentaje_iva="4",
        descripcion_libre=None,
    )
    producto = SimpleNamespace(
        codigo_principal="PROD-001",
        nombre="Producto de prueba",
        unidad_medida="UNIDAD",
    )

    rechazada = SimpleNamespace(
        id_factura=50,
        id_venta=101,
        estado_autorizacion="rechazada",
        numero_comprobante="001-001-000000001",
        clave_acceso="1" * 49,
        mensajes_sri=[{"identificador": "45", "mensaje": "ERROR", "tipo": "ERROR"}],
        intentos_envio=3,
        numero_autorizacion=None,
        fecha_autorizacion=None,
        xml_autorizado=None,
        pdf_ride_path=None,
    )
    session = FakeSessionCompleta([venta, rechazada], empresa)
    servicio = FacturaService(cast(Session, session), empresa_id=1)
    reservas = []

    monkeypatch.setattr(
        servicio.secuencias,
        "reservar",
        lambda **kwargs: reservas.append(kwargs) or 2,
    )
    monkeypatch.setattr(
        servicio,
        "_obtener_firmador",
        lambda empresa: FirmadorSinFirma(),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "obtener",
        lambda id_venta: (venta, None),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "detalles",
        lambda ids: {101: [(detalle, producto)]},
    )

    factura = servicio.emitir(101)

    assert factura is rechazada  # la misma fila: la venta tiene una sola factura
    assert session.added == []
    assert session.commits == 1
    assert len(reservas) == 1
    assert factura.numero_comprobante == "001-001-000000002"
    assert factura.clave_acceso != "1" * 49
    assert (factura.estado_autorizacion, factura.intentos_envio) == ("por_enviar", 0)
    assert factura.mensajes_sri is not None
    assert factura.mensajes_sri[0]["identificador"] == "REINTENTO"
    assert "001-001-000000001" in factura.mensajes_sri[0]["mensaje"]


def test_factura_en_proceso_no_se_reemite(monkeypatch):
    venta = SimpleNamespace(id_venta=101, id_empresa=1, estado="COMPLETADA")
    for estado in ("autorizada", "por_enviar", "por_autorizar"):
        existente = SimpleNamespace(id_factura=50, estado_autorizacion=estado)
        servicio, session, reservas = _servicio(monkeypatch, [venta, existente])
        with pytest.raises(ConflictError):
            servicio.emitir(101)
        assert reservas == []


def test_emision_pendiente_no_intenta_contactar_al_sri(monkeypatch):
    venta = SimpleNamespace(
        id_venta=102,
        id_empresa=1,
        estado="COMPLETADA",
        subtotal=Decimal("10.00"),
        iva=Decimal("1.50"),
        monto_total=Decimal("11.50"),
        metodo_pago="EFECTIVO",
    )
    empresa = SimpleNamespace(
        datos_facturacion_electronica={
            "ambiente": "1",
            "establecimiento": "001",
            "punto_emision": "001",
            "obligado_contabilidad": False,
            "contribuyente_especial": None,
            "contribuyente_rimpe": False,
        },
        ruc="1790010937001",
        razon_social="Empresa de prueba",
        nombre_comercial="Empresa de prueba",
        direccion="Quito, Ecuador",
    )
    detalle = SimpleNamespace(
        cantidad=Decimal("1"),
        precio_unitario=Decimal("10"),
        descuento=Decimal("0"),
        codigo_porcentaje_iva="4",
        descripcion_libre=None,
    )
    producto = SimpleNamespace(
        codigo_principal="PROD-001",
        nombre="Producto de prueba",
        unidad_medida="UNIDAD",
    )

    session = FakeSessionCompleta([venta, None], empresa)
    servicio = FacturaService(cast(Session, session), empresa_id=1)
    reservas = []

    monkeypatch.setattr(
        servicio.secuencias,
        "reservar",
        lambda **kwargs: reservas.append(kwargs) or 2,
    )
    monkeypatch.setattr(
        servicio,
        "_obtener_firmador",
        lambda empresa: FirmadorSinFirma(),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "obtener",
        lambda id_venta: (venta, None),
    )
    monkeypatch.setattr(
        servicio.ventas,
        "detalles",
        lambda ids: {102: [(detalle, producto)]},
    )

    factura = servicio.emitir(102)

    assert len(session.added) == 1
    assert session.commits == 1
    assert session.rollbacks == 0
    assert len(reservas) == 1
    assert factura.estado_autorizacion == "por_enviar"
    assert factura.intentos_envio == 0
    assert factura.clave_acceso
    assert factura.xml_firmado
    assert factura.xml_autorizado is None
    assert factura.numero_autorizacion is None


def test_venta_de_otra_empresa_no_emite_factura(monkeypatch):
    servicio, session, reservas = _servicio(monkeypatch, [None])
    consultas = []
    scalar_original = session.scalar

    def scalar_capturando(consulta):
        consultas.append(consulta)
        return scalar_original(consulta)

    monkeypatch.setattr(session, "scalar", scalar_capturando)

    with pytest.raises(NotFoundError, match="La venta solicitada no existe"):
        servicio.emitir(101)

    assert len(consultas) == 1

    sql = str(consultas[0])
    parametros = consultas[0].compile().params

    assert "id_empresa" in sql
    assert "id_venta" in sql
    assert 1 in parametros.values()
    assert 101 in parametros.values()

    assert session.rollbacks == 1
    assert session.commits == 0
    assert reservas == []
    assert len(session.ejecutadas) == 1


def test_recupera_ride_desde_xml_autorizado_si_storage_falla(monkeypatch):
    from app.core.errors import ServiceUnavailableError

    factura = SimpleNamespace(
        id_factura=50,
        id_venta=101,
        id_empresa=1,
        estado_autorizacion="autorizada",
        xml_autorizado="<factura>XML autorizado</factura>",
        numero_autorizacion="1234567890",
        fecha_autorizacion=datetime(2026, 11, 11, 20, 0, 0),
        pdf_ride_path="empresas/1/facturas/50/ride.pdf",
    )

    session = FakeSessionCompleta([factura], empresa=None)
    servicio = FacturaService(cast(Session, session), empresa_id=1)

    pdf_generado = b"%PDF-1.4 RIDE reconstruido"
    llamadas_generador = []

    def generar_ride_falso(xml, **kwargs):
        llamadas_generador.append((xml, kwargs))
        return pdf_generado

    class AlmacenamientoFalso:
        def guardar(self, empresa_id: int, factura_id: int, contenido: bytes) -> str:
            raise ServiceUnavailableError(
                "Storage no disponible",
                code="RIDE_STORAGE_UNAVAILABLE",
            )

        def descargar(self, ruta: str) -> bytes:
            raise ServiceUnavailableError(
                "Storage no disponible",
                code="RIDE_STORAGE_UNAVAILABLE",
            )

    monkeypatch.setattr(
        "app.services.factura.generar_ride",
        generar_ride_falso,
    )

    servicio.almacenamiento = AlmacenamientoFalso()

    resultado = servicio.obtener_ride(101)

    assert resultado == pdf_generado
    assert len(llamadas_generador) == 1
    assert llamadas_generador[0][0] == b"<factura>XML autorizado</factura>"
    assert llamadas_generador[0][1]["numero_autorizacion"] == "1234567890"
    assert session.commits == 0


def test_descarga_ride_existente_sin_reconstruirlo(monkeypatch):
    factura = SimpleNamespace(
        id_factura=50,
        id_venta=101,
        id_empresa=1,
        estado_autorizacion="autorizada",
        xml_autorizado="<factura>XML autorizado</factura>",
        numero_autorizacion="1234567890",
        fecha_autorizacion=datetime(2026, 11, 11, 20, 0, 0),
        pdf_ride_path="empresas/1/facturas/50/ride.pdf",
    )

    session = FakeSessionCompleta([factura], empresa=None)
    servicio = FacturaService(cast(Session, session), empresa_id=1)

    pdf_guardado = b"%PDF-1.4 RIDE existente"
    rutas_descargadas = []

    class AlmacenamientoFalso:
        def guardar(self, empresa_id: int, factura_id: int, contenido: bytes) -> str:
            return f"empresas/{empresa_id}/facturas/{factura_id}/ride.pdf"

        def descargar(self, ruta: str) -> bytes:
            rutas_descargadas.append(ruta)
            return pdf_guardado

    monkeypatch.setattr(
        "app.services.factura.generar_ride",
        lambda *args, **kwargs: pytest.fail(
            "No debe reconstruirse un RIDE que ya está almacenado."
        ),
    )

    servicio.almacenamiento = AlmacenamientoFalso()

    resultado = servicio.obtener_ride(101)

    assert resultado == pdf_guardado
    assert rutas_descargadas == ["empresas/1/facturas/50/ride.pdf"]
    assert session.commits == 0
    assert session.rollbacks == 0
