"""trace.py — builds a human-readable "why was this flagged" trail.

Owner: Meghana (shared with whoever writes a rule).

Every violation should come with a list of short strings explaining the
decision, e.g.:
    ["SIGNAL_STATE=RED conf=0.91", "VEH#17 crossed STOP_LINE at frame=142"]

This is cheap to build and gives the dashboard/judges something concrete
to show under "why was this flagged?" — no extra model needed.
"""
from __future__ import annotations


class DecisionTrace:
    """Collects trace strings for a single violation as rules evaluate it."""

    def __init__(self):
        self._steps: list[str] = []

    def add(self, step: str) -> None:
        self._steps.append(step)

    def as_list(self) -> list[str]:
        return list(self._steps)
