# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic data models for yt-fetch."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class Metadata(BaseModel):
    video_id: str
    source_url: str
    title: str | None = None
    channel_title: str | None = None
    channel_id: str | None = None
    upload_date: str | None = None
    duration_seconds: float | None = None
    description: str | None = None
    tags: list[str] = []
    view_count: int | None = None
    like_count: int | None = None
    fetched_at: datetime
    metadata_source: str
    raw: dict | None = None


class TranscriptSegment(BaseModel):
    start: float
    duration: float
    text: str


class Transcript(BaseModel):
    video_id: str
    language: str
    is_generated: bool | None = None
    segments: list[TranscriptSegment]
    fetched_at: datetime
    transcript_source: str
    available_languages: list[str] = []
    errors: list[str] = []


class FetchResult(BaseModel):
    video_id: str
    success: bool
    metadata_path: Path | None = None
    transcript_path: Path | None = None
    media_paths: list[Path] = []
    metadata: Metadata | None = None
    transcript: Transcript | None = None
    errors: list[str] = []


class BatchResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[FetchResult]
