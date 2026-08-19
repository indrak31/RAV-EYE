"""detector.py — runs YOLO on a frame to find vehicles/people/lights.

Owner: Meghana. Runs on the Asus TUF (needs a GPU for real-time speed;
falls back to CPU but will be slow).

Status: STUB. detect() is not implemented yet — it raises NotImplementedError
on purpose so nothing silently pretends to work. Next step: load a real
yolov8n.pt model with the `ultralytics` package and return real boxes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Detection:
    """One detected object in one frame."""
    class_name: str       # e.g. "person", "motorcycle", "car", "traffic light"
    confidence: float     # 0.0 - 1.0
    box_xyxy: tuple[float, float, float, float]  # (x1, y1, x2, y2) pixel coords


class Detector:
    """Wraps a YOLO model. One instance, reused across all frames of a video."""

    def __init__(self, model_path: str = "models/yolov8n.pt", device: str = "cuda"):
        self.model_path = model_path
        self.device = device
        self._model = None  # loaded lazily in load()

    def load(self) -> None:
        """Load the model weights into memory.

        TODO(Meghana):
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
        Keep device="cuda" for the TUF's GPU; fall back to "cpu" if no GPU
        is found (ultralytics does this automatically if cuda isn't available).
        """
        raise NotImplementedError("detector.load() — plug in ultralytics YOLO here")

    def detect(self, frame) -> List[Detection]:
        """Run detection on a single frame, return a list of Detections.

        TODO(Meghana): call self._model(frame) and convert results into
        Detection objects. Filter to the classes we care about:
        person, motorcycle, car, bus, truck, traffic light.
        """
        raise NotImplementedError("detector.detect() — plug in real inference here")
