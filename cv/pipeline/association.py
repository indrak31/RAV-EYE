"""association.py — matches a detected plate to the correct tracked vehicle.

Owner: Aryan.

Why needed: plate_detector.py finds plates, tracker.py tracks vehicles —
but nothing yet says "this plate belongs to THAT vehicle". This module
answers that using IOU (how much two boxes overlap) across a few frames.

Status: STUB.
"""
from __future__ import annotations

from cv.pipeline.tracker import TrackedObject
from cv.pipeline.plate_detector import PlateBox


def iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    """Intersection-over-union of two (x1,y1,x2,y2) boxes. 0 = no overlap, 1 = identical."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def match_plate_to_vehicle(
    plate: PlateBox, candidates: list[TrackedObject], min_iou: float = 0.1
) -> TrackedObject | None:
    """Return the tracked vehicle whose box overlaps the plate box the most,
    or None if nothing overlaps enough.

    TODO(Aryan): this is a real, working first version already — the main
    thing left is calling it correctly within the pipeline (across a
    5-frame window per the plan, not just one frame).
    """
    best_match = None
    best_score = min_iou
    for candidate in candidates:
        score = iou(plate.box_xyxy, candidate.box_xyxy)
        if score > best_score:
            best_score = score
            best_match = candidate
    return best_match
