"""Da a un usuario de Supabase acceso a una empresa de la base LOCAL de desarrollo.

En producción las pertenencias se crean desde el sistema; en local, la base no conoce
a los usuarios de Supabase, así que tras iniciar sesión en el frontend la API responde
NO_COMPANY. Este script registra el id del usuario en auth.users (tabla auxiliar local)
y le crea la pertenencia a la empresa con el rol indicado.

El id (UUID) del usuario se ve en Supabase > Authentication > Users.

Uso, desde backend/ (con Docker encendido):
    $env:DATABASE_URL = "postgresql+psycopg://iondu:<clave>@127.0.0.1:15432/iondu"
    .venv\\Scripts\\python.exe -m scripts.asignar_usuario_local `
        --usuario <uuid> --nombre "Franklin Aguilar" [--empresa 1] [--rol Operativo]
"""

import argparse
import os
import sys
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

SERVIDORES_LOCALES = {"127.0.0.1", "localhost", "db"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--usuario", required=True, type=uuid.UUID, help="id del usuario en Supabase"
    )
    parser.add_argument("--nombre", required=True, help="nombre que se mostrará en la empresa")
    parser.add_argument("--empresa", type=int, default=1, help="id de la empresa (por defecto 1)")
    parser.add_argument("--rol", choices=("Administrador", "Operativo"), default="Administrador")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL", "")
    destino = make_url(url) if url else None
    if destino is None or destino.host not in SERVIDORES_LOCALES or destino.database != "iondu":
        sys.exit("Solo se usa con la base local iondu (define DATABASE_URL con 127.0.0.1:15432).")

    from app.db.base import auth_users
    from app.models import Empresa, Rol, UsuarioEmpresa

    engine = create_engine(destino)
    with Session(engine) as db:
        empresa = db.get(Empresa, args.empresa)
        if empresa is None:
            sys.exit(f"No existe la empresa {args.empresa}. ¿Cargaste los datos demo?")
        rol = db.scalar(select(Rol).where(Rol.nombre == args.rol))
        if rol is None:
            sys.exit(f"No existe el rol {args.rol}. ¿Cargaste los datos demo?")

        if db.scalar(select(auth_users.c.id).where(auth_users.c.id == args.usuario)) is None:
            db.execute(auth_users.insert().values(id=args.usuario))

        pertenencia = db.get(UsuarioEmpresa, (args.usuario, args.empresa))
        if pertenencia is None:
            db.add(
                UsuarioEmpresa(
                    id_usuario=args.usuario,
                    id_empresa=args.empresa,
                    id_rol=rol.id_rol,
                    nombre_visible=args.nombre,
                    estado="ACTIVO",
                )
            )
            accion = "creada"
        else:
            pertenencia.id_rol = rol.id_rol
            pertenencia.nombre_visible = args.nombre
            pertenencia.estado = "ACTIVO"
            accion = "actualizada"
        nombre_empresa = empresa.razon_social
        db.commit()
    engine.dispose()
    print(f"Pertenencia {accion}: {args.nombre} es {args.rol} en {nombre_empresa}")


if __name__ == "__main__":
    main()
