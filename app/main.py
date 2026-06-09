from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes.bookmarks import router as bookmarks_router
from app.api.routes.brief import router as brief_router
from app.api.routes.feed import router as feed_router
from app.api.routes.news import router as news_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.symbols import router as symbols_router
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_engine, get_session_factory
from app.services.cache_service import get_cache_backend

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")

        factory = get_session_factory()
        async with factory() as session:
            await init_db(session)
            await session.commit()
        logger.info("Database seed complete")
    except Exception as exc:
        logger.error("Database startup failed: %s", exc)
        raise
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(brief_router, prefix="/brief", tags=["Brief"])
app.include_router(feed_router, prefix="/feed", tags=["Feed"])
app.include_router(news_router, prefix="/news", tags=["News"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(bookmarks_router, prefix="/bookmarks", tags=["Bookmarks"])
app.include_router(symbols_router, prefix="/symbols", tags=["Symbols"])


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


def _cache_status() -> str:
    if settings.cache_backend != "redis":
        return "memory"
    try:
        backend = get_cache_backend()
        ping = getattr(backend, "_client", None)
        if ping is not None and hasattr(ping, "ping"):
            ping.ping()
            return "ok"
        return "memory"
    except Exception:
        return "error"


@app.get("/health")
async def health():
    db_status = "error"
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    cache_status = _cache_status()
    overall = "ok" if db_status == "ok" else "degraded"

    return {
        "status": overall,
        "api": "ok",
        "database": db_status,
        "cache": cache_status,
        "environment": settings.environment,
    }
