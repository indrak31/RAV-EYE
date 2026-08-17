# Traffic Violation Backend

A FastAPI service that ingests traffic-violation detections from a computer-vision pipeline, lets
reviewers approve or reject each case, generates challan mocks, exposes analytics for the
dashboard, and broadcasts live case events over WebSocket.

**Status:** Day 1 — [`docs/api-contract.md`](docs/api-contract.md) v1 published; `POST /api/ingest`
fully working; remaining endpoints stubbed to `501` per plan.

---

## Highlights

- **FastAPI + SQLAlchemy 2.0 + Pydantic v2** on Python 3.12.
- **DB-portable:** SQLite by default, Postgres via a single env var. No code changes.
- **Zero infra:** no auth, no microservices, no message queue. Suitable for a hackathon.
- **Contract-first:** `docs/api-contract.md` is the source of truth; every PR that changes an
  endpoint shape edits the contract in the same PR.
- **Tested:** smoke tests cover all 8 endpoints (8/8 passing on Day 1).

---

## API Surface (v1)

| #  | Method   | Path                          | Status (Day 1) | Planned (Day) |
|----|----------|-------------------------------|----------------|---------------|
| 1  | `POST`   | `/api/ingest`                 | 201 / 200      | D1-2 (done)   |
| 2  | `GET`    | `/api/cases`                  | 501            | D3-5          |
| 3  | `GET`    | `/api/cases/{case_id}`        | 501            | D3-5          |
| 4  | `PATCH`  | `/api/cases/{case_id}/review` | 501            | D3-5          |
| 5  | `POST`   | `/api/challan`                | 501            | D5-7          |
| 6  | `GET`    | `/api/analytics`              | 501            | D5-7          |
| 7  | `WS`     | `/api/stream`                 | 1011 (stub)    | D5-7          |
| 8  | `GET`    | `/health`                     | 200            | D1 (done)     |

Full request/response shapes, enums, and WS events: see [`docs/api-contract.md`](docs/api-contract.md).

---

## Quick Start

```powershell
# from repo root
python -m venv .venv
& .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest "httpx[http2]"      # test deps

Copy-Item .env.example .env             # default: SQLite at ./data/tv.db

uvicorn app.main:app --reload          # http://127.0.0.1:8000/docs
pytest -q                               # 8 passed
```

### End-to-end smoke from PowerShell

```powershell
$body = @'
{
  "client_request_id": "demo-001",
  "vehicle": { "plate": "dl01ab1234", "vehicle_type": "car", "color": "white" },
  "violation_type": "red_light_jump",
  "camera_id": "CAM-ND-042",
  "occurred_at": "2026-08-17T10:24:00Z",
  "evidence": [
    { "kind": "image", "ref": "s3://tv-bucket/demo-001/001.jpg" }
  ]
}
'@
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/ingest -Method POST `
  -ContentType application/json -Body $body
# -> 201 {"case_id":"...","status":"ingested","created_at":"...","replayed":false}

Invoke-WebRequest -Uri http://127.0.0.1:8000/health   # -> {"db":"ok", "status":"ok", ...}
```

---

## Project Structure

```
app/
+-- main.py            FastAPI factory + lifespan (create_all on startup)
+-- config.py           pydantic-settings (.env)
+-- db.py               SQLAlchemy engine / SessionLocal / Base / init_db / get_db
+-- api/                One router per endpoint group
+-- models/             Case, EvidenceItem, Vehicle, Officer (SQLAlchemy ORM)
+-- schemas/            enums + Pydantic request/response models
+-- services/           ingest + serialization business logic
docs/
+-- api-contract.md     v1 contract — edit FIRST; code follows
tests/                  pytest; conftest pins a fresh SQLite DB
readme.md  plan.md  skill.md  requirements.txt  .env.example
```

For an in-depth tour including layering and conventions, read [`skill.md`](skill.md).

---

## Configuration

All settings come from `.env` (or real environment variables):

| Variable        | Default                      | Description                                |
|-----------------|------------------------------|--------------------------------------------|
| `DATABASE_URL`  | `sqlite:///./data/tv.db`     | SQLAlchemy URL. Postgres: see below.       |
| `APP_NAME`      | `tv-backend`                 | Surfaced by `/health`.                     |
| `APP_VERSION`   | `v1`                         | Surfaced by `/health`.                     |
| `ENV`           | `dev`                        | `dev` / `test` / `prod`.                   |
| `HOST` / `PORT` | `127.0.0.1` / `8000`         | For local uvicorn only.                    |
| `LOG_LEVEL`     | `info`                       | root logger level.                         |
| `CORS_ORIGINS`  | `*`                          | CSV or `*`.                                |

**Postgres:**
```bash
DATABASE_URL=postgresql+psycopg://tv:tv@localhost:5432/tv
pip install "psycopg[binary]"
uvicorn app.main:app --reload
```

---

## Data Model (summary)

```
Case 1 --- 1 Vehicle
Case * --- 1 Officer (optional)
Case 1 --- * EvidenceItem
```

Key enumerations (see `app/schemas/enums.py`):

- `CaseStatus`: `ingested` | `in_review` | `approved` | `rejected` | `challan_issued`
- `ViolationType`: `red_light_jump`, `speeding`, `no_helmet`, `wrong_side`, `seatbelt_violation`,
  `pollution_certificate`, `distracted_driving`, `illegal_parking`, `oversized_vehicle`, `other`
- `ReviewDecision`: `approved` | `rejected`

---

## Testing

```bash
pytest                 # all tests
pytest -q              # quiet
pytest tests/test_smoke.py::test_health   # single test
```

Tests use FastAPI's `TestClient` with the lifespan enabled, so `create_all()` runs on the test DB
once per session. The `conftest.py` sets `DATABASE_URL` to a fresh `./data/tv-test.db` before any
`from app.main import ...`.

| Day | Test directory expectation                                     |
|-----|----------------------------------------------------------------|
| D1  | `tests/test_smoke.py` — 8 tests across the contract surface.   |
| D3-5 | Add `tests/test_cases.py` for list/detail/review.           |
| D5-7 | Add `tests/test_challan.py`, `test_analytics.py`, `test_stream.py`. |
| D9-11 | Add `tests/test_integration.py` for end-to-end CV push.      |

---

## Roadmap

The day-by-day delivery plan, owners, decisions log, risks, and progress log live in
[`plan.md`](plan.md). Headline:

- **Day 1-2 (done)** contract + bootstrap + `/api/ingest`.
- **Day 3-5** reviewer flow — list, detail, review.
- **Day 5-7** challan, analytics, WS stream.
- **Day 9-11** merge CV branch and run end-to-end.

---

## Contributing

Please read [`skill.md`](skill.md) first — it covers layering, conventions, and where things live.
Short version:

1. Contract first — edit `docs/api-contract.md` in the same PR if you change a route shape.
2. Branch `feat/<area>-<short>` off `main`.
3. Add a test under `tests/` for any new public surface.
4. Reviewers are listed in [`plan.md`](plan.md) → Owners table.
5. After merge, append a one-liner to `plan.md` → Progress Log and `skill.md` → Update Log.

---

## License

Hackathon project — internal only. Not licensed for distribution.
