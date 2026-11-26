"""Proteger usuario y sesion_refresh con RLS y un rol de autenticación dedicado.

Hasta ahora estas tablas no tenían RLS: iondu_app podía leer TODOS los usuarios (con su
hash de contraseña) y todas las sesiones, y modificar contraseñas de cualquiera.

El login y la renovación ocurren antes de saber quién es el usuario y en qué empresa
trabaja, así que una política por empresa no sirve. Diseño:

- Rol nuevo iondu_auth (conexión AUTH_DATABASE_URL, solo la usa el servicio de
  autenticación): login, renovación, cierre, cambio y restablecimiento de contraseña y
  creación de cuentas. Es el único que lee hashes y sesiones. No tiene permisos sobre
  ninguna otra tabla. Para impedir que un Administrador restablezca la contraseña de
  alguien que trabaja en otra empresa, ejecuta auth_puede_restablecer(usuario, empresa):
  una función SECURITY DEFINER de iondu_funciones que solo responde OK, NO_PERTENECE u
  OTRA_EMPRESA, sin dar acceso a usuario_empresa.
- iondu_app: en usuario solo puede leer id y correo de su propio usuario y de los
  miembros de la empresa del contexto que el RLS de usuario_empresa le deje ver (el
  Administrador, todos; el Operativo, solo a sí mismo). Nada en sesion_refresh.
- iondu_worker y PUBLIC: nada.
- RLS habilitado y FORZADO en ambas tablas (el dueño también queda sujeto).

El login no usa funciones SECURITY DEFINER: necesita leer el hash para verificarlo con
argon2 en Python, y una función que lo devuelva podría llamarla cualquier consulta de
iondu_app (por ejemplo, una inyección SQL). Con un rol y una conexión aparte, esa
consulta no tiene forma de leerlos.

El rol se crea si no existe con NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB
NOINHERIT. Si ya existe, puede tener LOGIN (el despliegue se lo da con
scripts/configurar_roles_locales.py), pero si tiene SUPERUSER, BYPASSRLS, CREATEROLE,
CREATEDB, INHERIT o REPLICATION la migración se detiene. iondu_funciones, además, debe ser
NOLOGIN.

Revision ID: d6a8c0e2f417
Revises: e1f3a5b7c902
Create Date: 2026-11-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d6a8c0e2f417"
down_revision: str | Sequence[str] | None = "e1f3a5b7c902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH = "iondu_auth"
USUARIO_ACTUAL = "NULLIF(current_setting('app.current_user_id', true), '')::uuid"
EMPRESA_ACTUAL = "NULLIF(current_setting('app.current_empresa_id', true), '')::integer"

USUARIO_COLUMNAS = "id, email, password_hash, activo, intentos_fallidos, bloqueado_hasta, creado_en"
SESION_COLUMNAS = "id, id_usuario, token_hash, creado_en, expira_en, rotada_en, revocada_en"

# (tabla, política, comando, rol, USING, WITH CHECK)
POLITICAS: tuple[tuple[str, str, str, str, str | None, str | None], ...] = (
    # iondu_app: su propio usuario y los miembros de la empresa del contexto que el RLS de
    # usuario_empresa le muestre. Solo id y correo (permisos por columna).
    (
        "usuario",
        "usuario_app_select",
        "SELECT",
        "iondu_app",
        f"""id = {USUARIO_ACTUAL}
            OR EXISTS (
                SELECT 1 FROM public.usuario_empresa AS ue
                WHERE ue.id_usuario = usuario.id AND ue.id_empresa = {EMPRESA_ACTUAL}
            )""",
        None,
    ),
    # iondu_auth: el login busca por correo y la renovación por hash del token, sin
    # contexto. Su aislamiento es el rol: nadie más usa esa conexión.
    ("usuario", "usuario_auth_select", "SELECT", AUTH, "true", None),
    ("usuario", "usuario_auth_insert", "INSERT", AUTH, None, "true"),
    ("usuario", "usuario_auth_update", "UPDATE", AUTH, "true", "true"),
    ("sesion_refresh", "sesion_refresh_auth_select", "SELECT", AUTH, "true", None),
    (
        "sesion_refresh",
        "sesion_refresh_auth_insert",
        "INSERT",
        AUTH,
        None,
        # Solo se abren sesiones de cuentas activas.
        """EXISTS (
            SELECT 1 FROM public.usuario AS u WHERE u.id = id_usuario AND u.activo
        )""",
    ),
    ("sesion_refresh", "sesion_refresh_auth_update", "UPDATE", AUTH, "true", "true"),
    ("sesion_refresh", "sesion_refresh_auth_delete", "DELETE", AUTH, "true", None),
)

PUEDE_RESTABLECER = "public.auth_puede_restablecer(uuid, integer)"


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
    # Antes de conceder nada: iondu_auth (se crea NOLOGIN si falta) e iondu_funciones (de la
    # migración anterior) deben tener atributos seguros. iondu_auth puede tener LOGIN: se lo
    # da scripts/configurar_roles_locales.py y la API se conecta con él, así que la migración
    # se puede volver a ejecutar (tras una bajada) sin tocarlo. iondu_funciones nunca.
    asegurar_rol_restringido(AUTH, permitir_login=True)
    asegurar_rol_restringido("iondu_funciones", crear=False)

    # Se parte de cero en las dos tablas (REVOKE ALL también quita los permisos por columna).
    op.execute(
        "REVOKE ALL ON public.usuario, public.sesion_refresh "
        f"FROM iondu_app, iondu_worker, {AUTH}, PUBLIC"
    )

    # iondu_app: id y correo (listado de usuarios, historiales de auditoría y del agente).
    op.execute("GRANT SELECT (id, email) ON public.usuario TO iondu_app")

    # iondu_auth: lo que usa el servicio de autenticación (y nada más).
    op.execute(f"GRANT SELECT ({USUARIO_COLUMNAS}) ON public.usuario TO {AUTH}")
    op.execute(f"GRANT INSERT (id, email, password_hash) ON public.usuario TO {AUTH}")
    op.execute(
        f"GRANT UPDATE (password_hash, intentos_fallidos, bloqueado_hasta) "
        f"ON public.usuario TO {AUTH}"
    )
    op.execute(f"GRANT SELECT ({SESION_COLUMNAS}) ON public.sesion_refresh TO {AUTH}")
    # El INSERT del ORM nombra rotada_en y revocada_en (en NULL): no tienen server_default.
    op.execute(
        "GRANT INSERT (id, id_usuario, token_hash, expira_en, rotada_en, revocada_en) "
        f"ON public.sesion_refresh TO {AUTH}"
    )
    op.execute(f"GRANT UPDATE (rotada_en, revocada_en) ON public.sesion_refresh TO {AUTH}")
    # Limpieza de las sesiones vencidas del usuario al iniciar sesión.
    op.execute(f"GRANT DELETE ON public.sesion_refresh TO {AUTH}")

    # ¿Puede un Administrador de p_empresa restablecer la contraseña de p_usuario? Solo si
    # pertenece a esa empresa y no tiene otra pertenencia activa. Responde un código y nada
    # más: iondu_auth no obtiene acceso a usuario_empresa. Dueño: iondu_funciones (migración
    # e1f3a5b7c902), que solo lee las columnas necesarias.
    op.execute(
        """
        CREATE FUNCTION public.auth_puede_restablecer(p_usuario uuid, p_empresa integer)
        RETURNS text
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT CASE
                WHEN p_usuario IS NULL OR p_empresa IS NULL OR NOT EXISTS (
                    SELECT 1 FROM public.usuario_empresa AS ue
                    WHERE ue.id_usuario = p_usuario AND ue.id_empresa = p_empresa
                ) THEN 'NO_PERTENECE'
                WHEN EXISTS (
                    SELECT 1 FROM public.usuario_empresa AS ue
                    WHERE ue.id_usuario = p_usuario
                      AND ue.id_empresa <> p_empresa
                      AND ue.estado = 'ACTIVO'
                ) THEN 'OTRA_EMPRESA'
                ELSE 'OK'
            END;
        $$
        """
    )
    op.execute(f"REVOKE ALL ON FUNCTION {PUEDE_RESTABLECER} FROM PUBLIC")
    op.execute("GRANT CREATE ON SCHEMA public TO iondu_funciones")
    op.execute(f"ALTER FUNCTION {PUEDE_RESTABLECER} OWNER TO iondu_funciones")
    op.execute("REVOKE CREATE ON SCHEMA public FROM iondu_funciones")
    op.execute(f"GRANT EXECUTE ON FUNCTION {PUEDE_RESTABLECER} TO {AUTH}")

    for tabla in ("usuario", "sesion_refresh"):
        op.execute(f"ALTER TABLE public.{tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{tabla} FORCE ROW LEVEL SECURITY")

    for tabla, politica, comando, rol, using, check in POLITICAS:
        sentencia = f"CREATE POLICY {politica} ON public.{tabla} FOR {comando} TO {rol}"
        if using is not None:
            sentencia += f" USING ({using})"
        if check is not None:
            sentencia += f" WITH CHECK ({check})"
        op.execute(sentencia)


def downgrade() -> None:
    for tabla, politica, *_ in reversed(POLITICAS):
        op.execute(f"DROP POLICY IF EXISTS {politica} ON public.{tabla}")
    for tabla in ("usuario", "sesion_refresh"):
        op.execute(f"ALTER TABLE public.{tabla} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{tabla} DISABLE ROW LEVEL SECURITY")

    op.execute(f"REVOKE ALL ON public.usuario, public.sesion_refresh FROM iondu_app, {AUTH}")
    op.execute(f"DROP FUNCTION IF EXISTS {PUEDE_RESTABLECER}")

    # Permisos anteriores de iondu_app (migraciones e5b1c7a9d203 y f7a2d4c8e915).
    # El rol iondu_auth no se borra: puede tener LOGIN y conexiones del despliegue.
    op.execute("GRANT SELECT ON public.usuario TO iondu_app")
    op.execute("GRANT INSERT (id, email, password_hash) ON public.usuario TO iondu_app")
    op.execute(
        "GRANT UPDATE (password_hash, intentos_fallidos, bloqueado_hasta) "
        "ON public.usuario TO iondu_app"
    )
    op.execute("GRANT SELECT, INSERT, DELETE ON public.sesion_refresh TO iondu_app")
    op.execute("GRANT UPDATE (rotada_en, revocada_en) ON public.sesion_refresh TO iondu_app")
