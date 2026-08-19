"""red_light_rule.py — flags a vehicle that crosses the stop line while the light is red.

Owner: Meghana. Flagged as the highest-risk module in the plan — needs
signal_state.py + a calibrated stop-line ROI (region of interest) per camera.

Status: STUB.
"""
from __future__ import annotations

from typing import List

from cv.pipeline.tracker import TrackedObject
from cv.rules.rule_engine import Violation


def check_red_light(tracked_objects: List[TrackedObject], frame_context: dict) -> "Violation | None":
    """TODO(Meghana):
    1. Read frame_context["signal_color"] (from signal_state.py).
    2. If signal_color != RED, return None immediately.
    3. Otherwise, for each vehicle track, check if its box crossed the
       stop_line coordinates (from configs/default.yaml) between this
       frame and the previous one.
    4. If yes, build a Violation with violation_type 'red_light_jump'.
    """
    raise NotImplementedError("red_light_rule.check_red_light() — needs signal_state + stop-line calibration")
