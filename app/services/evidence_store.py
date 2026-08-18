"""Evidence media store — disk-backed storage for frames and clips.

Saves media under MEDIA_DIR/{yyyy-mm-dd}/ with UUID filenames.
Returns evidence_id that can be used to retrieve the file later.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from app.config import get_settings


settings = get_settings()


def _media_root() -> Path:
    """Resolve the media root directory from settings."""
    media_dir = getattr(settings, "MEDIA_DIR", "./media")
    return Path(media_dir).resolve()


def _daily_dir() -> Path:
    """Get or create today's date-based subdirectory."""
    root = _media_root()
    today = datetime.now().strftime("%Y-%m-%d")
    daily = root / today
    daily.mkdir(parents=True, exist_ok=True)
    return daily


def _evidence_path(evidence_id: str) -> Path | None:
    """Find the file for a given evidence_id across all date dirs."""
    root = _media_root()
    if not root.exists():
        return None
    for date_dir in root.iterdir():
        if not date_dir.is_dir():
            continue
        for file in date_dir.iterdir():
            if file.is_file() and file.stem == evidence_id:
                return file
    return None


def save_frame(frame_bytes: bytes, extension: str = ".jpg") -> str:
    """Save a single frame image to disk.

    Args:
        frame_bytes: Raw image bytes.
        extension: File extension (default .jpg).

    Returns:
        evidence_id (UUID string) that can be used to retrieve the file.
    """
    evidence_id = str(uuid.uuid4())
    daily = _daily_dir()
    file_path = daily / f"{evidence_id}{extension}"
    file_path.write_bytes(frame_bytes)
    return evidence_id


def save_clip(clip_path: str | Path, extension: str = ".mp4") -> str:
    """Save a video clip by copying from a source path.

    Args:
        clip_path: Path to the source video file.
        extension: File extension (default .mp4).

    Returns:
        evidence_id (UUID string) that can be used to retrieve the file.
    """
    evidence_id = str(uuid.uuid4())
    daily = _daily_dir()
    dest_path = daily / f"{evidence_id}{extension}"
    src = Path(clip_path)
    dest_path.write_bytes(src.read_bytes())
    return evidence_id


def get_media_path(evidence_id: str) -> Path:
    """Get the filesystem path for an evidence_id.

    Raises:
        HTTPException: 404 if not found.
    """
    path = _evidence_path(evidence_id)
    if path is None or not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "evidence_not_found", "evidence_id": evidence_id},
        )
    return path


def get_media_response(evidence_id: str) -> FileResponse:
    """Return a FileResponse for streaming the evidence file."""
    path = get_media_path(evidence_id)
    media_type = _guess_media_type(path.suffix)
    return FileResponse(
        path=path,
        media_type=media_type,
        filename=path.name,
    )


def _guess_media_type(suffix: str) -> str:
    """Map file extension to MIME type."""
    suffix = suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix in (".mp4", ".mov"):
        return "video/mp4"
    if suffix == ".webm":
        return "video/webm"
    return "application/octet-stream"


def delete_media(evidence_id: str) -> bool:
    """Delete an evidence file by ID. Returns True if deleted."""
    path = _evidence_path(evidence_id)
    if path and path.exists():
        path.unlink()
        return True
    return False