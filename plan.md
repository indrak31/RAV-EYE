# Plan — Traffic Violation Backend

**Status:** Living document. Update the "Progress Log" at the bottom after every working session.
**Owner:** Backend Lead (you). Reviewers: Alok (CV services / tests), Integration Lead (Day 9-11).
**Source of truth for the API:** [`docs/api-contract.md`](docs/api-contract.md) — v1 published Day 1.

---

## 0. North Star

Ship a working FastAPI backend that:
1. Accepts violation detections from the CV pipeline (`POST /api/ingest`).
2. Lets a reviewer approve/reject each case.
3. Generates a challan mock and exposes analytics for the dashboard.
4. Streams live case events to the dashboard over WebSocket.

**Hard rules (per mandate):**
- SQLite by default; Postgres only via `DATABASE_URL` env var.
- No auth. No microservices. No extra infra.
- The Backend Lead owns `docs/api-contract.md` — any contract change is a versioned edit there first, code second.

---

## 1. Milestones

| Milestone | End date (relative) | Deliverables                                            | Exit criteria                              |
|-----------|---------------------|---------------------------------------------------------|--------------------------------------------|
| M1 — Foundations      | Day 1  | `docs/api-contract.md` v1; FastAPI bootstrap; `POST /api/ingest`; 7 stubs at 501 | 8/8 smoke tests pass; contract link in chat. |
| M2 — Reviewer flow   | Day 5  | `GET /api/cases` (filter), `GET /api/cases/{id}`, `PATCH /api/cases/{id}/review` | Reviewer can list, open, approve/reject.    |
| M3 — Issuance & data | Day 7  | `POST /api/challan` mock, `GET /api/analytics`, `WS /api/stream`           | Dashboard can chart by type/camera/hour; live stream works. |
| M4 — Integration      | Day 11 | Merge Alok's CV branch; wire CV push into `/api/ingest`; end-to-end run.   | A real detection flows from camera → DB → dashboard. |

---

## 2. Day-by-Day Schedule

### Day 1-2 — Foundations & contract **[DONE Day 1]**

- [x] Write `docs/api-contract.md` v1 — 8 endpoints, Case & EvidenceItem JSON, WS event shape, status & violation_type enums.
- [x] Bootstrap repo: `app/main.py`, `app/db.py` (SQLAlchemy `create_all`), `app/models/{case,vehicle,officer}.py`, `app/config.py` (pydantic-settings + `.env`).
- [x] Implement `POST /api/ingest` — persists `Case` + `EvidenceItem` rows (plus `Vehicle`/`Officer`); idempotent on `client_request_id`; returns `{case_id}`.
- [x] Stub remaining 7 endpoints as `501 Not Implemented` (`{ "detail": "not_implemented", "planned_day": "D3-5" }`).
- [x] Smoke tests (`tests/test_smoke.py`) covering all 8 endpoints — 8/8 pass.
- [x] Share `docs/api-contract.md` link in team chat.

### Day 3-5 — Reviewer flow

- [ ] `GET /api/cases` — filters: `status` (csv), `camera_id`, `violation_type`, `plate` (substring), `limit`/`offset`. Returns `{ total, limit, offset, items[] }` with evidence stripped.
- [ ] `GET /api/cases/{case_id}` — full Case with `evidence[]` populated. `404 case_not_found` on miss.
- [ ] `PATCH /api/cases/{case_id}/review` — body `{ decision, reviewer_id, note }`. Sets `status` to `approved`/`rejected`, stamps `reviewed_at`. `409 case_not_reviewable` if Case not in `ingested`/`in_review`.
- [ ] Move cases from `ingested` → `in_review` automatically on first `GET /api/cases/{id}`? **Decision needed — see open questions.**
- [ ] Tests: list pagination, filters, 404, status transitions, 409.

### Day 5-7 — Challan, analytics, stream

- [ ] `POST /api/challan` — returns 202 with `{ challan_id, status: "queued" }`. Refuses if target Case `status != approved` (-> `409 challan_not_eligible`). Mock service writes a `challans` table row; no real SMS/email.
- [ ] `GET /api/analytics` — `from`/`to` (ISO date), `group_by` ∈ `type`, `camera`, `hour` (repeatable). Returns `rows[]` plus `totals.by_type / by_camera / by_hour`. Implement with `GROUP BY` against the `cases` table.
- [ ] `WS /api/stream` — broadcast `case.ingested`, `case.reviewed`, `challan.issued`, `heartbeat` (30s). Use an in-process pub/sub (a simple `asyncio.Queue` per connection from a singleton event bus is fine).
- [ ] Hook the three new events into existing mutation paths (`ingest`, `review`, `challan`).
- [ ] Tests: challan 202 / 409, analytics aggregation correctness, WS event subscription.

### Day 9-11 — Integration lead

- [ ] Merge Alok's CV-pipeline branch into a shared `main` (squash, review his services + tests PRs).
- [ ] Wire CV detection output → `POST /api/ingest` (agree on `client_request_id` convention).
- [ ] Run full pipeline end-to-end on a sample camera feed; verify the dashboard sees `case.ingested` events live.
- [ ] Capture a demo recording + a `curl` transcript for the final submission.
- [ ] Retire stubs: anything still at 501 must either be implemented or explicitly descoped with a note in this file.

---

## 3. Owners & Review Responsibilities

| Area                  | Owner           | Reviewer(s)            |
|-----------------------|-----------------|------------------------|
| `docs/api-contract.md`| Backend Lead    | Full team             |
| API routes + schemas  | Backend Lead    | Alok                  |
| Models + DB           | Backend Lead    | Alok                  |
| CV services / push    | Alok            | Backend Lead           |
| Tests                 | Whoever wrote the code | The other of (Alok / Backend Lead) |
| Final integration     | Integration Lead| Backend Lead + Alok    |

**PR rules:**
1. Every PR must reference an endpoint or model from `docs/api-contract.md`.
2. Tests required — no PR merges with fewer than 1 test per changed public surface.
3. Contract changes ship in the same PR as the code that implements them.

---

## 4. Decisions (record and date every one)

| #  | Date       | Decision                                                              | Rationale                              |
|----|------------|----------------------------------------------------------------------|----------------------------------------|
| D1 | Day 1      | SQLite default; Postgres only via `DATABASE_URL`.                    | Spec mandate; zero-infra.              |
| D2 | Day 1      | Vehicle stored as its own table (not JSON column).                  | Plate search future-proof; works on SQLite + Postgres. |
| D3 | Day 1      | Idempotency via `client_request_id` (24h window).                    | CV pipeline may retry; avoid dupes.    |
| D4 | Day 1      | Plate normalized to upper ASCII on write.                            | Cheap, deterministic plate search.     |
| D5 | Day 1      | `evidence.metadata` stored as JSON text on SQLite, JSONB on Postgres. | Portable across both DBs.              |
| D6 | Day 1      | WS `/api/stream` stub closes 1011 after `hello` until Day 5-7.        | Per contract; avoids silent hangs.     |

---

## 5. Open Questions

- [ ] Should `GET /api/cases/{id}` auto-transition `ingested` → `in_review`, or does review start explicitly (separate action)? Lean toward explicit to keep reads side-effect-free.
- [ ] Analytics `hour` bucket — local camera time or UTC? Defaulting to UTC unless Alok's CV sends TZ.
- [ ] Challan ID format — `CH-YYYY-NNNNNN` suggested in contract; confirm with the integration lead.
- [ ] Retention: do we ever purge rejected cases? Out of scope for v1 but worth a one-liner here.

---

## 6. Risks

| Risk                                          | Likelihood | Mitigation                                              |
|-----------------------------------------------|------------|--------------------------------------------------------|
| CV pipeline shape drifts from contract.       | High       | Alok's tests must consume the contract's `IngestRequest` schema verbatim. |
| SQLite write contention under load.           | Medium     | Single-writer is fine for demo; Postgres gate is just `DATABASE_URL`. |
| WS broadcast causes backpressure.             | Low        | Drop slow subscribers; emit heartbeat every 30s.       |
| Stub left untouched past Day 7.               | Medium     | Day 9-11 integration lead audits remaining `501`s.    |

---

## 7. Progress Log

Append a single line per session: `YYYY-MM-DD — author — what shipped`.

- `2026-08-17 — Backend Lead — Day 1: published api-contract.md v1; bootstrapped FastAPI app (models/db/config/main); implemented POST /api/ingest with idempotency; stubbed remaining 7 endpoints at 501; 8/8 smoke tests passing.`
