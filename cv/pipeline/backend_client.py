"""backend_client.py — pushes a built case to the backend's POST /api/ingest.

Owner: Meghana. Tiny wrapper, verified against a REAL running backend
(uvicorn app.main:app), not just assumed to work from reading the contract.
"""
from __future__ import annotations

import httpx


def push_case(payload: dict, base_url: str = "http://127.0.0.1:8000", timeout: float = 10.0) -> dict:
    """POST payload (from case_builder.build_ingest_request) to /api/ingest.
    Returns the parsed JSON response ({case_id, status, created_at, ...})
    on success. Raises httpx.HTTPStatusError with the backend's own error
    detail on failure (422 validation error, etc.) — deliberately not
    swallowed, since a silently-dropped violation is worse than a loud crash.
    """
    response = httpx.post(f"{base_url}/api/ingest", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()
