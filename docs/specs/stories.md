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

### Story 3.5: v0.0.5 Logging Framework [Planned]

Console and structured JSONL logging.

- [ ] Implement `yt_fetch/core/logging.py`:
  - [ ] Console logger using `rich` (concise by default, verbose with `--verbose`)
  - [ ] Structured JSONL logger with fields: `timestamp`, `level`, `video_id`, `event`, `details`, `error`
- [ ] Wire logging into CLI (respect `--verbose` flag)
- [ ] Verify: console output is clean; JSONL output is valid JSON per line

---

## Phase 4: Core Services

### Story 4.1: v0.1.0 Video ID Parsing and Validation [Planned]

- [ ] Implement `yt_fetch/services/id_parser.py`:
  - [ ] `parse_video_id(input_str) -> str | None` — extract ID from URL or raw string
  - [ ] `parse_many(inputs) -> list[str]` — parse, deduplicate, preserve order
  - [ ] `load_ids_from_file(path) -> list[str]` — load from text, CSV, or JSONL
- [ ] Supported URL patterns:
  - [ ] `https://www.youtube.com/watch?v=<id>`
  - [ ] `https://youtu.be/<id>`
  - [ ] `https://www.youtube.com/shorts/<id>`
  - [ ] URLs with extra query parameters
  - [ ] Raw 11-character IDs
- [ ] Validation: 11 chars, alphanumeric + `-` + `_`
- [ ] Write `tests/test_id_parser.py`:
  - [ ] All URL forms
  - [ ] Raw IDs
  - [ ] Invalid inputs return `None`
  - [ ] Deduplication preserves order
  - [ ] File loading (text, CSV, JSONL)

### Story 4.2: v0.1.1 Metadata Retrieval (yt-dlp) [Planned]

- [ ] Implement `yt_fetch/services/metadata.py`:
  - [ ] `get_metadata(video_id, options) -> Metadata`
  - [ ] `_yt_dlp_backend(video_id) -> dict` — extract metadata via yt-dlp
- [ ] Map yt-dlp raw output to `Metadata` model fields
- [ ] Store raw payload in `Metadata.raw`
- [ ] Handle errors: video not found, private video, network failure
- [ ] Write unit tests with mocked yt-dlp responses

### Story 4.3: v0.1.2 Metadata Retrieval (YouTube Data API v3, optional) [Planned]

- [ ] Implement `_youtube_api_backend(video_id, api_key) -> dict` in `metadata.py`
- [ ] Add `google-api-python-client` as optional dependency
- [ ] Implement automatic fallback to yt-dlp backend on API failure
- [ ] Guard behind `yt_api_key` option — skip if not configured
- [ ] Write unit tests with mocked API responses

### Story 4.4: v0.1.3 Transcript Fetching [Planned]

- [ ] Implement `yt_fetch/services/transcript.py`:
  - [ ] `get_transcript(video_id, options) -> Transcript`
  - [ ] `list_available_transcripts(video_id) -> list[TranscriptInfo]`
- [ ] Language selection algorithm:
  - [ ] Try preferred languages in order
  - [ ] Prefer manual over generated (when `allow_generated` is false)
  - [ ] Fall back to any language (when `allow_any_language` is true)
  - [ ] Return structured `TRANSCRIPT_NOT_FOUND` error when none available
- [ ] Edge cases:
  - [ ] Video has no transcript
  - [ ] Transcripts blocked by region/permissions
  - [ ] Multiple language variants
- [ ] Write unit tests with mocked `youtube-transcript-api` responses

### Story 4.5: v0.1.4 Media Download [Planned]

- [ ] Implement `yt_fetch/services/media.py`:
  - [ ] `download_media(video_id, options, out_dir) -> MediaResult`
  - [ ] `check_ffmpeg() -> bool`
- [ ] Implement `yt_fetch/utils/ffmpeg.py` — ffmpeg detection helper
- [ ] Download modes: `none`, `video`, `audio`, `both`
- [ ] Respect `max_height` and format preferences
- [ ] Handle missing ffmpeg: error or skip based on `ffmpeg_fallback` option
- [ ] Write unit tests with mocked yt-dlp download calls

---

## Phase 5: Pipeline & Orchestration

### Story 5.1: v0.2.0 Per-Video Pipeline [Planned]

- [ ] Implement `yt_fetch/core/pipeline.py`:
  - [ ] `process_video(video_id, options) -> FetchResult`
- [ ] Workflow steps:
  - [ ] Create output folder `<out_dir>/<video_id>/`
  - [ ] Check cache — skip steps where output exists (unless `--force*`)
  - [ ] Fetch metadata → pass to writer
  - [ ] Fetch transcript → pass to writer
  - [ ] Download media (if enabled) → write to `media/` subfolder
  - [ ] Return structured `FetchResult`
- [ ] Write `tests/test_pipeline.py` with mocked services

### Story 5.2: v0.2.1 Output File Writing [Planned]

- [ ] Implement `yt_fetch/core/writer.py`:
  - [ ] `write_metadata(metadata, out_dir) -> Path`
  - [ ] `write_transcript_json(transcript, out_dir) -> Path`
  - [ ] `write_transcript_txt(transcript, out_dir) -> Path` — plain text, no timestamps
  - [ ] `write_transcript_vtt(transcript, out_dir) -> Path`
  - [ ] `write_transcript_srt(transcript, out_dir) -> Path`
  - [ ] `write_summary(results, out_dir) -> Path`
- [ ] Implement `yt_fetch/utils/time_fmt.py` — VTT/SRT timestamp formatting
- [ ] All writes are atomic: write to `.tmp`, then `os.rename()`
- [ ] Write `tests/test_writer.py`:
  - [ ] Verify JSON output structure
  - [ ] Verify transcript.txt has no timestamps
  - [ ] Verify VTT/SRT timestamp formatting correctness
- [ ] Write `tests/test_transcript_format.py` for timestamp edge cases

### Story 5.3: v0.2.2 Caching and Idempotency [Planned]

- [ ] Before each pipeline step, check if output file exists
- [ ] If exists and no `--force*` flag: skip that step, log skip
- [ ] Selective force: `--force-metadata`, `--force-transcript`, `--force-media`
- [ ] `--force` overrides all selective flags
- [ ] Write idempotency tests:
  - [ ] Re-run without `--force` skips work
  - [ ] Re-run with `--force` overwrites

### Story 5.4: v0.2.3 Batch Processing with Concurrency [Planned]

- [ ] Implement `process_batch(video_ids, options) -> BatchResult` in `pipeline.py`
- [ ] Use `asyncio` with semaphore for concurrency (`--workers N`, default 3)
- [ ] Per-video error isolation: one failure does not stop the batch
- [ ] `--fail-fast` mode: stop on first error
- [ ] Write batch tests:
  - [ ] Mixed valid/invalid IDs
  - [ ] Error isolation
  - [ ] Fail-fast behavior

### Story 5.5: v0.2.4 Error Handling and Retry [Planned]

- [ ] Implement `yt_fetch/utils/retry.py`:
  - [ ] Exponential backoff with jitter (base 1s, multiplier 2x, jitter ±25%)
  - [ ] Configurable max retries (default 3)
  - [ ] Applies to network errors, HTTP 429/5xx
- [ ] Apply retry decorator to metadata, transcript, and media service calls
- [ ] Write retry tests with simulated failures

### Story 5.6: v0.2.5 Rate Limiting [Planned]

- [ ] Implement `yt_fetch/utils/rate_limit.py`:
  - [ ] Token bucket algorithm
  - [ ] Configurable rate (default 2 RPS)
  - [ ] Thread-safe, shared across all workers
- [ ] Integrate rate limiter into pipeline before each external call
- [ ] Write rate limiter unit tests

### Story 5.7: v0.2.6 Summary Reporting [Planned]

- [ ] At end of batch run, print summary to console:
  - [ ] Total IDs processed, successes, failures
  - [ ] Transcript successes/failures
  - [ ] Media downloads
  - [ ] Output directory path
- [ ] Optionally write `out/summary.json` with list of results and status
- [ ] Write summary output tests

---

## Phase 6: CLI & Library API

### Story 6.1: v0.3.0 CLI Subcommands [Planned]

- [ ] Implement Click subcommands in `yt_fetch/cli.py`:
  - [ ] `yt_fetch fetch` — full pipeline (metadata + transcript + media)
  - [ ] `yt_fetch transcript` — transcript only
  - [ ] `yt_fetch metadata` — metadata only
  - [ ] `yt_fetch media` — media download only
- [ ] Shared input flags: `--id`, `--file`, `--jsonl` + `--id-field`
- [ ] All option flags per features.md (--out, --languages, --download, etc.)
- [ ] Exit codes: 0 (success), 1 (generic error), 2 (partial failure + --strict), 3 (all failed)
- [ ] Write `tests/test_cli.py` — smoke tests for each subcommand

### Story 6.2: v0.3.0 Library API [Planned]

- [ ] Export public API from `yt_fetch/__init__.py`:
  - [ ] `fetch_video(video_id, options) -> FetchResult`
  - [ ] `fetch_batch(video_ids, options) -> BatchResult`
- [ ] Ensure library usage does not require CLI context
- [ ] Write library API tests

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
