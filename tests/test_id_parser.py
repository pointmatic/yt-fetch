# Copyright (c) 2026 Pointmatic
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for yt_fetch.services.id_parser."""

from pathlib import Path

import pytest

from yt_fetch.services.id_parser import load_ids_from_file, parse_many, parse_video_id


class TestParseVideoId:
    """Test parse_video_id with various URL forms and raw IDs."""

    # --- Raw IDs ---

    def test_raw_id(self):
        assert parse_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_raw_id_with_hyphens_underscores(self):
        assert parse_video_id("a1-B2_c3D4e") == "a1-B2_c3D4e"

    def test_raw_id_with_whitespace(self):
        assert parse_video_id("  dQw4w9WgXcQ  ") == "dQw4w9WgXcQ"

    # --- youtube.com/watch URLs ---

    def test_watch_url(self):
        assert parse_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_http(self):
        assert parse_video_id("http://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_no_www(self):
        assert parse_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_mobile(self):
        assert parse_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        assert parse_video_id(url) == "dQw4w9WgXcQ"

    def test_watch_url_v_not_first_param(self):
        url = "https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ"
        assert parse_video_id(url) == "dQw4w9WgXcQ"

    # --- youtu.be URLs ---

    def test_short_url(self):
        assert parse_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url_with_params(self):
        assert parse_video_id("https://youtu.be/dQw4w9WgXcQ?t=42") == "dQw4w9WgXcQ"

    # --- youtube.com/shorts URLs ---

    def test_shorts_url(self):
        assert parse_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url_with_params(self):
        assert parse_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share") == "dQw4w9WgXcQ"

    # --- embed and /v/ URLs ---

    def test_embed_url(self):
        assert parse_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_v_url(self):
        assert parse_video_id("https://www.youtube.com/v/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # --- Invalid inputs ---

    def test_empty_string(self):
        assert parse_video_id("") is None

    def test_whitespace_only(self):
        assert parse_video_id("   ") is None

    def test_too_short(self):
        assert parse_video_id("abc") is None

    def test_too_long(self):
        assert parse_video_id("dQw4w9WgXcQx") is None

    def test_invalid_chars(self):
        assert parse_video_id("dQw4w9WgXc!") is None

    def test_random_url(self):
        assert parse_video_id("https://example.com/watch?v=dQw4w9WgXcQ") is None

    def test_youtube_no_v_param(self):
        assert parse_video_id("https://www.youtube.com/watch?list=PLfoo") is None

    def test_youtube_channel_url(self):
        assert parse_video_id("https://www.youtube.com/channel/UCfoo") is None


class TestParseMany:
    """Test parse_many with deduplication and order preservation."""

    def test_multiple_ids(self):
        result = parse_many(["dQw4w9WgXcQ", "a1-B2_c3D4e"])
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_deduplication(self):
        result = parse_many([
            "dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ])
        assert result == ["dQw4w9WgXcQ"]

    def test_preserves_order(self):
        result = parse_many(["bbbbbbbbbbb", "aaaaaaaaaaa", "ccccccccccc"])
        assert result == ["bbbbbbbbbbb", "aaaaaaaaaaa", "ccccccccccc"]

    def test_skips_invalid(self):
        result = parse_many(["dQw4w9WgXcQ", "invalid", "a1-B2_c3D4e"])
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_empty_list(self):
        assert parse_many([]) == []

    def test_mixed_urls_and_ids(self):
        result = parse_many([
            "dQw4w9WgXcQ",
            "https://youtu.be/a1-B2_c3D4e",
            "https://www.youtube.com/shorts/xxxxxxxxxxx",
        ])
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e", "xxxxxxxxxxx"]


class TestLoadIdsFromFile:
    """Test load_ids_from_file with text, CSV, and JSONL files."""

    def test_text_file(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("dQw4w9WgXcQ\na1-B2_c3D4e\n\n# comment\n")
        result = load_ids_from_file(f)
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_text_file_with_urls(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("https://youtu.be/dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=a1-B2_c3D4e\n")
        result = load_ids_from_file(f)
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_text_file_deduplication(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("dQw4w9WgXcQ\ndQw4w9WgXcQ\na1-B2_c3D4e\n")
        result = load_ids_from_file(f)
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_csv_file(self, tmp_path):
        f = tmp_path / "ids.csv"
        f.write_text("id,title\ndQw4w9WgXcQ,Video 1\na1-B2_c3D4e,Video 2\n")
        result = load_ids_from_file(f)
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_csv_file_custom_field(self, tmp_path):
        f = tmp_path / "ids.csv"
        f.write_text("video_id,title\ndQw4w9WgXcQ,Video 1\n")
        result = load_ids_from_file(f, id_field="video_id")
        assert result == ["dQw4w9WgXcQ"]

    def test_jsonl_file(self, tmp_path):
        f = tmp_path / "ids.jsonl"
        f.write_text('{"id": "dQw4w9WgXcQ"}\n{"id": "a1-B2_c3D4e"}\n')
        result = load_ids_from_file(f)
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_jsonl_file_custom_field(self, tmp_path):
        f = tmp_path / "ids.jsonl"
        f.write_text('{"video_id": "dQw4w9WgXcQ"}\n')
        result = load_ids_from_file(f, id_field="video_id")
        assert result == ["dQw4w9WgXcQ"]

    def test_jsonl_skips_bad_lines(self, tmp_path):
        f = tmp_path / "ids.jsonl"
        f.write_text('{"id": "dQw4w9WgXcQ"}\nnot json\n{"id": "a1-B2_c3D4e"}\n')
        result = load_ids_from_file(f)
        assert result == ["dQw4w9WgXcQ", "a1-B2_c3D4e"]

    def test_empty_file(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("")
        assert load_ids_from_file(f) == []
