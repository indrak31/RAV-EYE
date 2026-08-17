"""Helpers for 501 Not Implemented stubs shipped during Day 1.

The Day 1 contract states endpoints planned for D3-5 or D5-7 return 501 with
a `{ "detail": "not_implemented", "planned_day": "D3-5" }` body until they are
implemented in their scheduled day. Centralising keeps the routers quiet.
"""
from __future__ import annotations

from fastapi import HTTPException, status


def not_implemented(planned_day: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"detail": "not_implemented", "planned_day": planned_day},
    )
