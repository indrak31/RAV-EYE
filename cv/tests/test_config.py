"""test_config.py — verify the YAML config loader and stop-line conversion."""
from cv.pipeline.config import load_config, stop_line_from_config


def test_load_config_reads_real_default_yaml():
    config = load_config()
    assert config["camera"]["camera_id"] == "CAM-DEMO-01"


def test_stop_line_from_config_converts_flat_list_to_points():
    config = {"camera": {"stop_line": [170, 445, 430, 450]}}
    points = stop_line_from_config(config)
    assert points == ((170, 445), (430, 450))


def test_stop_line_from_config_returns_none_when_not_calibrated():
    config = {"camera": {"stop_line": None}}
    assert stop_line_from_config(config) is None


def test_stop_line_from_config_returns_none_when_camera_missing():
    assert stop_line_from_config({}) is None
