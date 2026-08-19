"""tracker.py — gives each detected object a stable ID across frames.

Owner: Meghana.

Why this matters: detector.py finds boxes frame-by-frame with no memory.
Without a tracker, the same motorcycle would look like a "new" object in
every frame, and we could never say "this vehicle ran the red light" as
ONE continuous event. ByteTrack solves that by matching boxes across
frames and assigning a persistent track_id.

Status: STUB. update() is not implemented yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cv.pipeline.detector import Detection


@dataclass
class TrackedObject:
    track_id: int
    class_name: str
    confidence: float
    box_xyxy: tuple[float, float, float, float]


class Tracker:
    """Wraps a ByteTrack (or BoT-SORT fallback) tracker."""

    def __init__(self, track_thresh: float = 0.5):
        self.track_thresh = track_thresh
        self._impl = None  # loaded lazily

    def load(self) -> None:
        """TODO(Meghana):
            from boxmot import ByteTrack
            self._impl = ByteTrack(track_thresh=self.track_thresh)
        If ByteTrack loses IDs in dense traffic, switch to BoT-SORT and/or
        lower track_thresh (this was flagged as a known risk).
        """
        raise NotImplementedError("tracker.load() — plug in boxmot ByteTrack here")

    def update(self, detections: List[Detection]) -> List[TrackedObject]:
        """Feed this frame's detections in, get back the same objects with
        a track_id attached (matched against previous frames).

        TODO(Meghana): convert Detection list -> tracker input format,
        call self._impl.update(...), convert results back to TrackedObject.
        """
        raise NotImplementedError("tracker.update() — plug in real tracking here")
