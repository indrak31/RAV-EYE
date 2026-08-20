"""test_run_violations_integration.py — proves the FULL wiring works, not
just RedLightRule in isolation.

We still don't have real footage of an actual red-light violation. So
instead of testing RedLightRule directly (already covered in
test_red_light_rule.py), this drives the exact function run_pipeline.py's
--violations mode calls every frame (evaluate_frame_for_red_light), with
fake-but-controlled tracked objects and a fake signal reading — no video
file, no GPU, no model download needed. This is what actually proves "find
the traffic light among tracked objects -> read its color -> check the
rule -> report the violation" is wired together correctly.
"""
from cv.pipeline.signal_state import SignalColor
from cv.pipeline.tracker import TrackedObject
from cv.rules.red_light_rule import RedLightRule
from cv.run_pipeline import evaluate_frame_for_red_light

_STOP_LINE = ((0, 300), (500, 300))


def _car(track_id: int, bottom_y: float) -> TrackedObject:
    return TrackedObject(track_id=track_id, class_name="car", confidence=0.9, box_xyxy=(90, bottom_y - 20, 110, bottom_y))


def _traffic_light() -> TrackedObject:
    # Position doesn't matter here — the fake signal_lookup below ignores
    # the actual pixels and just returns a canned answer.
    return TrackedObject(track_id=99, class_name="traffic light", confidence=0.8, box_xyxy=(200, 50, 220, 90))


def _always_red(frame, box_xyxy):
    return SignalColor.RED, 0.95


def _always_green(frame, box_xyxy):
    return SignalColor.GREEN, 0.95


def test_full_wiring_reports_violation_when_car_crosses_during_red():
    rule = RedLightRule(stop_line=_STOP_LINE)
    fake_frame = None  # not actually read by our fake signal_lookup

    # Frame 1: traffic light visible + red, car south of the line (baseline).
    v1, color1, conf1 = evaluate_frame_for_red_light(
        [_traffic_light(), _car(1, bottom_y=350)], fake_frame, 1, rule, signal_lookup=_always_red
    )
    assert v1 is None
    assert color1 == SignalColor.RED

    # Frame 2: same car now north of the line — this is the actual crossing.
    v2, color2, conf2 = evaluate_frame_for_red_light(
        [_traffic_light(), _car(1, bottom_y=250)], fake_frame, 2, rule, signal_lookup=_always_red
    )

    assert v2 is not None, "expected a violation: car crossed the stop line while the light was red"
    assert v2.violation_type == "red_light_jump"
    assert v2.vehicle_track_id == 1


def test_full_wiring_stays_silent_when_signal_is_green():
    rule = RedLightRule(stop_line=_STOP_LINE)
    fake_frame = None

    evaluate_frame_for_red_light([_traffic_light(), _car(2, bottom_y=350)], fake_frame, 1, rule, signal_lookup=_always_green)
    violation, color, conf = evaluate_frame_for_red_light(
        [_traffic_light(), _car(2, bottom_y=250)], fake_frame, 2, rule, signal_lookup=_always_green
    )

    assert violation is None
    assert color == SignalColor.GREEN


def test_full_wiring_signal_unknown_when_no_traffic_light_tracked():
    """Matches what actually happened on our real calibration clip — no
    traffic light was ever detected, so signal stays UNKNOWN."""
    rule = RedLightRule(stop_line=_STOP_LINE)
    fake_frame = None

    # No traffic light in the tracked objects at all — signal_lookup should
    # never even be called, and signal_color should default to UNKNOWN.
    violation, color, conf = evaluate_frame_for_red_light([_car(3, bottom_y=350)], fake_frame, 1, rule)

    assert color == SignalColor.UNKNOWN
    assert violation is None
