# Changelog

All notable changes to this project will be documented in this file.

## [0.5.1] — 2026-02-06

### Added
- `yt-fetch` (hyphenated) CLI entry point — both `yt_fetch` and `yt-fetch` now work
- MPL-2.0 copyright and license header on all Python source files
- LLM project guide (`docs/guides/project_guide.md`)

### Fixed
- License mismatch: `README.md` and `pyproject.toml` incorrectly listed GPL-3.0-or-later; corrected to MPL-2.0 to match `LICENSE` file

## [0.5.0] — 2025-02-06

### Added
- `README.md` with project description, features, installation, usage, configuration reference, and library API examples
- `CHANGELOG.md`
- Final acceptance testing and code cleanup

## [0.4.2] — 2025-02-06

### Added
- Pipeline and error edge case tests (idempotency transcript verification, batch transcript errors, fail-fast with transcript errors, retry integration)

## [0.4.1] — 2025-02-06

### Added
- Integration tests (`tests/integration/test_fetch_live.py`) for metadata, transcript, pipeline, and batch
- All integration tests guarded behind `RUN_INTEGRATION=1` env var

## [0.4.0] — 2025-02-06

### Added
- Logging module tests (`tests/test_logging.py`)
- CLI error path tests (transcript/metadata/media errors, `_build_options` format/languages, JSONL collection)
- 96% test coverage across all modules

## [0.3.1] — 2025-02-06

### Added
- Public library API: `fetch_video()` and `fetch_batch()` in `yt_fetch/__init__.py`
- `__all__` exports: `FetchOptions`, `FetchResult`, `BatchResult`, `Metadata`, `Transcript`
- Library API tests (`tests/test_library_api.py`)

## [0.3.0] — 2025-02-06

### Added
- CLI subcommands: `fetch`, `transcript`, `metadata`, `media`
- Shared input flags: `--id`, `--file`, `--jsonl`, `--id-field`
- All option flags per features.md
- `--strict` flag for exit code 2 on partial failure
- Exit codes: 0 (success), 1 (error), 2 (partial + strict), 3 (all failed)
- CLI smoke tests (`tests/test_cli.py`)

## [0.2.6] — 2025-02-06

### Added
- `print_summary()` — console summary at end of batch run
- `process_batch()` now writes `summary.json` automatically
- Summary tests (`tests/test_summary.py`)

## [0.2.5] — 2025-02-06

### Added
- `TokenBucket` rate limiter (`yt_fetch/utils/rate_limit.py`) — thread-safe, configurable rate
- Rate limiter integrated into pipeline before each external call
- Shared rate limiter across batch workers
- Rate limiter tests (`tests/test_rate_limit.py`)

## [0.2.4] — 2025-02-06

### Added
- `retry()` decorator (`yt_fetch/utils/retry.py`) — exponential backoff with jitter
- `is_retryable_http_status()` — checks for 429/5xx
- Applied `@retry` to metadata, transcript, and media service calls
- Retry tests (`tests/test_retry.py`)

## [0.2.3] — 2025-02-06

### Added
- `process_batch()` — async batch processing with `asyncio.Semaphore` concurrency
- Per-video error isolation
- `--fail-fast` mode
- Batch tests (`tests/test_batch.py`)

## [0.2.2] — 2025-02-06

### Added
- Idempotency tests (`tests/test_idempotency.py`) — skip, force, selective force

## [0.2.1] — 2025-02-06

### Added
- `write_transcript_txt()`, `write_transcript_vtt()`, `write_transcript_srt()`, `write_summary()`
- `seconds_to_vtt()`, `seconds_to_srt()` timestamp formatting (`yt_fetch/utils/time_fmt.py`)
- Atomic text file writing
- Writer tests (`tests/test_writer.py`) and timestamp tests (`tests/test_transcript_format.py`)

## [0.2.0] — 2025-02-06

### Added
- `process_video()` pipeline orchestration (`yt_fetch/core/pipeline.py`)
- `write_metadata()`, `write_transcript_json()` with atomic writes
- Pipeline tests (`tests/test_pipeline.py`)

## [0.1.4] — 2025-02-06

### Added
- Media download service (`yt_fetch/services/media.py`) — video, audio, both modes
- ffmpeg detection helper (`yt_fetch/utils/ffmpeg.py`)
- Media tests (`tests/test_media.py`)

## [0.1.3] — 2025-02-06

### Added
- YouTube Data API v3 backend (`yt_fetch/services/metadata.py`) — optional, with fallback to yt-dlp
- YouTube API tests (`tests/test_metadata.py`)

## [0.1.2] — 2025-02-06

### Added
- Transcript service (`yt_fetch/services/transcript.py`) — language selection algorithm
- Transcript tests (`tests/test_transcript.py`)

## [0.1.1] — 2025-02-06

### Added
- Metadata service (`yt_fetch/services/metadata.py`) — yt-dlp backend
- Metadata tests (`tests/test_metadata.py`)

## [0.1.0] — 2025-02-06

### Added
- Pydantic data models (`yt_fetch/core/models.py`)
- `FetchOptions` settings model with CLI → env → YAML → defaults precedence
- Model tests (`tests/test_models.py`)

## [0.0.5] — 2025-02-06

### Added
- Structured logging (`yt_fetch/core/logging.py`) — Rich console + JSONL file handler
- CLI entry point with Click (`yt_fetch/cli.py`)

## [0.0.4] — 2025-02-06

### Added
- ID parser service (`yt_fetch/services/id_parser.py`) — URLs, raw IDs, file loading
- ID parser tests (`tests/test_id_parser.py`)

## [0.0.3] — 2025-02-06

### Added
- Project scaffolding: package structure, pyproject.toml, dependencies
- Placeholder modules for all planned components
