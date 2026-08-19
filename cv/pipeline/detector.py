"""detector.py — runs YOLO on a frame to find vehicles/people/lights.

Owner: Meghana. Runs on the Asus TUF (needs a GPU for real-time speed;
falls back to CPU but will be slow).

Status: IMPLEMENTED (first real version). Uses the `ultralytics` package's
pretrained YOLOv8n model, which already knows how to recognize ~80 everyday
object classes (it was trained on a public dataset called COCO) — including
"person", "car", "motorcycle", "bus", "truck", "traffic light". We are not
training anything ourselves here; we're just asking a model that already
knows these things to look at our frames.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

# Only keep detections for classes we actually care about for this project.
# YOLOv8n (COCO-pretrained) knows ~80 classes total; everything else
# (e.g. "banana", "chair") gets filtered out before it ever reaches the
# rest of the pipeline.
RELEVANT_CLASSES = {"person", "car", "motorcycle", "bus", "truck", "traffic light"}


@dataclass
class Detection:
    """One detected object in one frame."""
    class_name: str       # e.g. "person", "motorcycle", "car", "traffic light"
    confidence: float     # 0.0 - 1.0
    box_xyxy: tuple[float, float, float, float]  # (x1, y1, x2, y2) pixel coords


class Detector:
    """Wraps a YOLO model. One instance, reused across all frames of a video."""

    def __init__(self, model_path: str = "yolov8n.pt", device: str = "cuda", conf_threshold: float = 0.4):
        self.model_path = model_path
        self.device = device
        self.conf_threshold = conf_threshold  # ignore detections the model itself is < 40% sure about
        self._model = None  # loaded lazily in load()

    def load(self) -> None:
        """Load the model weights into memory.

        model_path defaults to just "yolov8n.pt" (not a local file path) —
        ultralytics recognizes this as a "standard" model name and will
        automatically download it the first time (a few MB) and cache it
        locally after that, so nothing needs to be committed to the repo.

        device="cuda" targets your GPU. If no GPU is available, ultralytics
        prints a warning and quietly falls back to CPU on its own — it
        won't crash, it'll just run slower.
        """
        from ultralytics import YOLO  # imported here, not at the top of the file,

        # so this module can still be imported (e.g. by tests) even before
        # ultralytics is installed — only load() needs it.
        self._model = YOLO(self.model_path)
        # .to(device) moves the model onto the GPU (or CPU) explicitly.
        self._model.to(self.device)

    def detect(self, frame) -> List[Detection]:
        """Run detection on a single frame, return a list of Detections.

        `frame` is a single image — the same kind of object video_reader.py
        hands you in its (frame_number, frame) loop.
        """
        if self._model is None:
            raise RuntimeError("Detector.load() must be called before detect()")

        # Running the model on a frame gives back a `results` list (one
        # entry per image passed in — we only pass one, so we take [0]).
        # `verbose=False` stops ultralytics from printing a log line per frame.
        results = self._model(frame, verbose=False)[0]

        detections: List[Detection] = []
        for box in results.boxes:
            class_id = int(box.cls[0])                 # a number, e.g. 2
            class_name = self._model.names[class_id]    # ultralytics maps number -> name, e.g. "car"
            confidence = float(box.conf[0])              # e.g. 0.87

            if class_name not in RELEVANT_CLASSES:
                continue  # skip anything we don't care about (e.g. "dog")
            if confidence < self.conf_threshold:
                continue  # skip low-confidence guesses

            # box.xyxy[0] is a tensor like [x1, y1, x2, y2] in pixel coords —
            # convert to a plain tuple of floats so the rest of our code
            # doesn't need to know anything about PyTorch tensors.
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])

            detections.append(
                Detection(
                    class_name=class_name,
                    confidence=confidence,
                    box_xyxy=(x1, y1, x2, y2),
                )
            )

        return detections
