"""Validar membresía activa en las operaciones de negocio.

Revision ID: f3a8c1d72e90
Revises: c82f6a91d304
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f3a8c1d72e90"
down_revision: str | Sequence[str] | None = "c82f6a91d304"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.validar_membresia_activa()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.id_usuario IS NOT NULL
               AND NOT EXISTS (
                    SELECT 1
                    FROM public.usuario_empresa AS ue
                    WHERE ue.id_usuario = NEW.id_usuario
                      AND ue.id_empresa = NEW.id_empresa
                      AND ue.estado = 'ACTIVO'
               )
            THEN
                RAISE EXCEPTION
                    'El usuario no tiene membresia activa en la empresa %',
                    NEW.id_empresa;
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_venta_membresia_activa
        BEFORE INSERT OR UPDATE OF id_usuario, id_empresa
        ON public.venta
        FOR EACH ROW
        EXECUTE FUNCTION public.validar_membresia_activa();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_gasto_membresia_activa
        BEFORE INSERT OR UPDATE OF id_usuario, id_empresa
        ON public.gasto
        FOR EACH ROW
        EXECUTE FUNCTION public.validar_membresia_activa();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_movimiento_inventario_membresia_activa
        BEFORE INSERT OR UPDATE OF id_usuario, id_empresa
        ON public.movimiento_inventario
        FOR EACH ROW
        EXECUTE FUNCTION public.validar_membresia_activa();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_accion_ia_membresia_activa
        BEFORE INSERT OR UPDATE OF id_usuario, id_empresa
        ON public.accion_ia
        FOR EACH ROW
        WHEN (NEW.id_usuario IS NOT NULL)
        EXECUTE FUNCTION public.validar_membresia_activa();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_accion_ia_membresia_activa ON public.accion_ia")
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_movimiento_inventario_membresia_activa
        ON public.movimiento_inventario
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_gasto_membresia_activa ON public.gasto")
    op.execute("DROP TRIGGER IF EXISTS trg_venta_membresia_activa ON public.venta")
    op.execute("DROP FUNCTION IF EXISTS public.validar_membresia_activa()")
