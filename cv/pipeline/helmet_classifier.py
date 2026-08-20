"""helmet_classifier.py — detects "With Helmet" / "Without Helmet" boxes on a frame.

Owner: Meghana.

Uses a pretrained model (not trained by us): Weights/best.pt from
https://github.com/Juliowiwiwiwi/Bike-Helmet-Detction-Model — a YOLOv8l
model, 2 classes, trained by a third party for 100 epochs on a Roboflow
bike-helmet dataset. Downloaded 2026-08-21, saved to cv/models/helmet_best.pt
(gitignored — large binary, everyone re-downloads it, doesn't belong in git).

IMPORTANT — tested on our own footage before trusting it: on our real
intersection clip, this model produced false positives on non-people
(a billboard, a car roof), at low confidence (0.29-0.54). It's a decent
starting point, NOT a validated, trustworthy classifier on its own.
This is exactly why no_helmet_rule.py doesn't use this module's output
directly — it only trusts a "Without Helmet" detection that's physically
close to an actual tracked motorcycle, which filters out exactly the kind
of stray false positives we saw (a billboard has no nearby motorcycle
track). See no_helmet_rule.py for that association logic.

This module itself just wraps the model — same shape as detector.py,
deliberately, so it's easy to understand if you already read that file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

# A higher floor than detector.py's 0.4 default — we already measured this
# model producing garbage even up to conf~0.4 on real footage, so we start
# more skeptical here. Revisit if this turns out to reject too much.
_DEFAULT_CONF_THRESHOLD = 0.5

_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "helmet_best.pt"
)


@dataclass
class HelmetDetection:
    label: str             # "with_helmet" or "without_helmet"
    confidence: float
    box_xyxy: tuple[float, float, float, float]


# The model's own class names -> our normalized labels.
_LABEL_MAP = {"With Helmet": "with_helmet", "Without Helmet": "without_helmet"}


class HelmetClassifier:
    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH, device: str = "cuda", conf_threshold: float = _DEFAULT_CONF_THRESHOLD):
        self.model_path = model_path
        self.device = device
        self.conf_threshold = conf_threshold
        self._model = None

    def load(self) -> None:
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Helmet model not found at {self.model_path}. "
                "Download it from https://github.com/Juliowiwiwiwi/Bike-Helmet-Detction-Model "
                "(Weights/best.pt) and save it there — it's gitignored, not committed to the repo."
            )
        from ultralytics import YOLO

        self._model = YOLO(self.model_path)
        self._model.to(self.device)

    def detect(self, frame) -> List[HelmetDetection]:
        if self._model is None:
            raise RuntimeError("HelmetClassifier.load() must be called before detect()")

        results = self._model(frame, conf=self.conf_threshold, verbose=False)[0]

        detections: List[HelmetDetection] = []
        if results.boxes is None:
            return detections

        for box in results.boxes:
            class_id = int(box.cls[0])
            raw_label = self._model.names[class_id]
            label = _LABEL_MAP.get(raw_label)
            if label is None:
                continue  # unexpected class, ignore rather than crash
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])

            detections.append(HelmetDetection(label=label, confidence=confidence, box_xyxy=(x1, y1, x2, y2)))

        return detections
