"""run_pipeline.py — CLI entry point: video in, violations pushed to the backend.

Owner: Meghana (glues together both her and Aryan's modules).

Usage (once the STUB pieces below are implemented):
    python -m cv.run_pipeline --video data/videos/demo.mp4

What this SHOULD end up doing, step by step:
    1. Read frames from the video (video_reader.py — DONE).
    2. Run detection on each frame (detector.py — DONE, see --detect-only).
    3. Track objects across frames (tracker.py — DONE, see --track-only).
    4. Check signal color if relevant (signal_state.py — STUB).
    5. Run rules to find violations (rule_engine.py — STUB rules).
    6. For each violation, build evidence (evidence_engine.py — STUB)
       and package it (case_builder.py — ready).
    7. POST the packaged case to the backend's /api/ingest.
    8. Optionally write an annotated output video (annotator.py — works).

Status: steps 1-3 are real and tested on actual footage. Steps 4-7 (rules,
evidence, backend push) are next.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter

from cv.pipeline.video_reader import get_video_meta, read_frames


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CV pipeline on a video file.")
    parser.add_argument("--video", required=True, help="Path to input video file")
    parser.add_argument(
        "--config", default=None,
        help="Path to config YAML (defaults to cv/configs/default.yaml, resolved regardless of cwd)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only read the video and print frame count/fps — skip detection (safe today, no deps needed beyond opencv)",
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Run real YOLO detection on the video (no tracking/rules yet — those are still stubs). "
        "First run downloads the yolov8n model (a few MB).",
    )
    parser.add_argument(
        "--track-only",
        action="store_true",
        help="Run detection + tracking (ByteTrack) — each object gets a stable ID across frames. "
        "No violation rules yet.",
    )
    parser.add_argument(
        "--violations",
        action="store_true",
        help="Full red-light pipeline: detect + track + read the traffic light color + check the "
        "calibrated stop line. Prints any violations found. Needs configs/default.yaml's "
        "camera.stop_line to be calibrated (see cv/rules/red_light_rule.py for how).",
    )
    parser.add_argument(
        "--limit-frames",
        type=int,
        default=None,
        help="Only process the first N frames (useful for a quick smoke test instead of the whole video)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="If set with --detect-only, writes an annotated video (boxes drawn) to this path, e.g. out.mp4",
    )
    return parser.parse_args()


def run_detect_only(args) -> int:
    """Real detection, frame by frame. No tracking/rules yet — this just
    proves detector.py works end-to-end on an actual video."""
    from cv.pipeline.annotator import draw_detections
    from cv.pipeline.detector import Detector

    print("Loading YOLO model (first run downloads yolov8n.pt automatically)...")
    detector = Detector(device="cuda")
    try:
        detector.load()
    except Exception as exc:  # noqa: BLE001 - surface any load failure plainly
        print(f"Could not load on GPU ('cuda'): {exc}\nFalling back to CPU...")
        detector = Detector(device="cpu")
        detector.load()

    writer = None
    if args.output:
        import cv2

        meta = get_video_meta(args.video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.output, fourcc, meta.fps, (meta.width, meta.height))

    class_counts: Counter[str] = Counter()
    frame_total = 0
    start = time.time()

    for frame_number, frame in read_frames(args.video, resize_width=None):
        if args.limit_frames is not None and frame_number >= args.limit_frames:
            break

        detections = detector.detect(frame)
        for det in detections:
            class_counts[det.class_name] += 1

        if writer is not None:
            writer.write(draw_detections(frame, detections))

        frame_total += 1
        if frame_total % 30 == 0:
            print(f"  ...processed {frame_total} frames")

    if writer is not None:
        writer.release()

    elapsed = time.time() - start
    fps = frame_total / elapsed if elapsed > 0 else 0.0

    print(f"\nProcessed {frame_total} frames in {elapsed:.1f}s ({fps:.1f} FPS).")
    print("Detections by class (summed across all frames, not unique objects — no tracker yet):")
    for class_name, count in class_counts.most_common():
        print(f"  {class_name}: {count}")
    if args.output:
        print(f"\nAnnotated video written to: {args.output}")
    return 0


def run_track_only(args) -> int:
    """Real detection + tracking. Each TrackedObject carries a track_id that
    stays the same across frames — this is what lets us count UNIQUE
    vehicles instead of raw per-frame detections."""
    from cv.pipeline.annotator import draw_tracked_objects
    from cv.pipeline.tracker import Tracker

    print("Loading YOLO + ByteTrack (first run downloads yolov8n.pt automatically)...")
    tracker = Tracker(device="cuda")
    try:
        tracker.load()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not load on GPU ('cuda'): {exc}\nFalling back to CPU...")
        tracker = Tracker(device="cpu")
        tracker.load()

    writer = None
    if args.output:
        import cv2

        meta = get_video_meta(args.video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.output, fourcc, meta.fps, (meta.width, meta.height))

    # Track unique (class_name, track_id) pairs seen — this is how we get
    # a real "N distinct vehicles" count instead of "N detections total".
    unique_by_class: dict[str, set[int]] = {}
    frame_total = 0
    start = time.time()

    for frame_number, frame in read_frames(args.video, resize_width=None):
        if args.limit_frames is not None and frame_number >= args.limit_frames:
            break

        tracked_objects = tracker.update(frame)
        for obj in tracked_objects:
            unique_by_class.setdefault(obj.class_name, set()).add(obj.track_id)

        if writer is not None:
            writer.write(draw_tracked_objects(frame, tracked_objects))

        frame_total += 1
        if frame_total % 30 == 0:
            print(f"  ...processed {frame_total} frames")

    if writer is not None:
        writer.release()

    elapsed = time.time() - start
    fps = frame_total / elapsed if elapsed > 0 else 0.0

    print(f"\nProcessed {frame_total} frames in {elapsed:.1f}s ({fps:.1f} FPS).")
    print("Unique objects tracked by class (this is the real count — same vehicle counted once):")
    for class_name, ids in sorted(unique_by_class.items(), key=lambda kv: -len(kv[1])):
        print(f"  {class_name}: {len(ids)}")
    if args.output:
        print(f"\nAnnotated video (with track IDs) written to: {args.output}")
    return 0


def evaluate_frame_for_red_light(tracked_objects, frame, frame_number, red_light_rule, signal_lookup=None):
    """The 'glue' logic for one frame: find a traffic light among what was
    tracked, read its color, hand everything to the rule, return what
    happened. Pulled out of run_violations() so it can be tested directly
    with FAKE tracked_objects/signal readings — no real video, GPU, or
    model needed to verify this wiring is correct.

    signal_lookup(frame, box_xyxy) -> (SignalColor, confidence). Defaults
    to the real classify_signal_crop; tests inject a fake one instead.

    Returns (violation_or_none, signal_color, signal_confidence).
    """
    from cv.pipeline.signal_state import SignalColor, classify_signal_crop

    if signal_lookup is None:
        signal_lookup = classify_signal_crop

    signal_color = SignalColor.UNKNOWN
    signal_confidence = 0.0
    for obj in tracked_objects:
        if obj.class_name == "traffic light":
            signal_color, signal_confidence = signal_lookup(frame, obj.box_xyxy)
            break

    frame_context = {
        "signal_color": signal_color,
        "signal_confidence": signal_confidence,
        "frame_number": frame_number,
    }
    violation = red_light_rule(tracked_objects, frame_context)
    return violation, signal_color, signal_confidence


def run_violations(args) -> int:
    """The real target: detect + track + read the signal + check the
    calibrated stop line, and report any red-light violations found."""
    import cv2

    from cv.pipeline.annotator import draw_tracked_objects
    from cv.pipeline.config import load_config, stop_line_from_config
    from cv.pipeline.tracker import Tracker
    from cv.rules.red_light_rule import RedLightRule

    config = load_config(args.config)
    stop_line = stop_line_from_config(config)
    if stop_line is None:
        print(
            "No calibrated stop line in configs/default.yaml (camera.stop_line is null).\n"
            "The rule will run but can never fire. See cv/rules/red_light_rule.py for how to calibrate."
        )
    else:
        print(f"Using calibrated stop line: {stop_line}")

    print("Loading YOLO + BoT-SORT...")
    tracker = Tracker(device="cuda")
    try:
        tracker.load()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not load on GPU ('cuda'): {exc}\nFalling back to CPU...")
        tracker = Tracker(device="cpu")
        tracker.load()

    red_light_rule = RedLightRule(stop_line=stop_line)

    writer = None
    if args.output:
        meta = get_video_meta(args.video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.output, fourcc, meta.fps, (meta.width, meta.height))

    frame_total = 0
    violations_found = []
    start = time.time()

    for frame_number, frame in read_frames(args.video, resize_width=None):
        if args.limit_frames is not None and frame_number >= args.limit_frames:
            break

        tracked_objects = tracker.update(frame)

        violation, signal_color, signal_confidence = evaluate_frame_for_red_light(
            tracked_objects, frame, frame_number, red_light_rule
        )
        if violation is not None:
            violations_found.append(violation)
            print(f"  !! VIOLATION at frame {frame_number}: {violation}")

        if writer is not None:
            annotated = draw_tracked_objects(frame, tracked_objects)
            if stop_line is not None:
                p1, p2 = stop_line
                cv2.line(annotated, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (0, 0, 255), 2)
            cv2.putText(
                annotated, f"SIGNAL: {signal_color.value}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2,
            )
            writer.write(annotated)

        frame_total += 1
        if frame_total % 30 == 0:
            print(f"  ...processed {frame_total} frames")

    if writer is not None:
        writer.release()

    elapsed = time.time() - start
    fps = frame_total / elapsed if elapsed > 0 else 0.0

    print(f"\nProcessed {frame_total} frames in {elapsed:.1f}s ({fps:.1f} FPS).")
    print(f"Violations found: {len(violations_found)}")
    if args.output:
        print(f"Annotated video (stop line + signal color overlaid) written to: {args.output}")
    return 0


def main() -> int:
    args = parse_args()

    meta = get_video_meta(args.video)
    print(f"Video: {args.video}")
    print(f"  fps={meta.fps:.2f}  size={meta.width}x{meta.height}  frames={meta.frame_count}")

    if args.dry_run:
        print("Dry run only (--dry-run) — stopping before detection.")
        return 0

    if args.detect_only:
        return run_detect_only(args)

    if args.track_only:
        return run_track_only(args)

    if args.violations:
        return run_violations(args)

    print(
        "\nFull pipeline (evidence saving + push to backend) is not wired yet.\n"
        "What IS working: detection, tracking, AND the red-light rule. Try:\n"
        "  python -m cv.run_pipeline --video <path> --violations --output out.mp4\n"
        "Next to build: rules/no_helmet_rule.py, then evidence saving + /api/ingest push."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
