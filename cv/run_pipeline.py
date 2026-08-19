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
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    meta = get_video_meta(args.video)
    print(f"Video: {args.video}")
    print(f"  fps={meta.fps:.2f}  size={meta.width}x{meta.height}  frames={meta.frame_count}")

    if args.dry_run:
        print("Dry run only (--dry-run) — stopping before detection.")
        return 0

    print(
        "\nFull pipeline is not wired to real models yet.\n"
        "Next steps: implement Detector.load()/detect() in cv/pipeline/detector.py,\n"
        "then Tracker.load()/update() in cv/pipeline/tracker.py.\n"
        "Until then, run with --dry-run to just sanity-check video reading."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
