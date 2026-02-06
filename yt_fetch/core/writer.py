"""Output file writing (JSON, txt, VTT, SRT)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from yt_fetch.core.models import BatchResult, Metadata, Transcript
from yt_fetch.utils.time_fmt import seconds_to_srt, seconds_to_vtt


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


def write_transcript_txt(transcript: Transcript, out_dir: Path) -> Path:
    """Write transcript as plain text (no timestamps). Returns the written file path."""
    video_dir = out_dir / transcript.video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    dest = video_dir / "transcript.txt"
    lines = [seg.text for seg in transcript.segments]
    _atomic_write_text(dest, "\n".join(lines) + "\n")
    return dest


def write_transcript_vtt(transcript: Transcript, out_dir: Path) -> Path:
    """Write transcript as WebVTT. Returns the written file path."""
    video_dir = out_dir / transcript.video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    dest = video_dir / "transcript.vtt"

    parts = ["WEBVTT", ""]
    for seg in transcript.segments:
        start = seconds_to_vtt(seg.start)
        end = seconds_to_vtt(seg.start + seg.duration)
        parts.append(f"{start} --> {end}")
        parts.append(seg.text)
        parts.append("")

    _atomic_write_text(dest, "\n".join(parts))
    return dest


def write_transcript_srt(transcript: Transcript, out_dir: Path) -> Path:
    """Write transcript as SRT. Returns the written file path."""
    video_dir = out_dir / transcript.video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    dest = video_dir / "transcript.srt"

    parts = []
    for i, seg in enumerate(transcript.segments, start=1):
        start = seconds_to_srt(seg.start)
        end = seconds_to_srt(seg.start + seg.duration)
        parts.append(str(i))
        parts.append(f"{start} --> {end}")
        parts.append(seg.text)
        parts.append("")

    _atomic_write_text(dest, "\n".join(parts))
    return dest


def write_summary(results: BatchResult, out_dir: Path) -> Path:
    """Write a batch summary as JSON. Returns the written file path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "summary.json"
    _atomic_write_json(dest, results.model_dump(mode="json"))
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


def _atomic_write_text(dest: Path, content: str) -> None:
    """Write text atomically: write to temp file, then rename."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=dest.parent, suffix=".tmp", prefix=".yt_fetch_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, dest)
    except BaseException:
        os.unlink(tmp_path)
        raise
