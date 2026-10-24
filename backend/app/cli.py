"""AniMatch CLI application for administrative and seeding commands."""

import asyncio
import logging
from datetime import datetime
from typing import Annotated

import typer

from app.core.config import setup_logging
from app.services.anilist import AniListClient
from app.services.catalog_sync import CatalogSyncService

app = typer.Typer(
    name="animatch-cli",
    help="AniMatch Command Line Interface",
    add_completion=False,
)

logger = logging.getLogger(__name__)


@app.callback()
def main_callback() -> None:
    """AniMatch CLI administrative tool."""
    pass


def parse_since(since_val: str | None) -> int | None:
    """Parses a timestamp integer or ISO format date string into unix epoch."""
    if not since_val:
        return None
    try:
        return int(since_val)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(since_val)
        return int(dt.timestamp())
    except Exception as err:
        raise typer.BadParameter(
            f"Invalid --since value '{since_val}'. Expected epoch integer or ISO date string."
        ) from err


@app.command("sync-catalog")
def sync_catalog(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of titles to fetch and sync (default 1000, up to 5000).",
            min=1,
            max=5000,
        ),
    ] = 1000,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            "-s",
            help="Incremental sync filter: epoch timestamp or ISO 8601 date string.",
        ),
    ] = None,
    batch_size: Annotated[
        int,
        typer.Option(
            "--batch-size",
            "-b",
            help="Number of media items per page request.",
            min=1,
            max=50,
        ),
    ] = 50,
    rate: Annotated[
        int,
        typer.Option(
            "--rate",
            "-r",
            help="Max AniList requests per minute budget.",
            min=1,
            max=90,
        ),
    ] = 80,
    reset: Annotated[
        bool,
        typer.Option(
            "--reset",
            help="Discard saved resume checkpoint and start sync from page 1.",
        ),
    ] = False,
) -> None:
    """Syncs anime catalog from AniList into the local database."""
    setup_logging()
    since_epoch = parse_since(since)

    typer.echo(
        f"🚀 Initiating catalog sync: limit={limit}, since={since_epoch}, rate={rate}/min, reset={reset}"
    )

    async def _run() -> None:
        async with AniListClient(requests_per_minute=rate) as client:
            service = CatalogSyncService(client=client)
            result = await service.sync_catalog(
                limit=limit,
                since=since_epoch,
                batch_size=batch_size,
                reset=reset,
            )
            typer.echo(
                f"✅ Catalog sync completed successfully: "
                f"Total={result['total_synced']} "
                f"(SFW={result['sfw_synced']}, Adult={result['adult_synced']})"
            )

    asyncio.run(_run())


if __name__ == "__main__":
    app()
