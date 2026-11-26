"""Aislamiento de usuario y sesion_refresh, privilegios efectivos y migración (sube y baja).

Todo se comprueba iniciando sesión con los roles reales: iondu_app, iondu_auth, iondu_worker.
"""

import psycopg
import pytest

from tests.postgres_auth.conftest import (
    ANA,
    BETO,
    CORREOS,
    HEAD,
    INACTIVO,
    MULTI,
    OSCAR,
    PREFIJO,
    PREVIA,
    admin,
    borrar_base,
    como,
    crear_base,
    migrar,
)

DENEGADO = psycopg.errors.InsufficientPrivilege


def _contexto(conn, usuario, empresa) -> None:
    conn.execute(
        "SELECT set_config('app.current_user_id', %s, false), "
        "set_config('app.current_empresa_id', %s, false)",
        (str(usuario) if usuario else "", str(empresa) if empresa else ""),
    )


@pytest.fixture
def app_conn(base):
    with como(base["nombre"], "iondu_app") as conn:
        yield conn


@pytest.fixture
def auth_conn(base):
    with como(base["nombre"], "iondu_auth") as conn:
        yield conn


@pytest.fixture
def sesiones(base):
    """Una sesión abierta de Ana y otra de Beto (creadas por el administrador de la base)."""
    with admin(base["nombre"]) as conn:
        conn.execute("DELETE FROM sesion_refresh")
        for usuario, token in ((ANA, "a" * 64), (BETO, "b" * 64)):
            conn.execute(
                "INSERT INTO sesion_refresh (id_usuario, token_hash, expira_en) "
                "VALUES (%s, %s, now() + interval '1 day')",
                (usuario, token),
            )
    yield
    with admin(base["nombre"]) as conn:
        conn.execute("DELETE FROM sesion_refresh")


# ---------- iondu_app: usuario ----------
def test_sin_contexto_iondu_app_no_ve_ningun_usuario(app_conn):
    assert app_conn.execute("SELECT count(*) FROM usuario").fetchone()[0] == 0


def test_iondu_app_no_puede_consultar_todos_los_usuarios(app_conn, base):
    _contexto(app_conn, ANA, base["empresas"]["A"])  # Administradora de A
    correos = {c for (c,) in app_conn.execute("SELECT email FROM usuario")}
    assert correos == {CORREOS[u] for u in (ANA, OSCAR, INACTIVO, MULTI)}
    assert CORREOS[BETO] not in correos


def test_un_operativo_solo_ve_su_propio_usuario(app_conn, base):
    _contexto(app_conn, OSCAR, base["empresas"]["A"])
    assert [c for (c,) in app_conn.execute("SELECT email FROM usuario")] == [CORREOS[OSCAR]]


def test_pedir_otra_empresa_no_muestra_sus_usuarios(app_conn, base):
    _contexto(app_conn, ANA, base["empresas"]["B"])  # Ana no pertenece a B
    assert [c for (c,) in app_conn.execute("SELECT email FROM usuario")] == [CORREOS[ANA]]


@pytest.mark.parametrize(
    "sentencia",
    (
        "SELECT password_hash FROM usuario",
        "SELECT * FROM usuario",
        "SELECT intentos_fallidos, bloqueado_hasta FROM usuario",
        "UPDATE usuario SET password_hash = 'x'",
        "UPDATE usuario SET activo = false",
        "INSERT INTO usuario (email, password_hash) VALUES ('nuevo@x.ec', 'x')",
        "DELETE FROM usuario",
    ),
)
def test_iondu_app_no_lee_hashes_ni_modifica_usuarios(app_conn, base, sentencia):
    _contexto(app_conn, ANA, base["empresas"]["A"])
    with pytest.raises(DENEGADO):
        app_conn.execute(sentencia)


# ---------- iondu_app: sesiones ----------
@pytest.mark.parametrize(
    "sentencia",
    (
        "SELECT * FROM sesion_refresh",
        "SELECT id_usuario FROM sesion_refresh",
        "UPDATE sesion_refresh SET revocada_en = now()",
        "DELETE FROM sesion_refresh",
        "INSERT INTO sesion_refresh (id_usuario, token_hash, expira_en) "
        "VALUES ('a0000000-0000-4000-8000-000000000001', 'x', now())",
    ),
)
def test_iondu_app_no_accede_a_sesiones(app_conn, base, sesiones, sentencia):
    _contexto(app_conn, ANA, base["empresas"]["A"])
    with pytest.raises(DENEGADO):
        app_conn.execute(sentencia)


def test_ni_con_contexto_ajeno_se_revocan_sesiones_ni_contrasenas_de_otros(
    app_conn, base, sesiones
):
    # Aunque iondu_app falsificara el contexto de Beto, no tiene ningún permiso.
    _contexto(app_conn, BETO, base["empresas"]["B"])
    with pytest.raises(DENEGADO):
        app_conn.execute(
            "UPDATE sesion_refresh SET revocada_en = now() WHERE id_usuario = %s", (BETO,)
        )
    with pytest.raises(DENEGADO):
        app_conn.execute("UPDATE usuario SET password_hash = 'x' WHERE id = %s", (BETO,))
    with admin(base["nombre"]) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM sesion_refresh WHERE revocada_en IS NULL"
            ).fetchone()[0]
            == 2
        )


# ---------- iondu_auth ----------
def test_iondu_auth_funciona_sin_contexto_de_empresa(auth_conn, sesiones):
    assert auth_conn.execute(
        "SELECT id FROM usuario WHERE email = %s", (CORREOS[BETO],)
    ).fetchone() == (BETO,)
    assert auth_conn.execute(
        "SELECT id_usuario FROM sesion_refresh WHERE token_hash = %s", ("a" * 64,)
    ).fetchone() == (ANA,)


@pytest.mark.parametrize(
    "sentencia",
    (
        "SELECT * FROM empresa",
        "SELECT * FROM venta",
        "SELECT * FROM producto",
        "SELECT * FROM factura",
        "SELECT nombre_visible FROM usuario_empresa",
        "SELECT id_usuario, id_empresa FROM usuario_empresa",
        "UPDATE usuario_empresa SET estado = 'ACTIVO'",
        "UPDATE usuario SET email = 'otro@x.ec'",
        "UPDATE usuario SET activo = true",
        "DELETE FROM usuario",
        "UPDATE sesion_refresh SET token_hash = 'x'",
        "CREATE TABLE intrusa (id int)",
    ),
)
def test_iondu_auth_no_toca_el_negocio_ni_columnas_ajenas(auth_conn, sentencia):
    with pytest.raises(DENEGADO):
        auth_conn.execute(sentencia)


def test_no_se_abren_sesiones_de_cuentas_inactivas(auth_conn):
    with pytest.raises(DENEGADO, match="row-level security"):
        auth_conn.execute(
            "INSERT INTO sesion_refresh (id_usuario, token_hash, expira_en) "
            "VALUES (%s, %s, now() + interval '1 day')",
            (INACTIVO, "c" * 64),
        )


# ---------- iondu_worker ----------
@pytest.mark.parametrize(
    "sentencia",
    ("SELECT id FROM usuario", "SELECT * FROM sesion_refresh", "SELECT * FROM usuario_empresa"),
)
def test_iondu_worker_no_accede_a_usuarios_ni_sesiones(base, sentencia):
    with como(base["nombre"], "iondu_worker") as conn, pytest.raises(DENEGADO):
        conn.execute(sentencia)


# ---------- Privilegios de los roles y de PUBLIC ----------
def test_ningun_rol_de_ejecucion_puede_eludir_el_rls(base):
    with admin(base["nombre"]) as conn:
        filas = conn.execute(
            "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole FROM pg_roles "
            "WHERE rolname IN ('iondu_app', 'iondu_auth', 'iondu_worker')"
        ).fetchall()
        assert len(filas) == 3
        assert all(not s and not b and not c for _r, s, b, c in filas), filas
        # iondu_app no puede convertirse en iondu_auth (ni al revés).
        assert not conn.execute(
            "SELECT pg_has_role('iondu_app', 'iondu_auth', 'MEMBER') "
            "OR pg_has_role('iondu_auth', 'iondu_app', 'MEMBER')"
        ).fetchone()[0]
    with como(base["nombre"], "iondu_app") as conn, pytest.raises(DENEGADO):
        conn.execute("SET ROLE iondu_auth")


def test_rls_habilitado_y_forzado_con_sus_politicas(base):
    with admin(base["nombre"]) as conn:
        estado = dict(
            (n, (r, f))
            for n, r, f in conn.execute(
                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname IN ('usuario', 'sesion_refresh')"
            )
        )
        assert estado == {"usuario": (True, True), "sesion_refresh": (True, True)}
        politicas = {
            (t, r)
            for t, roles in conn.execute(
                "SELECT tablename, roles FROM pg_policies "
                "WHERE tablename IN ('usuario', 'sesion_refresh')"
            )
            for r in roles
        }
        assert politicas == {
            ("usuario", "iondu_app"),
            ("usuario", "iondu_auth"),
            ("sesion_refresh", "iondu_auth"),
        }


def test_sin_permisos_amplios_sobre_usuario_y_sesiones(base):
    with admin(base["nombre"]) as conn:
        # Ningún permiso a nivel de tabla para la API ni para PUBLIC (solo por columna).
        amplios = conn.execute(
            """
            SELECT c.relname, CASE WHEN p.grantee = 0 THEN 'PUBLIC'
                                   ELSE pg_get_userbyid(p.grantee) END, p.privilege_type
            FROM pg_class c, aclexplode(c.relacl) p
            WHERE c.relname IN ('usuario', 'sesion_refresh')
              AND (p.grantee = 0 OR pg_get_userbyid(p.grantee) IN ('iondu_app', 'iondu_worker'))
            """
        ).fetchall()
        assert amplios == []
        app = {
            (t, c, p)
            for t, c, p in conn.execute(
                """
                SELECT c.relname, a.attname, p.privilege_type
                FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid,
                     aclexplode(a.attacl) p
                WHERE c.relname IN ('usuario', 'sesion_refresh')
                  AND p.grantee = 'iondu_app'::regrole
                """
            )
        }
        assert app == {("usuario", "id", "SELECT"), ("usuario", "email", "SELECT")}


def test_public_no_ejecuta_funciones_privilegiadas(base):
    with admin(base["nombre"]) as conn:
        con_public = conn.execute(
            """
            SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' AND p.prosecdef
              AND EXISTS (
                  SELECT 1 FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                  WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE'
              )
            """
        ).fetchall()
        assert con_public == []
        sin_search_path = conn.execute(
            "SELECT proname FROM pg_proc WHERE prosecdef AND pronamespace = 'public'::regnamespace "
            "AND NOT coalesce(proconfig::text LIKE '%search_path%', false)"
        ).fetchall()
        assert sin_search_path == []


# ---------- El RLS de negocio sigue igual ----------
def test_las_politicas_de_negocio_siguen_aislando_empresas(app_conn, base):
    a, b = base["empresas"]["A"], base["empresas"]["B"]
    _contexto(app_conn, ANA, a)
    assert {e for (e,) in app_conn.execute("SELECT id_empresa FROM producto")} == {a}
    assert (
        app_conn.execute("UPDATE producto SET nombre = 'x' WHERE id_empresa = %s", (b,)).rowcount
        == 0
    )
    with pytest.raises(DENEGADO, match="row-level security"):
        app_conn.execute(
            "INSERT INTO categoria_producto (id_empresa, nombre) VALUES (%s, 'Intrusa')", (b,)
        )
    # Las pertenencias y la función del Administrador siguen funcionando.
    assert app_conn.execute("SELECT public.app_es_admin_de(%s)", (a,)).fetchone()[0] is True
    assert (
        app_conn.execute(
            "SELECT public.app_usuario_en_otras_empresas(%s, %s)", (MULTI, a)
        ).fetchone()[0]
        is True
    )


# ---------- Migración: sube, baja y vuelve a subir ----------
def test_la_migracion_baja_y_sube_sin_alterar_el_resto(cluster):
    nombre = f"{PREFIJO}migracion"
    crear_base(nombre)
    try:
        migrar(nombre, "upgrade", PREVIA)
        with admin(nombre) as conn:
            politicas_antes = conn.execute(
                "SELECT tablename, policyname, roles::text, cmd, qual, with_check FROM pg_policies "
                "WHERE tablename NOT IN ('usuario', 'sesion_refresh') ORDER BY 1, 2"
            ).fetchall()

        migrar(nombre, "upgrade", "head")
        migrar(nombre, "check")
        with admin(nombre) as conn:
            assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == HEAD
            nombres_antes = [fila[1] for fila in politicas_antes]
            assert (
                conn.execute(
                    "SELECT tablename, policyname, roles::text, cmd, qual, with_check "
                    "FROM pg_policies WHERE policyname = ANY(%s) ORDER BY 1, 2",
                    (nombres_antes,),
                ).fetchall()
                == politicas_antes
            ), "Las migraciones no deben cambiar las políticas de negocio existentes"
            # Lo único nuevo fuera de usuario y sesion_refresh: la lectura del dueño de las
            # funciones (iondu_funciones), que no afecta a iondu_app ni a iondu_worker.
            nuevas = conn.execute(
                "SELECT tablename, policyname, roles::text FROM pg_policies "
                "WHERE tablename NOT IN ('usuario', 'sesion_refresh') "
                "AND NOT policyname = ANY(%s) ORDER BY 1, 2",
                (nombres_antes,),
            ).fetchall()
            assert nuevas == [
                ("borrador_gasto", "borrador_gasto_app_tenant", "{iondu_app}"),
                ("borrador_gasto", "borrador_gasto_worker_insert", "{iondu_worker}"),
                ("buzon_correo", "buzon_correo_app_tenant", "{iondu_app}"),
                ("buzon_correo", "buzon_correo_worker_select", "{iondu_worker}"),
                ("buzon_correo", "buzon_correo_worker_update", "{iondu_worker}"),
                ("rol", "rol_funciones_select", "{iondu_funciones}"),
                ("usuario_empresa", "usuario_empresa_funciones_select", "{iondu_funciones}"),
            ]

        migrar(nombre, "downgrade", PREVIA)
        with admin(nombre) as conn:
            assert (
                conn.execute(
                    "SELECT relrowsecurity FROM pg_class WHERE relname = 'usuario'"
                ).fetchone()[0]
                is False
            )
            assert (
                conn.execute(
                    "SELECT count(*) FROM pg_policies "
                    "WHERE tablename IN ('usuario', 'sesion_refresh') "
                    "OR policyname LIKE '%funciones_select'"
                ).fetchone()[0]
                == 0
            )
            # Se restauran los permisos anteriores de iondu_app.
            assert (
                conn.execute(
                    "SELECT has_table_privilege('iondu_app', 'usuario', 'SELECT') "
                    "AND has_table_privilege('iondu_app', 'sesion_refresh', 'DELETE')"
                ).fetchone()[0]
                is True
            )

        migrar(nombre, "upgrade", "head")
        with admin(nombre) as conn:
            assert (
                conn.execute(
                    "SELECT count(*) FROM pg_policies "
                    "WHERE tablename IN ('usuario', 'sesion_refresh')"
                ).fetchone()[0]
                == 8
            )
    finally:
        borrar_base(nombre)
