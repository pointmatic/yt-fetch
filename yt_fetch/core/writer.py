"""Output file writing (JSON, txt, VTT, SRT)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from yt_fetch.core.models import Metadata, Transcript


def write_metadata(metadata: Metadata, out_dir: Path) -> Path:
    """Write metadata as JSON. Returns the written file path."""
    video_dir = out_dir / metadata.video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    dest = video_dir / "metadata.json"
    _atomic_write_json(dest, metadata.model_dump(mode="json"))
    return dest


def write_transcript_json(transcript: Transcript, out_dir: Path) -> Path:
    """Write transcript as JSON. Returns the written file path."""
    video_dir = out_dir / transcript.video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    dest = video_dir / "transcript.json"
    _atomic_write_json(dest, transcript.model_dump(mode="json"))
    return dest


def _atomic_write_json(dest: Path, data: dict) -> None:
    """Write JSON atomically: write to temp file, then rename."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=dest.parent, suffix=".tmp", prefix=".yt_fetch_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, dest)
    except BaseException:
        os.unlink(tmp_path)
        raise
