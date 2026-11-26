from contextlib import contextmanager
from datetime import UTC
from types import SimpleNamespace

import pytest

from app.sri.emision import EstadoEmision, ResultadoEmision
from app.sri.simulado import ClienteSriSimulado
from app.worker import __main__ as worker

XML = "<factura>firmada</factura>"
CLAVE = "1234567890123456789012345678901234567890123456789"


class SesionFalsa:
    def __init__(self, resultados=(), empresa=None):
        self.resultados = list(resultados)
        self.empresa = empresa
        self.transaccion_confirmada = False
        self.transaccion_activa = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    @contextmanager
    def begin(self):
        if self.transaccion_activa:
            raise AssertionError("La sesión ya tiene una transacción activa.")

        self.transaccion_activa = True
        try:
            yield
        except Exception:
            raise
        else:
            self.transaccion_confirmada = True
        finally:
            self.transaccion_activa = False

    def scalar(self, sentencia):
        if not self.resultados:
            raise AssertionError("Se solicitó un resultado inesperado a scalar().")
        return self.resultados.pop(0)

    def execute(self, sentencia):
        fila = None
        if self.empresa is not None:
            fila = (
                self.empresa.id_empresa,
                self.empresa.datos_facturacion_electronica,
            )
        return SimpleNamespace(one_or_none=lambda: fila)

    def get(self, modelo, identificador):
        return self.empresa


class FabricaSesionesFalsa:
    def __init__(self, *sesiones):
        self.sesiones = list(sesiones)
        self.sesiones_creadas = []

    def __call__(self):
        if not self.sesiones:
            raise AssertionError("Se solicitó una sesión inesperada.")

        sesion = self.sesiones.pop(0)
        self.sesiones_creadas.append(sesion)
        return sesion


class ClienteSriFalso:
    def __init__(self, ambiente):
        self.ambiente = ambiente

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ServicioSriFalso:
    def __init__(self, resultado_envio=None, resultado_consulta=None):
        self.resultado_envio = resultado_envio
        self.resultado_consulta = resultado_consulta
        self.envios = []
        self.consultas = []
        self.al_enviar = None

    def enviar(self, xml, clave):
        self.envios.append((xml, clave))
        if self.al_enviar is not None:
            self.al_enviar()
        return self.resultado_envio

    def consultar(self, xml, clave):
        self.consultas.append((xml, clave))
        return self.resultado_consulta


@pytest.fixture(autouse=True)
def bloqueo_factura_falso(monkeypatch):
    @contextmanager
    def bloqueo(empresa_id, factura_id, **kwargs):
        yield True

    monkeypatch.setattr(worker, "bloqueo_factura", bloqueo)


def factura_falsa(estado="por_enviar"):
    return SimpleNamespace(
        id_empresa=7,
        id_factura=15,
        estado_autorizacion=estado,
        clave_acceso=CLAVE,
        xml_firmado=XML,
        xml_autorizado=None,
        numero_autorizacion=None,
        fecha_autorizacion=None,
        mensajes_sri=[{"mensaje": "mensaje anterior"}],
        intentos_envio=0,
        pdf_ride_path=None,
    )


def empresa_falsa():
    return SimpleNamespace(id_empresa=7, datos_facturacion_electronica={"ambiente": "1"})


def instalar_sri_falso(monkeypatch, servicio):
    monkeypatch.setattr(worker, "ClienteSri", ClienteSriFalso)
    monkeypatch.setattr(
        worker,
        "ServicioEmision",
        lambda *args, **kwargs: servicio,
    )


def _cliente_usado(monkeypatch, ambiente, empresas):
    """Procesa una factura de la empresa 7 y devuelve el cliente SRI que usó el worker."""
    usados = []
    resultado = ResultadoEmision(EstadoEmision.POR_AUTORIZAR, CLAVE, XML.encode("utf-8"))
    monkeypatch.setattr(worker, "ClienteSri", ClienteSriFalso)
    monkeypatch.setattr(
        worker,
        "ServicioEmision",
        lambda cliente, **kwargs: usados.append(cliente) or ServicioSriFalso(resultado),
    )
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(sri_simulado_empresas=frozenset(empresas)),
    )
    empresa = SimpleNamespace(id_empresa=7, datos_facturacion_electronica={"ambiente": ambiente})
    factura = factura_falsa()
    worker._procesar_factura(
        FabricaSesionesFalsa(SesionFalsa([factura], empresa=empresa), SesionFalsa([factura])),
        7,
        15,
        None,
    )
    return usados[0] if usados else None


def test_empresa_en_sri_simulado_no_llama_al_sri_real(monkeypatch):
    assert isinstance(_cliente_usado(monkeypatch, "1", {7}), ClienteSriSimulado)


@pytest.mark.parametrize(("ambiente", "empresas"), [("1", set()), ("1", {3}), ("2", {7})])
def test_sin_la_variable_otra_empresa_o_produccion_usa_el_sri_real(monkeypatch, ambiente, empresas):
    assert isinstance(_cliente_usado(monkeypatch, ambiente, empresas), ClienteSriFalso)


def test_serializar_mensajes_sri():
    mensaje = SimpleNamespace(
        identificador="43",
        mensaje="Clave registrada",
        informacion_adicional="Comprobante recibido",
        tipo="ERROR",
    )

    assert worker._serializar_mensajes([mensaje]) == [
        {
            "identificador": "43",
            "mensaje": "Clave registrada",
            "informacion_adicional": "Comprobante recibido",
            "tipo": "ERROR",
        }
    ]


def test_por_enviar_reutiliza_xml_y_clave_y_aumenta_intentos(monkeypatch):
    factura = factura_falsa()
    resultado = ResultadoEmision(
        EstadoEmision.POR_AUTORIZAR,
        CLAVE,
        XML.encode("utf-8"),
    )
    servicio = ServicioSriFalso(resultado_envio=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa(
        [factura],
        empresa=empresa_falsa(),
    )
    sesion_respuesta = SesionFalsa([factura])

    worker._procesar_factura(
        FabricaSesionesFalsa(sesion_inicio, sesion_respuesta),
        7,
        15,
        None,
    )

    assert servicio.envios == [(XML.encode("utf-8"), CLAVE)]
    assert servicio.consultas == []
    assert factura.intentos_envio == 1
    assert factura.estado_autorizacion == "por_autorizar"


def test_envio_sri_ocurre_sin_transaccion_y_con_intento_confirmado(
    monkeypatch,
):
    factura = factura_falsa("por_enviar")
    resultado = ResultadoEmision(
        EstadoEmision.POR_AUTORIZAR,
        CLAVE,
        XML.encode("utf-8"),
    )
    servicio = ServicioSriFalso(resultado_envio=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa(
        [factura],
        empresa=empresa_falsa(),
    )
    sesion_respuesta = SesionFalsa([factura])
    fabrica = FabricaSesionesFalsa(sesion_inicio, sesion_respuesta)
    bloqueo_activo = False

    @contextmanager
    def bloqueo_controlado(empresa_id, factura_id, **kwargs):
        nonlocal bloqueo_activo
        bloqueo_activo = True
        try:
            yield True
        finally:
            bloqueo_activo = False

    monkeypatch.setattr(
        worker,
        "bloqueo_factura",
        bloqueo_controlado,
    )

    def verificar_estado_antes_del_envio():
        assert bloqueo_activo is True
        assert sesion_inicio.transaccion_confirmada is True
        assert sesion_inicio.transaccion_activa is False
        assert sesion_respuesta.transaccion_confirmada is False
        assert sesion_respuesta.transaccion_activa is False
        assert factura.intentos_envio == 1
        assert factura.estado_autorizacion == "por_enviar"

    servicio.al_enviar = verificar_estado_antes_del_envio

    worker._procesar_factura(
        fabrica,
        7,
        15,
        None,
    )

    assert servicio.envios == [(XML.encode("utf-8"), CLAVE)]
    assert sesion_inicio.transaccion_confirmada is True
    assert sesion_inicio.transaccion_activa is False
    assert sesion_respuesta.transaccion_confirmada is True
    assert sesion_respuesta.transaccion_activa is False
    assert bloqueo_activo is False
    assert factura.intentos_envio == 1
    assert factura.estado_autorizacion == "por_autorizar"


def test_por_autorizar_consulta_sin_reenviar_ni_aumentar_intentos(
    monkeypatch,
):
    factura = factura_falsa("por_autorizar")
    factura.intentos_envio = 3

    resultado = ResultadoEmision(
        EstadoEmision.POR_AUTORIZAR,
        CLAVE,
        XML.encode("utf-8"),
    )
    servicio = ServicioSriFalso(resultado_consulta=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa(
        [factura],
        empresa=empresa_falsa(),
    )
    sesion_respuesta = SesionFalsa([factura])

    worker._procesar_factura(
        FabricaSesionesFalsa(sesion_inicio, sesion_respuesta),
        7,
        15,
        None,
    )

    assert servicio.envios == []
    assert servicio.consultas == [(XML.encode("utf-8"), CLAVE)]
    assert factura.intentos_envio == 3
    assert factura.estado_autorizacion == "por_autorizar"


def test_bloqueo_advisory_impide_procesamiento(monkeypatch):
    servicio = ServicioSriFalso()
    instalar_sri_falso(monkeypatch, servicio)

    @contextmanager
    def bloqueo_no_adquirido(empresa_id, factura_id, **kwargs):
        yield False

    monkeypatch.setattr(
        worker,
        "bloqueo_factura",
        bloqueo_no_adquirido,
    )

    worker._procesar_factura(
        FabricaSesionesFalsa(SesionFalsa()),
        7,
        15,
        None,
    )

    assert servicio.envios == []
    assert servicio.consultas == []


def test_autorizacion_se_confirma_antes_de_guardar_ride(monkeypatch):
    factura = factura_falsa("por_autorizar")
    fecha = SimpleNamespace(isoformat=lambda: "2026-11-18T10:00:00")

    resultado = ResultadoEmision(
        EstadoEmision.AUTORIZADA,
        CLAVE,
        XML.encode("utf-8"),
        numero_autorizacion=CLAVE,
        fecha_autorizacion=fecha,
        xml_autorizado=b"<autorizado/>",
    )
    servicio = ServicioSriFalso(resultado_consulta=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa(
        [factura],
        empresa=empresa_falsa(),
    )
    sesion_proceso = SesionFalsa([factura])
    sesion_ruta = SesionFalsa([factura])
    fabrica = FabricaSesionesFalsa(
        sesion_inicio,
        sesion_proceso,
        sesion_ruta,
    )

    def generar_ride_falso(xml, *, numero_autorizacion, fecha_autorizacion, simulado):
        assert simulado is False  # autorización real: el RIDE no lleva el aviso
        assert sesion_proceso.transaccion_confirmada
        assert xml == b"<autorizado/>"
        assert numero_autorizacion == CLAVE
        assert fecha_autorizacion is fecha
        return b"%PDF-1.4 prueba"

    monkeypatch.setattr(worker, "generar_ride", generar_ride_falso)

    class AlmacenamientoFalso:
        def guardar(self, empresa_id, factura_id, contenido):
            assert sesion_proceso.transaccion_confirmada
            assert factura.estado_autorizacion == "autorizada"
            assert contenido == b"%PDF-1.4 prueba"
            return "empresas/7/facturas/15/ride.pdf"

    worker._procesar_factura(
        fabrica,
        7,
        15,
        AlmacenamientoFalso(),
    )

    assert factura.estado_autorizacion == "autorizada"
    assert factura.numero_autorizacion == CLAVE
    assert factura.xml_autorizado == "<autorizado/>"
    assert factura.pdf_ride_path == "empresas/7/facturas/15/ride.pdf"


def test_fallo_al_generar_ride_no_revierte_autorizacion(monkeypatch):
    factura = factura_falsa("por_autorizar")
    resultado = ResultadoEmision(
        EstadoEmision.AUTORIZADA,
        CLAVE,
        XML.encode("utf-8"),
        numero_autorizacion=CLAVE,
        fecha_autorizacion=SimpleNamespace(isoformat=lambda: "2026-11-18T10:00:00"),
        xml_autorizado=b"<autorizado/>",
    )
    servicio = ServicioSriFalso(resultado_consulta=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa(
        [factura],
        empresa=empresa_falsa(),
    )
    sesion = SesionFalsa([factura])

    def fallar_generacion(*args, **kwargs):
        assert sesion.transaccion_confirmada
        raise RuntimeError("fallo simulado al generar PDF")

    monkeypatch.setattr(worker, "generar_ride", fallar_generacion)

    class AlmacenamientoFalso:
        def guardar(self, *args):
            raise AssertionError("No debe intentar Storage si falla el PDF.")

    worker._procesar_factura(
        FabricaSesionesFalsa(sesion_inicio, sesion),
        7,
        15,
        AlmacenamientoFalso(),
    )

    assert sesion.transaccion_confirmada
    assert factura.estado_autorizacion == "autorizada"
    assert factura.numero_autorizacion == CLAVE
    assert factura.xml_autorizado == "<autorizado/>"
    assert factura.pdf_ride_path is None


def test_fallo_de_storage_no_revierte_autorizacion(monkeypatch):
    factura = factura_falsa("por_autorizar")

    resultado = ResultadoEmision(
        EstadoEmision.AUTORIZADA,
        CLAVE,
        XML.encode("utf-8"),
        numero_autorizacion=CLAVE,
        fecha_autorizacion=SimpleNamespace(isoformat=lambda: "2026-11-18T10:00:00"),
        xml_autorizado=b"<autorizado/>",
    )
    servicio = ServicioSriFalso(resultado_consulta=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa(
        [factura],
        empresa=empresa_falsa(),
    )
    sesion = SesionFalsa([factura])

    monkeypatch.setattr(
        worker,
        "generar_ride",
        lambda xml, **kwargs: b"%PDF-1.4 prueba",
    )

    class AlmacenamientoConError:
        def guardar(self, *args):
            raise RuntimeError("fallo simulado de Storage")

    worker._procesar_factura(
        FabricaSesionesFalsa(sesion_inicio, sesion),
        7,
        15,
        AlmacenamientoConError(),
    )

    assert sesion.transaccion_confirmada
    assert factura.estado_autorizacion == "autorizada"
    assert factura.numero_autorizacion == CLAVE
    assert factura.xml_autorizado == "<autorizado/>"
    assert factura.pdf_ride_path is None


def test_error_al_enviar_conserva_por_enviar_y_aumenta_intentos(monkeypatch):
    factura = factura_falsa("por_enviar")

    class ServicioConError:
        def enviar(self, xml, clave):
            raise RuntimeError("fallo simulado de comunicación")

        def consultar(self, xml, clave):
            raise AssertionError("No debe consultar después del fallo de envío.")

    instalar_sri_falso(monkeypatch, ServicioConError())
    sesion = SesionFalsa([factura], empresa=empresa_falsa())

    worker._procesar_factura(FabricaSesionesFalsa(sesion), 7, 15, None)

    assert sesion.transaccion_confirmada
    assert factura.estado_autorizacion == "por_enviar"
    assert factura.intentos_envio == 1


def test_error_al_consultar_conserva_por_autorizar_y_no_aumenta_intentos(
    monkeypatch,
):
    factura = factura_falsa("por_autorizar")
    factura.intentos_envio = 4

    class ServicioConError:
        def enviar(self, xml, clave):
            raise AssertionError("Nunca debe reenviar.")

        def consultar(self, xml, clave):
            raise RuntimeError("fallo simulado de comunicación")

    instalar_sri_falso(monkeypatch, ServicioConError())
    sesion = SesionFalsa([factura], empresa=empresa_falsa())

    worker._procesar_factura(FabricaSesionesFalsa(sesion), 7, 15, None)

    assert sesion.transaccion_confirmada
    assert factura.estado_autorizacion == "por_autorizar"
    assert factura.intentos_envio == 4


def test_rotacion_de_lotes_avanza_y_vuelve_al_inicio():
    from datetime import datetime

    fecha = datetime(2026, 11, 18, tzinfo=UTC)

    class ResultadoConsulta:
        def __init__(self, filas):
            self.filas = filas

        def all(self):
            return self.filas

    class SesionConsulta:
        def __init__(self, resultados):
            self.resultados = list(resultados)
            self.sentencias = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sentencia):
            self.sentencias.append(sentencia)
            return ResultadoConsulta(self.resultados.pop(0))

    worker._ultimo_pendiente = None

    # Primer lote: dos facturas. Segundo ciclo: no quedan filas después
    # del cursor y la consulta circular recupera la primera.
    sesion_primera = SesionConsulta(
        [
            [(fecha, 7, 15), (fecha, 7, 16)],
        ]
    )
    sesion_segunda = SesionConsulta(
        [
            [],
            [(fecha, 7, 15)],
        ]
    )

    fabrica = FabricaSesionesFalsa(sesion_primera, sesion_segunda)

    primero = worker._obtener_pendientes(fabrica)
    segundo = worker._obtener_pendientes(fabrica)

    assert primero == [(7, 15), (7, 16)]
    assert segundo == [(7, 15)]
    assert len(sesion_primera.sentencias) == 1
    assert len(sesion_segunda.sentencias) == 2
    assert worker._ultimo_pendiente == (fecha, 7, 15)


def test_rechazo_sri_persiste_estado_y_mensajes_sin_datos_de_autorizacion(
    monkeypatch,
):
    factura = factura_falsa("por_autorizar")
    factura.intentos_envio = 2

    mensaje = SimpleNamespace(
        identificador="43",
        mensaje="Comprobante rechazado",
        informacion_adicional="Validación tributaria",
        tipo="ERROR",
    )
    resultado = ResultadoEmision(
        EstadoEmision.RECHAZADA,
        CLAVE,
        XML.encode("utf-8"),
        mensajes=[mensaje],
    )
    servicio = ServicioSriFalso(resultado_consulta=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa([factura], empresa=empresa_falsa())
    sesion_respuesta = SesionFalsa([factura])

    worker._procesar_factura(
        FabricaSesionesFalsa(sesion_inicio, sesion_respuesta),
        7,
        15,
        None,
    )

    assert servicio.envios == []
    assert servicio.consultas == [(XML.encode("utf-8"), CLAVE)]
    assert factura.estado_autorizacion == "rechazada"
    assert factura.mensajes_sri == [
        {
            "identificador": "43",
            "mensaje": "Comprobante rechazado",
            "informacion_adicional": "Validación tributaria",
            "tipo": "ERROR",
        }
    ]
    assert factura.intentos_envio == 2
    assert factura.numero_autorizacion is None
    assert factura.fecha_autorizacion is None
    assert factura.xml_autorizado is None


def test_respuesta_sri_sin_mensajes_limpia_mensajes_anteriores(monkeypatch):
    factura = factura_falsa("por_autorizar")
    factura.mensajes_sri = [{"mensaje": "error anterior"}]

    resultado = ResultadoEmision(
        EstadoEmision.POR_AUTORIZAR,
        CLAVE,
        XML.encode("utf-8"),
        mensajes=[],
    )
    servicio = ServicioSriFalso(resultado_consulta=resultado)
    instalar_sri_falso(monkeypatch, servicio)

    sesion_inicio = SesionFalsa([factura], empresa=empresa_falsa())
    sesion_respuesta = SesionFalsa([factura])

    worker._procesar_factura(
        FabricaSesionesFalsa(sesion_inicio, sesion_respuesta),
        7,
        15,
        None,
    )

    assert factura.estado_autorizacion == "por_autorizar"
    assert factura.mensajes_sri == []
    assert factura.intentos_envio == 0
