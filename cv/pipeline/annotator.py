"""annotator.py — draws boxes, track IDs, and labels onto a frame for preview/demo video.

Owner: Meghana (shared — anyone can extend this, it's low-risk visual code).

Status: IMPLEMENTED. Bigger, more legible labels (with a solid background
so text doesn't get lost against a busy road), and each track_id gets its
own consistent color — makes it much easier to visually confirm "is this
the same car staying the same ID across frames?" at a glance, instead of
squinting at small numbers.
"""
from __future__ import annotations

from typing import Iterable

from cv.pipeline.detector import Detection
from cv.pipeline.tracker import TrackedObject

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

_GREEN = (0, 200, 0)

# A small fixed palette (BGR, since that's what OpenCV uses) — picked from
# it deterministically per track_id, so #3 is always the same color across
# every frame it appears in, without needing anything fancy like a hash.
_PALETTE = [
    (66, 135, 245),   # orange-blue
    (52, 194, 235),   # yellow
    (60, 76, 231),    # red
    (235, 52, 194),   # magenta
    (52, 235, 168),   # teal
    (235, 168, 52),   # cyan-ish
    (168, 52, 235),   # purple
    (52, 235, 79),    # green
]


def _color_for_track_id(track_id: int) -> tuple[int, int, int]:
    return _PALETTE[track_id % len(_PALETTE)]


def _draw_box_with_label(frame, box_xyxy, label: str, color: tuple[int, int, int]):
    x1, y1, x2, y2 = (int(v) for v in box_xyxy)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

    # Draw a solid background rectangle behind the text so it stays
    # readable over any part of the video (road, sky, another car, etc.)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    thickness = 2
    (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
    label_y1 = max(0, y1 - text_h - baseline - 6)
    cv2.rectangle(frame, (x1, label_y1), (x1 + text_w + 6, y1), color, -1)
    cv2.putText(
        frame, label, (x1 + 3, y1 - baseline - 3), font, font_scale, (255, 255, 255), thickness
    )


def draw_detections(frame, detections: Iterable[Detection]):
    """Same idea as draw_tracked_objects, but for raw Detections (no track_id
    yet — useful for testing detector.py on its own, without a tracker)."""
    if cv2 is None:
        raise RuntimeError("opencv-python is not installed yet.")

    out = frame.copy()
    for det in detections:
        label = f"{det.class_name} {det.confidence:.2f}"
        _draw_box_with_label(out, det.box_xyxy, label, _GREEN)
    return out


def draw_tracked_objects(frame, objects: Iterable[TrackedObject]):
    """Return a copy of frame with boxes + 'ClassName #track_id' labels drawn
    on it. Each track_id gets a consistent color, so the same vehicle
    should look visually the same color across every frame it appears in —
    a quick eyeball test for whether tracking is stable.

    TODO(Meghana/Aryan): color-code by violation status once rules exist
    (e.g. force red if flagged, overriding the per-ID color).
    """
    if cv2 is None:
        raise RuntimeError("opencv-python is not installed yet.")

    out = frame.copy()
    for obj in objects:
        color = _color_for_track_id(obj.track_id)
        label = f"#{obj.track_id} {obj.class_name}"
        _draw_box_with_label(out, obj.box_xyxy, label, color)
    return out
