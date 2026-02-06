# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests that hit real YouTube APIs.

All tests in this module require network access and are guarded behind
the RUN_INTEGRATION=1 environment variable. They will be skipped by default.

Uses "Never Gonna Give You Up" (dQw4w9WgXcQ) as the known public video —
it has metadata, English transcript, and is unlikely to be removed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Skip entire module unless RUN_INTEGRATION=1
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION", "0") != "1",
    reason="Integration tests disabled. Set RUN_INTEGRATION=1 to run.",
)

KNOWN_VIDEO_ID = "dQw4w9WgXcQ"
INVALID_VIDEO_ID = "xxxxxxxxxxx"


class TestMetadataLive:
    """Fetch metadata for a known public video."""

    def test_fetch_metadata(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.services.metadata import get_metadata

        opts = FetchOptions(out=tmp_path)
        meta = get_metadata(KNOWN_VIDEO_ID, opts)

        assert meta.video_id == KNOWN_VIDEO_ID
        assert meta.title is not None
        assert len(meta.title) > 0
        assert meta.metadata_source == "yt-dlp"
        assert meta.duration_seconds is not None
        assert meta.duration_seconds > 0

    def test_metadata_writes_json(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.core.writer import write_metadata
        from yt_fetch.services.metadata import get_metadata

        opts = FetchOptions(out=tmp_path)
        meta = get_metadata(KNOWN_VIDEO_ID, opts)
        path = write_metadata(meta, tmp_path)

        assert path.exists()
        assert path.name == "metadata.json"

        import json
        data = json.loads(path.read_text())
        assert data["video_id"] == KNOWN_VIDEO_ID


class TestTranscriptLive:
    """Fetch transcript for a known public video."""

    def test_fetch_transcript(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.services.transcript import get_transcript

        opts = FetchOptions(out=tmp_path, languages=["en"])
        transcript = get_transcript(KNOWN_VIDEO_ID, opts)

        assert transcript.video_id == KNOWN_VIDEO_ID
        assert transcript.language == "en"
        assert len(transcript.segments) > 0
        assert transcript.segments[0].text is not None

    def test_transcript_writes_json(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.core.writer import write_transcript_json
        from yt_fetch.services.transcript import get_transcript

        opts = FetchOptions(out=tmp_path, languages=["en"])
        transcript = get_transcript(KNOWN_VIDEO_ID, opts)
        path = write_transcript_json(transcript, tmp_path)

        assert path.exists()
        assert path.name == "transcript.json"


class TestPipelineLive:
    """Full pipeline end-to-end."""

    def test_process_video(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.core.pipeline import process_video

        opts = FetchOptions(out=tmp_path)
        result = process_video(KNOWN_VIDEO_ID, opts)

        assert result.success is True
        assert result.video_id == KNOWN_VIDEO_ID
        assert result.metadata_path is not None
        assert result.metadata_path.exists()
        assert result.transcript_path is not None
        assert result.transcript_path.exists()
        assert result.errors == []

    def test_process_video_output_structure(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.core.pipeline import process_video

        opts = FetchOptions(out=tmp_path)
        process_video(KNOWN_VIDEO_ID, opts)

        video_dir = tmp_path / KNOWN_VIDEO_ID
        assert video_dir.is_dir()
        assert (video_dir / "metadata.json").exists()
        assert (video_dir / "transcript.json").exists()


class TestBatchLive:
    """Batch with mixed valid/invalid IDs."""

    def test_batch_mixed_ids(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.core.pipeline import process_batch

        opts = FetchOptions(out=tmp_path, workers=1)
        result = process_batch([KNOWN_VIDEO_ID, INVALID_VIDEO_ID], opts)

        assert result.total == 2
        assert result.succeeded >= 1

        good = [r for r in result.results if r.video_id == KNOWN_VIDEO_ID]
        assert len(good) == 1
        assert good[0].success is True

        bad = [r for r in result.results if r.video_id == INVALID_VIDEO_ID]
        assert len(bad) == 1
        assert bad[0].success is False
        assert len(bad[0].errors) > 0

    def test_batch_writes_summary(self, tmp_path):
        from yt_fetch.core.options import FetchOptions
        from yt_fetch.core.pipeline import process_batch

        opts = FetchOptions(out=tmp_path, workers=1)
        process_batch([KNOWN_VIDEO_ID], opts)

        summary = tmp_path / "summary.json"
        assert summary.exists()

        import json
        data = json.loads(summary.read_text())
        assert data["total"] == 1
        assert data["succeeded"] == 1
