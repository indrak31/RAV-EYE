"""pytest fixtures.

Strategy:
- Set `DATABASE_URL` to a fresh SQLite file in a per-session tmp dir BEFORE
  any `app.*` import happens (pytest imports conftest first).
- `client` fixture uses TestClient with the lifespan scope so DB tables are
  created on startup and dropped on teardown.
- `db` fixture provides a session that is used to override `get_db` dependency
  so API calls in tests use the same session.
- After each test, all tables are cleared to ensure isolation (since services
  call commit() explicitly).
"""
from __future__ import annotations

import os
from pathlib import Path

# IMPORTANT: this runs at conftest import time — before any test module
# triggers `from app.main import app`. Therefore the lru_cache on
# `get_settings()` will see the fresh DATABASE_URL.
_DB_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_FILE = _DB_DIR / "tv-test.db"
if _DB_FILE.exists():
    _DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE.as_posix()}"
os.environ.setdefault("ENV", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal, init_db, get_db, Base  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def _init_db():
    """Initialize database once per session."""
    init_db()


def _clear_tables(db):
    """Delete all rows from all tables in reverse FK order."""
    # Order matters due to FK constraints
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


@pytest.fixture()
def db(_init_db):
    """Provide a session for a test.

    This session is used to override the `get_db` dependency so that
    API calls during the test use the same session.
    Tables are cleared after each test to ensure isolation.
    """
    s = SessionLocal()
    try:
        yield s
    finally:
        _clear_tables(s)
        s.close()


@pytest.fixture()
def client(db):
    """TestClient that uses the test session via dependency override."""
    # Override get_db to use the test session
    def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client_no_override(_init_db):
    """TestClient without dependency override (for testing actual dependency injection)."""
    with TestClient(app) as c:
        yield c