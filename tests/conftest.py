"""pytest fixtures.

Strategy:
- Set `DATABASE_URL` to a fresh SQLite file in a per-session tmp dir BEFORE
  any `app.*` import happens (pytest imports conftest first).
- `client` fixture uses TestClient with the lifespan scope so DB tables are
  created on startup and dropped on teardown.
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

from app.main import app  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402


@pytest.fixture(scope="session")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()
