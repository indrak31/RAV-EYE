"""case_builder.py — assembles everything into the exact JSON the backend expects.

Owner: Aryan (shared — this is the "contract glue" piece, worth both of you
reading it since it's what run_pipeline.py sends to POST /api/ingest).

This MUST match docs/api-contract.md's IngestRequest shape exactly, or the
backend will reject it with a 422 error. See that file for the full spec.

Status: STUB, but the shape below is filled in from the real contract so
it's ready to have real values plugged in.
"""
from __future__ import annotations

from typing import Any


def build_ingest_request(
    client_request_id: str,
    vehicle_plate: str | None,
    violation_type: str,
    camera_id: str,
    occurred_at_iso: str,
    evidence_refs: list[dict],
    location: dict | None = None,
    officer: dict | None = None,
) -> dict[str, Any]:
    """Build a dict matching docs/api-contract.md's POST /api/ingest body.

    evidence_refs: list of dicts like
        {"kind": "image", "ref": "media/case123/frame-001.jpg",
         "sha256": "...", "captured_at": "...", "metadata": {"width":..,"height":..}}

    TODO(Aryan): call this from run_pipeline.py once a Violation +
    EvidencePackage exist, filling in real values instead of the caller
    passing None everywhere. vehicle_plate may be None if OCR failed —
    the contract allows that.
    """
    return {
        "client_request_id": client_request_id,
        "vehicle": {
            "plate": vehicle_plate,
            "vehicle_type": None,   # TODO: fill from detector class_name
            "color": None,
            "make": None,
            "model": None,
        },
        "officer": officer,  # None is fine — contract allows null for automated cases
        "violation_type": violation_type,
        "location": location,
        "camera_id": camera_id,
        "occurred_at": occurred_at_iso,
        "evidence": evidence_refs,
    }
