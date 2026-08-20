"""test_signal_state.py — verify the HSV heuristic on synthetic traffic-light images.

We build a fake image by hand instead of needing a real traffic-light photo
— that keeps this test fast, deterministic, and independent of whatever
video clip happens to be on someone's machine.
"""
import numpy as np

from cv.pipeline.signal_state import SignalColor, classify_signal_crop

_WIDTH = 40
_BAND_HEIGHT = 40
_HEIGHT = _BAND_HEIGHT * 3

# BGR (OpenCV's channel order, not RGB) for a bright, saturated bulb color.
_BRIGHT_RED = (0, 0, 255)
_BRIGHT_YELLOW = (0, 255, 255)
_BRIGHT_GREEN = (0, 255, 0)
_DARK_UNLIT = (20, 20, 20)  # dim gray, like an unlit bulb


def _make_traffic_light_image(lit_band: int, lit_color) -> np.ndarray:
    """lit_band: 0=top, 1=middle, 2=bottom. Other two bands are dark/unlit."""
    image = np.full((_HEIGHT, _WIDTH, 3), _DARK_UNLIT, dtype=np.uint8)
    start = lit_band * _BAND_HEIGHT
    end = start + _BAND_HEIGHT
    image[start:end, :, :] = lit_color
    return image


def test_top_red_band_detected_as_red():
    image = _make_traffic_light_image(lit_band=0, lit_color=_BRIGHT_RED)
    color, confidence = classify_signal_crop(image, (0, 0, _WIDTH, _HEIGHT))
    assert color == SignalColor.RED
    assert confidence > 0.5


def test_middle_yellow_band_detected_as_yellow():
    image = _make_traffic_light_image(lit_band=1, lit_color=_BRIGHT_YELLOW)
    color, confidence = classify_signal_crop(image, (0, 0, _WIDTH, _HEIGHT))
    assert color == SignalColor.YELLOW
    assert confidence > 0.5


def test_bottom_green_band_detected_as_green():
    image = _make_traffic_light_image(lit_band=2, lit_color=_BRIGHT_GREEN)
    color, confidence = classify_signal_crop(image, (0, 0, _WIDTH, _HEIGHT))
    assert color == SignalColor.GREEN
    assert confidence > 0.5


def test_all_unlit_returns_unknown():
    image = np.full((_HEIGHT, _WIDTH, 3), _DARK_UNLIT, dtype=np.uint8)
    color, confidence = classify_signal_crop(image, (0, 0, _WIDTH, _HEIGHT))
    assert color == SignalColor.UNKNOWN


def test_empty_box_returns_unknown():
    image = np.full((_HEIGHT, _WIDTH, 3), _DARK_UNLIT, dtype=np.uint8)
    color, confidence = classify_signal_crop(image, (5, 5, 5, 5))  # zero-size box
    assert color == SignalColor.UNKNOWN
    assert confidence == 0.0
