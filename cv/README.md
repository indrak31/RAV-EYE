# cv/ — Computer Vision Track

Scaffold created 2026-08-19 on branch `cv/scaffold-stub`. Nothing here does
real AI work yet — every function that needs a model raises
`NotImplementedError` with a note on what to plug in. This is intentional:
it's a skeleton matching the shape of `docs/api-contract.md`, ready to fill
in incrementally without redesigning the structure later.

## Ownership (swapped from the original plan, based on hardware)

Hardware note: real-time YOLO detection/tracking needs a GPU. Meghana has
an Nvidia GPU (Asus TUF); Aryan has a MacBook (CPU only). So:

- **Meghana** — `pipeline/video_reader.py`, `detector.py`, `tracker.py`,
  `signal_state.py`, `annotator.py`, `rules/*`, `run_pipeline.py`.
  Needs GPU — runs on the TUF.
- **Aryan** — `pipeline/plate_detector.py`, `ocr_engine.py`,
  `association.py`, `evidence/*`. CPU-friendly — runs fine on the Mac.

## What's real vs. stub right now

| File | Status |
|---|---|
| `pipeline/video_reader.py` | Real — reads video frames, just needs `opencv-python` installed |
| `pipeline/annotator.py` | Real — draws boxes, no model needed |
| `pipeline/association.py` (`iou`) | Real — has a passing test |
| `evidence/case_builder.py` | Real shape, matches `docs/api-contract.md` exactly |
| `run_pipeline.py` | Wiring works with `--dry-run`; full run needs the stubs below filled in |
| `pipeline/detector.py`, `tracker.py`, `signal_state.py` | Stub — needs real model code |
| `pipeline/plate_detector.py`, `ocr_engine.py` | Stub — needs real model code |
| `rules/no_helmet_rule.py`, `red_light_rule.py` | Stub — needs classifier/signal state first |
| `evidence/evidence_engine.py` | Stub — needs frame-saving + ffmpeg clip logic |

## Try it today (no models needed yet)

```bash
pip install -r requirements-cv.txt
python -m cv.run_pipeline --video path/to/any/clip.mp4 --dry-run
```

That should print the video's fps/resolution/frame count — confirms the
plumbing works before any AI code is written.

## Run the one test that exists so far

```bash
pytest cv/tests/
```
