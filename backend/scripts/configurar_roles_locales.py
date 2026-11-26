"""Habilita en la base LOCAL los roles de ejecución con la contraseña del .env.

En producción la API se conecta como iondu_app (negocio) e iondu_auth (login y
contraseñas), y el worker como iondu_worker: sin privilegios de administrador y sujetos a
RLS. Para que en local pase lo mismo (y los errores de permisos aparezcan aquí y no en
producción), este script les da LOGIN con la contraseña que traen DATABASE_URL,
AUTH_DATABASE_URL y WORKER_DATABASE_URL.

Solo hace ALTER ROLE ... LOGIN PASSWORD: no concede privilegios. No hay contraseñas
predeterminadas: cada una sale del .env y se rechaza si es corta, si es un marcador del
.env.example (<clave>), si se repite entre roles o si es la del administrador.
Tampoco habilita un rol que tenga privilegios de administrador (SUPERUSER, BYPASSRLS,
CREATEROLE, CREATEDB): eso indicaría que no es el rol que crearon las migraciones.
iondu_funciones (dueño de las funciones SECURITY DEFINER) nunca recibe LOGIN.

Los roles los crean las migraciones (b72e91c4a630: iondu_app e iondu_worker;
d6a8c0e2f417: iondu_auth). Correrlo después de `alembic upgrade head`.
Usa MIGRATION_DATABASE_URL (el usuario iondu, administrador de la base local).

Uso, con Docker encendido:
    docker compose run --rm --no-deps api python -m scripts.configurar_roles_locales
"""

import sys

from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.core.config import get_settings

SERVIDORES_LOCALES = {"127.0.0.1", "localhost", "db"}
# Cada conexión con su rol: DATABASE_URL no puede usar iondu_auth, ni al revés.
ROL_DE_CADA_URL = {
    "DATABASE_URL": "iondu_app",
    "AUTH_DATABASE_URL": "iondu_auth",
    "WORKER_DATABASE_URL": "iondu_worker",
}
ROLES_SIN_LOGIN = ("iondu_funciones",)
LONGITUD_MINIMA = 12
ATRIBUTOS_PROHIBIDOS = ("rolsuper", "rolbypassrls", "rolcreaterole", "rolcreatedb")


def validar_credenciales(urls: dict[str, str | None], clave_admin: str | None) -> dict[str, str]:
    """{rol: contraseña} a partir de las URL del .env; termina con un mensaje si algo falla."""
    credenciales: dict[str, str] = {}
    for variable, rol in ROL_DE_CADA_URL.items():
        url = urls.get(variable)
        destino = make_url(url) if url else None
        if destino is None:
            sys.exit(f"Define {variable} con el usuario {rol} (ver .env.example).")
        if destino.username != rol:
            sys.exit(f"{variable} debe usar el usuario {rol}, no {destino.username}.")
        clave = destino.password or ""
        if len(clave) < LONGITUD_MINIMA:
            sys.exit(
                f"La contraseña de {variable} debe tener al menos {LONGITUD_MINIMA} caracteres."
            )
        if "<" in clave or ">" in clave:
            sys.exit(f"{variable} tiene un marcador del .env.example: escribe una contraseña real.")
        if clave_admin and clave == clave_admin:
            sys.exit(f"{variable} no puede usar la contraseña del administrador.")
        credenciales[rol] = clave
    if len(set(credenciales.values())) != len(credenciales):
        sys.exit("Cada rol necesita una contraseña distinta.")
    return credenciales


def main() -> None:
    settings = get_settings()
    if not settings.migration_database_url:
        sys.exit("Define MIGRATION_DATABASE_URL (usuario administrador de la base local).")
    admin = make_url(settings.migration_database_url)
    if admin.host not in SERVIDORES_LOCALES or admin.database != "iondu":
        sys.exit("Solo se usa con la base local iondu.")

    credenciales = validar_credenciales(
        {
            "DATABASE_URL": settings.database_url,
            "AUTH_DATABASE_URL": settings.auth_database_url,
            "WORKER_DATABASE_URL": settings.worker_database_url,
        },
        admin.password,
    )

    engine = create_engine(admin)
    try:
        with engine.begin() as conn:
            cursor = conn.connection.cursor()
            cursor.execute(
                "SELECT rolname, rolcanlogin, " + ", ".join(ATRIBUTOS_PROHIBIDOS) + " "
                "FROM pg_roles WHERE rolname = ANY(%s)",
                ([*credenciales, *ROLES_SIN_LOGIN],),
            )
            roles = {fila[0]: fila[1:] for fila in cursor.fetchall()}
            for rol in credenciales:
                if rol not in roles:
                    sys.exit(f"No existe el rol {rol}: ejecuta antes `alembic upgrade head`.")
                if any(roles[rol][1:]):
                    sys.exit(f"{rol} tiene privilegios de administrador; revísalo antes de seguir.")
            for rol in ROLES_SIN_LOGIN:
                if rol in roles and roles[rol][0]:
                    sys.exit(f"{rol} no debe poder iniciar sesión (ALTER ROLE {rol} NOLOGIN).")

            for rol, contrasena in credenciales.items():
                cursor.execute(
                    sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(rol), sql.Literal(contrasena)
                    )
                )
                print(f"{rol}: LOGIN habilitado.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
