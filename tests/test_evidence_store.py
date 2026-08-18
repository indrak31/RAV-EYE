"""Tests for evidence_store service."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from app.config import Settings
from app.services.evidence_store import (
    delete_media,
    get_media_path,
    get_media_response,
    save_clip,
    save_frame,
    _evidence_path,
)


@pytest.fixture(autouse=True)
def _isolate_media_dir(tmp_path, monkeypatch):
    """Point MEDIA_DIR to a temp directory for each test."""
    media_dir = tmp_path / "media"
    monkeypatch.setenv("MEDIA_DIR", str(media_dir))
    # Clear the settings cache so it picks up the new env var
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_save_frame_returns_evidence_id():
    """save_frame should return a UUID evidence_id and write the file."""
    frame_bytes = b"fake-image-data"
    evidence_id = save_frame(frame_bytes, ".jpg")

    # Should return a valid UUID string
    assert evidence_id
    assert len(evidence_id) == 36  # UUID format

    # File should exist on disk
    path = get_media_path(evidence_id)
    assert path.exists()
    assert path.read_bytes() == frame_bytes


def test_save_frame_custom_extension():
    """save_frame should respect custom extension."""
    evidence_id = save_frame(b"png-data", ".png")
    path = get_media_path(evidence_id)
    assert path.suffix == ".png"


def test_save_clip_copies_file(tmp_path):
    """save_clip should copy a source file to media dir."""
    # Create a source clip
    src = tmp_path / "source_clip.mp4"
    src.write_bytes(b"fake-video-data")

    evidence_id = save_clip(str(src), ".mp4")
    path = get_media_path(evidence_id)
    assert path.exists()
    assert path.read_bytes() == b"fake-video-data"


def test_get_media_response_returns_file_response():
    """get_media_response should return a FileResponse for valid evidence_id."""
    evidence_id = save_frame(b"test-image")
    response = get_media_response(evidence_id)

    assert response.path.exists()
    assert response.media_type == "image/jpeg"


def test_get_media_path_raises_404_for_missing():
    """get_media_path should raise HTTPException 404 for unknown evidence_id."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        get_media_path("non-existent-id")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["detail"] == "evidence_not_found"


def test_delete_media_removes_file():
    """delete_media should remove the file and return True."""
    evidence_id = save_frame(b"to-delete")
    assert delete_media(evidence_id) is True
    # Use internal _evidence_path to check without raising 404
    assert _evidence_path(evidence_id) is None


def test_delete_media_returns_false_for_missing():
    """delete_media should return False for non-existent evidence_id."""
    assert delete_media("non-existent-id") is False


def test_media_stored_in_daily_subdirectory():
    """Files should be stored under media/{YYYY-MM-DD}/."""
    evidence_id = save_frame(b"date-test")
    path = get_media_path(evidence_id)

    # Should be in a date-named subdirectory
    parts = path.parts
    date_dir = parts[-2]  # parent directory
    # Should match YYYY-MM-DD pattern
    assert len(date_dir) == 10
    assert date_dir[4] == "-"
    assert date_dir[7] == "-"