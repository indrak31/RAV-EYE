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
| `pipeline/video_reader.py` | Real — reads video frames |
| `pipeline/detector.py` | Real — YOLOv8n detection, tested on real footage (`--detect-only`) |
| `pipeline/tracker.py` | Real — YOLOv8n + BoT-SORT tracking, tested on real footage (`--track-only`). **Known limitation:** dense/low-resolution traffic still causes ID switches (measured, not just suspected — see comments in the file); flagged as a risk in the original plan, not yet fully solved. |
| `pipeline/annotator.py` | Real — draws boxes + per-track-id colors |
| `pipeline/association.py` (`iou`) | Real — has a passing test |
| `evidence/case_builder.py` | Real shape, matches `docs/api-contract.md` exactly |
| `run_pipeline.py` | `--dry-run`, `--detect-only`, `--track-only`, `--violations` all work on real video |
| `pipeline/config.py` | Real — loads `configs/default.yaml`, converts stop-line coords for `RedLightRule` |
| `pipeline/signal_state.py` | Real — HSV heuristic (top/mid/bottom band = red/yellow/green), verified with synthetic-image tests. **Not yet validated on a real traffic light** — none was detectable in our test clip (too small/distant), so this still needs a real-footage check before trusting it fully. |
| `pipeline/plate_detector.py`, `ocr_engine.py` | Stub — Aryan's, needs real model code |
| `rules/red_light_rule.py` | Real logic + **calibrated** for `videoplayback (1).mp4` (Kolkata intersection clip) — stop line measured and confirmed visually, saved in `configs/default.yaml`. Ran end-to-end via `--violations` with no errors. **Not yet confirmed to correctly DETECT a real violation** — the calibration clip shows queued/stationary traffic, not an actual red-light run, so 0 violations found is the expected correct answer for that clip, not proof the detection itself works on a real violation. Needs footage of an actual red-light-jump to fully confirm. |
| `rules/no_helmet_rule.py` | Stub — needs a helmet classifier first |
| `evidence/evidence_engine.py` | Stub — needs frame-saving + ffmpeg clip logic |

## Try it today

```bash
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-cv.txt
# CUDA-enabled PyTorch (the plain pip install grabs a CPU-only build by default):
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

.venv\Scripts\python.exe -m cv.run_pipeline --video path\to\clip.mp4 --dry-run
.venv\Scripts\python.exe -m cv.run_pipeline --video path\to\clip.mp4 --detect-only --output out.mp4
.venv\Scripts\python.exe -m cv.run_pipeline --video path\to\clip.mp4 --track-only --output out.mp4
.venv\Scripts\python.exe -m cv.run_pipeline --video path\to\clip.mp4 --violations --output out.mp4
```

Needs Python 3.11 or 3.12 specifically — newer Python versions (e.g. 3.14)
don't yet have prebuilt installers for these ML libraries.

## Run the one test that exists so far

```bash
pytest cv/tests/
```
