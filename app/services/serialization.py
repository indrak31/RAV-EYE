"""Candidate-IR / model <-> schema conversions.

The DB schema stores vehicle, officer, location as columns/tables instead of
JSON, but the public API nests them per api-contract.md. These helpers project
the ORM rows back into the Pydantic response models.
"""
from __future__ import annotations

import json

from app.models import Case
from app.schemas.case import (
    CaseListItem,
    CaseOut,
    EvidenceItemOut,
    LocationOut,
    OfficerOut,
    VehicleOut,
)
from app.schemas.enums import CaseStatus, ReviewDecision


def _evidence_item_to_out(item) -> EvidenceItemOut:
    return EvidenceItemOut(
        evidence_id=item.evidence_id,
        kind=item.kind,
        ref=item.ref,
        sha256=item.sha256,
        captured_at=item.captured_at,
        metadata=json.loads(item.metadata_json) if item.metadata_json else {},
    )


def case_to_out(case: Case) -> CaseOut:
    return CaseOut(
        case_id=case.case_id,
        status=case.status if isinstance(case.status, CaseStatus) else CaseStatus(case.status),
        vehicle=VehicleOut(
            plate=case.vehicle.plate if case.vehicle else "",
            vehicle_type=case.vehicle.vehicle_type if case.vehicle else None,
            color=case.vehicle.color if case.vehicle else None,
            make=case.vehicle.make if case.vehicle else None,
            model=case.vehicle.model if case.vehicle else None,
        )
        if case.vehicle
        else None,
        officer=OfficerOut(
            officer_id=case.officer.officer_id,
            name=case.officer.name,
            badge=case.officer.badge,
            station=case.officer.station,
        )
        if case.officer
        else None,
        violation_type=case.violation_type,
        location=LocationOut(lat=case.lat, lng=case.lng, address=case.address),
        camera_id=case.camera_id,
        occurred_at=case.occurrence_occurred_at,
        ingested_at=case.occurrence_ingested_at,
        reviewed_at=case.occurrence_reviewed_at,
        review_decision=_safe_review_decision(case.review_decision),
        reviewer_id=case.reviewer_id,
        evidence=[_evidence_item_to_out(e) for e in (case.evidence or [])],
    )


def case_to_list_item(case: Case) -> CaseListItem:
    return CaseListItem(
        case_id=case.case_id,
        status=case.status if isinstance(case.status, CaseStatus) else CaseStatus(case.status),
        violation_type=case.violation_type,
        camera_id=case.camera_id,
        plate=case.vehicle.plate if case.vehicle else None,
        occurred_at=case.occurrence_occurred_at,
        ingested_at=case.occurrence_ingested_at,
        reviewed_at=case.occurrence_reviewed_at,
        review_decision=_safe_review_decision(case.review_decision),
        evidence=[],
    )


def _safe_review_decision(raw) -> ReviewDecision | None:
    if raw is None:
        return None
    if isinstance(raw, ReviewDecision):
        return raw
    try:
        return ReviewDecision(raw)
    except ValueError:
        return None
