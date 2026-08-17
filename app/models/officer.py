"""Officer ORM model — many cases can be assigned to one officer."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Officer(Base):
    __tablename__ = "officers"

    officer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    badge: Mapped[str | None] = mapped_column(String(64))
    station: Mapped[str | None] = mapped_column(String(128))

    cases: Mapped[list["Case"]] = relationship("Case", back_populates="officer")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Officer officer_id={self.officer_id!r}>"
