import re

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnprocessableError
from app.models import SecuenciaComprobante


class SecuenciaComprobanteService:
    """Reserva secuenciales únicos por empresa y configuración del comprobante.

    La sesión y su transacción pertenecen al servicio que coordina la emisión.
    El llamador debe confirmar la transacción antes de enviar el comprobante al SRI.
    """

    def __init__(self, db: Session):
        self._db = db

    def reservar(
        self,
        *,
        id_empresa: int,
        establecimiento: str,
        punto_emision: str,
        tipo_comprobante: str,
    ) -> int:
        """Reserva y devuelve el siguiente secuencial, comenzando en 1."""

        if id_empresa <= 0:
            raise UnprocessableError("La empresa indicada no es válida.")

        configuracion = {
            "establecimiento": (establecimiento, r"[0-9]{3}"),
            "punto_emision": (punto_emision, r"[0-9]{3}"),
            "tipo_comprobante": (tipo_comprobante, r"[0-9]{2}"),
        }

        for campo, (valor, patron) in configuracion.items():
            if not isinstance(valor, str) or re.fullmatch(patron, valor) is None:
                raise UnprocessableError(f"El campo {campo} tiene un formato inválido.")

        tabla = SecuenciaComprobante

        stmt = (
            insert(tabla)
            .values(
                id_empresa=id_empresa,
                establecimiento=establecimiento,
                punto_emision=punto_emision,
                tipo_comprobante=tipo_comprobante,
                ultimo_secuencial=1,
            )
            .on_conflict_do_update(
                constraint="secuencia_comprobante_configuracion_uq",
                set_={
                    "ultimo_secuencial": tabla.ultimo_secuencial + 1,
                },
                where=tabla.ultimo_secuencial < 999_999_999,
            )
            .returning(tabla.ultimo_secuencial)
        )

        secuencial = self._db.scalar(stmt)

        if secuencial is None:
            raise ConflictError("Se agotaron los secuenciales disponibles para esta configuración.")

        return int(secuencial)
