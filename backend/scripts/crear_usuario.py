"""Crea un usuario (o le cambia la contraseña) y le da acceso a una empresa.

Sirve para el primer Administrador de cada ambiente y para restablecer contraseñas.
Usa MIGRATION_DATABASE_URL (credencial administrativa): la API no puede crear usuarios.
Si el correo ya existe, actualiza su contraseña, lo reactiva, quita el bloqueo y
cierra sus sesiones abiertas.

Uso, con Docker encendido (pide la contraseña sin mostrarla):
    docker compose exec api python -m scripts.crear_usuario `
        --email ana@empresa.ec --nombre "Ana Torres" [--empresa 1] [--rol Operativo]

Sin terminal interactiva, la contraseña se lee de la entrada estándar con --password-stdin.
"""

import argparse
import getpass
import sys

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from app.core import contrasenas
from app.core.config import get_settings
from app.models import Empresa, Rol, SesionRefresh, Usuario, UsuarioEmpresa
from app.models.rol import ADMINISTRADOR, OPERATIVO
from app.services.autenticacion import normalizar_email


def _leer_contrasena(desde_stdin: bool) -> str:
    if desde_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    primera = getpass.getpass("Contraseña: ")
    if getpass.getpass("Repite la contraseña: ") != primera:
        sys.exit("Las contraseñas no coinciden.")
    return primera


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", required=True, help="nombre que se mostrará en la empresa")
    parser.add_argument("--empresa", type=int, default=1, help="id de la empresa (por defecto 1)")
    parser.add_argument("--rol", choices=(ADMINISTRADOR, OPERATIVO), default=ADMINISTRADOR)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()

    email = normalizar_email(args.email)
    if "@" not in email:
        sys.exit("El correo no es válido.")
    contrasena = _leer_contrasena(args.password_stdin)
    try:
        contrasenas.validar_nueva(contrasena)
    except ValueError as exc:
        sys.exit(str(exc))

    url = get_settings().migration_database_url
    if not url:
        sys.exit("Define MIGRATION_DATABASE_URL (credencial administrativa de la base).")

    engine = create_engine(url)
    try:
        with Session(engine) as db:
            empresa = db.get(Empresa, args.empresa)
            if empresa is None:
                sys.exit(f"No existe la empresa {args.empresa}.")
            rol = db.scalar(select(Rol).where(Rol.nombre == args.rol))
            if rol is None:
                sys.exit(f"No existe el rol {args.rol}. ¿Aplicaste las migraciones?")

            usuario = db.scalar(select(Usuario).where(Usuario.email == email))
            if usuario is None:
                usuario = Usuario(email=email, password_hash=contrasenas.hashear(contrasena))
                db.add(usuario)
                db.flush()
                accion = "creado"
            else:
                usuario.password_hash = contrasenas.hashear(contrasena)
                usuario.activo = True
                usuario.intentos_fallidos = 0
                usuario.bloqueado_hasta = None
                db.execute(
                    update(SesionRefresh)
                    .where(
                        SesionRefresh.id_usuario == usuario.id,
                        SesionRefresh.revocada_en.is_(None),
                    )
                    .values(revocada_en=func.now())
                )
                accion = "actualizado"

            pertenencia = db.get(UsuarioEmpresa, (usuario.id, empresa.id_empresa))
            if pertenencia is None:
                db.add(
                    UsuarioEmpresa(
                        id_usuario=usuario.id,
                        id_empresa=empresa.id_empresa,
                        id_rol=rol.id_rol,
                        nombre_visible=args.nombre,
                        estado="ACTIVO",
                    )
                )
            else:
                pertenencia.id_rol = rol.id_rol
                pertenencia.nombre_visible = args.nombre
                pertenencia.estado = "ACTIVO"
            nombre_empresa = empresa.razon_social
            db.commit()
    finally:
        engine.dispose()

    print(f"Usuario {accion}: {email} es {args.rol} en {nombre_empresa}.")


if __name__ == "__main__":
    main()
