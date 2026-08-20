"""test_no_helmet_rule.py — verify the streak + association logic, including
scenarios modeled directly on the false positives we saw on real footage.
"""
from cv.pipeline.helmet_classifier import HelmetDetection
from cv.pipeline.tracker import TrackedObject
from cv.rules.no_helmet_rule import NoHelmetRule


def _motorcycle(track_id: int, center=(100, 100)) -> TrackedObject:
    cx, cy = center
    return TrackedObject(track_id=track_id, class_name="motorcycle", confidence=0.8, box_xyxy=(cx - 15, cy - 15, cx + 15, cy + 15))


def _without_helmet(center=(100, 100), confidence=0.5) -> HelmetDetection:
    cx, cy = center
    return HelmetDetection(label="without_helmet", confidence=confidence, box_xyxy=(cx - 10, cy - 10, cx + 10, cy + 10))


def _with_helmet(center=(100, 100), confidence=0.5) -> HelmetDetection:
    cx, cy = center
    return HelmetDetection(label="with_helmet", confidence=confidence, box_xyxy=(cx - 10, cy - 10, cx + 10, cy + 10))


def test_fires_after_required_consecutive_frames():
    rule = NoHelmetRule(required_streak=3)
    moto = _motorcycle(1)

    v1 = rule([moto], {"helmet_detections": [_without_helmet()]})
    v2 = rule([moto], {"helmet_detections": [_without_helmet()]})
    v3 = rule([moto], {"helmet_detections": [_without_helmet()]})

    assert v1 is None
    assert v2 is None
    assert v3 is not None
    assert v3.violation_type == "no_helmet"
    assert v3.vehicle_track_id == 1


def test_one_frame_flicker_does_not_fire():
    rule = NoHelmetRule(required_streak=3)
    moto = _motorcycle(1)

    rule([moto], {"helmet_detections": [_without_helmet()]})
    rule([moto], {"helmet_detections": []})  # detection disappears — streak resets
    violation = rule([moto], {"helmet_detections": [_without_helmet()]})

    assert violation is None


def test_far_away_false_positive_is_ignored():
    """Models exactly what we saw on real footage: a stray 'without_helmet'
    box on something that isn't a rider at all (e.g. a billboard), far
    from any real motorcycle — should never be associated or fire."""
    rule = NoHelmetRule(required_streak=1, association_distance=80.0)
    moto = _motorcycle(1, center=(100, 100))
    far_away_false_positive = _without_helmet(center=(500, 500))  # nowhere near the motorcycle

    violation = rule([moto], {"helmet_detections": [far_away_false_positive]})

    assert violation is None


def test_with_helmet_detection_never_fires():
    rule = NoHelmetRule(required_streak=1)
    moto = _motorcycle(1)

    violation = rule([moto], {"helmet_detections": [_with_helmet()]})

    assert violation is None


def test_only_fires_once_per_track_id():
    rule = NoHelmetRule(required_streak=1)
    moto = _motorcycle(1)

    v1 = rule([moto], {"helmet_detections": [_without_helmet()]})
    v2 = rule([moto], {"helmet_detections": [_without_helmet()]})  # still no helmet next frame too

    assert v1 is not None
    assert v2 is None  # already flagged this track_id once, don't repeat
