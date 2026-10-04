from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from meridian_config.settings import get_settings
from meridian_db.session import create_engine_from_url
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    settings = get_settings()
    checks: dict[str, str] = {}
    try:
        engine = create_engine_from_url(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "down"
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.3, socket_timeout=0.3)
        client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"
    ready_ok = all(value == "ok" for value in checks.values())
    return JSONResponse(
        {"status": "ok" if ready_ok else "degraded", "checks": checks},
        status_code=200 if ready_ok else 503,
    )
