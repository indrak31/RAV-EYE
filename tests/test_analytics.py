"""Tests for analytics endpoint."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Case
from app.schemas.enums import CaseStatus, ViolationType
from app.services.ingest import ingest
from app.schemas.case import (
    IngestRequest,
    VehicleIn,
    LocationIn,
    EvidenceItemIn,
)
from app.schemas.enums import EvidenceKind


def _ingest_case(
    db: Session,
    *,
    plate: str = "TEST1234",
    violation_type: ViolationType = ViolationType.red_light_jump,
    camera_id: str = "CAM-TEST",
    occurred_at: datetime | None = None,
    status: CaseStatus = CaseStatus.ingested,
    client_request_id: str | None = None,
) -> Case:
    """Helper to create a case via ingest service.

    Uses a fixed past date (2024) to avoid future-date validation.
    """
    if occurred_at is None:
        occurred_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    if client_request_id is None:
        import uuid
        client_request_id = f"test-{uuid.uuid4().hex[:8]}"

    payload = IngestRequest(
        client_request_id=client_request_id,
        vehicle=VehicleIn(plate=plate),
        violation_type=violation_type,
        camera_id=camera_id,
        occurred_at=occurred_at,
        evidence=[
            EvidenceItemIn(
                kind=EvidenceKind.image,
                ref="s3://test/frame.jpg",
            )
        ],
    )
    case, _ = ingest(db, payload)
    if status != CaseStatus.ingested:
        case.status = status
        db.add(case)
        db.commit()
        db.refresh(case)
    return case


class TestAnalyticsEndpoint:
    def test_analytics_empty_db(self, client: TestClient):
        r = client.get("/api/analytics")
        assert r.status_code == 200
        body = r.json()
        assert body["rows"] == []
        # Default group_by is ["type"], so totals includes by_type (empty)
        assert body["totals"] == {"by_type": {}}

    def test_analytics_group_by_type(self, client: TestClient, db: Session):
        _ingest_case(db, violation_type=ViolationType.red_light_jump, client_request_id="t1")
        _ingest_case(db, violation_type=ViolationType.red_light_jump, client_request_id="t2")
        _ingest_case(db, violation_type=ViolationType.speeding, client_request_id="t3")

        r = client.get("/api/analytics?group_by=type")
        assert r.status_code == 200
        body = r.json()
        assert body["group_by"] == ["type"]
        type_rows = [row for row in body["rows"] if row.get("violation_type")]
        assert len(type_rows) == 2
        counts = {row["violation_type"]: row["count"] for row in type_rows}
        assert counts["red_light_jump"] == 2
        assert counts["speeding"] == 1
        assert body["totals"]["by_type"]["red_light_jump"] == 2

    def test_analytics_group_by_camera(self, client: TestClient, db: Session):
        _ingest_case(db, camera_id="CAM-A", client_request_id="c1")
        _ingest_case(db, camera_id="CAM-A", client_request_id="c2")
        _ingest_case(db, camera_id="CAM-B", client_request_id="c3")

        r = client.get("/api/analytics?group_by=camera")
        assert r.status_code == 200
        body = r.json()
        camera_rows = [row for row in body["rows"] if row.get("camera_id")]
        assert len(camera_rows) == 2
        counts = {row["camera_id"]: row["count"] for row in camera_rows}
        assert counts["CAM-A"] == 2
        assert counts["CAM-B"] == 1
        assert body["totals"]["by_camera"]["CAM-A"] == 2

    def test_analytics_group_by_hour(self, client: TestClient, db: Session):
        from datetime import timedelta
        base = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        _ingest_case(db, occurred_at=base, client_request_id="h1")
        _ingest_case(db, occurred_at=base + timedelta(minutes=30), client_request_id="h2")
        _ingest_case(db, occurred_at=base + timedelta(hours=1), client_request_id="h3")

        r = client.get("/api/analytics?group_by=hour")
        assert r.status_code == 200
        body = r.json()
        hour_rows = [row for row in body["rows"] if row.get("hour") is not None]
        assert len(hour_rows) == 2
        counts = {row["hour"]: row["count"] for row in hour_rows}
        assert counts[10] == 2
        assert counts[11] == 1
        assert body["totals"]["by_hour"]["10"] == 2

    def test_analytics_multiple_group_by(self, client: TestClient, db: Session):
        _ingest_case(db, violation_type=ViolationType.red_light_jump, camera_id="CAM-A", client_request_id="m1")
        _ingest_case(db, violation_type=ViolationType.speeding, camera_id="CAM-A", client_request_id="m2")
        _ingest_case(db, violation_type=ViolationType.red_light_jump, camera_id="CAM-B", client_request_id="m3")

        r = client.get("/api/analytics?group_by=type&group_by=camera")
        assert r.status_code == 200
        body = r.json()
        assert set(body["group_by"]) == {"type", "camera"}
        assert "by_type" in body["totals"]
        assert "by_camera" in body["totals"]

    def test_analytics_date_filter_from(self, client: TestClient, db: Session):
        base = datetime(2024, 8, 1, tzinfo=timezone.utc)
        _ingest_case(db, occurred_at=base, client_request_id="d1")
        _ingest_case(db, occurred_at=base, client_request_id="d2")
        _ingest_case(db, occurred_at=datetime(2024, 7, 15, tzinfo=timezone.utc), client_request_id="d3")

        r = client.get("/api/analytics?from=2024-08-01&group_by=type")
        assert r.status_code == 200
        body = r.json()
        total = sum(row["count"] for row in body["rows"])
        assert total == 2  # only August cases

    def test_analytics_date_filter_to(self, client: TestClient, db: Session):
        _ingest_case(db, occurred_at=datetime(2024, 8, 10, tzinfo=timezone.utc), client_request_id="d1")
        _ingest_case(db, occurred_at=datetime(2024, 8, 15, tzinfo=timezone.utc), client_request_id="d2")

        r = client.get("/api/analytics?to=2024-08-12&group_by=type")
        assert r.status_code == 200
        body = r.json()
        total = sum(row["count"] for row in body["rows"])
        assert total == 1  # only up to Aug 12

    def test_analytics_date_filter_both(self, client: TestClient, db: Session):
        _ingest_case(db, occurred_at=datetime(2024, 7, 1, tzinfo=timezone.utc), client_request_id="d1")
        _ingest_case(db, occurred_at=datetime(2024, 8, 15, tzinfo=timezone.utc), client_request_id="d2")
        _ingest_case(db, occurred_at=datetime(2024, 9, 1, tzinfo=timezone.utc), client_request_id="d3")

        r = client.get("/api/analytics?from=2024-08-01&to=2024-08-31&group_by=type")
        assert r.status_code == 200
        body = r.json()
        total = sum(row["count"] for row in body["rows"])
        assert total == 1  # only August

    def test_analytics_invalid_group_by_returns_422(self, client: TestClient):
        r = client.get("/api/analytics?group_by=invalid")
        assert r.status_code == 422
        body = r.json()
        # Error detail is a dict with 'detail' key
        assert "invalid group_by value" in body["detail"]["detail"]

    def test_analytics_respects_status_not_filtered(self, client: TestClient, db: Session):
        # Analytics should include ALL cases regardless of status
        _ingest_case(db, status=CaseStatus.ingested, client_request_id="s1")
        _ingest_case(db, status=CaseStatus.approved, client_request_id="s2")
        _ingest_case(db, status=CaseStatus.rejected, client_request_id="s3")

        r = client.get("/api/analytics?group_by=type")
        assert r.status_code == 200
        body = r.json()
        total = sum(row["count"] for row in body["rows"])
        assert total == 3  # all statuses included