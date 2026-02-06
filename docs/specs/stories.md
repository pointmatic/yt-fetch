# stories.md — YouTube Fetch + Transcript Collector (Python)

This is a detailed breakdown of the step-by-step stories (tasks) with detailed checklists that can be completed independently. Stories are organized by phase (see `plan.md`) and reference modules defined in `tech_spec.md`.

Each story is numbered (e.g. 3.1), followed by an application version number (e.g. v0.0.1) that will be bumped in the app when the story is completed.

---

## Phase 3: Foundation

### Story 3.1: v0.0.1 Hello World [Done]

Minimal runnable package with CLI entry point.

- [x] Create `pyproject.toml` with project metadata and dependencies (see tech_spec.md)
- [x] Create `yt_fetch/__init__.py` with `__version__`
- [x] Create `yt_fetch/__main__.py` for `python -m yt_fetch` support
- [x] Create `yt_fetch/cli.py` with a Click group and a `--version` flag
- [x] Verify: `python -m yt_fetch --version` prints version and exits

### Story 3.2: v0.0.2 Project Structure [Done]

Full package layout per tech_spec.md.

- [x] Create all package directories: `yt_fetch/core/`, `yt_fetch/services/`, `yt_fetch/utils/`
- [x] Create all `__init__.py` files
- [x] Create `tests/` directory with `conftest.py`
- [x] Create `tests/integration/` directory
- [x] Verify: package imports work (`from yt_fetch.core import models`)

### Story 3.3: v0.0.3 Core Models and Options [Done]

Pydantic data models and settings.

- [x] Implement `yt_fetch/core/models.py`:
  - [x] `Metadata` model with all fields per tech_spec.md
  - [x] `TranscriptSegment` model
  - [x] `Transcript` model
  - [x] `FetchResult` model
  - [x] `BatchResult` model
- [x] Implement `yt_fetch/core/options.py`:
  - [x] `FetchOptions` Pydantic `BaseSettings` with all fields per tech_spec.md
  - [x] Environment variable prefix `YT_FETCH_`
  - [x] YAML config file support (`yt_fetch.yaml`)
- [x] Write `tests/test_models.py`:
  - [x] Validation tests for each model
  - [x] Serialization round-trip tests
  - [x] Default values tests for `FetchOptions`

### Story 3.4: v0.0.4 Configuration System [Done]

CLI flags, env vars, and YAML config file integration.

- [x] Wire `FetchOptions` into `cli.py` Click commands
- [x] Implement config precedence: CLI flags → env vars → YAML → defaults
- [x] Create a sample `yt_fetch.yaml.example` file
- [x] Verify: CLI flag overrides env var overrides YAML overrides default

### Story 3.5: v0.0.5 Logging Framework [Done]

Console and structured JSONL logging.

- [x] Implement `yt_fetch/core/logging.py`:
  - [x] Console logger using `rich` (concise by default, verbose with `--verbose`)
  - [x] Structured JSONL logger with fields: `timestamp`, `level`, `video_id`, `event`, `details`, `error`
- [x] Wire logging into CLI (respect `--verbose` flag)
- [x] Verify: console output is clean; JSONL output is valid JSON per line

---

## Phase 4: Core Services

### Story 4.1: v0.1.0 Video ID Parsing and Validation [Done]

- [x] Implement `yt_fetch/services/id_parser.py`:
  - [x] `parse_video_id(input_str) -> str | None` — extract ID from URL or raw string
  - [x] `parse_many(inputs) -> list[str]` — parse, deduplicate, preserve order
  - [x] `load_ids_from_file(path) -> list[str]` — load from text, CSV, or JSONL
- [x] Supported URL patterns:
  - [x] `https://www.youtube.com/watch?v=<id>`
  - [x] `https://youtu.be/<id>`
  - [x] `https://www.youtube.com/shorts/<id>`
  - [x] URLs with extra query parameters
  - [x] Raw 11-character IDs
- [x] Validation: 11 chars, alphanumeric + `-` + `_`
- [x] Write `tests/test_id_parser.py`:
  - [x] All URL forms
  - [x] Raw IDs
  - [x] Invalid inputs return `None`
  - [x] Deduplication preserves order
  - [x] File loading (text, CSV, JSONL)

### Story 4.2: v0.1.1 Metadata Retrieval (yt-dlp) [Done]

- [x] Implement `yt_fetch/services/metadata.py`:
  - [x] `get_metadata(video_id, options) -> Metadata`
  - [x] `_yt_dlp_backend(video_id) -> dict` — extract metadata via yt-dlp
- [x] Map yt-dlp raw output to `Metadata` model fields
- [x] Store raw payload in `Metadata.raw`
- [x] Handle errors: video not found, private video, network failure
- [x] Write unit tests with mocked yt-dlp responses

### Story 4.3: v0.1.2 Metadata Retrieval (YouTube Data API v3, optional) [Done]

- [x] Implement `_youtube_api_backend(video_id, api_key) -> dict` in `metadata.py`
- [x] Add `google-api-python-client` as optional dependency
- [x] Implement automatic fallback to yt-dlp backend on API failure
- [x] Guard behind `yt_api_key` option — skip if not configured
- [x] Write unit tests with mocked API responses

### Story 4.4: v0.1.3 Transcript Fetching [Done]

- [x] Implement `yt_fetch/services/transcript.py`:
  - [x] `get_transcript(video_id, options) -> Transcript`
  - [x] `list_available_transcripts(video_id) -> list[TranscriptInfo]`
- [x] Language selection algorithm:
  - [x] Try preferred languages in order
  - [x] Prefer manual over generated (when `allow_generated` is false)
  - [x] Fall back to any language (when `allow_any_language` is true)
  - [x] Return structured `TRANSCRIPT_NOT_FOUND` error when none available
- [x] Edge cases:
  - [x] Video has no transcript
  - [x] Transcripts blocked by region/permissions
  - [x] Multiple language variants
- [x] Write unit tests with mocked `youtube-transcript-api` responses

### Story 4.5: v0.1.4 Media Download [Done]

- [x] Implement `yt_fetch/services/media.py`:
  - [x] `download_media(video_id, options, out_dir) -> MediaResult`
  - [x] `check_ffmpeg() -> bool`
- [x] Implement `yt_fetch/utils/ffmpeg.py` — ffmpeg detection helper
- [x] Download modes: `none`, `video`, `audio`, `both`
- [x] Respect `max_height` and format preferences
- [x] Handle missing ffmpeg: error or skip based on `ffmpeg_fallback` option
- [x] Write unit tests with mocked yt-dlp download calls

---

## Phase 5: Pipeline & Orchestration

### Story 5.1: v0.2.0 Per-Video Pipeline [Done]

- [x] Implement `yt_fetch/core/pipeline.py`:
  - [x] `process_video(video_id, options) -> FetchResult`
- [x] Workflow steps:
  - [x] Create output folder `<out_dir>/<video_id>/`
  - [x] Check cache — skip steps where output exists (unless `--force*`)
  - [x] Fetch metadata → pass to writer
  - [x] Fetch transcript → pass to writer
  - [x] Download media (if enabled) → write to `media/` subfolder
  - [x] Return structured `FetchResult`
- [x] Write `tests/test_pipeline.py` with mocked services

### Story 5.2: v0.2.1 Output File Writing [Done]

- [x] Implement `yt_fetch/core/writer.py`:
  - [x] `write_metadata(metadata, out_dir) -> Path`
  - [x] `write_transcript_json(transcript, out_dir) -> Path`
  - [x] `write_transcript_txt(transcript, out_dir) -> Path` — plain text, no timestamps
  - [x] `write_transcript_vtt(transcript, out_dir) -> Path`
  - [x] `write_transcript_srt(transcript, out_dir) -> Path`
  - [x] `write_summary(results, out_dir) -> Path`
- [x] Implement `yt_fetch/utils/time_fmt.py` — VTT/SRT timestamp formatting
- [x] All writes are atomic: write to `.tmp`, then `os.rename()`
- [x] Write `tests/test_writer.py`:
  - [x] Verify JSON output structure
  - [x] Verify transcript.txt has no timestamps
  - [x] Verify VTT/SRT timestamp formatting correctness
- [x] Write `tests/test_transcript_format.py` for timestamp edge cases

### Story 5.3: v0.2.2 Caching and Idempotency [Done]

- [x] Before each pipeline step, check if output file exists
- [x] If exists and no `--force*` flag: skip that step, log skip
- [x] Selective force: `--force-metadata`, `--force-transcript`, `--force-media`
- [x] `--force` overrides all selective flags
- [x] Write idempotency tests:
  - [x] Re-run without `--force` skips work
  - [x] Re-run with `--force` overwrites

### Story 5.4: v0.2.3 Batch Processing with Concurrency [Done]

- [x] Implement `process_batch(video_ids, options) -> BatchResult` in `pipeline.py`
- [x] Use `asyncio` with semaphore for concurrency (`--workers N`, default 3)
- [x] Per-video error isolation: one failure does not stop the batch
- [x] `--fail-fast` mode: stop on first error
- [x] Write batch tests:
  - [x] Mixed valid/invalid IDs
  - [x] Error isolation
  - [x] Fail-fast behavior

### Story 5.5: v0.2.4 Error Handling and Retry [Done]

- [x] Implement `yt_fetch/utils/retry.py`:
  - [x] Exponential backoff with jitter (base 1s, multiplier 2x, jitter ±25%)
  - [x] Configurable max retries (default 3)
  - [x] Applies to network errors, HTTP 429/5xx
- [x] Apply retry decorator to metadata, transcript, and media service calls
- [x] Write retry tests with simulated failures

### Story 5.6: v0.2.5 Rate Limiting [Done]

- [x] Implement `yt_fetch/utils/rate_limit.py`:
  - [x] Token bucket algorithm
  - [x] Configurable rate (default 2 RPS)
  - [x] Thread-safe, shared across all workers
- [x] Integrate rate limiter into pipeline before each external call
- [x] Write rate limiter unit tests

### Story 5.7: v0.2.6 Summary Reporting [Done]

- [x] At end of batch run, print summary to console:
  - [x] Total IDs processed, successes, failures
  - [x] Transcript successes/failures
  - [x] Media downloads
  - [x] Output directory path
- [x] Optionally write `out/summary.json` with list of results and status
- [x] Write summary output tests

---

## Phase 6: CLI & Library API

### Story 6.1: v0.3.0 CLI Subcommands [Done]

- [x] Implement Click subcommands in `yt_fetch/cli.py`:
  - [x] `yt_fetch fetch` — full pipeline (metadata + transcript + media)
  - [x] `yt_fetch transcript` — transcript only
  - [x] `yt_fetch metadata` — metadata only
  - [x] `yt_fetch media` — media download only
- [x] Shared input flags: `--id`, `--file`, `--jsonl` + `--id-field`
- [x] All option flags per features.md (--out, --languages, --download, etc.)
- [x] Exit codes: 0 (success), 1 (generic error), 2 (partial failure + --strict), 3 (all failed)
- [x] Write `tests/test_cli.py` — smoke tests for each subcommand

### Story 6.2: v0.3.1 Library API [Done]

- [x] Export public API from `yt_fetch/__init__.py`:
  - [x] `fetch_video(video_id, options) -> FetchResult`
  - [x] `fetch_batch(video_ids, options) -> BatchResult`
- [x] Ensure library usage does not require CLI context
- [x] Write library API tests

---

## Phase 7: Testing & Quality

### Story 7.1: v0.4.0 Unit Test Suite [Planned]

- [ ] Ensure all unit tests pass: ID parsing, models, transcript formatting, writer, rate limiter
- [ ] Achieve meaningful coverage across core modules
- [ ] All tests run without network access

### Story 7.2: v0.4.1 Integration Tests [Planned]

- [ ] Implement `tests/integration/test_fetch_live.py`:
  - [ ] Fetch metadata for a known public video
  - [ ] Fetch transcript for a known public video
  - [ ] Full pipeline end-to-end
  - [ ] Batch with mixed valid/invalid IDs
- [ ] Guard all integration tests behind `RUN_INTEGRATION=1` env var

### Story 7.3: v0.4.2 Pipeline and Error Tests [Planned]

- [ ] Idempotency: verify skip behavior and force overwrite
- [ ] Error isolation: one bad ID doesn't crash batch
- [ ] Fail-fast: verify early termination
- [ ] Retry: verify backoff on transient failures

---

## Phase 8: Documentation & Release

### Story 8.1: v0.5.0 README and Documentation [Planned]

- [ ] Create `README.md` with:
  - [ ] Project description and features
  - [ ] Installation instructions
  - [ ] Quick start / usage examples
  - [ ] Configuration reference
  - [ ] Library API usage
- [ ] Create `CHANGELOG.md`

### Story 8.2: v0.5.1 Final Testing and Refinement [Planned]

- [ ] Run full test suite (unit + integration)
- [ ] Fix any remaining bugs
- [ ] Review and clean up code
- [ ] Verify acceptance criteria from features.md:
  - [ ] `yt_fetch fetch --id dQw4w9WgXcQ` produces metadata + transcript
  - [ ] Batch mode with summary and per-video isolation
  - [ ] Re-run without `--force` skips completed work
  - [ ] Transcript exports (.txt, .json, .vtt, .srt) are correct
  - [ ] Errors are structured and do not crash the run
