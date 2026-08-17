# Traffic Violation API — Contract v1

**Status:** v1 (Day 1 baseline). Owner: Backend Lead.
**Base URL (local):** `http://127.0.0.1:8000`
**Docs:** FastAPI auto-generated at `/docs` (OpenAPI 3.1) and `/redoc`.
**Transport:** JSON over HTTP/1.1, one WebSocket endpoint. No auth. No microservices.
**DB:** SQLite (`./data/tv.db`) by default; Postgres via `DATABASE_URL` env var.

---

## Conventions

- All timestamps are ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
- IDs are UUIDv4 strings, generated server-side.
- Snake_case for JSON keys.
- HTTP status codes: `200` success, `201` created, `422` validation error, `500` server error, `501` not implemented (stub).
- Empty arrays `[]` are returned instead of `null`.

---

## Resource: Case

```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ingested",
  "vehicle": {
    "plate": "DL01AB1234",
    "vehicle_type": "car",
    "color": "white",
    "make": "Maruti",
    "model": "Swift"
  },
  "officer": {
    "officer_id": "OF-2026-007",
    "name": "Sub-Inspector R. Kumar",
    "badge": "B-4471",
    "station": "PS Connaught Place"
  },
  "violation_type": "red_light_jump",
  "location": {
    "lat": 28.6315,
    "lng": 77.2167,
    "address": "Ito, New Delhi"
  },
  "camera_id": "CAM-ND-042",
  "occurred_at": "2026-08-17T10:24:00Z",
  "ingested_at": "2026-08-17T10:25:12Z",
  "reviewed_at": null,
  "review_decision": null,
  "reviewer_id": null,
  "evidence": [
    {
      "evidence_id": "7a3f...",
      "kind": "image",
      "ref": "s3://tv-bucket/case-550e8400/frame-001.jpg",
      "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
      "captured_at": "2026-08-17T10:24:00Z",
      "metadata": { "width": 1920, "height": 1080, "fps": null }
    }
  ]
}
```

### `status` enum

| Value        | Meaning                                            |
|--------------|----------------------------------------------------|
| `ingested`   | Case created from a camera/CV push.                |
| `in_review`  | Pulled by a reviewer, awaiting decision.           |
| `approved`   | Reviewer confirmed violation; dispatched to challan.|
| `rejected`   | Reviewer discarded (false positive).               |
| `challan_issued` | Challan mock/push completed.                     |

### `violation_type` enum

`red_light_jump`, `speeding`, `no_helmet`, `wrong_side`, `seatbelt_violation`, `pollution_certificate`, `distracted_driving`, `illegal_parking`, `oversized_vehicle`, `other`.

---

## Endpoints (v1)

| #  | Method   | Path                          | Purpose                                  | Day     | Status |
|----|----------|-------------------------------|------------------------------------------|---------|--------|
| 1  | `POST`   | `/api/ingest`                 | Create Case + EvidenceItems from a CV push. | D1-2 | 201    |
| 2  | `GET`    | `/api/cases`                  | List cases, filter by `status`/`camera_id`/`violation_type`. | D3-5 | 200 |
| 3  | `GET`    | `/api/cases/{case_id}`        | Case detail including evidence refs.      | D3-5 | 200    |
| 4  | `PATCH`  | `/api/cases/{case_id}/review` | Apply review decision (approve/reject).   | D3-5 | 200    |
| 5  | `POST`   | `/api/challan`                | Mock challan generation against an approved case. | D5-7 | 202 |
| 6  | `GET`    | `/api/analytics`              | Aggregate counts grouped by type/camera/hour. | D5-7 | 200 |
| 7  | `WS`     | `/api/stream`                 | Push real-time case events to the dashboard. | D5-7 | —     |
| 8  | `GET`    | `/health`                     | Readiness + DB ping.                      | D1     | 200    |

> **Day 1 rule:** endpoints marked "D3-5" and "D5-7" return `501 Not Implemented` with `{ "detail": "not_implemented", "planned_day": "D3-5" }`.

---

### 1. `POST /api/ingest`

Create a Case from a CV (computer-vision) push. Persists the `Case` and all `EvidenceItem` rows.
Idempotent best-effort: if `client_request_id` repeats within 24h, returns the existing `case_id`.

**Request body** (`IngestRequest`):

```json
{
  "client_request_id": "cv-pipe-run-9876",
  "vehicle": {
    "plate": "DL01AB1234",
    "vehicle_type": "car",
    "color": "white",
    "make": "Maruti",
    "model": "Swift"
  },
  "officer": {
    "officer_id": "OF-2026-007",
    "name": "Sub-Inspector R. Kumar",
    "badge": "B-4471",
    "station": "PS Connaught Place"
  },
  "violation_type": "red_light_jump",
  "location": { "lat": 28.6315, "lng": 77.2167, "address": "Ito, New Delhi" },
  "camera_id": "CAM-ND-042",
  "occurred_at": "2026-08-17T10:24:00Z",
  "evidence": [
    {
      "kind": "image",
      "ref": "s3://tv-bucket/cv-run-9876/frame-001.jpg",
      "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
      "captured_at": "2026-08-17T10:24:00Z",
      "metadata": { "width": 1920, "height": 1080 }
    }
  ]
}
```

Field rules:
- `vehicle.plate` required, normalized to upper ASCII.
- `officer` may be `null` for automated cases (assigned later).
- `evidence` min length 1, max length 64.
- `occurred_at` required, must be <= `now()`.

**Responses**

`201 Created`
```json
{ "case_id": "550e8400-e29b-41d4-a716-446655440000", "status": "ingested", "created_at": "2026-08-17T10:25:12Z" }
```
`200 OK` (idempotent replay of same `client_request_id`)
```json
{ "case_id": "550e8400-e29b-41d4-a716-446655440000", "status": "ingested", "created_at": "...", "replayed": true }
```
`422 Unprocessable Entity` — validation error (FastAPI default).

---

### 2. `GET /api/cases`

Query params (all optional, all string):

| Param            | Type   | Notes                                  |
|------------------|--------|----------------------------------------|
| `status`         | enum   | Comma-separated, e.g. `ingested,approved`. |
| `camera_id`      | string | Exact match.                           |
| `violation_type` | enum   | Exact match.                           |
| `plate`          | string | Case-insensitive substring match.      |
| `limit`          | int    | Default `50`, max `200`.               |
| `offset`         | int    | Default `0`.                           |

**`200`** — `{ "total": 138, "limit": 50, "offset": 0, "items": [Case, Case, ...] }` where each `Case` is the full shape above (evidence omitted in list view — set to `[]`).

---

### 3. `GET /api/cases/{case_id}`

**`200`** — full `Case` shape with `evidence[]` populated.
**`404`** — `{ "detail": "case_not_found" }`.

---

### 4. `PATCH /api/cases/{case_id}/review`

**Request body:**
```json
{
  "decision": "approved",
  "reviewer_id": "RV-007",
  "note": "Clear plate capture, frame 0:02."
}
```
`decision` is one of `approved`, `rejected`. Server sets `status` accordingly and stamps `reviewed_at`.

**Responses:** `200` (updated Case), `404` (`case_not_found`), `409` (`case_not_reviewable` — only `ingested`/`in_review` cases can be reviewed).

---

### 5. `POST /api/challan` (D5-7, stub on D1)

**Request body:**
```json
{ "case_id": "550e8400-...", "channel": "sms|email|post" }
```

**`202 Accepted`:**
```json
{ "challan_id": "CH-2026-000123", "case_id": "...", "status": "queued", "channel": "sms" }
```
Server refuses if target Case `status != "approved"` (-> `409 challan_not_eligible`).

---

### 6. `GET /api/analytics` (D5-7, stub on D1)

Query params: `from` (ISO date), `to` (ISO date), `group_by` ∈ `type`, `camera`, `hour` (comma-separated, allows multiple groupings).

**`200`:**
```json
{
  "from": "2026-08-01",
  "to": "2026-08-17",
  "group_by": ["type", "camera"],
  "rows": [
    { "violation_type": "red_light_jump", "camera_id": "CAM-ND-042", "count": 47 },
    { "violation_type": "speeding",       "camera_id": "CAM-ND-042", "count": 12 }
  ],
  "totals": { "by_type": { "red_light_jump": 47, "speeding": 12 }, "by_camera": { "CAM-ND-042": 59 }, "by_hour": { "10": 59 } }
}
```

---

### 7. `WS /api/stream` (D5-7, stub on D1)

Client connects with `ws://127.0.0.1:8000/api/stream`. Server pushes JSON events:

```json
{
  "event": "case.ingested",
  "case_id": "550e8400-...",
  "violation_type": "red_light_jump",
  "camera_id": "CAM-ND-042",
  "occurred_at": "2026-08-17T10:24:00Z",
  "sent_at": "2026-08-17T10:25:12Z"
}
```

Event types: `case.ingested`, `case.reviewed`, `challan.issued`, `heartbeat` (every 30s).

**Stub behavior (D1):** connection accepts, sends a single `hello` event, then closes with code 1011:
```json
{ "event": "not_implemented", "planned_day": "D5-7" }
```

---

### 8. `GET /health`

**`200`:**
```json
{ "status": "ok", "service": "tv-backend", "version": "v1", "db": "ok", "time": "2026-08-17T10:25:12Z" }
```
**`503`** if DB ping fails (`db: "fail"`).

---

## Changes from v0

- Initial v1 release. Establishes Case, EvidenceItem, Officer, Vehicle shapes and the 8 endpoint surface. All `D3-7` endpoints stubbed to `501`.
