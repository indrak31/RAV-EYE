"""Tests for case_service business logic."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import Case
from app.schemas.case import ReviewRequest
from app.schemas.enums import CaseStatus, ReviewDecision, ViolationType
from app.services.case_service import (
    CaseNotFoundError,
    CaseNotReviewableError,
    CaseTransitionError,
    get_case,
    is_challan_eligible,
    list_cases,
    mark_challan_issued,
    review_case,
    transition_to_in_review,
)


def _create_test_case(db: Session, **overrides) -> Case:
    """Helper to create a test case with defaults."""
    from app.services.ingest import ingest
    from app.schemas.case import IngestRequest, VehicleIn, LocationIn, EvidenceItemIn
    from app.schemas.enums import EvidenceKind

    payload = IngestRequest(
        client_request_id=f"test-{overrides.get('suffix', 'case')}",
        vehicle=VehicleIn(plate=overrides.get("plate", "TEST1234")),
        violation_type=overrides.get("violation_type", ViolationType.red_light_jump),
        camera_id=overrides.get("camera_id", "CAM-TEST"),
        occurred_at=overrides.get("occurred_at", datetime.now(timezone.utc)),
        evidence=[
            EvidenceItemIn(
                kind=EvidenceKind.image,
                ref="s3://test/frame.jpg",
            )
        ],
    )
    case, _ = ingest(db, payload)
    return case


class TestGetCase:
    def test_get_case_returns_case(self, db: Session):
        case = _create_test_case(db)
        found = get_case(db, case.case_id)
        assert found.case_id == case.case_id

    def test_get_case_raises_not_found(self, db: Session):
        with pytest.raises(CaseNotFoundError):
            get_case(db, "non-existent-id")


class TestListCases:
    def test_list_cases_no_filters(self, db: Session):
        _create_test_case(db, suffix="1")
        _create_test_case(db, suffix="2")
        total, cases = list_cases(db)
        assert total == 2
        assert len(cases) == 2

    def test_list_cases_status_filter(self, db: Session):
        case1 = _create_test_case(db, suffix="1")
        case2 = _create_test_case(db, suffix="2")
        # Both start as ingested
        total, cases = list_cases(db, status_filter=[CaseStatus.ingested])
        assert total == 2

        # Change one to approved
        case1.status = CaseStatus.approved
        db.add(case1)
        db.commit()

        total, cases = list_cases(db, status_filter=[CaseStatus.ingested])
        assert total == 1
        assert cases[0].case_id == case2.case_id

    def test_list_cases_camera_filter(self, db: Session):
        _create_test_case(db, suffix="1", camera_id="CAM-A")
        _create_test_case(db, suffix="2", camera_id="CAM-B")
        total, cases = list_cases(db, camera_id="CAM-A")
        assert total == 1
        assert cases[0].camera_id == "CAM-A"

    def test_list_cases_violation_type_filter(self, db: Session):
        _create_test_case(db, suffix="1", violation_type=ViolationType.red_light_jump)
        _create_test_case(db, suffix="2", violation_type=ViolationType.speeding)
        total, cases = list_cases(db, violation_type=ViolationType.red_light_jump.value)
        assert total == 1
        assert cases[0].violation_type == ViolationType.red_light_jump

    def test_list_cases_plate_filter(self, db: Session):
        _create_test_case(db, suffix="1", plate="ABC123")
        _create_test_case(db, suffix="2", plate="XYZ789")
        total, cases = list_cases(db, plate="abc")  # case-insensitive
        assert total == 1
        assert cases[0].vehicle.plate == "ABC123"

    def test_list_cases_pagination(self, db: Session):
        for i in range(5):
            _create_test_case(db, suffix=str(i))
        total, cases = list_cases(db, limit=2, offset=1)
        assert total == 5
        assert len(cases) == 2


class TestTransitionToInReview:
    def test_transition_ingested_to_in_review(self, db: Session):
        case = _create_test_case(db)
        assert case.status == CaseStatus.ingested

        updated = transition_to_in_review(db, case.case_id)
        assert updated.status == CaseStatus.in_review

    def test_transition_idempotent(self, db: Session):
        case = _create_test_case(db)
        transition_to_in_review(db, case.case_id)
        # Second call should not error
        updated = transition_to_in_review(db, case.case_id)
        assert updated.status == CaseStatus.in_review

    def test_transition_from_approved_noop(self, db: Session):
        case = _create_test_case(db)
        case.status = CaseStatus.approved
        db.add(case)
        db.commit()

        updated = transition_to_in_review(db, case.case_id)
        assert updated.status == CaseStatus.approved  # unchanged


class TestReviewCase:
    def test_review_approve_ingested(self, db: Session):
        case = _create_test_case(db)
        assert case.status == CaseStatus.ingested

        updated = review_case(
            db,
            case.case_id,
            ReviewRequest(decision=ReviewDecision.approved, reviewer_id="REV-001", note="Clear violation"),
        )
        assert updated.status == CaseStatus.approved
        assert updated.review_decision == ReviewDecision.approved.value
        assert updated.reviewer_id == "REV-001"
        assert updated.review_note == "Clear violation"
        assert updated.occurrence_reviewed_at is not None

    def test_review_reject_ingested(self, db: Session):
        case = _create_test_case(db)

        updated = review_case(
            db,
            case.case_id,
            ReviewRequest(decision=ReviewDecision.rejected, reviewer_id="REV-002", note="False positive"),
        )
        assert updated.status == CaseStatus.rejected
        assert updated.review_decision == ReviewDecision.rejected.value

    def test_review_in_review_to_approved(self, db: Session):
        case = _create_test_case(db)
        transition_to_in_review(db, case.case_id)

        updated = review_case(
            db,
            case.case_id,
            ReviewRequest(decision=ReviewDecision.approved, reviewer_id="REV-003"),
        )
        assert updated.status == CaseStatus.approved

    def test_review_raises_not_reviewable_when_approved(self, db: Session):
        case = _create_test_case(db)
        case.status = CaseStatus.approved
        db.add(case)
        db.commit()

        with pytest.raises(CaseNotReviewableError):
            review_case(
                db,
                case.case_id,
                ReviewRequest(decision=ReviewDecision.approved),
            )

    def test_review_raises_not_reviewable_when_rejected(self, db: Session):
        case = _create_test_case(db)
        case.status = CaseStatus.rejected
        db.add(case)
        db.commit()

        with pytest.raises(CaseNotReviewableError):
            review_case(
                db,
                case.case_id,
                ReviewRequest(decision=ReviewDecision.rejected),
            )

    def test_review_raises_not_reviewable_when_challan_issued(self, db: Session):
        case = _create_test_case(db)
        case.status = CaseStatus.challan_issued
        db.add(case)
        db.commit()

        with pytest.raises(CaseNotReviewableError):
            review_case(
                db,
                case.case_id,
                ReviewRequest(decision=ReviewDecision.approved),
            )

    def test_review_raises_not_found(self, db: Session):
        with pytest.raises(CaseNotFoundError):
            review_case(
                db,
                "non-existent",
                ReviewRequest(decision=ReviewDecision.approved),
            )


class TestChallanEligibility:
    def test_is_challan_eligible_approved(self, db: Session):
        case = _create_test_case(db)
        case.status = CaseStatus.approved
        db.add(case)
        db.commit()
        assert is_challan_eligible(case) is True

    def test_is_challan_eligible_not_approved(self, db: Session):
        case = _create_test_case(db)
        assert is_challan_eligible(case) is False

        case.status = CaseStatus.rejected
        db.add(case)
        db.commit()
        assert is_challan_eligible(case) is False

        case.status = CaseStatus.ingested
        db.add(case)
        db.commit()
        assert is_challan_eligible(case) is False


class TestMarkChallanIssued:
    def test_mark_challan_issued_from_approved(self, db: Session):
        case = _create_test_case(db)
        case.status = CaseStatus.approved
        db.add(case)
        db.commit()

        updated = mark_challan_issued(db, case.case_id)
        assert updated.status == CaseStatus.challan_issued

    def test_mark_challan_issued_raises_from_ingested(self, db: Session):
        case = _create_test_case(db)

        with pytest.raises(CaseTransitionError):
            mark_challan_issued(db, case.case_id)

    def test_mark_challan_issued_raises_from_rejected(self, db: Session):
        case = _create_test_case(db)
        case.status = CaseStatus.rejected
        db.add(case)
        db.commit()

        with pytest.raises(CaseTransitionError):
            mark_challan_issued(db, case.case_id)