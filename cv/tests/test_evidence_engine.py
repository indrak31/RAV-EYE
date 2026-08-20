"""test_evidence_engine.py — verify frame + clip saving using a small
synthetic video we build ourselves (no real footage needed)."""
import os

import cv2
import numpy as np

from cv.evidence.evidence_engine import build_evidence


def _make_synthetic_video(path: str, n_frames: int = 30, fps: float = 30.0, size=(64, 48)):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, size)
    for i in range(n_frames):
        # Each frame a different brightness, so we can tell frames apart later if needed.
        frame = np.full((size[1], size[0], 3), fill_value=i * 5 % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_build_evidence_saves_frames_and_clip(tmp_path):
    video_path = str(tmp_path / "synthetic.mp4")
    _make_synthetic_video(video_path, n_frames=30, fps=30.0)

    output_dir = str(tmp_path / "evidence")
    package = build_evidence(
        video_path=video_path,
        trigger_frame_number=15,
        fps=30.0,
        output_dir=output_dir,
        case_id="TEST-CASE-001",
    )

    assert os.path.exists(package.pre_frame_path)
    assert os.path.exists(package.trigger_frame_path)
    assert os.path.exists(package.post_frame_path)
    assert os.path.exists(package.clip_path)

    # Sanity check the saved frames are actually readable images, not empty files.
    assert cv2.imread(package.trigger_frame_path) is not None
    assert os.path.getsize(package.clip_path) > 0


def test_build_evidence_clamps_to_video_bounds(tmp_path):
    """Trigger frame near the very start/end shouldn't crash trying to
    grab a 'before'/'after' frame that doesn't exist."""
    video_path = str(tmp_path / "short.mp4")
    _make_synthetic_video(video_path, n_frames=10, fps=30.0)

    output_dir = str(tmp_path / "evidence")
    package = build_evidence(
        video_path=video_path,
        trigger_frame_number=0,  # very first frame — no "before" frame exists
        fps=30.0,
        output_dir=output_dir,
        case_id="TEST-CASE-002",
    )

    assert os.path.exists(package.pre_frame_path)
    assert os.path.exists(package.trigger_frame_path)
    assert os.path.exists(package.post_frame_path)
