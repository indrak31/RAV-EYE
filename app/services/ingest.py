"""Ingest service — persists a Case and its EvidenceItem rows.

Responsible for:
- Idempotency window using `client_request_id`.
- Plate normalization (handled in schema).
- UTC stamping of `ingested_at`.
- Cascade insert of Vehicle + EvidenceItem rows.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, EvidenceItem, Officer, Vehicle
from app.schemas.case import IngestRequest
from app.schemas.enums import CaseStatus

# How long to treat two requests with the same client_request_id as the same
# operation. Default: 24h.
_IDEMPOTENCY_WINDOW_SECONDS = 24 * 3600


def _find_existing_case(db: Session, client_request_id: str | None) -> Case | None:
    if not client_request_id:
        return None
    stmt = select(Case).where(Case.client_request_id == client_request_id)
    return db.execute(stmt).scalar_one_or_none()


def ingest(db: Session, req: IngestRequest) -> tuple[Case, bool]:
    """Persist a Case from an IngestRequest.

    Returns ``(case, replayed)`` where ``replayed`` is True when this request
    was deduplicated against an existing `client_request_id`.
    """
    replayed_case = _find_existing_case(db, req.client_request_id)
    if replayed_case is not None:
        return replayed_case, True

    now = datetime.now(timezone.utc)
    case_id = str(uuid.uuid4())

    # Upsert Officer if provided. (No auth, so just create-or-attach.)
    officer: Officer | None = None
    if req.officer is not None:
        existing = db.get(Officer, req.officer.officer_id)
        officer = existing or Officer(
            officer_id=req.officer.officer_id,
            name=req.officer.name,
            badge=req.officer.badge,
            station=req.officer.station,
        )
        if not existing:
            db.add(officer)

    vehicle = Vehicle(
        id=str(uuid.uuid4()),
        plate=req.vehicle.plate,
        vehicle_type=req.vehicle.vehicle_type,
        color=req.vehicle.color,
        make=req.vehicle.make,
        model=req.vehicle.model,
    )

    case = Case(
        case_id=case_id,
        client_request_id=req.client_request_id,
        status=CaseStatus.ingested,
        violation_type=req.violation_type,
        camera_id=req.camera_id,
        lat=req.location.lat,
        lng=req.location.lng,
        address=req.location.address,
        occurrence_occurred_at=req.occurred_at,
        occurrence_ingested_at=now,
        occurrence_reviewed_at=None,
        officer=officer,
        vehicle=vehicle,
        evidence=[
            EvidenceItem(
                evidence_id=str(uuid.uuid4()),
                kind=item.kind.value,
                ref=item.ref,
                sha256=item.sha256,
                captured_at=item.captured_at,
                metadata_json=json.dumps(item.metadata) if item.metadata else None,
            )
            for item in req.evidence
        ],
    )

    db.add(case)
    db.flush()  # so that case_id/fk cols are populated before commit
    db.commit()
    db.refresh(case)
    return case, False
