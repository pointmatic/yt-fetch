# features.md — yt-fetch: AI-Ready YouTube Content Extraction

## Overview
This document defines the features and functionality (not technical or implementation details) for yt-fetch. For architecture, modules, and dependencies see `tech_spec.md`.

## Project Goal
Build a Python tool that extracts structured, AI-ready content from YouTube videos. Given one or more video IDs, URLs, playlists, or channels, yt-fetch produces normalized metadata, transcripts, and optional media in formats optimized for downstream AI/LLM pipelines (summarization, fact-checking, RAG, search indexing, etc.).

### Core Requirements
- fetch and store video metadata in structured JSON
- fetch and store transcripts (when available) in multiple formats
- produce LLM-ready plain text transcripts with configurable formatting
- resolve playlist and channel URLs to video IDs for batch processing
- emit consistent, deterministic outputs to a local folder
- provide content hashes for change detection in incremental pipelines
- optionally estimate token counts for context window planning

### Secondary Requirements
- download video and/or audio media (optional, for speech-to-text fallback or archival)

### Operational Requirements
- operate gracefully with structured error classification and configurable retries
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
- batch jobs from a file or playlist/channel URL
- being imported as a library from another Python project (e.g., `yt-factify`)

### Non-goals
- UI/web app
- bypassing DRM or paywalled content
- speech-to-text / audio transcription (yt-fetch fetches existing transcripts; it does not generate them from audio)
- LLM integration (yt-fetch prepares content for LLMs; it does not call LLM APIs itself)

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

### Playlist and channel inputs
Accept playlist and channel URLs as batch input sources:
- `https://www.youtube.com/playlist?list=<playlist_id>`
- `https://www.youtube.com/@<handle>` or `https://www.youtube.com/channel/<channel_id>`

Behavior:
- Resolve the URL to a list of video IDs using `yt-dlp`'s playlist/channel extraction
- Feed the resolved IDs into the existing pipeline (deduplication, caching, etc. all apply)
- Optionally limit the number of videos resolved (`--max-videos N`)
- Store the resolved video ID list in the output directory for reproducibility

### Optional inputs
- Output directory (default `./out`)
- Language preferences for transcripts (e.g., `en`, `en-US`, `es`)
- Whether to download: `none|video|audio|both`
- Desired media format(s): mp4, webm, m4a, mp3 (as applicable)
- Max resolution / best available
- Rate limits and retries
- "Fail fast" vs "continue on errors"
- API keys (optional): YouTube Data API v3 key for richer metadata
- Token count estimation: tokenizer name (default `cl100k_base`), or disabled

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
- `content_hash` (SHA-256 of the canonical metadata fields, for change detection)
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
- `content_hash` (SHA-256 of the concatenated segment text, for change detection)
- `token_count` (estimated token count using configured tokenizer, if enabled; `null` if disabled)
- `errors` (optional list; empty when ok)

#### `transcript.txt` (LLM-ready)
Plain text transcript optimized for LLM ingestion. Configurable formatting:
- **Default mode**: concatenation of segment text with paragraph breaks at natural silence gaps (configurable gap threshold, default 2.0 seconds)
- **Timestamped mode** (`--txt-timestamps`): include `[MM:SS]` markers at paragraph boundaries for citation support
- **Raw mode** (`--txt-raw`): bare concatenation with no formatting (backward-compatible with current behavior)

The `is_generated` status is noted at the top of the file when true, so downstream consumers can weight human vs. auto-generated transcripts differently.

#### Optional: `transcript.vtt` and `transcript.srt`
Generate from segments with correct timestamp formatting.

#### Optional: `video_bundle.json`
A single unified envelope combining metadata + transcript + error info per video. Enabled with `--bundle`. Contains:
- `video_id`
- `metadata` (full metadata object)
- `transcript` (full transcript object, or `null`)
- `errors` (list of structured `FetchError` objects)
- `content_hash` (SHA-256 of the combined metadata + transcript content)
- `token_count` (estimated token count of transcript, if enabled)
- `fetched_at` (timestamp of this bundle generation)

This is a convenience for programmatic consumers that prefer a single file per video over multiple files.

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
- When transcript fetch fails for the requested language, report the available languages in the error message and in `result.errors` so callers can provide actionable feedback.
- When `is_generated` is true, note it prominently in both `transcript.json` and `transcript.txt` so downstream AI pipelines can weight human vs. auto-generated transcripts differently.

Edge cases:
- Video has no transcript
- Transcripts exist but blocked by region or permissions
- Multiple language variants exist
- Network failures / throttling

### 4) Media download (optional, secondary)
Media download is secondary to the text extraction mission. It is primarily useful for:
- speech-to-text fallback when no transcript exists (yt-fetch provides the audio; external tools do STT)
- archival or offline playback

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
- If output files already exist, default behavior should skip re-fetching from the network unless `--force`.
- When cached files exist and the result is returned via the library API, the in-memory objects (`result.metadata`, `result.transcript`) must still be populated by reading from the cached files.
- Allow selective force:
  - `--force-metadata`
  - `--force-transcript`
  - `--force-media`

### 6) Error handling + resilience
- Per-video isolation: one failing ID should not stop the batch by default.
- Provide `--fail-fast` to stop on first failure.
- Retries with exponential backoff for transient errors only (not for permanently unavailable content).
  - Retries are configurable (`--retries N`); setting `--retries 0` disables internal retries entirely, allowing library consumers to manage retries externally (e.g., via `gentlify`).
- Respect rate limiting:
  - global requests per second (simple token bucket)
  - rate limiting is configurable; setting `--rate-limit 0` disables internal rate limiting for library consumers that manage throttling externally.

#### Structured error classification

All errors reported in `FetchResult.errors` must be structured objects (`FetchError`) with:
- **`code`** — a machine-readable `FetchErrorCode` enum value (e.g., `transcripts_disabled`, `rate_limited`, `network_error`)
- **`phase`** — a `FetchPhase` enum indicating which pipeline step failed (`metadata`, `transcript`, or `media`)
- **`retryable`** — a boolean hint indicating whether the error is transient (worth retrying) or permanent (content unavailable)
- **`message`** — a human-readable description
- **`details`** — optional dict with extra context (e.g., available languages, HTTP status)

Callers must be able to programmatically distinguish:
- **Content unavailable** (video private/deleted, transcripts disabled, no transcript in requested language) — `retryable=False`
- **Transient infrastructure failure** (rate limited, HTTP 5xx, network error, timeout) — `retryable=True`

See `error_handling_features.md` for the full error code reference and exception hierarchy.

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
- `yt_fetch fetch --playlist <playlist_url>` (resolve playlist to IDs, then fetch)
- `yt_fetch fetch --channel <channel_url>` (resolve channel to IDs, then fetch)
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
- `--max-videos N` (limit videos resolved from playlist/channel)
- `--txt-timestamps` (include `[MM:SS]` markers in transcript.txt)
- `--txt-raw` (bare concatenation, no paragraph formatting)
- `--bundle` (emit `video_bundle.json` per video)
- `--tokenizer <name>` (enable token count estimation; default disabled)

Exit codes:
- `0` success (even if some videos failed, if not fail-fast) — but print a summary
- `1` generic error (bad args, unable to initialize)
- `2` partial failure (some video IDs failed) when `--strict` is set
- `3` all failed

### 9) Library API (importable)
Expose a Python API so other code can do:

- `fetch_video(video_id, options) -> FetchResult`
- `fetch_batch(video_ids, options) -> BatchResult`
- `resolve_playlist(url, max_videos=None) -> list[str]`
- `resolve_channel(url, max_videos=None) -> list[str]`

Where results include:
- paths written
- metadata object (always populated on success, even when read from cache)
- transcript object (always populated when available, even when read from cache)
- structured error list (`list[FetchError]`) with machine-readable codes and retryable hints
- content hashes for change detection
- token count (if tokenizer configured)

The library API must behave identically to the CLI for the same inputs. In particular:
- `result.metadata` must always be populated when metadata is available, regardless of `force_metadata` or caching state.
- `result.transcript` must always be populated when a transcript is available, regardless of `force_transcript` or caching state.
- When a transcript is not available, `result.errors` must contain a structured `FetchError` with the appropriate `FetchErrorCode` (e.g., `TRANSCRIPTS_DISABLED`, `TRANSCRIPT_NOT_FOUND`) and `details` (e.g., available languages) so the caller can programmatically distinguish "no captions" from "not fetched."

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

### 10) Playlist and channel resolution
Accept playlist URLs and channel URLs as input sources. Resolve them to video ID lists using `yt-dlp`'s extraction capabilities.

- `resolve_playlist(url)` returns an ordered list of video IDs from a playlist
- `resolve_channel(url)` returns video IDs from a channel's uploads
- Both support `--max-videos N` to limit the number of resolved IDs
- The resolved ID list is written to `<out>/resolved_ids.json` for reproducibility and auditing
- Resolved IDs feed into the standard pipeline (deduplication, caching, batch processing all apply)

### 11) LLM-ready transcript formatting
The `transcript.txt` output is optimized for LLM consumption:

- **Paragraph chunking**: insert paragraph breaks at natural silence gaps between segments (configurable gap threshold, default 2.0 seconds). This produces readable, semantically coherent paragraphs rather than a wall of text.
- **Timestamp markers** (optional, `--txt-timestamps`): insert `[MM:SS]` markers at paragraph boundaries. Useful for citation and reference back to the original video.
- **Raw mode** (optional, `--txt-raw`): bare concatenation with no formatting, for backward compatibility.
- **Auto-generated notice**: when `is_generated` is true, prepend a notice line (e.g., `[Auto-generated transcript]`) so downstream consumers can adjust confidence weighting.

### 12) Token count estimation
Optionally estimate the token count of transcript text using a configurable tokenizer.

- Enabled via `--tokenizer <name>` (CLI) or `FetchOptions(tokenizer="cl100k_base")` (library)
- Default: disabled (no tokenizer dependency required)
- Supported tokenizers: `cl100k_base` (GPT-4), `o200k_base` (GPT-4o), or any tokenizer supported by `tiktoken`
- Token count is stored in `transcript.json` as `token_count` (integer or `null`)
- Also available in `video_bundle.json` and `FetchResult.transcript.token_count`
- `tiktoken` is an optional dependency (installed via `pip install yt-fetch[tokens]`)

This lets AI pipelines know upfront whether a transcript fits in a context window without importing `tiktoken` themselves.

### 13) Content hash / change detection
Compute SHA-256 content hashes for metadata and transcript outputs.

- `metadata.json` includes `content_hash`: SHA-256 of canonical metadata fields (title, description, tags, upload_date, duration_seconds)
- `transcript.json` includes `content_hash`: SHA-256 of concatenated segment text
- `video_bundle.json` includes `content_hash`: SHA-256 of combined metadata + transcript content
- Hashes enable downstream pipelines to detect when a re-fetch actually changed content (e.g., auto-captions improved, description updated) without diffing full files
- Hashes are deterministic: same content always produces the same hash

### 14) Video bundle output
Optionally emit a single `video_bundle.json` per video that combines all structured data into one file.

- Enabled via `--bundle` (CLI) or `FetchOptions(bundle=True)` (library)
- Contains: `video_id`, `metadata`, `transcript`, `errors`, `content_hash`, `token_count`, `fetched_at`
- Simplifies programmatic consumption: one file to read per video instead of joining `metadata.json` + `transcript.json`
- The bundle is written after all other outputs, so it reflects the final state

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
- `transcript.txt` uses paragraph chunking by default, producing readable LLM-ready text.
- Errors are structured, logged, and do not crash the whole run unless configured.
- Playlist and channel URLs resolve to video IDs and feed into the standard pipeline.
- Content hashes are present in `metadata.json` and `transcript.json`.
- Token counts are present when a tokenizer is configured.
- `--bundle` produces a valid `video_bundle.json` per video.
