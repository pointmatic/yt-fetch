"""URL/ID parsing and validation."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _is_valid_video_id(candidate: str) -> bool:
    """Check if a string looks like a valid YouTube video ID."""
    return bool(_VIDEO_ID_RE.match(candidate))


def parse_video_id(input_str: str) -> str | None:
    """Extract a YouTube video ID from a URL or raw ID string.

    Returns None if input cannot be parsed.
    """
    text = input_str.strip()
    if not text:
        return None

    if _is_valid_video_id(text):
        return text

    try:
        parsed = urlparse(text)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower().removeprefix("www.")

    if host in ("youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            candidates = qs.get("v", [])
            if candidates and _is_valid_video_id(candidates[0]):
                return candidates[0]
        elif parsed.path.startswith("/shorts/"):
            candidate = parsed.path.removeprefix("/shorts/").split("/")[0]
            if _is_valid_video_id(candidate):
                return candidate
        elif parsed.path.startswith("/embed/"):
            candidate = parsed.path.removeprefix("/embed/").split("/")[0]
            if _is_valid_video_id(candidate):
                return candidate
        elif parsed.path.startswith("/v/"):
            candidate = parsed.path.removeprefix("/v/").split("/")[0]
            if _is_valid_video_id(candidate):
                return candidate

    elif host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
        if _is_valid_video_id(candidate):
            return candidate

    return None


def parse_many(inputs: list[str]) -> list[str]:
    """Parse multiple inputs, deduplicate, preserve order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in inputs:
        video_id = parse_video_id(raw)
        if video_id is not None and video_id not in seen:
            seen.add(video_id)
            result.append(video_id)
    return result


def load_ids_from_file(path: Path, *, id_field: str = "id") -> list[str]:
    """Load video IDs from a text file (one per line), CSV, or JSONL.

    For CSV files, looks for a column matching `id_field`.
    For JSONL files, looks for a key matching `id_field` in each JSON object.
    For plain text files, treats each non-empty line as an ID or URL.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    raw_ids: list[str] = []

    if suffix == ".jsonl":
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and id_field in obj:
                        raw_ids.append(str(obj[id_field]))
                except json.JSONDecodeError:
                    continue

    elif suffix == ".csv":
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if id_field in row and row[id_field]:
                    raw_ids.append(row[id_field].strip())

    else:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    raw_ids.append(line)

    return parse_many(raw_ids)
