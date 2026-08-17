"""Vehicle ORM model — one-to-one with Case (embedded JSON in API, row in DB).

Stores plate + descriptive fields captured by the CV pipeline. Storing it as
its own table (rather than a JSON column on Case) makes plate search future-
proof regardless of the backend DB.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.case_id", ondelete="CASCADE"), unique=True, index=True
    )

    plate: Mapped[str] = mapped_column(String(32), index=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(32))
    color: Mapped[str | None] = mapped_column(String(32))
    make: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(64))

    case: Mapped["Case"] = relationship("Case", back_populates="vehicle")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Vehicle id={self.id} plate={self.plate!r}>"
