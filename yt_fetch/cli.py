"""CLI entry point for yt-fetch."""

import click

from yt_fetch import __version__


@click.group()
@click.version_option(version=__version__, prog_name="yt_fetch")
def cli() -> None:
    """YouTube video metadata, transcript, and media fetcher."""


if __name__ == "__main__":
    cli()
