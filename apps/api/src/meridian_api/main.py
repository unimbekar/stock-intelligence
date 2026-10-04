from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from meridian_config.settings import get_settings

from meridian_api.gateway import PricesUnavailable
from meridian_api.limiter import RateLimiter
from meridian_api.routers import assistant, auth, health, market, meta, workspace

EXEMPT_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    settings = get_settings()
    if settings.data_mode == "live":
        from meridian_api.gateway import active_book

        threading.Thread(target=active_book, name="market-warm", daemon=True).start()
        threading.Thread(target=_warm_directory, name="symbol-warm", daemon=True).start()
    if settings.local_ai_model.strip():
        threading.Thread(target=_warm_model, name="model-warm", daemon=True).start()
    stop = threading.Event()
    if settings.alert_watch:
        threading.Thread(target=_watch_alerts, args=(stop,), name="alert-watch", daemon=True).start()
    yield
    stop.set()


def _watch_alerts(stop: threading.Event) -> None:
    if stop.wait(20):
        return
    while not stop.is_set():
        try:
            from meridian_api.mail import sweep

            sweep()
        except Exception:
            logging.getLogger("meridian.alerts").exception("alert sweep failed")
        if stop.wait(get_settings().alert_check_seconds):
            return


def _warm_directory() -> None:
    from meridian_market.symbols import get_directory

    get_directory()


def _warm_model() -> None:
    from meridian_ai.provider import _ollama_chat
    from meridian_config.settings import get_settings

    settings = get_settings()
    _ollama_chat(
        settings.local_ai_base_url,
        {
            "model": settings.local_ai_model,
            "stream": False,
            "think": False,
            "options": {"num_predict": 8, "temperature": 0},
            "messages": [{"role": "user", "content": "Reply with the word ready."}],
        },
    )


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(title="Meridian API", version="0.1.0", lifespan=lifespan)
    app.state.limiter = RateLimiter(settings)
    cors_kwargs: dict[str, object] = {
        "allow_origins": settings.web_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PATCH", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
    if settings.environment == "local":
        cors_kwargs["allow_origin_regex"] = r"http://(localhost|127\.0\.0\.1):\d+"
    app.add_middleware(CORSMiddleware, **cors_kwargs)

    @app.middleware("http")
    async def protect(request: Request, call_next):
        if request.url.path not in EXEMPT_PATHS:
            client = request.client.host if request.client else "unknown"
            limiter: RateLimiter = request.app.state.limiter
            if not limiter.allow(client):
                return JSONResponse({"detail": "Rate limit exceeded."}, status_code=429)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(PricesUnavailable)
    async def prices_unavailable(request: Request, exc: PricesUnavailable) -> JSONResponse:
        del request
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("meridian").exception("request failed", extra={"path": request.url.path})
        return JSONResponse({"detail": "The request could not be completed."}, status_code=500)

    app.include_router(health.router)
    app.include_router(meta.router)
    app.include_router(market.router)
    app.include_router(auth.router)
    app.include_router(workspace.router)
    app.include_router(assistant.router)
    return app


app = create_app()
