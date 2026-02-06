# plan.md — YouTube Fetch + Transcript Collector (Python)

This is a high-level checklist for the project.

## Phase 1: Project Definition

- [x] define features.md
- [x] define plan.md

## Phase 2: Technical Design

- [x] define tech_spec.md
- [x] define stories.md

## Phase 3: Foundation

- [ ] hello world — minimal runnable package with CLI entry point
- [ ] project structure — full package layout per tech_spec.md
- [ ] core models and options (Pydantic)
- [ ] configuration system (CLI flags, env vars, YAML config file)
- [ ] logging framework (console + structured JSONL)

## Phase 4: Core Services

- [ ] video ID parsing and validation
- [ ] metadata retrieval (yt-dlp backend)
- [ ] metadata retrieval (YouTube Data API v3 backend, optional)
- [ ] transcript fetching with language selection and fallbacks
- [ ] media download (video/audio via yt-dlp)

## Phase 5: Pipeline & Orchestration

- [ ] per-video pipeline (metadata → transcript → media → write outputs)
- [ ] output file writing (JSON, txt, VTT, SRT)
- [ ] caching / idempotency (skip existing, --force flags)
- [ ] batch processing with concurrency (--workers)
- [ ] error handling and retry with exponential backoff
- [ ] rate limiting (token bucket)
- [ ] summary reporting

## Phase 6: CLI & Library API

- [ ] CLI subcommands (fetch, transcript, metadata, media)
- [ ] library API (fetch_video, fetch_batch)

## Phase 7: Testing & Quality

- [ ] unit tests (ID parsing, transcript formatting, models)
- [ ] integration tests (guarded by env var)
- [ ] pipeline idempotency tests
- [ ] error handling tests

## Phase 8: Documentation & Release

- [ ] README.md
- [ ] usage examples
- [ ] installation guide
- [ ] final testing and refinement
