"""video_reader.py — turns a video file into a stream of frames.

Owner: Meghana.

Status: STUB. The frame-reading loop is real and works today (it just needs
opencv-python installed). What's NOT done yet: any actual detection — that
lives in detector.py.

Why a generator? So the rest of the pipeline can do:
    for frame_number, frame in read_frames("clip.mp4"):
        ...
without loading the whole video into memory at once.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Tuple

try:
    import cv2  # opencv-python
except ImportError:  # pragma: no cover - allows importing this module before deps are installed
    cv2 = None


@dataclass
class VideoMeta:
    fps: float
    width: int
    height: int
    frame_count: int


def read_frames(video_path: str, resize_width: int | None = 640) -> Iterator[Tuple[int, "cv2.Mat"]]:
    """Yield (frame_number, frame) pairs from a video file.

    resize_width: if set, frames are resized so their width matches this
    value (keeps aspect ratio). Smaller frames = faster detection later.
    Set to None to keep original resolution.

    TODO(Meghana): add support for RTSP/live camera URLs, not just files.
    """
    if cv2 is None:
        raise RuntimeError(
            "opencv-python is not installed yet. Run: pip install -r requirements-cv.txt"
        )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    frame_number = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if resize_width is not None:
                h, w = frame.shape[:2]
                scale = resize_width / w
                frame = cv2.resize(frame, (resize_width, int(h * scale)))
            yield frame_number, frame
            frame_number += 1
    finally:
        cap.release()


def get_video_meta(video_path: str) -> VideoMeta:
    """Read basic metadata (fps, size, frame count) without decoding frames."""
    if cv2 is None:
        raise RuntimeError(
            "opencv-python is not installed yet. Run: pip install -r requirements-cv.txt"
        )
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    meta = VideoMeta(
        fps=cap.get(cv2.CAP_PROP_FPS),
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    )
    cap.release()
    return meta
