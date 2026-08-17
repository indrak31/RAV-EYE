"""FastAPI application entrypoint.

Boot behaviour:
- Registers all model modules so `Base.metadata.create_all()` sees the schema.
- Initialises the DB on startup.
- Mounts the routers in api-contract.md v1.

Run locally:
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# IMPORTANT: importing `app.models` registers every ORM class on Base.metadata.
# This must happen before `init_db()` is called.
import app.models  # noqa: F401
from app.api import analytics, cases, challan, health, ingest, stream
from app.config import get_settings
from app.db import init_db

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL.upper())
log = logging.getLogger("tv-backend")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("init_db() -> create_all on %s", settings.DATABASE_URL)
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Traffic Violation backend — see docs/api-contract.md for v1 contract.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(cases.router)
    app.include_router(challan.router)
    app.include_router(analytics.router)
    app.include_router(stream.router)

    return app


app = create_app()
