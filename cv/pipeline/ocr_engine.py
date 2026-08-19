"""ocr_engine.py — reads the text off a cropped license plate image.

Owner: Aryan. CPU-only — PaddleOCR runs fine without a GPU.

Status: STUB.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlateReading:
    text: str            # e.g. "MH12AB1234"
    confidence: float


class OCREngine:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._reader = None

    def load(self) -> None:
        """TODO(Aryan):
            from paddleocr import PaddleOCR
            self._reader = PaddleOCR(lang=self.lang, use_angle_cls=True)
        """
        raise NotImplementedError("ocr_engine.load() — plug in PaddleOCR")

    def read_plate(self, plate_crop) -> PlateReading | None:
        """Preprocess (grayscale, resize 2x, deskew, threshold) then OCR.
        Return None if no text could be confidently read.

        TODO(Aryan): if PaddleOCR fails or is unavailable, fall back to
        EasyOCR (this fallback was flagged as a risk mitigation in the plan).
        """
        raise NotImplementedError("ocr_engine.read_plate() — plug in real OCR")
