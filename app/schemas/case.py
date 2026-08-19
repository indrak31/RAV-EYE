"""Request/response Pydantic schemas mirroring api-contract.md v1."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.enums import CaseStatus, ChallanChannel, EvidenceKind, ReviewDecision, ViolationType


# ---------------------------------------------------------------------------
# Shared sub-shapes
# ---------------------------------------------------------------------------


class VehicleIn(BaseModel):
    plate: str = Field(..., min_length=1, max_length=32)
    vehicle_type: str | None = Field(default=None, max_length=32)
    color: str | None = Field(default=None, max_length=32)
    make: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=64)

    @field_validator("plate")
    @classmethod
    def _normalize_plate(cls, v: str) -> str:
        # Upper-case ASCII, strip interior spaces — plates commonly arrive
        # lowercased from the CV stage.
        return "".join(ch for ch in v.upper() if ch.isalnum())


class VehicleOut(VehicleIn):
    pass


class OfficerIn(BaseModel):
    officer_id: str = Field(..., min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    badge: str | None = Field(default=None, max_length=64)
    station: str | None = Field(default=None, max_length=128)


class OfficerOut(OfficerIn):
    pass


class LocationIn(BaseModel):
    lat: float | None = None
    lng: float | None = None
    address: str | None = Field(default=None, max_length=256)


class LocationOut(LocationIn):
    pass


class EvidenceItemIn(BaseModel):
    kind: EvidenceKind
    ref: str = Field(..., min_length=1, max_length=512)
    sha256: str | None = Field(default=None, max_length=64)
    captured_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class EvidenceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    kind: str
    ref: str
    sha256: str | None
    captured_at: datetime | None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Case shapes
# ---------------------------------------------------------------------------


class CaseOut(BaseModel):
    """Full Case shape per api-contract.md."""

    model_config = ConfigDict(from_attributes=True)

    case_id: str
    status: CaseStatus
    vehicle: VehicleOut | None = None
    officer: OfficerOut | None = None
    violation_type: ViolationType
    location: LocationOut
    camera_id: str
    occurred_at: datetime
    ingested_at: datetime
    reviewed_at: datetime | None = None
    review_decision: ReviewDecision | None = None
    reviewer_id: str | None = None
    review_note: str | None = None
    evidence: list[EvidenceItemOut] = Field(default_factory=list)


class CaseListItem(BaseModel):
    """Lighter Case shape for list view (evidence stripped to empty array)."""

    model_config = ConfigDict(from_attributes=True)

    case_id: str
    status: CaseStatus
    violation_type: ViolationType
    camera_id: str
    plate: str | None = None
    occurred_at: datetime
    ingested_at: datetime
    reviewed_at: datetime | None = None
    review_decision: ReviewDecision | None = None
    evidence: list[EvidenceItemOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    client_request_id: str | None = Field(default=None, max_length=128)
    vehicle: VehicleIn
    officer: OfficerIn | None = None
    violation_type: ViolationType
    location: LocationIn = Field(default_factory=LocationIn)
    camera_id: str = Field(..., min_length=1, max_length=64)
    occurred_at: datetime
    evidence: list[EvidenceItemIn] = Field(..., min_length=1, max_length=64)

    @field_validator("occurred_at", mode="before")
    @classmethod
    def _coerce_utc(cls, v):
        # Per api-contract.md all timestamps are UTC. Treat naive input as UTC.
        from datetime import timezone

        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @field_validator("occurred_at")
    @classmethod
    def _occurred_not_future(cls, v: datetime) -> datetime:
        from datetime import timezone

        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if (v - now).total_seconds() > 300:
            raise ValueError("occurred_at cannot be more than 5 minutes in the future")
        return v


class IngestResponse(BaseModel):
    case_id: str
    status: CaseStatus
    created_at: datetime
    replayed: bool = False


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class CaseListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CaseListItem]


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    decision: ReviewDecision
    reviewer_id: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=2048)


# ---------------------------------------------------------------------------
# Challan
# ---------------------------------------------------------------------------


class ChallanRequest(BaseModel):
    case_id: str
    channel: ChallanChannel = ChallanChannel.sms


class ChallanResponse(BaseModel):
    challan_id: str
    case_id: str
    status: str
    channel: ChallanChannel


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class AnalyticsRow(BaseModel):
    violation_type: str | None = None
    camera_id: str | None = None
    hour: int | None = None
    count: int


class AnalyticsResponse(BaseModel):
    from_: str | None = None
    to: str | None = None
    group_by: list[str]
    rows: list[AnalyticsRow]
    totals: dict[str, dict[str, int]]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    db: str
    time: datetime


# ---------------------------------------------------------------------------
# Errors / stubs
# ---------------------------------------------------------------------------


class NotImplementedResponse(BaseModel):
    detail: str = "not_implemented"
    planned_day: str


class ErrorResponse(BaseModel):
    detail: str
