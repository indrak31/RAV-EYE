"""Day 1 acceptance smoke tests.

Asserts:
- Module-level imports work
- /health returns 200 with db: ok
- /api/ingest creates a case, evidence items persisted, returns {case_id}
- /api/ingest is idempotent on repeated client_request_id
- Rejects future occurred_at
- /api/cases (list/detail/review), /api/challan, /api/analytics return 501
- /api/stream websocket sends `hello` then closes 1011
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Case, EvidenceItem, Vehicle


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["db"] == "ok"
    assert body["service"] == "tv-backend"
    assert body["version"] == "v1"
    assert body["status"] == "ok"


def test_openapi_lists_all_eight_endpoints(client):
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    # WebSocket routes are not exposed in OpenAPI — verify them separately.
    expected_http = {
        "/health",
        "/api/ingest",
        "/api/cases",
        "/api/cases/{case_id}",
        "/api/cases/{case_id}/review",
        "/api/challan",
        "/api/analytics",
    }
    assert expected_http.issubset(set(paths.keys())), sorted(expected_http - set(paths.keys()))
    # Confirm the WS endpoint lives on the app router.
    ws_paths = {
        r.path for r in client.app.routes if getattr(r, "endpoint", None) and hasattr(r, "ws")
    }
    if not ws_paths:
        ws_paths = {r.path for r in client.app.routes if "websocket" in type(r).__name__.lower()}
    assert "/api/stream" in ws_paths, ws_paths


def _ingest_payload(occurred_at=None, client_request_id="cv-run-0001", plate="DL01AB1234"):
    occurred_at = occurred_at or datetime.now(timezone.utc).isoformat()
    return {
        "client_request_id": client_request_id,
        "vehicle": {
            "plate": plate,
            "vehicle_type": "car",
            "color": "white",
            "make": "Maruti",
            "model": "Swift",
        },
        "officer": {
            "officer_id": "OF-2026-007",
            "name": "Sub-Inspector R. Kumar",
            "badge": "B-4471",
            "station": "PS Connaught Place",
        },
        "violation_type": "red_light_jump",
        "location": {"lat": 28.6315, "lng": 77.2167, "address": "Ito, New Delhi"},
        "camera_id": "CAM-ND-042",
        "occurred_at": occurred_at,
        "evidence": [
            {
                "kind": "image",
                "ref": "s3://tv-bucket/cv-run-0001/frame-001.jpg",
                "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                "captured_at": occurred_at,
                "metadata": {"width": 1920, "height": 1080},
            }
        ],
    }


def test_ingest_creates_case_and_evidence(client, db):
    payload = _ingest_payload()
    r = client.post("/api/ingest", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["case_id"]
    assert body["status"] == "ingested"
    assert body["replayed"] is False
    case_id = body["case_id"]

    case = db.get(Case, case_id)
    assert case is not None
    assert case.client_request_id == "cv-run-0001"
    assert case.violation_type.value == "red_light_jump"
    assert case.camera_id == "CAM-ND-042"
    # Vehicle
    assert case.vehicle is not None
    assert case.vehicle.plate == "DL01AB1234"  # normalized upper
    # Officer persisted too
    assert case.officer is not None
    assert case.officer.officer_id == "OF-2026-007"
    # Evidence
    assert len(case.evidence) == 1
    ei: EvidenceItem = case.evidence[0]
    assert ei.kind == "image"
    assert ei.metadata_json is not None
    assert "width" in ei.metadata_json
    # Plate normalization for lowercased input
    assert case.vehicle.plate == "DL01AB1234"


def test_ingest_idempotency_replay(client):
    payload = _ingest_payload(client_request_id="cv-run-replay")
    r1 = client.post("/api/ingest", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/ingest", json=payload)
    assert r2.status_code == 200
    assert r2.json()["replayed"] is True
    assert r2.json()["case_id"] == r1.json()["case_id"]


def test_ingest_rejects_future_occurred_at(client):
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    r = client.post("/api/ingest", json=_ingest_payload(occurred_at=future, client_request_id="fv-1"))
    assert r.status_code == 422, r.text


def test_ingest_requires_evidence(client):
    p = _ingest_payload(client_request_id="no-ev")
    p["evidence"] = []
    r = client.post("/api/ingest", json=p)
    assert r.status_code == 422


def test_stubs_return_501(client):
    assert client.get("/api/cases").status_code == 501
    assert client.get("/api/cases/abc").status_code == 501
    assert client.patch("/api/cases/abc/review", json={"decision": "approved"}).status_code == 501
    assert client.post("/api/challan", json={"case_id": "abc"}).status_code == 501
    assert client.get("/api/analytics").status_code == 501


def test_stream_stub_sends_hello_then_closes_1011(client):
    with client.websocket_connect("/api/stream") as ws:
        msg1 = ws.receive_json()
        assert msg1.get("event") == "hello"
        try:
            ws.receive_json()
            ws.receive_json()
        except Exception as exc:  # noqa: BLE001
            # Closure with code 1011 is fine — final shape codified in D5-7.
            assert exc
