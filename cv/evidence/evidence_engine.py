"""evidence_engine.py — saves the "proof" frames + clip for a violation.

Owner: Aryan.

For every violation, an officer needs to SEE proof, not just trust a
number. This module picks 3 frames (before / at-the-moment / after the
violation) and cuts a short video clip around it.

Status: STUB.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvidencePackage:
    pre_frame_path: str
    trigger_frame_path: str
    post_frame_path: str
    clip_path: str


def build_evidence(video_path: str, trigger_frame_number: int, fps: float, output_dir: str) -> EvidencePackage:
    """TODO(Aryan):
    1. Save the trigger frame, plus one ~1s before and ~1s after, as JPEGs.
    2. Cut a short clip (e.g. 3 seconds centered on the trigger) using
       ffmpeg (-ss/-t/-c copy, per the plan — fast, no re-encoding).
    3. Return paths to all of it as an EvidencePackage.
    """
    raise NotImplementedError("evidence_engine.build_evidence() — needs frame-saving + ffmpeg clip cut")
