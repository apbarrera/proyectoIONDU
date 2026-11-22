from types import SimpleNamespace
from uuid import UUID

import pytest

from app.api import deps
from app.core.errors import ForbiddenError, UnauthenticatedError


USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


@pytest.fixture(autouse=True)
def clear_settings_cache():
    deps.get_settings.cache_clear()
    yield
    deps.get_settings.cache_clear()


def preparar(monkeypatch, *, app_env="development", dev_user_id=str(USER_ID),
             empresas=None, pertenencia=None):
    monkeypatch.setenv("APP_ENV", app_env)
    if dev_user_id is None:
        monkeypatch.delenv("DEV_USER_ID", raising=False)
    else:
        monkeypatch.setenv("DEV_USER_ID", dev_user_id)

    llamadas_rls = []
    monkeypatch.setattr(
        deps, "establecer_contexto_rls",
        lambda db, usuario_id, empresa_id: llamadas_rls.append(
            (usuario_id, empresa_id)
        ),
    )
    monkeypatch.setattr(
        deps, "obtener_empresas_activas",
        lambda db, usuario_id: empresas if empresas is not None else [
            SimpleNamespace(id_empresa=7)
        ],
    )
    monkeypatch.setattr(
        deps, "obtener_pertenencia_activa",
        lambda db, usuario_id, empresa_id: pertenencia if pertenencia is not None
        else SimpleNamespace(id_empresa=7, rol="Usuario operativo", nombre="Local"),
    )
    deps.get_settings.cache_clear()
    return llamadas_rls


def ejecutar(*, authorization=None, empresa_id=7):
    return deps.get_contexto(
        db=object(),
        verificador=None,
        authorization=authorization,
        x_empresa_id=empresa_id,
    )


def test_usuario_desarrollo_valida_membresia_y_usa_rol_real(monkeypatch):
    llamadas = preparar(monkeypatch)
    contexto = ejecutar()

    assert contexto.empresa_id == 7
    assert contexto.rol == "Usuario operativo"
    assert contexto.usuario.id == USER_ID
    assert llamadas == [(USER_ID, None), (USER_ID, 7)]


def test_desarrollo_sin_dev_user_id_rechaza(monkeypatch):
    preparar(monkeypatch, dev_user_id=None)
    with pytest.raises(UnauthenticatedError):
        ejecutar()


def test_desarrollo_sin_empresas_activas_rechaza(monkeypatch):
    preparar(monkeypatch, empresas=[])
    usuario = deps.UsuarioAutenticado(id=USER_ID, email=None)
    with pytest.raises(ForbiddenError) as error:
        deps._contexto_con_membresia(
            db=object(),
            usuario=usuario,
            x_empresa_id=None,
        )
    assert error.value.code == "NO_COMPANY"


def test_desarrollo_no_permite_empresa_de_otro_usuario(monkeypatch):
    preparar(monkeypatch, empresas=[SimpleNamespace(id_empresa=8)])
    with pytest.raises(ForbiddenError) as error:
        ejecutar(empresa_id=7)
    assert error.value.code == "COMPANY_ACCESS_DENIED"


def test_desarrollo_rechaza_membresia_que_dejo_de_estar_activa(monkeypatch):
    llamadas = preparar(monkeypatch)
    monkeypatch.setattr(
        deps, "obtener_pertenencia_activa",
        lambda db, usuario_id, empresa_id: None,
    )
    with pytest.raises(ForbiddenError) as error:
        ejecutar()
    assert error.value.code == "COMPANY_ACCESS_DENIED"
    assert llamadas == [(USER_ID, None), (USER_ID, 7)]


def test_produccion_rechaza_sin_jwt_aunque_dev_user_id_exista(monkeypatch):
    preparar(monkeypatch, app_env="production")
    with pytest.raises(UnauthenticatedError):
        ejecutar()


def test_authorization_invalido_no_activa_modo_desarrollo(monkeypatch):
    preparar(monkeypatch)
    with pytest.raises(UnauthenticatedError):
        ejecutar(authorization="Basic invalid-token")
