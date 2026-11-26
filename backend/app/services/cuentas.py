"""Operaciones sobre cuentas que el Administrador dispara, ejecutadas con el rol iondu_auth.

iondu_app no puede leer hashes ni sesiones, ni buscar correos de otras empresas. Por eso
estas operaciones van por la conexión de autenticación. Lo que el cliente decide está
acotado: UsuarioService ya comprobó con iondu_app (y el RLS) que quien llama es Administrador
de la empresa y que el usuario elegido pertenece a ella. Aquí se vuelve a comprobar con
datos que la API no puede manipular, dentro de la misma transacción que escribe.
"""

import uuid

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core import contrasenas
from app.core.errors import ConflictError, NotFoundError
from app.models import SesionRefresh, Usuario


class CuentasAuth:
    def __init__(self, db: Session):
        self.db = db

    def buscar_o_crear(self, email: str, contrasena: str) -> tuple[uuid.UUID, bool]:
        """Id de la cuenta con ese correo; la crea si no existe. (id, creada)."""
        nueva = uuid.uuid4()

        # ON CONFLICT: dos administradores pueden crear el mismo correo a la vez.
        creada = self.db.scalar(
            insert(Usuario)
            .values(id=nueva, email=email, password_hash=contrasenas.hashear(contrasena))
            .on_conflict_do_nothing(index_elements=[Usuario.email])
            .returning(Usuario.id)
        )

        if creada is None:
            existente = self.db.scalar(select(Usuario.id).where(Usuario.email == email))
            self.db.commit()

            if existente is None:
                raise RuntimeError(
                    "No se pudo recuperar la cuenta existente después de un conflicto de correo."
                )

            return existente, False

        self.db.commit()
        return creada, True

    def restablecer_contrasena(
        self, id_usuario: uuid.UUID, id_empresa: int, contrasena: str
    ) -> None:
        """Cambia la contraseña y revoca todas las sesiones atómicamente.

        Solo si el usuario pertenece a la empresa y no tiene otra pertenencia activa.
        El bloqueo de la cuenta se adquiere antes de comprobar las pertenencias para
        evitar cambios concurrentes durante el restablecimiento.
        """

        # Primero bloquea la cuenta para serializar las operaciones concurrentes.
        usuario = self.db.scalar(
            select(Usuario.id).where(Usuario.id == id_usuario).with_for_update()
        )

        if usuario is None:
            self.db.rollback()
            raise NotFoundError(
                "El usuario no existe.",
                code="USER_NOT_FOUND",
            )

        # SECURITY DEFINER: iondu_auth no lee usuario_empresa directamente.
        # La comprobación ocurre mientras se mantiene bloqueada la cuenta.
        respuesta = self.db.scalar(
            text("SELECT public.auth_puede_restablecer(:usuario, :empresa)"),
            {"usuario": id_usuario, "empresa": id_empresa},
        )

        if respuesta == "NO_PERTENECE":
            self.db.rollback()
            raise NotFoundError(
                "El usuario no pertenece a esta empresa.",
                code="USER_NOT_FOUND",
            )

        if respuesta != "OK":
            self.db.rollback()
            raise ConflictError(
                "Este usuario también trabaja en otra empresa: solo él puede cambiar su "
                "contraseña.",
                code="USER_IN_OTHER_COMPANY",
            )

        self.db.execute(
            update(Usuario)
            .where(Usuario.id == id_usuario)
            .values(
                password_hash=contrasenas.hashear(contrasena),
                intentos_fallidos=0,
                bloqueado_hasta=None,
            )
        )

        self.db.execute(
            update(SesionRefresh)
            .where(
                SesionRefresh.id_usuario == id_usuario,
                SesionRefresh.revocada_en.is_(None),
            )
            .values(revocada_en=func.now())
        )

        self.db.commit()
