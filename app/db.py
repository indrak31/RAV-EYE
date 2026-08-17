"""SQLAlchemy engine, session, and declarative base."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# `check_same_thread=False` is required for SQLite when used with FastAPI's
# thread-pool; ignored by Postgres drivers.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def init_db() -> None:
    """Run `create_all` against the configured engine.

    Imported models must be imported before this call so that their tables
    are registered on the Base.metadata. `app.main` imports all models for
    this reason.
    """
    settings.ensure_sqlite_dir()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped session and closing it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
