"""red_light_rule.py — flags a vehicle that crosses the stop line while the light is red.

Owner: Meghana. Flagged as the highest-risk module in the plan — needs
signal_state.py (done) + a calibrated stop-line ROI per camera (NOT done —
see CalibrationNeeded below).

Status: IMPLEMENTED, but running with a PLACEHOLDER stop line. The logic
itself (crossing detection, red-light check, building the Violation) is
complete and unit-tested. What's still missing is real-world numbers: the
exact pixel coordinates of the stop line for a specific camera's video,
which nobody can know until we look at an actual demo clip and measure it.

Design note — why this became a class, not a plain function (like the
original stub): detecting a "crossing" requires comparing THIS frame's
vehicle position to the PREVIOUS frame's position. A stateless function has
no memory between calls, so RedLightRule remembers each vehicle's last seen
position itself. It's still used the same way — call it with
(tracked_objects, frame_context), get back a Violation or None — just as an
instance instead of a bare function.
"""
from __future__ import annotations

from typing import List, Optional

from cv.pipeline.signal_state import SignalColor
from cv.pipeline.tracker import TrackedObject
from cv.rules.rule_engine import Violation

# Vehicle classes that can plausibly "run a red light" — excludes "person"
# (pedestrians jaywalking is a different, not-yet-built rule).
_VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}

# PLACEHOLDER — not calibrated. (x1, y1), (x2, y2): two points forming a
# line across the road, in the same pixel coordinates as the video frame.
# HOW TO CALIBRATE FOR REAL (once we have a fixed demo camera angle):
#   1. Grab one frame from the demo video (e.g. via video_reader + cv2.imwrite).
#   2. Open it in any image viewer that shows pixel coordinates (or MS Paint).
#   3. Find two points that trace the actual stop-line painted on the road.
#   4. Put them in configs/default.yaml under camera.stop_line: [x1,y1,x2,y2].
# Until then, this rule will simply never fire (see the guard in evaluate()).
PLACEHOLDER_STOP_LINE = None


def _bottom_center(box_xyxy: tuple[float, float, float, float]) -> tuple[float, float]:
    """Where a vehicle roughly touches the road — more accurate for line
    crossing than the box's actual center, which is higher up on the vehicle."""
    x1, y1, x2, y2 = box_xyxy
    return ((x1 + x2) / 2.0, y2)


def _side_of_line(point: tuple[float, float], line_start: tuple[float, float], line_end: tuple[float, float]) -> float:
    """Which side of the line is this point on? Positive = one side,
    negative = the other, ~0 = right on the line. (This is a cross product
    — the sign alone is all we need, not the magnitude.)"""
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)


class RedLightRule:
    """Stateful rule: remembers each vehicle's last position to detect crossings.

    stop_line: ((x1,y1), (x2,y2)) — two points, or None to disable (safe
    default until calibrated; see PLACEHOLDER_STOP_LINE above).
    Convention: a vehicle crossing from the POSITIVE side to the
    NEGATIVE/zero side of the line (per _side_of_line) counts as "crossed
    toward the intersection." If real testing shows it's backwards for a
    given camera, swap the order of the two points in configs/default.yaml
    — that alone flips which direction counts as "crossing in."
    """

    def __init__(self, stop_line: Optional[tuple[tuple[float, float], tuple[float, float]]] = PLACEHOLDER_STOP_LINE):
        self.stop_line = stop_line
        self._last_position: dict[int, tuple[float, float]] = {}

    def __call__(self, tracked_objects: List[TrackedObject], frame_context: dict) -> "Violation | None":
        signal_color = frame_context.get("signal_color", SignalColor.UNKNOWN)
        signal_confidence = frame_context.get("signal_confidence", 0.0)
        frame_number = frame_context.get("frame_number", -1)

        violation: "Violation | None" = None

        for obj in tracked_objects:
            if obj.class_name not in _VEHICLE_CLASSES:
                continue

            current_position = _bottom_center(obj.box_xyxy)
            previous_position = self._last_position.get(obj.track_id)
            # Always update, regardless of whether we flag a violation —
            # otherwise the NEXT frame would have stale/missing history.
            self._last_position[obj.track_id] = current_position

            if self.stop_line is None:
                continue  # not calibrated yet — rule stays silent, on purpose
            if previous_position is None:
                continue  # first frame we've seen this vehicle, nothing to compare against

            line_start, line_end = self.stop_line
            side_before = _side_of_line(previous_position, line_start, line_end)
            side_now = _side_of_line(current_position, line_start, line_end)

            crossed = side_before > 0 and side_now <= 0
            if not crossed:
                continue
            if signal_color != SignalColor.RED:
                continue  # crossed, but light wasn't red — not a violation

            trace = [
                f"SIGNAL_STATE=RED conf={signal_confidence:.2f}",
                f"VEH#{obj.track_id} crossed STOP_LINE at frame={frame_number}",
            ]
            # Conservative confidence: whichever signal is weaker (detection
            # vs. signal-color reading) is the honest bottleneck.
            confidence = min(obj.confidence, signal_confidence) if signal_confidence else obj.confidence

            violation = Violation(
                violation_type="red_light_jump",
                vehicle_track_id=obj.track_id,
                confidence=confidence,
                trace=trace,
            )
            # Only report one violation per frame from this rule (matches
            # rule_engine's one-Violation-per-rule-call contract). If two
            # vehicles cross in the exact same frame, the second is missed
            # this frame — acceptable for a hackathon demo, worth revisiting
            # if it turns out to matter.
            break

        return violation


# Module-level default instance so rule_engine.py can register this rule
# the same simple way as a plain function: rule_engine.register(check_red_light)
check_red_light = RedLightRule()
