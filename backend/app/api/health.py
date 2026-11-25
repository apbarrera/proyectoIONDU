from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from app.core.config import TIMEZONE, get_settings
from app.db.session import database_status

router = APIRouter()


# Siempre responde 200 si el proceso está vivo (lo usa el healthcheck de Docker).
# El campo "database" informa aparte si PostgreSQL responde.
@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "env": get_settings().app_env,
        "timezone": TIMEZONE,
        "time": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
        "database": database_status(),
    }
