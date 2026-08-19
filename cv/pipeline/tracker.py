"""tracker.py — gives each detected object a stable ID across frames.

Owner: Meghana.

Why this matters: detector.py finds boxes frame-by-frame with no memory.
Without a tracker, the same motorcycle would look like a "new" object in
every frame, and we could never say "this vehicle ran the red light" as
ONE continuous event. ByteTrack solves that by matching boxes across
frames and assigning a persistent track_id.

Status: IMPLEMENTED (first real version).

IMPORTANT design note — this deviates slightly from the original stub:
The original plan was Tracker.update(detections) — feed in detections
already produced by detector.py. But `ultralytics`'s built-in ByteTrack
does detection AND tracking together in a single call (model.track(frame)),
not "track these detections I already computed." Splitting them apart
would mean reimplementing frame-to-frame box matching ourselves for no
real benefit. So: Tracker wraps its OWN YOLO model (same weights as
detector.py) and Tracker.update() takes a raw `frame`, not a detections
list. detector.py is still useful on its own for one-off/no-tracking
checks (--detect-only mode); the real pipeline will use Tracker directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cv.pipeline.detector import RELEVANT_CLASSES


@dataclass
class TrackedObject:
    track_id: int
    class_name: str
    confidence: float
    box_xyxy: tuple[float, float, float, float]


class Tracker:
    """Wraps ultralytics' built-in ByteTrack. One instance, reused across
    all frames of a video (tracking needs memory of previous frames)."""

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        device: str = "cuda",
        conf_threshold: float = 0.4,
        tracker_config: str = "botsort.yaml",
        imgsz: int = 640,
    ):
        self.model_path = model_path
        self.device = device
        self.conf_threshold = conf_threshold
        # "botsort.yaml" is bundled with ultralytics (no download needed).
        # Measured on a real dense-traffic clip: BoT-SORT gave ~8% fewer
        # ID switches than default ByteTrack (82 vs 89 "unique" vehicles
        # on a 10s clip that visually has ~20-25 real ones). A real but
        # modest improvement — dense/low-res traffic footage remains a
        # known hard case (flagged as a risk in the original plan), not
        # something this one config switch fully solves.
        #
        # Tried and REJECTED after measuring (kept here so nobody re-tries
        # the same dead ends): raising imgsz to 960 made switching WORSE
        # (128 unique vehicles) — upscaling this already low-res, blocky
        # video just adds blurry noise, not real detail. Lowering
        # conf_threshold to 0.25 also made it worse for the same reason:
        # more noisy low-confidence detections flicker in and out, creating
        # more short-lived tracks, not fewer.
        self.tracker_config = tracker_config
        self.imgsz = imgsz
        self._model = None

    def load(self) -> None:
        from ultralytics import YOLO

        self._model = YOLO(self.model_path)
        self._model.to(self.device)

    def update(self, frame) -> List[TrackedObject]:
        """Run detection + tracking on one frame. `persist=True` tells
        ultralytics "remember what you saw in previous frames from this
        same model instance" — without it, every frame would restart
        tracking from zero, defeating the whole point.
        """
        if self._model is None:
            raise RuntimeError("Tracker.load() must be called before update()")

        results = self._model.track(
            frame,
            persist=True,
            tracker=self.tracker_config,
            imgsz=self.imgsz,
            conf=self.conf_threshold,
            verbose=False,
        )[0]

        tracked: List[TrackedObject] = []
        if results.boxes is None or results.boxes.id is None:
            # No tracks yet (can happen on the very first frame or a frame
            # with nothing detected) — return empty, not an error.
            return tracked

        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = self._model.names[class_id]
            confidence = float(box.conf[0])

            if class_name not in RELEVANT_CLASSES:
                continue
            if confidence < self.conf_threshold:
                continue
            if box.id is None:
                continue  # this particular box wasn't assigned a track yet

            track_id = int(box.id[0])
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])

            tracked.append(
                TrackedObject(
                    track_id=track_id,
                    class_name=class_name,
                    confidence=confidence,
                    box_xyxy=(x1, y1, x2, y2),
                )
            )

        return tracked
