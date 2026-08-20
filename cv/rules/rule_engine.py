"""rule_engine.py — takes tracked objects + frame context, produces violations.

Owner: Meghana.

Design: violations are "plugins". Each rule is a small function that looks
at the current tracked objects and either does nothing, or returns a
Violation. Adding a new violation type later (triple-riding, wrong-side)
means writing one new rule file, not touching this engine.

Status: dispatch engine works. Both rules implemented:
red_light_rule.py (logic tested, stop line calibrated on a real clip) and
no_helmet_rule.py (logic tested, uses a pretrained classifier with known
real-world accuracy caveats — see helmet_classifier.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from cv.pipeline.tracker import TrackedObject
from cv.rules.trace import DecisionTrace


@dataclass
class Violation:
    violation_type: str          # must match api-contract.md's violation_type enum
    vehicle_track_id: int
    confidence: float
    trace: list[str]


# A rule is: (tracked_objects, frame_context) -> Violation | None
RuleFn = Callable[[List[TrackedObject], dict], "Violation | None"]


class RuleEngine:
    def __init__(self):
        self._rules: list[RuleFn] = []

    def register(self, rule: RuleFn) -> None:
        self._rules.append(rule)

    def evaluate(self, tracked_objects: List[TrackedObject], frame_context: dict) -> List[Violation]:
        """Run every registered rule against the current frame's tracked
        objects. frame_context can carry extra info a rule needs (e.g.
        signal color, stop-line coordinates from configs/default.yaml)."""
        violations = []
        for rule in self._rules:
            result = rule(tracked_objects, frame_context)
            if result is not None:
                violations.append(result)
        return violations
