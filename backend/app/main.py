import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions

from app.api import (
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
)
from app.core.config import get_settings
from app.core.errors import register_error_handlers

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Administra el cliente compartido de Supabase."""

    http_client = None
    app.state.supabase = None

    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            http_client = httpx.Client(timeout=20)
            options = SyncClientOptions(
                auto_refresh_token=False,
                persist_session=False,
                httpx_client=http_client,
            )
            app.state.supabase = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
                options=options,
            )
            logger.info("Cliente de Supabase inicializado.")
        except Exception:
            logger.exception("No se pudo inicializar el cliente de Supabase.")
            if http_client is not None:
                http_client.close()
                http_client = None
    else:
        logger.warning(
            "Supabase no está configurado; el almacenamiento RIDE no estará disponible."
        )

    try:
        yield
    finally:
        if http_client is not None:
            http_client.close()
            logger.info("Cliente HTTP de Supabase cerrado.")

        app.state.supabase = None


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