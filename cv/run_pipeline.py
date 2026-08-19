"""run_pipeline.py — CLI entry point: video in, violations pushed to the backend.

Owner: Meghana (glues together both her and Aryan's modules).

Usage (once the STUB pieces below are implemented):
    python -m cv.run_pipeline --video data/videos/demo.mp4

What this SHOULD end up doing, step by step:
    1. Read frames from the video (video_reader.py — already works).
    2. Run detection on each frame (detector.py — STUB).
    3. Track objects across frames (tracker.py — STUB).
    4. Check signal color if relevant (signal_state.py — STUB).
    5. Run rules to find violations (rule_engine.py — STUB rules).
    6. For each violation, build evidence (evidence_engine.py — STUB)
       and package it (case_builder.py — ready).
    7. POST the packaged case to the backend's /api/ingest.
    8. Optionally write an annotated output video (annotator.py — works).

Status today: this file wires the steps together and prints what WOULD
happen, but does not yet call the STUB pieces (they'd just raise
NotImplementedError). This is intentional — it lets us verify the wiring
and CLI args work before real model code exists.
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
    parser.add_argument("--config", default="cv/configs/default.yaml", help="Path to config YAML")
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

    print(
        "\nFull pipeline (tracking + rules + evidence + push to backend) is not wired yet.\n"
        "What IS working: detection. Try:\n"
        "  python -m cv.run_pipeline --video <path> --detect-only --limit-frames 60 --output out.mp4\n"
        "Next to build: Tracker.load()/update() in cv/pipeline/tracker.py."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
