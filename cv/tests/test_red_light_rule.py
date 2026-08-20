"""test_red_light_rule.py — verify crossing + red-light logic with a fake stop line.

We don't need a real video for this — just fake vehicle positions across
two frames, since the whole rule is really just geometry + a signal check.
"""
from cv.pipeline.signal_state import SignalColor
from cv.pipeline.tracker import TrackedObject
from cv.rules.red_light_rule import RedLightRule

# A horizontal stop line at y=300, spanning x=0 to x=500.
_STOP_LINE = ((0, 300), (500, 300))


def _vehicle(track_id: int, bottom_y: float) -> TrackedObject:
    """A fake tracked car; only its bottom-center y coordinate matters for
    these tests (that's what the rule checks against the stop line)."""
    return TrackedObject(
        track_id=track_id,
        class_name="car",
        confidence=0.9,
        box_xyxy=(90, bottom_y - 20, 110, bottom_y),
    )


def test_crossing_while_red_is_a_violation():
    rule = RedLightRule(stop_line=_STOP_LINE)
    # Frame 1: vehicle is south of the line (y=350 > 300) — establishes baseline.
    rule([_vehicle(1, bottom_y=350)], {"signal_color": SignalColor.RED, "signal_confidence": 0.9, "frame_number": 1})
    # Frame 2: same vehicle now north of the line (y=250 <= 300) — crossed.
    violation = rule([_vehicle(1, bottom_y=250)], {"signal_color": SignalColor.RED, "signal_confidence": 0.9, "frame_number": 2})

    assert violation is not None
    assert violation.violation_type == "red_light_jump"
    assert violation.vehicle_track_id == 1
    assert "VEH#1 crossed STOP_LINE at frame=2" in violation.trace


def test_crossing_while_green_is_not_a_violation():
    rule = RedLightRule(stop_line=_STOP_LINE)
    rule([_vehicle(2, bottom_y=350)], {"signal_color": SignalColor.GREEN, "signal_confidence": 0.9, "frame_number": 1})
    violation = rule([_vehicle(2, bottom_y=250)], {"signal_color": SignalColor.GREEN, "signal_confidence": 0.9, "frame_number": 2})

    assert violation is None


def test_no_crossing_while_red_is_not_a_violation():
    rule = RedLightRule(stop_line=_STOP_LINE)
    # Vehicle stays south of the line both frames — never actually crosses.
    rule([_vehicle(3, bottom_y=340)], {"signal_color": SignalColor.RED, "signal_confidence": 0.9, "frame_number": 1})
    violation = rule([_vehicle(3, bottom_y=330)], {"signal_color": SignalColor.RED, "signal_confidence": 0.9, "frame_number": 2})

    assert violation is None


def test_uncalibrated_stop_line_never_fires():
    rule = RedLightRule(stop_line=None)  # the real default until calibrated
    rule([_vehicle(4, bottom_y=350)], {"signal_color": SignalColor.RED, "signal_confidence": 0.9, "frame_number": 1})
    violation = rule([_vehicle(4, bottom_y=250)], {"signal_color": SignalColor.RED, "signal_confidence": 0.9, "frame_number": 2})

    assert violation is None


def test_first_sighting_has_no_baseline_so_no_violation():
    rule = RedLightRule(stop_line=_STOP_LINE)
    # Only ONE frame seen so far — no previous position to compare against.
    violation = rule([_vehicle(5, bottom_y=250)], {"signal_color": SignalColor.RED, "signal_confidence": 0.9, "frame_number": 1})

    assert violation is None
