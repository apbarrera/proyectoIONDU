import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auditoria,
    auth,
    certificados,
    company,
    configuracion_facturacion,
    customers,
    dashboard,
    expenses,
    facturas,
    health,
    inventory,
    me,
    products,
    sales,
    usuarios,
)
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.services.almacenamiento import crear_almacenamiento

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea el cliente de almacenamiento S3 compartido (RIDE de las facturas)."""
    try:
        # En desarrollo crea el bucket si falta; en producción ya debe existir.
        app.state.almacenamiento = crear_almacenamiento(
            settings, crear_bucket=settings.app_env == "development"
        )
    except Exception:
        logger.exception("No se pudo inicializar el almacenamiento S3.")
        app.state.almacenamiento = None
    try:
        yield
    finally:
        app.state.almacenamiento = None


# Todo cuelga de /api: Nginx reenvía /api/* sin quitar el prefijo.
# La documentación interactiva solo existe fuera de producción.
app = FastAPI(
    title="IONDU API",
    version="0.1.0",
    docs_url=None if settings.is_production else "/api/docs",
    openapi_url=None if settings.is_production else "/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

register_error_handlers(app)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(auth.cuenta_router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(auditoria.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(facturas.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(certificados.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(configuracion_facturacion.router, prefix="/api")
