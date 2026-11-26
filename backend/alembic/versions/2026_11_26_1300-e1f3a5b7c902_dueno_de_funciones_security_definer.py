"""Dar a las funciones SECURITY DEFINER un dueño que pueda leer lo que consultan.

app_es_admin_de y app_usuario_en_otras_empresas leen usuario_empresa y rol, que tienen
RLS FORZADO con políticas solo para iondu_app. Una función SECURITY DEFINER se ejecuta
como su dueño: si el dueño no tiene BYPASSRLS (por ejemplo, iondu_migrator), el RLS le
oculta todas las filas y las funciones devuelven siempre false. Entonces:
- el Administrador no ve, no agrega y no edita las pertenencias de su empresa
  (usuario_empresa_app_admin_*), ni lee la auditoría (auditoria_app_select);
- "¿trabaja en otra empresa?" responde siempre que no.

Corrección, sin BYPASSRLS para nadie: un rol iondu_funciones NOLOGIN (nadie puede
conectarse con él) que es dueño de esas funciones y solo puede leer las columnas que ellas
usan, mediante políticas exclusivas para él. Las funciones conservan su código, su
search_path fijo y sus permisos de EXECUTE (solo iondu_app, nunca PUBLIC).

Cambiar el dueño de una función exige ser superusuario (o miembro del rol destino con
CREATE en el esquema): se ejecuta como el administrador de la base, igual que el resto
de las migraciones.

Revision ID: e1f3a5b7c902
Revises: c4e6a8b0d215
Create Date: 2026-11-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e1f3a5b7c902"
down_revision: str | Sequence[str] | None = "c4e6a8b0d215"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DUENO = "iondu_funciones"
FUNCIONES = (
    "public.app_es_admin_de(integer)",
    "public.app_usuario_en_otras_empresas(uuid, integer)",
)


# El dueño anterior se guarda en el comentario de la función para que la bajada lo
# restaure EXACTO (en una base puede ser iondu; en otra, iondu_migrator).
MARCA = "iondu:dueno_anterior"


def recordar_dueno(funcion: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE
            anterior text;
            comentario text;
        BEGIN
            SELECT pg_get_userbyid(proowner), obj_description(oid, 'pg_proc')
            INTO anterior, comentario
            FROM pg_proc WHERE oid = '{funcion}'::regprocedure;
            EXECUTE format(
                'COMMENT ON FUNCTION {funcion} IS %L',
                concat_ws(E'\\n', comentario, '[{MARCA}=' || anterior || ']')
            );
        END
        $$;
        """
    )


def restaurar_dueno(funcion: str) -> None:
    """Devuelve la función a su dueño anterior y deja el comentario como estaba."""
    op.execute(
        f"""
        DO $$
        DECLARE
            comentario text;
            anterior text;
        BEGIN
            SELECT obj_description(oid, 'pg_proc') INTO comentario
            FROM pg_proc WHERE oid = '{funcion}'::regprocedure;
            anterior := substring(comentario FROM '\\[{MARCA}=([^]]+)\\]');
            EXECUTE format(
                'ALTER FUNCTION {funcion} OWNER TO %I', coalesce(anterior, current_user)
            );
            comentario := nullif(
                regexp_replace(comentario, '\\n?\\[{MARCA}=[^]]+\\]', ''), ''
            );
            EXECUTE format('COMMENT ON FUNCTION {funcion} IS %L', comentario);
        END
        $$;
        """
    )


def asignar_dueno(funcion: str) -> None:
    """ALTER FUNCTION ... OWNER TO iondu_funciones (PostgreSQL exige que el nuevo dueño
    tenga CREATE en el esquema: se le da solo durante el cambio)."""
    recordar_dueno(funcion)
    op.execute(f"GRANT CREATE ON SCHEMA public TO {DUENO}")
    op.execute(f"ALTER FUNCTION {funcion} OWNER TO {DUENO}")
    op.execute(f"REVOKE CREATE ON SCHEMA public FROM {DUENO}")


# Atributos obligatorios. Un rol que no existe se crea con todos ellos (NOLOGIN incluido).
# Si ya existe y no los cumple, la migración se DETIENE: no se corrigen en silencio, porque
# un rol con privilegios de administrador no debe recibir permisos ni ser dueño de funciones
# privilegiadas. LOGIN solo se tolera donde se indica (iondu_auth: la API se conecta con él).
ATRIBUTOS_SEGUROS = "NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOINHERIT"


def asegurar_rol_restringido(rol: str, *, crear: bool = True, permitir_login: bool = False) -> None:
    accion_si_falta = (
        f'CREATE ROLE "{rol}" NOLOGIN {ATRIBUTOS_SEGUROS};'
        if crear
        else f"RAISE EXCEPTION 'No existe el rol {rol}: aplica antes las migraciones previas.';"
    )
    revisar_login = "" if permitir_login else "CASE WHEN r.rolcanlogin THEN 'LOGIN' END,"
    exigidos = ATRIBUTOS_SEGUROS if permitir_login else f"NOLOGIN {ATRIBUTOS_SEGUROS}"
    op.execute(
        f"""
        DO $$
        DECLARE
            r pg_roles%ROWTYPE;
            problemas text;
        BEGIN
            SELECT * INTO r FROM pg_roles WHERE rolname = '{rol}';
            IF NOT FOUND THEN
                {accion_si_falta}
                RETURN;
            END IF;
            problemas := concat_ws(', ',
                {revisar_login}
                CASE WHEN r.rolsuper THEN 'SUPERUSER' END,
                CASE WHEN r.rolbypassrls THEN 'BYPASSRLS' END,
                CASE WHEN r.rolcreaterole THEN 'CREATEROLE' END,
                CASE WHEN r.rolcreatedb THEN 'CREATEDB' END,
                CASE WHEN r.rolinherit THEN 'INHERIT' END,
                CASE WHEN r.rolreplication THEN 'REPLICATION' END
            );
            IF problemas <> '' THEN
                RAISE EXCEPTION 'El rol {rol} ya existe con atributos no permitidos: %', problemas
                    USING HINT = 'Revísalo y ajústalo con ALTER ROLE {rol} '
                        || '{exigidos}; la migración no cambia atributos.';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    # Primero: el rol dueño existe con atributos seguros (o se crea así).
    asegurar_rol_restringido(DUENO)
    # Solo las columnas que leen las funciones.
    op.execute(
        f"GRANT SELECT (id_usuario, id_empresa, id_rol, estado) "
        f"ON public.usuario_empresa TO {DUENO}"
    )
    op.execute(f"GRANT SELECT (id_rol, nombre) ON public.rol TO {DUENO}")
    op.execute(
        f"CREATE POLICY usuario_empresa_funciones_select ON public.usuario_empresa "
        f"FOR SELECT TO {DUENO} USING (true)"
    )
    op.execute(
        f"CREATE POLICY rol_funciones_select ON public.rol FOR SELECT TO {DUENO} USING (true)"
    )
    for funcion in FUNCIONES:
        asignar_dueno(funcion)


def downgrade() -> None:
    # Las funciones vuelven a su dueño anterior (guardado al subir).
    for funcion in FUNCIONES:
        restaurar_dueno(funcion)
    op.execute("DROP POLICY IF EXISTS rol_funciones_select ON public.rol")
    op.execute("DROP POLICY IF EXISTS usuario_empresa_funciones_select ON public.usuario_empresa")
    op.execute(f"REVOKE ALL ON public.usuario_empresa, public.rol FROM {DUENO}")
    # El rol NOLOGIN no se borra: no tiene acceso a nada y otra base del clúster podría usarlo.
