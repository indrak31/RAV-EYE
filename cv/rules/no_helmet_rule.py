"""no_helmet_rule.py — flags a motorcycle rider with no helmet detected.

Owner: Meghana.

Status: STUB. Needs a helmet classifier (not built yet — Day 3-5 per plan)
before this can do real work. The shape of the function is ready so it can
be registered with rule_engine.RuleEngine as soon as the classifier exists.
"""
from __future__ import annotations

from typing import List

from cv.pipeline.tracker import TrackedObject
from cv.rules.rule_engine import Violation
from cv.rules.trace import DecisionTrace


def check_no_helmet(tracked_objects: List[TrackedObject], frame_context: dict) -> "Violation | None":
    """TODO(Meghana): for each motorcycle track, check the overlapping
    person detection's helmet_status (added by a helmet classifier step
    that runs before rules). If helmet_status == 'no' and confidence is
    high enough, build and return a Violation with violation_type
    'no_helmet' (must match the enum in docs/api-contract.md)."""
    raise NotImplementedError("no_helmet_rule.check_no_helmet() — needs helmet classifier first")
