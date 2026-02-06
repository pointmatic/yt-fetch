"""CLI entry point for yt-fetch."""

from __future__ import annotations

from pathlib import Path

import click

from yt_fetch import __version__
from yt_fetch.core.options import FetchOptions


def _common_options(fn):
    """Shared Click options that map to FetchOptions fields."""
    decorators = [
        click.option("--out", type=click.Path(path_type=Path), default=None, help="Output directory."),
        click.option("--languages", type=str, default=None, help="Comma-separated language codes."),
        click.option("--allow-generated/--no-allow-generated", default=None, help="Allow auto-generated transcripts."),
        click.option("--allow-any-language/--no-allow-any-language", default=None, help="Fall back to any language."),
        click.option("--download", type=click.Choice(["none", "video", "audio", "both"]), default=None, help="Media download mode."),
        click.option("--max-height", type=int, default=None, help="Max video height (e.g. 720)."),
        click.option("--format", "format_", type=str, default=None, help="Video format."),
        click.option("--audio-format", type=str, default=None, help="Audio format."),
        click.option("--force", is_flag=True, default=None, help="Force re-fetch everything."),
        click.option("--force-metadata", is_flag=True, default=None, help="Force re-fetch metadata."),
        click.option("--force-transcript", is_flag=True, default=None, help="Force re-fetch transcript."),
        click.option("--force-media", is_flag=True, default=None, help="Force re-download media."),
        click.option("--retries", type=int, default=None, help="Max retries per request."),
        click.option("--rate-limit", type=float, default=None, help="Requests per second."),
        click.option("--workers", type=int, default=None, help="Parallel workers for batch."),
        click.option("--fail-fast", is_flag=True, default=None, help="Stop on first failure."),
        click.option("--verbose", is_flag=True, default=None, help="Verbose console output."),
    ]
    for decorator in reversed(decorators):
        fn = decorator(fn)
    return fn


def _build_options(**cli_kwargs) -> FetchOptions:
    """Build FetchOptions from CLI kwargs, filtering out unset (None) values.

    Only explicitly-provided CLI flags are passed to FetchOptions as init
    overrides. Unset flags fall through to env vars → YAML → defaults.
    """
    overrides = {}
    for key, value in cli_kwargs.items():
        if value is None:
            continue
        if key == "format_":
            overrides["format"] = value
        elif key == "languages":
            overrides["languages"] = [lang.strip() for lang in value.split(",")]
        else:
            overrides[key] = value
    return FetchOptions(**overrides)


@click.group()
@click.version_option(version=__version__, prog_name="yt_fetch")
def cli() -> None:
    """YouTube video metadata, transcript, and media fetcher."""


@cli.command()
@click.option("--id", "ids", multiple=True, help="YouTube video ID or URL (repeatable).")
@click.option("--file", "file_path", type=click.Path(exists=True, path_type=Path), default=None, help="Text file with one ID per line.")
@click.option("--jsonl", "jsonl_path", type=click.Path(exists=True, path_type=Path), default=None, help="JSONL file with video IDs.")
@click.option("--id-field", default="id", help="Field name for video ID in JSONL input.")
@_common_options
def fetch(ids, file_path, jsonl_path, id_field, **kwargs):
    """Fetch metadata, transcripts, and optionally media."""
    options = _build_options(**kwargs)
    click.echo(f"Options resolved: out={options.out}, workers={options.workers}, verbose={options.verbose}")


@cli.command()
@click.option("--id", "ids", multiple=True, help="YouTube video ID or URL (repeatable).")
@click.option("--file", "file_path", type=click.Path(exists=True, path_type=Path), default=None, help="Text file with one ID per line.")
@_common_options
def transcript(ids, file_path, **kwargs):
    """Fetch transcripts only."""
    options = _build_options(**kwargs)
    click.echo(f"Options resolved: out={options.out}, verbose={options.verbose}")


@cli.command()
@click.option("--id", "ids", multiple=True, help="YouTube video ID or URL (repeatable).")
@click.option("--file", "file_path", type=click.Path(exists=True, path_type=Path), default=None, help="Text file with one ID per line.")
@_common_options
def metadata(ids, file_path, **kwargs):
    """Fetch metadata only."""
    options = _build_options(**kwargs)
    click.echo(f"Options resolved: out={options.out}, verbose={options.verbose}")


@cli.command()
@click.option("--id", "ids", multiple=True, help="YouTube video ID or URL (repeatable).")
@click.option("--file", "file_path", type=click.Path(exists=True, path_type=Path), default=None, help="Text file with one ID per line.")
@_common_options
def media(ids, file_path, **kwargs):
    """Download media only."""
    options = _build_options(**kwargs)
    click.echo(f"Options resolved: out={options.out}, download={options.download}, verbose={options.verbose}")


if __name__ == "__main__":
    cli()
