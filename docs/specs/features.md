# features.md — YouTube Fetch + Transcript Collector (Python)

## Overview
This document defines the features and functionality (not technical or implementation details) for the YouTube Fetch + Transcript Collector project. For architecture, modules, and dependencies see `tech_spec.md`.

## Project Goal
Build a Python program that, given one or more YouTube video IDs, downloads assets according to the following requirements:

### Core Requirements
- fetch and store video metadata
- download the video (optional)
- download the audio (optional)
- fetch and store transcripts (when available)
- emit consistent outputs (JSON + text/VTT/SRT) to a local folder

### Operational Requirements
- operate gracefully with errors and retries
- provide clear feedback and logging
- support configuration via CLI flags and/or a config file
- support parallel processing for batch jobs
- support resume/continue from previous run

### Quality Requirements
- support deduplication of videos
- avoid downloading the same video multiple times
- avoid downloading the same transcript multiple times
- respect YouTube rate limits and terms of service

### Usability Requirements
The program should work well for:
- one-off CLI usage
- batch jobs from a file
- being imported as a library from another Python project

### Non-goals
- UI/web app
- full YouTube channel crawling
- bypassing DRM or paywalled content

---

## Inputs

### Required input: YouTube video IDs
Support:
- single ID (e.g., `dQw4w9WgXcQ`)
- multiple IDs via CLI args
- a text file with one ID per line
- a CSV/JSONL file containing an `id` field

Also accept full YouTube URLs and extract the video ID:
- `https://www.youtube.com/watch?v=<id>`
- `https://youtu.be/<id>`
- `https://www.youtube.com/shorts/<id>`
- URLs containing extra query params should still parse correctly

### Optional inputs
- Output directory (default `./out`)
- Language preferences for transcripts (e.g., `en`, `en-US`, `es`)
- Whether to download: `none|video|audio|both`
- Desired media format(s): mp4, webm, m4a, mp3 (as applicable)
- Max resolution / best available
- Rate limits and retries
- “Fail fast” vs “continue on errors”
- API keys (optional): YouTube Data API v3 key for richer metadata

---

## Outputs

### Folder structure (deterministic)
For each video ID, create:
```
./out/<video_id>/
    metadata.json
    transcript.json
    transcript.txt
    transcript.vtt (optional)
    transcript.srt (optional)
    media/
        video.<ext> (optional)
        audio.<ext> (optional)
    logs.jsonl (optional per-video log events)
```


### `metadata.json` (minimum fields)
Include at least:
- `video_id`
- `source_url`
- `title` (if available)
- `channel_title` / `uploader` (if available)
- `channel_id` (if available)
- `upload_date` (ISO 8601 if available)
- `duration_seconds` (if available)
- `description` (optional; may be long)
- `tags` (optional)
- `view_count`, `like_count` (optional)
- `fetched_at` (timestamp)
- `metadata_source` (e.g., `"yt-dlp"`, `"youtube-data-api"`)
- `raw` (optional: store the unmodified raw metadata payload under a key)

### Transcript outputs
Store transcript in multiple representations:

#### `transcript.json` (normalized)
Top-level keys:
- `video_id`
- `language` (final chosen language)
- `is_generated` (boolean if known)
- `segments`: list of objects:
  - `start` (float seconds)
  - `duration` (float seconds)
  - `text` (string)
- `fetched_at`
- `transcript_source` (e.g., `"youtube-transcript-api"`)
- `available_languages` (list if known)
- `errors` (optional list; empty when ok)

#### `transcript.txt`
Plain text concatenation of segment text in order, without timestamps. Intended for human reading and LLM ingestion.

#### Optional: `transcript.vtt` and `transcript.srt`
Generate from segments with correct timestamp formatting.

---

## Functional Requirements

### 1) Video ID parsing and validation
- Extract ID from common URL forms.
- Validate ID shape (11 chars, YouTube-like) but do not over-reject.
- De-duplicate IDs in batch runs.
- Preserve input order unless `--sort` option is used.

### 2) Metadata retrieval
Provide two metadata modes:

**Mode A (default, no API key):**
- Use `yt-dlp` (or similar) in Python to extract metadata.
- Must not require user login.

**Mode B (optional, with API key):**
- Use YouTube Data API v3 for richer/structured metadata when configured.
- If API fails, fallback to Mode A.

Metadata retrieval should be independent from media download.

### 3) Transcript retrieval (best-effort)
Use a transcript fetcher that does not require an API key (e.g., `youtube-transcript-api`) by default.

Behavior:
- Attempt transcript in preferred languages in priority order.
- If not found, optionally fall back to:
  - any available language (configurable)
  - generated transcript if human transcript not available (configurable)
- If transcripts are disabled for a video, store a structured error in output.

Edge cases:
- Video has no transcript
- Transcripts exist but blocked by region or permissions
- Multiple language variants exist
- Network failures / throttling

### 4) Media download (optional)
If enabled, use `yt-dlp` to download:
- video only, audio only, or both
- user can set max resolution (e.g., 720p)
- user can request audio extraction (e.g., bestaudio to m4a or mp3 if ffmpeg present)

Requirements:
- Detect whether `ffmpeg` is installed if conversion is requested.
- If ffmpeg missing and conversion requested, either:
  - fail with actionable error, or
  - skip conversion and store original format (configurable)

### 5) Caching / idempotency
- If output files already exist, default behavior should skip work unless `--force`.
- Allow selective force:
  - `--force-metadata`
  - `--force-transcript`
  - `--force-media`

### 6) Error handling + resilience
- Per-video isolation: one failing ID should not stop the batch by default.
- Provide `--fail-fast` to stop on first failure.
- Retries with exponential backoff for network errors.
- Respect rate limiting:
  - global requests per second (simple token bucket)
  - or per-component throttles (transcript vs metadata vs media)

### 7) Logging and observability
- Console logs should be concise, with a `--verbose` flag.
- Structured logs (JSONL) option with fields:
  - timestamp
  - level
  - video_id (when applicable)
  - event (e.g., `fetch_metadata_start`, `fetch_transcript_success`)
  - details/error

### 8) CLI interface
Provide a CLI named `yt_fetch` (or similar) with subcommands:

- `yt_fetch fetch --id <id> [--id <id2> ...]`
- `yt_fetch fetch --file ids.txt`
- `yt_fetch fetch --jsonl input.jsonl --id-field video_id`
- `yt_fetch transcript --id <id>` (transcript only)
- `yt_fetch metadata --id <id>` (metadata only)
- `yt_fetch media --id <id>` (download only)

Common flags:
- `--out <dir>`
- `--languages en,en-US,es`
- `--allow-generated / --no-allow-generated`
- `--allow-any-language / --no-allow-any-language`
- `--download none|video|audio|both`
- `--max-height 720`
- `--format mp4|webm|best`
- `--audio-format m4a|mp3|best`
- `--force` and selective force flags
- `--retries N`
- `--rate-limit RPS`
- `--fail-fast`
- `--verbose`

Exit codes:
- `0` success (even if some videos failed, if not fail-fast) — but print a summary
- `1` generic error (bad args, unable to initialize)
- `2` partial failure (some video IDs failed) when `--strict` is set
- `3` all failed

### 9) Library API (importable)
Expose a Python API so other code can do:

- `fetch_video(video_id, options) -> FetchResult`
- `fetch_batch(video_ids, options) -> BatchResult`

Where results include:
- paths written
- metadata object (optional)
- transcript object (optional)
- error list

---

## Configuration

### Config precedence
1. CLI flags
2. Environment variables
3. Config file (`yt_fetch.yaml`)
4. Defaults

Suggested env vars:
- `YT_FETCH_OUT`
- `YT_FETCH_LANGUAGES`
- `YT_FETCH_YT_API_KEY`
- `YT_FETCH_RATE_LIMIT`
- `YT_FETCH_RETRIES`

Config file fields should mirror CLI flags.

---

## Transcript Language Selection Rules
Given `preferred_languages = [L1, L2, ...]`:
1. If transcript exists in L1 (manual preferred over generated if setting requires), choose it.
2. Else try L2, etc.
3. If none found and `allow_any_language`, pick “best” available:
   - prefer manual over generated
   - prefer English variants if present (configurable heuristic)
4. If still none, record `TRANSCRIPT_NOT_FOUND`.

---

## Summary Reporting
At the end of a run, print a summary:
- total IDs processed
- successes
- failures
- transcript successes/failures
- media downloads
- output directory

Also write `out/summary.json` optionally:
- list of results with status and paths

---

## Testing Requirements
Minimum tests:
- ID parsing for all URL forms + raw IDs
- Transcript formatting to VTT/SRT timestamps correctness
- Pipeline idempotency (skip existing unless force)
- Error handling when transcript unavailable (should not crash)
- Batch continues on failure unless `fail-fast`

Prefer tests that do not require network:
- mock services for unit tests
- optionally include an integration test suite guarded by env var, e.g. `RUN_INTEGRATION=1`

---

## Security and Compliance Notes
- Do not store cookies, credentials, or personal tokens by default.
- If API key is used, read from env/config and avoid logging it.
- Respect YouTube’s Terms of Service; do not implement functionality intended to circumvent restrictions.

---

## Performance Notes
- Allow concurrency for batch runs (`--workers N`) but default to safe low parallelism (e.g., 2–4).
- Rate limit should apply across workers.
- Write files atomically (write temp then rename) to avoid partial outputs on crash.

---

## Acceptance Criteria (Definition of Done)
- `yt_fetch fetch --id dQw4w9WgXcQ` creates the output folder with metadata + transcript (if available).
- Batch mode processes multiple IDs, producing a clear summary and preserving per-video isolation.
- Re-running without `--force` skips completed work.
- Transcripts can be exported to `.txt` and `.json` reliably; optional `.vtt`/`.srt` formatting is correct.
- Errors are structured, logged, and do not crash the whole run unless configured.
