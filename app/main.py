import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.favorites.router import router as favorites_router
from app.listings.admin import router as admin_listings_router
from app.listings.media import router as media_router
from app.listings.router import router as listings_router
from app.reports.router import admin_router as admin_reports_router
from app.reports.router import router as reports_router
from app.users.router import router as users_router
from app.wilaya.router import router as wilayas_router

configure_logging("DEBUG" if settings.debug else "INFO")
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.middleware("http")
    async def add_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(favorites_router)
    app.include_router(listings_router)
    app.include_router(admin_listings_router)
    app.include_router(reports_router)
    app.include_router(admin_reports_router)
    app.include_router(admin_router)
    app.include_router(wilayas_router)
    app.include_router(media_router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    async def ready() -> dict[str, str]:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
