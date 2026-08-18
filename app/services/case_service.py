"""Case service — business logic for case lifecycle and status transitions.

This module contains the core business logic that Indra's API endpoints call.
Routes stay thin; all state transitions and validation live here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Case, Vehicle
from app.schemas.case import ReviewRequest
from app.schemas.enums import CaseStatus, ReviewDecision


class CaseNotFoundError(Exception):
    """Raised when a case_id does not exist."""

    def __init__(self, case_id: str):
        self.case_id = case_id
        super().__init__(f"Case not found: {case_id}")


class CaseNotReviewableError(Exception):
    """Raised when a case cannot be reviewed due to its current status."""

    def __init__(self, case_id: str, current_status: CaseStatus):
        self.case_id = case_id
        self.current_status = current_status
        super().__init__(
            f"Case {case_id} is not reviewable (status: {current_status.value})"
        )


class CaseTransitionError(Exception):
    """Raised when a status transition is invalid."""

    def __init__(self, case_id: str, from_status: CaseStatus, to_status: CaseStatus):
        self.case_id = case_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid transition for case {case_id}: {from_status.value} -> {to_status.value}"
        )


_REVIEWABLE_STATUSES = {CaseStatus.ingested, CaseStatus.in_review}
_APPROVABLE_STATUSES = {CaseStatus.ingested, CaseStatus.in_review}
_REJECTABLE_STATUSES = {CaseStatus.ingested, CaseStatus.in_review}


def get_case(db: Session, case_id: str) -> Case:
    """Fetch a case by ID or raise CaseNotFoundError."""
    case = db.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(case_id)
    return case


def list_cases(
    db: Session,
    *,
    status_filter: list[CaseStatus] | None = None,
    camera_id: str | None = None,
    violation_type: str | None = None,
    plate: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, Sequence[Case]]:
    """List cases with filters and pagination.

    Returns (total_count, cases_list).
    """
    stmt = select(Case)

    if status_filter:
        stmt = stmt.where(Case.status.in_(status_filter))
    if camera_id:
        stmt = stmt.where(Case.camera_id == camera_id)
    if violation_type:
        stmt = stmt.where(Case.violation_type == violation_type)
    if plate:
        # Case-insensitive substring match per api-contract.md
        # Use relationship.has() for correlated EXISTS subquery
        stmt = stmt.where(Case.vehicle.has(Vehicle.plate.ilike(f"%{plate.upper()}%")))

    # Total count (before pagination)
    count_stmt = select(func.count(Case.case_id))
    if stmt.whereclause is not None:
        count_stmt = count_stmt.where(stmt.whereclause)
    total_count = db.execute(count_stmt).scalar_one()

    # Paginated results
    stmt = stmt.order_by(Case.occurrence_ingested_at.desc()).limit(limit).offset(offset)
    cases = db.execute(stmt).scalars().all()

    return total_count, cases


def review_case(
    db: Session,
    case_id: str,
    payload: ReviewRequest,
) -> Case:
    """Apply a review decision to a case.

    Valid transitions:
    - ingested -> approved (sets status=approved, reviewed_at=now)
    - ingested -> rejected (sets status=rejected, reviewed_at=now)
    - in_review -> approved
    - in_review -> rejected

    Raises:
        CaseNotFoundError: if case_id doesn't exist.
        CaseNotReviewableError: if case status is not ingested or in_review.
    """
    case = get_case(db, case_id)

    if case.status not in _REVIEWABLE_STATUSES:
        raise CaseNotReviewableError(case_id, case.status)

    now = datetime.now(timezone.utc)

    if payload.decision == ReviewDecision.approved:
        case.status = CaseStatus.approved
    elif payload.decision == ReviewDecision.rejected:
        case.status = CaseStatus.rejected
    else:
        raise ValueError(f"Unknown review decision: {payload.decision}")

    case.occurrence_reviewed_at = now
    case.review_decision = payload.decision.value
    case.reviewer_id = payload.reviewer_id
    case.review_note = payload.note

    db.add(case)
    db.flush()
    db.commit()
    db.refresh(case)
    return case


def transition_to_in_review(db: Session, case_id: str) -> Case:
    """Move a case from ingested to in_review.

    This is called when a reviewer first opens a case for review.
    Idempotent: if already in_review or beyond, returns current case.
    """
    case = get_case(db, case_id)

    if case.status == CaseStatus.ingested:
        case.status = CaseStatus.in_review
        db.add(case)
        db.flush()
        db.commit()
        db.refresh(case)

    return case


def is_challan_eligible(case: Case) -> bool:
    """Check if a case can have a challan issued."""
    return case.status == CaseStatus.approved


def mark_challan_issued(db: Session, case_id: str) -> Case:
    """Mark a case as challan_issued after successful challan generation."""
    case = get_case(db, case_id)

    if not is_challan_eligible(case):
        raise CaseTransitionError(case_id, case.status, CaseStatus.challan_issued)

    case.status = CaseStatus.challan_issued
    db.add(case)
    db.flush()
    db.commit()
    db.refresh(case)
    return case