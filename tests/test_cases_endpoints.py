"""Tests for cases endpoints (list, detail, review)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Case
from app.schemas.enums import CaseStatus, ReviewDecision, ViolationType
from app.services.ingest import ingest
from app.schemas.case import (
    IngestRequest,
    VehicleIn,
    LocationIn,
    EvidenceItemIn,
    ReviewRequest,
)
from app.schemas.enums import EvidenceKind


def _ingest_case(
    db: Session,
    *,
    plate: str = "TEST1234",
    violation_type: ViolationType = ViolationType.red_light_jump,
    camera_id: str = "CAM-TEST",
    occurred_at: datetime | None = None,
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
    return case


def _err_detail(body: dict) -> str:
    """Extract detail string from error response (handles both string and dict)."""
    d = body.get("detail")
    if isinstance(d, dict):
        return d.get("detail", "")
    return d or ""


class TestCasesEndpoints:
    def test_list_cases_empty(self, client: TestClient):
        r = client.get("/api/cases")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_cases_with_data(self, client: TestClient, db: Session):
        _ingest_case(db, client_request_id="lc1")
        _ingest_case(db, client_request_id="lc2")
        r = client.get("/api/cases")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        for item in body["items"]:
            assert item["evidence"] == []

    def test_list_cases_status_filter(self, client: TestClient, db: Session):
        case1 = _ingest_case(db, client_request_id="lcs1")
        case2 = _ingest_case(db, client_request_id="lcs2")
        r = client.get("/api/cases?status=ingested")
        assert r.status_code == 200
        assert r.json()["total"] == 2

        case1.status = CaseStatus.approved
        db.add(case1)
        db.commit()

        r = client.get("/api/cases?status=ingested")
        assert r.status_code == 200
        assert r.json()["total"] == 1

        r = client.get("/api/cases?status=approved")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_list_cases_camera_filter(self, client: TestClient, db: Session):
        _ingest_case(db, camera_id="CAM-A", client_request_id="lcc1")
        _ingest_case(db, camera_id="CAM-B", client_request_id="lcc2")
        r = client.get("/api/cases?camera_id=CAM-A")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["camera_id"] == "CAM-A"

    def test_list_cases_violation_type_filter(self, client: TestClient, db: Session):
        _ingest_case(db, violation_type=ViolationType.red_light_jump, client_request_id="lcv1")
        _ingest_case(db, violation_type=ViolationType.speeding, client_request_id="lcv2")
        r = client.get("/api/cases?violation_type=red_light_jump")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["violation_type"] == "red_light_jump"

    def test_list_cases_plate_filter(self, client: TestClient, db: Session):
        _ingest_case(db, plate="ABC123", client_request_id="lcp1")
        _ingest_case(db, plate="XYZ789", client_request_id="lcp2")
        r = client.get("/api/cases?plate=abc")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["plate"] == "ABC123"

    def test_list_cases_pagination(self, client: TestClient, db: Session):
        for i in range(5):
            _ingest_case(db, client_request_id=f"lcp{i}")
        r = client.get("/api/cases?limit=2&offset=1")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2

    def test_list_cases_multiple_status_filter(self, client: TestClient, db: Session):
        _ingest_case(db, client_request_id="ms1")
        case2 = _ingest_case(db, client_request_id="ms2")
        case2.status = CaseStatus.approved
        db.add(case2)
        db.commit()
        case3 = _ingest_case(db, client_request_id="ms3")
        case3.status = CaseStatus.rejected
        db.add(case3)
        db.commit()

        r = client.get("/api/cases?status=ingested&status=approved")
        assert r.status_code == 200
        assert r.json()["total"] == 2


class TestCaseDetailEndpoint:
    def test_get_case_detail(self, client: TestClient, db: Session):
        case = _ingest_case(db, client_request_id="gcd1")
        r = client.get(f"/api/cases/{case.case_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["case_id"] == case.case_id
        assert body["status"] == "ingested"
        assert body["vehicle"]["plate"] == "TEST1234"
        assert len(body["evidence"]) == 1
        assert body["evidence"][0]["kind"] == "image"

    def test_get_case_not_found(self, client: TestClient):
        r = client.get("/api/cases/non-existent-id")
        assert r.status_code == 404
        assert _err_detail(r.json()) == "case_not_found"


class TestReviewEndpoint:
    def test_review_approve(self, client: TestClient, db: Session):
        case = _ingest_case(db, client_request_id="ra1")
        r = client.patch(
            f"/api/cases/{case.case_id}/review",
            json={"decision": "approved", "reviewer_id": "REV-001", "note": "Clear violation"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "approved"
        assert body["review_decision"] == "approved"
        assert body["reviewer_id"] == "REV-001"
        assert body["review_note"] == "Clear violation"
        assert body["reviewed_at"] is not None

    def test_review_reject(self, client: TestClient, db: Session):
        case = _ingest_case(db, client_request_id="rr1")
        r = client.patch(
            f"/api/cases/{case.case_id}/review",
            json={"decision": "rejected", "reviewer_id": "REV-002", "note": "False positive"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "rejected"
        assert body["review_decision"] == "rejected"

    def test_review_not_found(self, client: TestClient):
        r = client.patch(
            "/api/cases/non-existent/review",
            json={"decision": "approved"},
        )
        assert r.status_code == 404
        assert _err_detail(r.json()) == "case_not_found"

    def test_review_not_reviewable_when_approved(self, client: TestClient, db: Session):
        case = _ingest_case(db, client_request_id="rnr1")
        case.status = CaseStatus.approved
        db.add(case)
        db.commit()

        r = client.patch(
            f"/api/cases/{case.case_id}/review",
            json={"decision": "approved"},
        )
        assert r.status_code == 409
        assert _err_detail(r.json()) == "case_not_reviewable"

    def test_review_not_reviewable_when_rejected(self, client: TestClient, db: Session):
        case = _ingest_case(db, client_request_id="rnr2")
        case.status = CaseStatus.rejected
        db.add(case)
        db.commit()

        r = client.patch(
            f"/api/cases/{case.case_id}/review",
            json={"decision": "rejected"},
        )
        assert r.status_code == 409
        assert _err_detail(r.json()) == "case_not_reviewable"

    def test_review_not_reviewable_when_challan_issued(self, client: TestClient, db: Session):
        case = _ingest_case(db, client_request_id="rnr3")
        case.status = CaseStatus.challan_issued
        db.add(case)
        db.commit()

        r = client.patch(
            f"/api/cases/{case.case_id}/review",
            json={"decision": "approved"},
        )
        assert r.status_code == 409
        assert _err_detail(r.json()) == "case_not_reviewable"

    def test_review_invalid_decision(self, client: TestClient, db: Session):
        case = _ingest_case(db, client_request_id="rid1")
        r = client.patch(
            f"/api/cases/{case.case_id}/review",
            json={"decision": "invalid"},
        )
        assert r.status_code == 422