"""test_case_builder.py — verify the request payload shape, including the
two real mismatches found by testing against the live backend (plate
can't be null, location can't be null)."""
import os

from cv.evidence.case_builder import UNKNOWN_PLATE, build_ingest_request, evidence_refs_from_package
from cv.evidence.evidence_engine import EvidencePackage


def test_missing_plate_uses_placeholder_not_null():
    payload = build_ingest_request(
        violation_type="red_light_jump",
        camera_id="CAM-DEMO-01",
        occurred_at_iso="2026-08-20T18:30:00Z",
        evidence_refs=[{"kind": "image", "ref": "x.jpg"}],
        vehicle_plate=None,
    )
    # The real backend requires a non-empty string here — None/null gets a 422.
    assert payload["vehicle"]["plate"] == UNKNOWN_PLATE
    assert isinstance(payload["vehicle"]["plate"], str)


def test_missing_location_is_empty_dict_not_null():
    payload = build_ingest_request(
        violation_type="no_helmet",
        camera_id="CAM-DEMO-01",
        occurred_at_iso="2026-08-20T18:30:00Z",
        evidence_refs=[{"kind": "image", "ref": "x.jpg"}],
        location=None,
    )
    # The real backend's LocationIn schema rejects a literal null.
    assert payload["location"] == {}


def test_real_plate_is_used_as_is():
    payload = build_ingest_request(
        violation_type="red_light_jump",
        camera_id="CAM-DEMO-01",
        occurred_at_iso="2026-08-20T18:30:00Z",
        evidence_refs=[{"kind": "image", "ref": "x.jpg"}],
        vehicle_plate="MH12AB1234",
    )
    assert payload["vehicle"]["plate"] == "MH12AB1234"


def test_evidence_refs_from_package_includes_real_hashes(tmp_path):
    # Create small real files so we can hash them for real.
    paths = {}
    for name in ("pre", "trigger", "post", "clip"):
        p = tmp_path / f"{name}.bin"
        p.write_bytes(f"fake-{name}-content".encode())
        paths[name] = str(p)

    package = EvidencePackage(
        pre_frame_path=paths["pre"],
        trigger_frame_path=paths["trigger"],
        post_frame_path=paths["post"],
        clip_path=paths["clip"],
    )

    refs = evidence_refs_from_package(package, width=480, height=854)

    assert len(refs) == 4
    kinds = [r["kind"] for r in refs]
    assert kinds == ["image", "image", "image", "video"]
    # Every ref should have a real, non-placeholder sha256 (64 hex chars).
    for ref in refs:
        assert len(ref["sha256"]) == 64
        assert os.path.exists(ref["ref"])
