import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, me, products
from app.core.config import get_settings
from app.core.errors import register_error_handlers

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Todo cuelga de /api: Nginx reenvía /api/* sin quitar el prefijo.
# La documentación interactiva solo existe fuera de producción.
app = FastAPI(
    title="IONDU API",
    version="0.1.0",
    docs_url=None if settings.is_production else "/api/docs",
    openapi_url=None if settings.is_production else "/api/openapi.json",
    redoc_url=None,
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
app.include_router(me.router, prefix="/api")
