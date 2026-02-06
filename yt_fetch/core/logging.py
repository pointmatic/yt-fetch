# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Structured logging setup (console + JSONL)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


_console = Console(stderr=True)


class JsonlFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "video_id": getattr(record, "video_id", None),
            "event": getattr(record, "event", None),
            "details": getattr(record, "details", None),
            "error": getattr(record, "error", None),
        }
        if record.getMessage():
            entry["message"] = record.getMessage()
        return json.dumps(entry, default=str)


class JsonlFileHandler(logging.FileHandler):
    """File handler that uses JsonlFormatter by default."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(str(path), mode="a", encoding="utf-8")
        self.setFormatter(JsonlFormatter())


def setup_logging(*, verbose: bool = False, jsonl_path: Path | None = None) -> logging.Logger:
    """Configure and return the yt_fetch logger.

    Args:
        verbose: If True, set level to DEBUG; otherwise INFO.
        jsonl_path: If provided, also write structured JSONL logs to this file.

    Returns:
        The configured 'yt_fetch' logger.
    """
    logger = logging.getLogger("yt_fetch")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    rich_handler = RichHandler(
        console=_console,
        show_time=verbose,
        show_path=verbose,
        rich_tracebacks=True,
        markup=True,
    )
    rich_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(rich_handler)

    if jsonl_path is not None:
        jsonl_handler = JsonlFileHandler(jsonl_path)
        jsonl_handler.setLevel(logging.DEBUG)
        logger.addHandler(jsonl_handler)

    return logger


def get_logger() -> logging.Logger:
    """Get the yt_fetch logger (must call setup_logging first)."""
    return logging.getLogger("yt_fetch")


def log_event(
    level: int,
    message: str,
    *,
    video_id: str | None = None,
    event: str | None = None,
    details: str | None = None,
    error: str | None = None,
) -> None:
    """Log a structured event with optional yt-fetch-specific fields."""
    logger = get_logger()
    logger.log(
        level,
        message,
        extra={
            "video_id": video_id,
            "event": event,
            "details": details,
            "error": error,
        },
    )
