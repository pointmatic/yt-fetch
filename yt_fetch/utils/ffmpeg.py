"""ffmpeg detection and helpers."""

from __future__ import annotations

import shutil


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is found on PATH."""
    return shutil.which("ffmpeg") is not None
