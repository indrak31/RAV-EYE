"""Tests for challan endpoint."""
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


def _err_detail(body: dict) -> str:
    d = body.get("detail")
    if isinstance(d, dict):
        return d.get("detail", "")
    return d or ""


class TestChallanEndpoint:
    def test_create_challan_approved_case(self, client: TestClient, db: Session):
        case = _ingest_case(db, status=CaseStatus.approved, client_request_id="cc1")
        r = client.post("/api/challan", json={"case_id": case.case_id, "channel": "sms"})
        assert r.status_code == 202
        body = r.json()
        assert body["case_id"] == case.case_id
        assert body["status"] == "queued"
        assert body["channel"] == "sms"
        assert body["challan_id"].startswith("CH-")

        r2 = client.get(f"/api/cases/{case.case_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "challan_issued"

    def test_create_challan_not_eligible_ingested(self, client: TestClient, db: Session):
        case = _ingest_case(db, status=CaseStatus.ingested, client_request_id="cc2")
        r = client.post("/api/challan", json={"case_id": case.case_id, "channel": "sms"})
        assert r.status_code == 409
        assert _err_detail(r.json()) == "challan_not_eligible"

    def test_create_challan_not_eligible_rejected(self, client: TestClient, db: Session):
        case = _ingest_case(db, status=CaseStatus.rejected, client_request_id="cc3")
        r = client.post("/api/challan", json={"case_id": case.case_id, "channel": "email"})
        assert r.status_code == 409
        assert _err_detail(r.json()) == "challan_not_eligible"

    def test_create_challan_not_eligible_challan_issued(self, client: TestClient, db: Session):
        case = _ingest_case(db, status=CaseStatus.challan_issued, client_request_id="cc4")
        r = client.post("/api/challan", json={"case_id": case.case_id, "channel": "post"})
        assert r.status_code == 409
        assert _err_detail(r.json()) == "challan_not_eligible"

    def test_create_challan_case_not_found(self, client: TestClient):
        r = client.post("/api/challan", json={"case_id": "non-existent", "channel": "sms"})
        assert r.status_code == 404
        assert _err_detail(r.json()) == "case_not_found"

    def test_create_challan_different_channels(self, client: TestClient, db: Session):
        for channel in ["sms", "email", "post"]:
            case = _ingest_case(db, status=CaseStatus.approved, client_request_id=f"cc5-{channel}")
            r = client.post("/api/challan", json={"case_id": case.case_id, "channel": channel})
            assert r.status_code == 202
            assert r.json()["channel"] == channel