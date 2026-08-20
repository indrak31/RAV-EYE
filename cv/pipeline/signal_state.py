"""signal_state.py — figures out if a traffic light is red/yellow/green.

Owner: Meghana. Needed for the red-light-jump rule (Day 5-7 per the plan).

Status: IMPLEMENTED (HSV heuristic, no ML model). This is deliberately the
simplest thing that could work: a traffic light is always the same 3
colors in the same top-to-bottom order (red, yellow, green), so instead of
training a classifier, we just check which third of the cropped image is
"lit" — bright, saturated, and the right hue.

Why HSV instead of the usual RGB: in RGB, "is this pixel red" means
comparing 3 separate numbers with fiddly logic. In HSV (Hue-Saturation-
Value), a color's hue is ONE number on a 0-179 wheel (OpenCV's convention),
so "is this reddish" becomes a simple range check on Hue, plus checking
Saturation/Value are high enough to rule out the dark, unlit bulbs and the
black plastic housing around them.
"""
from __future__ import annotations

from enum import Enum

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None
    np = None

# OpenCV represents Hue as 0-179 (not the usual 0-360). Red wraps around
# 0/179, so it needs two ranges; yellow and green are each one contiguous
# range. These were picked to match typical LED traffic-light colors, not
# tuned on real footage yet — revisit if real-world testing shows misses.
_RED_HUE_RANGES = [(0, 10), (170, 179)]
_YELLOW_HUE_RANGE = (15, 35)
_GREEN_HUE_RANGE = (40, 90)

# A pixel only counts as "a lit bulb" if it's reasonably bright and
# colorful — this is what excludes the dark unlit bulbs and the black
# housing around all three lights.
_MIN_SATURATION = 80
_MIN_VALUE = 80

# If even the best-matching third has fewer than this fraction of
# "lit" pixels, we don't trust the result enough to guess a color.
_MIN_CONFIDENCE = 0.05


class SignalColor(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    UNKNOWN = "unknown"


def _hue_in_ranges(hue_channel, ranges: list[tuple[int, int]]):
    """Boolean mask: True where hue_channel falls inside ANY of the given ranges."""
    mask = np.zeros(hue_channel.shape, dtype=bool)
    for low, high in ranges:
        mask |= (hue_channel >= low) & (hue_channel <= high)
    return mask


def _lit_fraction(hsv_band, hue_ranges: list[tuple[int, int]]) -> float:
    """What fraction of pixels in this band look like a lit bulb of the given color?"""
    h, s, v = hsv_band[:, :, 0], hsv_band[:, :, 1], hsv_band[:, :, 2]
    hue_match = _hue_in_ranges(h, hue_ranges)
    bright_enough = (s >= _MIN_SATURATION) & (v >= _MIN_VALUE)
    matching = hue_match & bright_enough
    total_pixels = hsv_band.shape[0] * hsv_band.shape[1]
    return float(matching.sum()) / total_pixels if total_pixels > 0 else 0.0


def classify_signal_crop(frame, box_xyxy: tuple[float, float, float, float]) -> tuple[SignalColor, float]:
    """Given a frame and a traffic-light bounding box, return (color, confidence).

    confidence is "what fraction of the winning third's pixels actually
    looked like a lit bulb" — a rough but honest signal, not a calibrated
    probability. Returns (UNKNOWN, 0.0) if the box is empty/invalid or if
    nothing looks confidently lit (e.g. box is too small, blurry, or the
    light isn't actually visible in this crop).
    """
    if cv2 is None:
        raise RuntimeError("opencv-python is not installed yet.")

    x1, y1, x2, y2 = (int(v) for v in box_xyxy)
    crop = frame[max(0, y1):y2, max(0, x1):x2]
    if crop.size == 0 or crop.shape[0] < 3:
        # Too small to meaningfully split into 3 vertical bands.
        return SignalColor.UNKNOWN, 0.0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    height = hsv.shape[0]
    third = height // 3

    top_band = hsv[0:third, :, :]
    middle_band = hsv[third: 2 * third, :, :]
    bottom_band = hsv[2 * third:, :, :]

    scores = {
        SignalColor.RED: _lit_fraction(top_band, _RED_HUE_RANGES),
        SignalColor.YELLOW: _lit_fraction(middle_band, [_YELLOW_HUE_RANGE]),
        SignalColor.GREEN: _lit_fraction(bottom_band, [_GREEN_HUE_RANGE]),
    }

    best_color = max(scores, key=scores.get)
    best_score = scores[best_color]

    if best_score < _MIN_CONFIDENCE:
        return SignalColor.UNKNOWN, best_score

    return best_color, best_score
