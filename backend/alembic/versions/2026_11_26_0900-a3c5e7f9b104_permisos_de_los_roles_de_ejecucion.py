"""Conceder en una migración los permisos de los roles de ejecución.

Hasta ahora los GRANT de iondu_app (API) e iondu_worker se aplicaban a mano en
Supabase, y un ambiente nuevo quedaba sin permisos. Aquí quedan todos, con el
mínimo necesario: lectura e inserción por tabla y UPDATE solo de las columnas que
el código modifica. Las tablas sin funcionalidad (dashboard_financiero, accion_ia,
recomendacion, consumo_tokens) no reciben nada. GRANT es idempotente: aplicarlo
sobre una base que ya los tenía no cambia nada.

Las columnas Identity no necesitan USAGE sobre su secuencia.

Revision ID: a3c5e7f9b104
Revises: f7a2d4c8e915
Create Date: 2026-11-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a3c5e7f9b104"
down_revision: str | Sequence[str] | None = "f7a2d4c8e915"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP = "iondu_app"
WORKER = "iondu_worker"

# (rol, tabla, privilegios de tabla, columnas con UPDATE)
PERMISOS: tuple[tuple[str, str, str | None, tuple[str, ...]], ...] = (
    (
        APP,
        "empresa",
        "SELECT",
        (
            "razon_social",
            "nombre_comercial",
            "actividad_economica",
            "direccion",
            "correo_electronico",
            "datos_facturacion_electronica",
            "certificado_p12_cifrado",
            "certificado_password_cifrada",
            "certificado_fecha_vencimiento",
        ),
    ),
    (APP, "rol", "SELECT", ()),
    (
        APP,
        "cliente",
        "SELECT, INSERT",
        (
            "tipo_identificacion",
            "identificacion",
            "nombre_razon_social",
            "direccion",
            "telefono",
            "correo_electronico",
        ),
    ),
    (APP, "categoria_producto", "SELECT, INSERT", ()),
    (
        APP,
        "producto",
        "SELECT, INSERT",
        (
            "codigo_principal",
            "nombre",
            "descripcion",
            "id_categoria_producto",
            "tipo",
            "unidad_medida",
            "precio_venta",
            "precio_compra",
            "codigo_porcentaje_iva",
            "stock_actual",
            "stock_minimo",
            "activo",
        ),
    ),
    (APP, "venta", "SELECT, INSERT", ("estado", "observacion")),
    (APP, "detalle_venta", "SELECT, INSERT", ()),
    (APP, "movimiento_inventario", "SELECT, INSERT", ()),
    (
        APP,
        "factura",
        "SELECT, INSERT",
        (
            "numero_comprobante",
            "clave_acceso",
            "estado_autorizacion",
            "mensajes_sri",
            "intentos_envio",
            "subtotal",
            "impuestos",
            "total",
            "fecha_emision",
            "xml_firmado",
            "numero_autorizacion",
            "fecha_autorizacion",
            "xml_autorizado",
            "pdf_ride_path",
        ),
    ),
    (APP, "secuencia_comprobante", "SELECT, INSERT", ("ultimo_secuencial",)),
    (APP, "categoria_gasto", "SELECT, INSERT", ()),
    (
        APP,
        "proveedor",
        "SELECT, INSERT",
        ("ruc_identificacion", "razon_social", "telefono", "correo_electronico", "direccion"),
    ),
    (
        APP,
        "gasto",
        "SELECT, INSERT",
        (
            "id_categoria_gasto",
            "id_proveedor",
            "monto",
            "iva",
            "concepto",
            "metodo_pago",
            "fecha",
            "numero_comprobante",
            "estado",
        ),
    ),
    # El worker solo reintenta facturas pendientes y guarda el resultado del SRI.
    (WORKER, "empresa", "SELECT", ()),
    (
        WORKER,
        "factura",
        "SELECT",
        (
            "estado_autorizacion",
            "numero_autorizacion",
            "fecha_autorizacion",
            "mensajes_sri",
            "intentos_envio",
            "xml_autorizado",
            "pdf_ride_path",
        ),
    ),
)


def upgrade() -> None:
    for rol in (APP, WORKER):
        op.execute(
            f"""
            DO $$
            BEGIN
                EXECUTE format('GRANT CONNECT ON DATABASE %I TO "{rol}"', current_database());
            END
            $$;
            """
        )
        op.execute(f'GRANT USAGE ON SCHEMA public TO "{rol}"')

    for rol, tabla, privilegios, columnas in PERMISOS:
        if privilegios:
            op.execute(f'GRANT {privilegios} ON public."{tabla}" TO "{rol}"')
        if columnas:
            lista = ", ".join(columnas)
            op.execute(f'GRANT UPDATE ({lista}) ON public."{tabla}" TO "{rol}"')


def downgrade() -> None:
    # Solo se retira lo que esta migración agrega; usuario, sesion_refresh y
    # usuario_empresa conservan los permisos de sus propias migraciones.
    for rol, tabla, privilegios, columnas in reversed(PERMISOS):
        if columnas:
            lista = ", ".join(columnas)
            op.execute(f'REVOKE UPDATE ({lista}) ON public."{tabla}" FROM "{rol}"')
        if privilegios:
            op.execute(f'REVOKE {privilegios} ON public."{tabla}" FROM "{rol}"')
