"""annotator.py — draws boxes, track IDs, and labels onto a frame for preview/demo video.

Owner: Meghana (shared — anyone can extend this, it's low-risk visual code).

Status: STUB but simple — this one's mostly plumbing, safe to implement early
since it doesn't depend on a working model, just needs a frame + fake boxes.
"""
from __future__ import annotations

from typing import Iterable

from cv.pipeline.tracker import TrackedObject

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def draw_tracked_objects(frame, objects: Iterable[TrackedObject]):
    """Return a copy of frame with boxes + 'ClassName #track_id' labels drawn on it.

    TODO(Meghana/Aryan): color-code by violation status once rules exist
    (e.g. red box if flagged, green if clear).
    """
    if cv2 is None:
        raise RuntimeError("opencv-python is not installed yet.")

    out = frame.copy()
    for obj in objects:
        x1, y1, x2, y2 = (int(v) for v in obj.box_xyxy)
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{obj.class_name} #{obj.track_id} ({obj.confidence:.2f})"
        cv2.putText(out, label, (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return out
