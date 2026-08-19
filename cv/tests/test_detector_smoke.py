"""test_detector_smoke.py — the most basic possible check: does the code import and run?

Owner: Meghana. A "smoke test" doesn't check correctness deeply — it just
checks nothing is on fire. Good first test before real model tests exist.
"""
from cv.pipeline.association import iou


def test_iou_identical_boxes_is_one():
    box = (0, 0, 10, 10)
    assert iou(box, box) == 1.0


def test_iou_no_overlap_is_zero():
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_iou_partial_overlap_between_zero_and_one():
    score = iou((0, 0, 10, 10), (5, 5, 15, 15))
    assert 0.0 < score < 1.0
