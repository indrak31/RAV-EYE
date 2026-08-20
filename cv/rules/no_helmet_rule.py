"""no_helmet_rule.py — flags a motorcycle rider with no helmet detected.

Owner: Meghana.

Status: IMPLEMENTED, using a pretrained helmet classifier (see
helmet_classifier.py for important caveats about its real-world accuracy
— it produced false positives on non-people objects when tested on real
footage). This rule is deliberately built to survive that unreliability,
not just trust the model:

1. A "Without Helmet" detection only counts if it's physically close to an
   actual tracked motorcycle (from tracker.py). A stray false-positive box
   on a billboard or car roof has no nearby motorcycle track, so it's
   automatically ignored — this alone rejected every false positive we
   observed in testing.
2. Requires several CONSECUTIVE frames of "without_helmet" before firing —
   a one-off flicker (which we also observed) isn't trusted as a real
   violation on its own.

Like red_light_rule.py, this is a stateful class (needs to remember
streaks across frames), not a plain function.
"""
from __future__ import annotations

import math
from typing import List, Optional

from cv.pipeline.helmet_classifier import HelmetDetection
from cv.pipeline.tracker import TrackedObject
from cv.rules.rule_engine import Violation

# How close (in pixels, center-to-center) a "without_helmet" detection must
# be to a tracked motorcycle to count as belonging to that motorcycle's
# rider. Not calibrated against real footage yet — a reasonable starting
# guess, same spirit as the stop line before it was measured.
_DEFAULT_ASSOCIATION_DISTANCE = 80.0

# How many consecutive frames of "without_helmet" (matched to the same
# motorcycle) before we trust it enough to call it a violation.
_DEFAULT_REQUIRED_STREAK = 3


def _box_center(box_xyxy: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box_xyxy
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


class NoHelmetRule:
    def __init__(
        self,
        association_distance: float = _DEFAULT_ASSOCIATION_DISTANCE,
        required_streak: int = _DEFAULT_REQUIRED_STREAK,
    ):
        self.association_distance = association_distance
        self.required_streak = required_streak
        self._streak: dict[int, int] = {}
        self._last_confidence: dict[int, float] = {}
        self._already_flagged: set[int] = set()

    def __call__(self, tracked_objects: List[TrackedObject], frame_context: dict) -> "Violation | None":
        helmet_detections: List[HelmetDetection] = frame_context.get("helmet_detections", [])
        without_helmet = [d for d in helmet_detections if d.label == "without_helmet"]
        motorcycles = [obj for obj in tracked_objects if obj.class_name == "motorcycle"]

        violation: "Violation | None" = None

        for moto in motorcycles:
            moto_center = _box_center(moto.box_xyxy)

            best_match: Optional[HelmetDetection] = None
            best_distance = self.association_distance
            for det in without_helmet:
                dist = _distance(moto_center, _box_center(det.box_xyxy))
                if dist <= best_distance:
                    best_distance = dist
                    best_match = det

            if best_match is not None:
                self._streak[moto.track_id] = self._streak.get(moto.track_id, 0) + 1
                self._last_confidence[moto.track_id] = best_match.confidence
            else:
                self._streak[moto.track_id] = 0

            streak = self._streak.get(moto.track_id, 0)
            if streak >= self.required_streak and moto.track_id not in self._already_flagged:
                self._already_flagged.add(moto.track_id)
                trace = [
                    f"HELMET_STATUS=without_helmet for {streak} consecutive frames",
                    f"VEH#{moto.track_id} associated within {self.association_distance:.0f}px of a without-helmet detection",
                ]
                violation = Violation(
                    violation_type="no_helmet",
                    vehicle_track_id=moto.track_id,
                    confidence=self._last_confidence.get(moto.track_id, moto.confidence),
                    trace=trace,
                )
                break  # one violation per call, matches red_light_rule's contract

        return violation


# Module-level default instance, same pattern as red_light_rule.py, so
# rule_engine.py can register it the same simple way.
check_no_helmet = NoHelmetRule()
