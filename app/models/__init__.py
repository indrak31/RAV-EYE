"""ORM models package.

Importing `app.models` ensures all model classes are registered on
`Base.metadata` so `db.init_db()` (create_all) sees the full schema.
"""
from app.models.case import Case, EvidenceItem
from app.models.officer import Officer
from app.models.vehicle import Vehicle

__all__ = ["Case", "EvidenceItem", "Officer", "Vehicle"]
