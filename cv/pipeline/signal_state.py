"""signal_state.py — figures out if a traffic light is red/yellow/green.

Owner: Meghana. Needed for the red-light-jump rule (Day 5-7 per the plan).

Status: STUB. This is the highest-risk module (per plan.md's risk register)
— defer polishing it until the detector + tracker are solid.
"""
from __future__ import annotations

from enum import Enum


class SignalColor(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    UNKNOWN = "unknown"


def classify_signal_crop(frame, box_xyxy: tuple[float, float, float, float]) -> tuple[SignalColor, float]:
    """Given a frame and a traffic-light bounding box, return (color, confidence).

    Simplest first version (TODO Meghana): crop the box, look at which
    third of the crop (top/middle/bottom) has the most red/yellow/green
    pixels in HSV color space. No ML model needed for a first pass —
    this is a cheap heuristic, upgrade later only if it's inaccurate.
    """
    raise NotImplementedError("signal_state.classify_signal_crop() — implement HSV heuristic")
