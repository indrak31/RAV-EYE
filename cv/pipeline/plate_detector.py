"""plate_detector.py — finds license plate bounding boxes on a frame.

Owner: Aryan. CPU-friendly — runs fine on the Mac, no GPU needed for a
lightweight plate-detection model at this scale.

Status: STUB.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlateBox:
    box_xyxy: tuple[float, float, float, float]
    confidence: float


class PlateDetector:
    def __init__(self, model_path: str = "models/plate_yolov8n.pt"):
        self.model_path = model_path
        self._model = None

    def load(self) -> None:
        """TODO(Aryan): load a plate-detection YOLO model (Roboflow
        'indian-license-plate' or similar). CPU inference is fine here —
        plates are detected once per vehicle crop, not every frame."""
        raise NotImplementedError("plate_detector.load() — plug in plate model")

    def detect(self, vehicle_crop) -> list[PlateBox]:
        """TODO(Aryan): run detection on a cropped vehicle image, return
        plate boxes found within it."""
        raise NotImplementedError("plate_detector.detect() — plug in real inference")
