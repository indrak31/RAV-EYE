# Skills & Conventions — Traffic Violation Backend

**Audience:** Developers joining this project. **Purpose:** get a teammate productive in under 30 minutes, and tell them how to write code that fits the codebase.

This is the project "skill sheet" — it complements (but does not replace) [`README.md`](readme.md) and [`docs/api-contract.md`](docs/api-contract.md).

---

## 1. Skill Prerequisites

Before touching this repo you should be comfortable with:

- **Python 3.12+** — type hints, `from __future__ import annotations`, dataclasses vs Pydantic.
- **FastAPI** — routers, dependencies, `Depends(...)`, `TestClient`, lifespan events.
- **SQLAlchemy 2.0** — the *declarative* API (`Mapped`, `mapped_column`), `Session`, relationships, `create_engine`. No Flask-style `db.session`.
- **Pydantic v2** — `BaseModel`, `Field`, `field_validator`, `ConfigDict(from_attributes=True)`.
- **WebSockets** — Starlette's `WebSocket` API. The `/api/stream` endpoint is async-only.
- **pytest** — fixtures, `TestClient`, async-sync interop. No `unittest.TestClass`.

Nice-to-have:

- `pydantic-settings` for env loading.
- SQLite + Postgres parity traps (e.g., `DateTime(timezone=True)` behavior).
- `uvicorn` + `--reload` workflow.
- `docker compose` for Postgres.

---

## 2. Repository Map

```
Traffic Violation/
+-- docs/
|   +-- api-contract.md        # v1 API contract — Owned by Backend Lead. Edit FIRST.
+-- app/
|   +-- main.py                # FastAPI factory; lifespan; mounts all routers.
|   +-- config.py              # pydantic-settings (.env + DATABASE_URL).
|   +-- db.py                  # engine, SessionLocal, Base, init_db(), get_db().
|   +-- api/                   # All HTTP/WS routes, one file per endpoint group.
|   |   +-- health.py  ingest.py  cases.py  challan.py  analytics.py  stream.py
|   |   +-- stub.py            # `not_implemented("D3-5")` helper for 501s.
|   +-- models/                # SQLAlchemy ORM. Importing this package registers
|   |                          # every table on Base.metadata (required for create_all).
|   |   +-- case.py            # Case + EvidenceItem
|   |   +-- vehicle.py
|   |   +-- officer.py
|   +-- schemas/
|   |   +-- enums.py           # CaseStatus, ViolationType, ReviewDecision, ...
|   |   +-- case.py            # Request/response Pydantic models.
|   +-- services/              # Business logic (no HTTP here).
|       +-- ingest.py          # Persist Case + cascades; idempotency.
|       +-- evidence_store.py  # Disk-backed media storage (frames/clips).
|       +-- case_service.py    # Status transitions, list filters, review workflow.
|       +-- serialization.py   # ORM -> Pydantic projectors.
+-- tests/
|   +-- conftest.py            # Sets DATABASE_URL to a fresh SQLite before app import.
|   +-- test_smoke.py          # Contract surface tests.
|   +-- test_evidence_store.py # Media storage round-trip.
|   +-- test_case_service.py   # Status transitions, list filters, review workflow.
|   +-- test_analytics.py      # Group-by queries, date filters.
+-- requirements.txt           # Pinned deps (install with `pip install -r requirements.txt`)
+-- .env.example
+-- .gitignore
+-- README.md
+-- plan.md                    # Schedule, owners, progress log.
+-- skill.md                   # This file.
+-- docker-compose.yml         # Postgres 15 (profile db), API (profile api)
+-- Dockerfile                 # Python 3.12 slim image
```

**Layering rule:** `api/*` calls `services/*` calls `models/*`. Never import `api.*` from `services` or `models`. Pydantic schemas live in `schemas/` and cross both layers.

---

## 3. Local Setup

```powershell
# 1. Create venv
python -m venv .venv
& .venv\Scripts\Activate.ps1

# 2. Install (all deps including test deps are in requirements.txt)
pip install -r requirements.txt

# 3. Configure
Copy-Item .env.example .env
# Edit DATABASE_URL or leave the SQLite default.

# 4. Run (SQLite)
uvicorn app.main:app --reload
# Swagger UI:  http://127.0.0.1:8000/docs
# ReDoc:       http://127.0.0.1:8000/redoc

# 5. Test
pytest -q
```

### With Docker (Postgres)

```powershell
# Start Postgres only
docker compose --profile db up -d

# Run API against Postgres
$env:DATABASE_URL="postgresql+psycopg://tv:tv@localhost:5432/tv"
uvicorn app.main:app --reload

# Or run full stack (API + Postgres)
docker compose --profile db --profile api up -d
```

---

## 4. Code Conventions

### 4.1 Python style

- `from __future__ import annotations` at the top of every module (we already do).
- Type hints everywhere. Response models declared via `response_model=` on the route.
- No `print`. Use `logging.getLogger("tv-backend")`.
- **Do not add comments unless asked.** Docstrings at module and class level only, and only when the thing isn't self-explanatory.
- Public functions get a docstring; private helpers (`_snake_case`) do not.

### 4.2 FastAPI

- One router per file under `app/api/`. Register in `app/main.py:create_app()`.
- Use the `Depends(get_db)` pattern; do not reach for `SessionLocal()` inside a route.
- Set status codes on the decorator for non-200 happy paths. Inside the handler use `Response.status_code = ...` for branches (see `app/api/ingest.py`).
- For 501 stubs use `app.api.stub.not_implemented("D3-5")` — do not roll your own error body. The body shape is part of the contract.

### 4.3 SQLAlchemy

- All ORM models inherit from `app.db.Base`.
- Define strings as `String(N)` for length-bounded columns; `Text` for arbitrary blobs.
- For enums, prefer a Python `str, Enum` (see `app/schemas/enums.py`) — works on both SQLite and Postgres.
- Cascades: parent → child uses `cascade="all, delete-orphan"` (see `Case.evidence`). FKs use `ondelete="CASCADE"` or `SET NULL` as semantics demand.
- **Always** add an index on columns that lists/filters hit. We already index `status`, `camera_id`, `violation_type`, plate, `client_request_id`.
- Do **not** call `db.commit()` in routes. Services own the transaction. `get_db` Rollbacks on exception.

### 4.4 Pydantic

- Request models end in `Request` or `In` (`IngestRequest`, `VehicleIn`).
- Response models end in `Out` or `Response`, with `model_config = ConfigDict(from_attributes=True)` if they mirror an ORM row — but our `CaseOut` is hand-serialized (`services/serialization.py`) because we nest `vehicle`, `officer`, `location`, `evidence`. Copy that pattern for new nested shapes.
- Field constraints via `Field(..., min_length=, max_length=, le=, ge=)`. Validators only when `Field` can't express it.
- Enum-in-Pydantic: declare as the Enum class directly — FastAPI renders it as a string enum in the OpenAPI schema.

### 4.5 Timestamps

- All timestamps are UTC, ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`).
- Treat naive datetimes as UTC at the schema boundary (`field_validator(mode="before")` — see `IngestRequest._coerce_utc`).
- DB columns are `DateTime(timezone=True)`. SQLite ignores TZ; Postgres respects it.

### 4.6 Testing

- Tests live in `tests/`. One `test_*.py` per area; arrange / act / assert, no shared mutable state across files.
- The `client` fixture (session-scoped) starts the app with its lifespan so `create_all` runs.
- New tests must hit the real route (through `TestClient`), not call the service function directly. We test contracts here.
- Stubs are asserted to return `501` until the implementing PR lands.
- **Test isolation:** `conftest.py` clears all tables after each test because services call `commit()` explicitly.

---

## 5. Workflow

1. Pick a task from [`plan.md`](plan.md). Move it to "in_progress" mentally; we use PR titles to track.
2. **Contract first:** if your task changes request/response shape or an endpoint's status codes, edit `docs/api-contract.md` in the same PR.
3. Branch from `main`: `feat/<area>-<short>` (e.g., `feat/cases-filter`).
4. Implement. Run `pytest -q`. Run `uvicorn app.main:app --reload` and smoke the endpoint through `/docs`.
5. Open a PR. Reference the plan task and the contract section. Tag a reviewer from the owner table in `plan.md`.
6. After merge, append a one-liner to `plan.md` → "Progress Log".

---

## 6. Common Tasks

### 6.1 Add a new endpoint

1. Add it to the relevant router file in `app/api/`, or create a new file there and register it in `app/main.py`.
2. Add Pydantic models in `app/schemas/case.py` (or a new schema file).
3. Add a row to the endpoint table in `docs/api-contract.md`.
4. Add a test in `tests/test_smoke.py` or a new `tests/test_<area>.py`.
5. Implement the service in `app/services/<area>.py`; never write SQL inside a route.

### 6.2 Change a model

1. Edit the model in `app/models/`.
2. **Note:** we use `create_all`, not Alembic. For Day 1-7 any schema change is cheap — drop `data/tv.db` locally. Before Day 11 evaluate whether a migration tool is needed (decision recorded in `plan.md` → Decisions).
3. Update `services/serialization.py` if the new column ships in a response.
4. Update `docs/api-contract.md` Case shape if it's user-visible.

### 6.3 Switch to Postgres

```bash
# .env
DATABASE_URL=postgresql+psycopg://tv:tv@localhost:5432/tv
pip install psycopg[binary]
```
That's it. `app/db.py` already adjusts `connect_args` based on the URL scheme. `init_db()` calls `create_all` against Postgres the same way.

### 6.4 Add a new service (Alok's pattern)

1. Create `app/services/<name>.py` with pure functions (no HTTP, no FastAPI imports).
2. Functions accept `db: Session` as first arg; own the transaction (`commit`/`rollback`).
3. Raise custom exceptions (`CaseNotFoundError`, `CaseNotReviewableError`) for business rule violations.
4. Import and call from the corresponding `app/api/<endpoint>.py` route.
5. Add tests in `tests/test_<name>.py` — test the service directly AND the endpoint via `TestClient`.

---

## 7. Anti-Patterns to Avoid

- Importing `app.db` inside a model module's top level in a way that creates a cycle. `models/case.py` does `from app.db import Base` and `from app.schemas.enums import ...` — keep that minimal.
- Returning ORM objects directly from routes. Always go through a Pydantic response model.
- Calling `db.commit()` inside a route. Keep transactions in services.
- Using `Enum` value strings as ordinals. Always compare with the Enum member or its `.value`.
- Hard-coding `"ingested"`. Use `CaseStatus.ingested`.
- Adding a new endpoint without a row in `docs/api-contract.md` — the PR review will block on this.
- Using `join()` in `list_cases` for plate filter — use `Case.vehicle.has(Vehicle.plate.ilike(...))` to avoid cartesian product warnings.

---

## 8. Where to Look When...

| Question                                              | Look at                                            |
|-------------------------------------------------------|----------------------------------------------------|
| "What does this endpoint accept/return?"              | `docs/api-contract.md`                             |
| "Where is this route mounted?"                        | `app/main.py` → `app.include_router(...)`          |
| "How does the DB get created?"                        | `app/db.py:init_db()` (called from lifespan)       |
| "How is a Case serialized?"                           | `app/services/serialization.py:case_to_out`       |
| "What `status` values can a Case have?"               | `app/schemas/enums.py:CaseStatus`                  |
| "Why did my test fail with a 422?"                    | Mismatched Pydantic schema vs your request body — see `app/schemas/case.py`. |
| "How do I 501 a not-yet-implemented endpoint?"        | `app/api/stub.py:not_implemented("D3-5")`          |
| "How to save a frame/clip from CV pipeline?"          | `app/services/evidence_store.py:save_frame()` / `save_clip()` |
| "How to list cases with filters?"                     | `app/services/case_service.py:list_cases()`       |
| "How to review a case (approve/reject)?"              | `app/services/case_service.py:review_case()`      |
| "How to run analytics queries?"                       | `app/api/analytics.py` (endpoint) or service funcs |

---

## 9. Update Log

Append a one-liner when you refine this skill sheet.

- `2026-08-17 — Backend Lead — initial skill.md written for Day 1 onboarding.`
- `2026-08-18 — Alok — added services (evidence_store, case_service), analytics endpoint, Docker, test conventions, anti-patterns for join vs has().`