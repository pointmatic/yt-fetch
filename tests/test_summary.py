# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for summary reporting in yt_fetch.core.pipeline."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from yt_fetch.core.models import BatchResult, FetchResult, Metadata, Transcript, TranscriptSegment
from yt_fetch.core.options import FetchOptions
from yt_fetch.core.pipeline import print_summary, process_batch


def _make_metadata(video_id: str) -> Metadata:
    return Metadata(
        video_id=video_id,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        title=f"Video {video_id}",
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        metadata_source="yt-dlp",
    )


def _make_transcript(video_id: str) -> Transcript:
    return Transcript(
        video_id=video_id,
        language="en",
        is_generated=False,
        segments=[TranscriptSegment(start=0.0, duration=1.0, text="Hello")],
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        transcript_source="youtube-transcript-api",
    )


class TestPrintSummary:
    """Test console summary output."""

    def test_prints_totals(self, tmp_path, caplog):
        batch = BatchResult(
            total=3,
            succeeded=2,
            failed=1,
            results=[
                FetchResult(video_id="a", success=True, transcript_path=Path("/a/t.json")),
                FetchResult(video_id="b", success=True, transcript_path=Path("/b/t.json")),
                FetchResult(video_id="c", success=False, errors=["transcript: fail"]),
            ],
        )
        with caplog.at_level(logging.INFO, logger="yt_fetch"):
            print_summary(batch, tmp_path)

        output = caplog.text
        assert "Total:        3" in output
        assert "Succeeded:    2" in output
        assert "Failed:       1" in output

    def test_prints_transcript_counts(self, tmp_path, caplog):
        batch = BatchResult(
            total=2,
            succeeded=1,
            failed=1,
            results=[
                FetchResult(video_id="a", success=True, transcript_path=Path("/a/t.json")),
                FetchResult(video_id="b", success=False, errors=["transcript: not found"]),
            ],
        )
        with caplog.at_level(logging.INFO, logger="yt_fetch"):
            print_summary(batch, tmp_path)

        assert "Transcripts:  1 ok, 1 failed" in caplog.text

    def test_prints_media_count(self, tmp_path, caplog):
        batch = BatchResult(
            total=2,
            succeeded=2,
            failed=0,
            results=[
                FetchResult(video_id="a", success=True, media_paths=[Path("/a/v.mp4")]),
                FetchResult(video_id="b", success=True, media_paths=[Path("/b/v.mp4"), Path("/b/a.m4a")]),
            ],
        )
        with caplog.at_level(logging.INFO, logger="yt_fetch"):
            print_summary(batch, tmp_path)

        assert "Media files:  3" in caplog.text

    def test_prints_output_dir(self, tmp_path, caplog):
        batch = BatchResult(total=0, succeeded=0, failed=0, results=[])
        with caplog.at_level(logging.INFO, logger="yt_fetch"):
            print_summary(batch, tmp_path)

        assert str(tmp_path.resolve()) in caplog.text

    def test_empty_batch(self, tmp_path, caplog):
        batch = BatchResult(total=0, succeeded=0, failed=0, results=[])
        with caplog.at_level(logging.INFO, logger="yt_fetch"):
            print_summary(batch, tmp_path)

        assert "Total:        0" in caplog.text
        assert "Transcripts:  0 ok, 0 failed" in caplog.text
        assert "Media files:  0" in caplog.text


class TestProcessBatchSummary:
    """Test that process_batch writes summary.json and prints summary."""

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_writes_summary_json(self, mock_meta, mock_trans, tmp_path):
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        result = process_batch(["vid_aaaaaaa", "vid_bbbbbbb"], opts)

        summary_path = tmp_path / "summary.json"
        assert summary_path.exists()

        data = json.loads(summary_path.read_text())
        assert data["total"] == 2
        assert data["succeeded"] == 2
        assert data["failed"] == 0
        assert len(data["results"]) == 2

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_summary_json_includes_errors(self, mock_meta, mock_trans, tmp_path):
        from yt_fetch.services.metadata import MetadataError

        def meta_side(vid, opts):
            if vid == "bad_vid_aaaaa":
                raise MetadataError("not found")
            return _make_metadata(vid)

        mock_meta.side_effect = meta_side
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        process_batch(["vid_aaaaaaa", "bad_vid_aaaaa"], opts)

        data = json.loads((tmp_path / "summary.json").read_text())
        assert data["failed"] == 1
        failed = [r for r in data["results"] if not r["success"]]
        assert len(failed) == 1
        assert len(failed[0]["errors"]) > 0

    @patch("yt_fetch.core.pipeline.get_transcript")
    @patch("yt_fetch.core.pipeline.get_metadata")
    def test_prints_summary_to_log(self, mock_meta, mock_trans, tmp_path, caplog):
        mock_meta.side_effect = lambda vid, opts: _make_metadata(vid)
        mock_trans.side_effect = lambda vid, opts: _make_transcript(vid)

        opts = FetchOptions(out=tmp_path, workers=1)
        with caplog.at_level(logging.INFO, logger="yt_fetch"):
            process_batch(["vid_aaaaaaa"], opts)

        assert "yt-fetch Summary" in caplog.text
        assert "Total:        1" in caplog.text
