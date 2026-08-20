"""case_builder.py — assembles everything into the exact JSON the backend expects.

Owner: Aryan (shared — this is the "contract glue" piece, worth both of you
reading it since it's what run_pipeline.py sends to POST /api/ingest).

Status: IMPLEMENTED, and verified against the REAL running backend, not
just docs/api-contract.md's markdown — which turned out to be stale in two
ways (found by actually POSTing to a live server and reading the 422):

1. docs/api-contract.md says vehicle.plate can be absent for automated
   cases. The real Pydantic schema (app/schemas/case.py: VehicleIn.plate)
   requires a non-empty string — no null, no missing key. So when we don't
   have a real plate yet (Aryan's OCR isn't built, or detection failed),
   we send a placeholder "UNKNOWN" instead of null. Flagged clearly below
   so nobody mistakes a placeholder for a real reading.
2. The doc implies location can be omitted/null. The real schema
   (LocationIn) has a default_factory, so it wants an object (possibly all
   fields empty), not the JSON value null.

Moral: when the code and the doc disagree, trust a real request against
the running server over what the markdown says — and fix the doc.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from cv.evidence.evidence_engine import EvidencePackage

# Placeholder plate value when we genuinely don't have one (OCR not run,
# or it failed). The real backend REQUIRES a non-empty string here — see
# the module docstring above for why this isn't just null.
UNKNOWN_PLATE = "UNKNOWN"


def _sha256_of_file(path: str) -> str:
    """Real content hash of an evidence file — lets anyone later verify a
    piece of evidence hasn't been altered since it was captured. Cheap at
    the file sizes involved here (a few frames + a short clip)."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def evidence_refs_from_package(package: EvidencePackage, width: int, height: int) -> list[dict]:
    """Convert an EvidencePackage (file paths) into the evidence[] shape
    the backend expects, with real sha256 hashes — not placeholders."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {
            "kind": "image",
            "ref": package.pre_frame_path,
            "sha256": _sha256_of_file(package.pre_frame_path),
            "captured_at": now_iso,
            "metadata": {"width": width, "height": height},
        },
        {
            "kind": "image",
            "ref": package.trigger_frame_path,
            "sha256": _sha256_of_file(package.trigger_frame_path),
            "captured_at": now_iso,
            "metadata": {"width": width, "height": height},
        },
        {
            "kind": "image",
            "ref": package.post_frame_path,
            "sha256": _sha256_of_file(package.post_frame_path),
            "captured_at": now_iso,
            "metadata": {"width": width, "height": height},
        },
        {
            "kind": "video",
            "ref": package.clip_path,
            "sha256": _sha256_of_file(package.clip_path),
            "captured_at": now_iso,
            "metadata": {"width": width, "height": height},
        },
    ]


def build_ingest_request(
    violation_type: str,
    camera_id: str,
    occurred_at_iso: str,
    evidence_refs: list[dict],
    client_request_id: str | None = None,
    vehicle_plate: str | None = None,
    vehicle_type: str | None = None,
    location: dict | None = None,
    officer: dict | None = None,
) -> dict[str, Any]:
    """Build a dict matching the REAL backend's IngestRequest schema
    (app/schemas/case.py), verified by an actual POST against a running
    server — not just read off the markdown doc.

    evidence_refs: list of dicts like
        {"kind": "image", "ref": "media/case123/frame-001.jpg",
         "sha256": "...", "captured_at": "...", "metadata": {"width":..,"height":..}}
        Must have at least 1 item — the backend rejects an empty list.

    vehicle_plate: pass None if OCR hasn't run or failed — this function
    substitutes UNKNOWN_PLATE, since the backend requires a real string.
    """
    return {
        "client_request_id": client_request_id,
        "vehicle": {
            "plate": vehicle_plate or UNKNOWN_PLATE,
            "vehicle_type": vehicle_type,
            "color": None,
            "make": None,
            "model": None,
        },
        "officer": officer,
        "violation_type": violation_type,
        "location": location or {},  # backend wants {} or omitted, NOT null
        "camera_id": camera_id,
        "occurred_at": occurred_at_iso,
        "evidence": evidence_refs,
    }
