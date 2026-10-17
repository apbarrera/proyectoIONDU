from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from app.core.config import TIMEZONE, get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "env": get_settings().app_env,
        "timezone": TIMEZONE,
        "time": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
    }
