"""Case ORM model — the central entity.

A Case represents a single detected traffic violation. It owns its evidence
items via one-to-many and points (optionally) at an Officer. Vehicle is one-to-
one back-populated.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.schemas.enums import CaseStatus, ViolationType


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_request_id: Mapped[str | None] = mapped_column(String(128), index=True)

    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status"), default=CaseStatus.ingested, index=True
    )

    violation_type: Mapped[ViolationType] = mapped_column(
        Enum(ViolationType, name="violation_type"), index=True
    )
    camera_id: Mapped[str] = mapped_column(String(64), index=True)

    # Location — stored as scalar columns for portability across SQLite/Postgres.
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(String(256))

    occurrence_occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    occurrence_ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occurrence_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_decision: Mapped[str | None] = mapped_column(String(32))
    reviewer_id: Mapped[str | None] = mapped_column(String(64))
    review_note: Mapped[str | None] = mapped_column(Text)

    # Relationships
    officer_id: Mapped[str | None] = mapped_column(
        ForeignKey("officers.officer_id", ondelete="SET NULL"), index=True
    )
    officer: Mapped["Officer | None"] = relationship("Officer", back_populates="cases")

    vehicle: Mapped["Vehicle | None"] = relationship(
        "Vehicle",
        back_populates="case",
        uselist=False,
        cascade="all, delete-orphan",
    )
    evidence: Mapped[list["EvidenceItem"]] = relationship(
        "EvidenceItem",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="EvidenceItem.captured_at",
    )

    __table_args__ = (
        Index("ix_cases_camera_type_status", "camera_id", "violation_type", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Case case_id={self.case_id!r} status={self.status}>"


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.case_id", ondelete="CASCADE"), index=True
    )

    kind: Mapped[str] = mapped_column(String(32))  # image | video | audio | document
    ref: Mapped[str] = mapped_column(String(512))   # URI / object key
    sha256: Mapped[str | None] = mapped_column(String(64))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[str | None] = mapped_column(Text)  # JSON-encoded dict

    case: Mapped["Case"] = relationship("Case", back_populates="evidence")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EvidenceItem id={self.evidence_id} kind={self.kind}>"
