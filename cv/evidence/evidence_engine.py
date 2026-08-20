"""evidence_engine.py — saves the "proof" frames + clip for a violation.

Owner: Aryan.

For every violation, an officer needs to SEE proof, not just trust a
number. This module picks 3 frames (before / at-the-moment / after the
violation) and cuts a short video clip around it.

Status: IMPLEMENTED using OpenCV directly (cv2.VideoWriter), NOT ffmpeg —
ffmpeg isn't installed in this dev environment, and adding it as a
dependency would mean every teammate needs to separately install it
outside of `pip install -r requirements-cv.txt`. OpenCV re-encodes frames
instead of ffmpeg's instant "-c copy" trick (a bit slower, produces a
slightly larger file for the same clip), but it's something we already
depend on everywhere else — no new install required for anyone. Worth
switching to ffmpeg later if clip-cutting speed becomes an actual problem
during the real demo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


@dataclass
class EvidencePackage:
    pre_frame_path: str
    trigger_frame_path: str
    post_frame_path: str
    clip_path: str


def build_evidence(
    video_path: str,
    trigger_frame_number: int,
    fps: float,
    output_dir: str,
    case_id: str,
    gap_seconds: float = 1.0,
    clip_seconds: float = 3.0,
) -> EvidencePackage:
    """Save 3 evidence frames (before/trigger/after) + a short clip
    centered on the violation moment.

    gap_seconds: how far before/after the trigger frame to grab the other
        2 still frames (default: 1 second before, 1 second after).
    clip_seconds: total length of the saved clip, centered on the trigger.
    case_id: used to namespace filenames so evidence from different
        violations doesn't overwrite each other.
    """
    if cv2 is None:
        raise RuntimeError("opencv-python is not installed yet.")

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        gap_frames = max(1, int(gap_seconds * fps))
        pre_frame_number = max(0, trigger_frame_number - gap_frames)
        post_frame_number = min(total_frames - 1, trigger_frame_number + gap_frames)

        def _save_frame(frame_number: int, suffix: str) -> str:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not read frame {frame_number} from {video_path}")
            path = os.path.join(output_dir, f"{case_id}_{suffix}.jpg")
            cv2.imwrite(path, frame)
            return path

        pre_path = _save_frame(pre_frame_number, "pre")
        trigger_path = _save_frame(trigger_frame_number, "trigger")
        post_path = _save_frame(post_frame_number, "post")

        # Clip: centered on the trigger frame, clip_seconds long total.
        clip_half_frames = max(1, int((clip_seconds / 2) * fps))
        clip_start = max(0, trigger_frame_number - clip_half_frames)
        clip_end = min(total_frames - 1, trigger_frame_number + clip_half_frames)

        clip_path = os.path.join(output_dir, f"{case_id}_clip.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, clip_start)
            for _ in range(clip_start, clip_end + 1):
                ok, frame = cap.read()
                if not ok:
                    break
                writer.write(frame)
        finally:
            writer.release()

    finally:
        cap.release()

    return EvidencePackage(
        pre_frame_path=pre_path,
        trigger_frame_path=trigger_path,
        post_frame_path=post_path,
        clip_path=clip_path,
    )
