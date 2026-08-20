"""config.py — loads cv/configs/default.yaml so code can actually use it.

Owner: Meghana. Small and boring on purpose — this just turns the YAML
file into Python values other modules can use, e.g. the calibrated
stop-line coordinates for red_light_rule.py.
"""
from __future__ import annotations

import os

import yaml

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "default.yaml"
)


def load_config(path: str | None = None) -> dict:
    """Read the YAML config file into a plain dict."""
    path = path or _DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def stop_line_from_config(config: dict) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Read camera.stop_line ([x1,y1,x2,y2] or null) and turn it into the
    ((x1,y1), (x2,y2)) point-pair shape red_light_rule.RedLightRule expects.
    Returns None if not calibrated (stop_line is null/missing in the YAML).
    """
    raw = config.get("camera", {}).get("stop_line")
    if not raw:
        return None
    x1, y1, x2, y2 = raw
    return ((x1, y1), (x2, y2))
