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
            franchise_summary = result.get("franchise_summary")
            if franchise_summary:
                typer.echo("\nFranchise summary:")
                typer.echo(
                    f"  Titles with shared franchise: {franchise_summary['titles_with_shared_franchise']}"
                )
                typer.echo("  Five largest franchises:")
                for f in franchise_summary.get("largest_franchises", []):
                    typer.echo(
                        f"    franchise_id={f['franchise_id']}: {f['catalog_count']} catalog titles (root title: {f['root_title']})"
                    )

    asyncio.run(_run())


@app.command("recs-demo")
def recs_demo(
    title: Annotated[
        str,
        typer.Argument(
            help="Anime title keyword to search for seed anime.",
        ),
    ] = "",
    seed_id: Annotated[
        int | None,
        typer.Option(
            "--seed-id",
            help="Direct seed anime ID (bypasses title keyword lookup).",
        ),
    ] = None,
    n: Annotated[
        int,
        typer.Option(
            "--n",
            "-n",
            help="Number of recommendations to return (default 10).",
            min=1,
            max=50,
        ),
    ] = 10,
    include_mature: Annotated[
        bool,
        typer.Option(
            "--include-mature",
            help="Include adult / 18+ titles in recommendations.",
        ),
    ] = False,
) -> None:
    """Demonstrates recommendation engine outputs for a given title or seed ID."""
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.anime import Anime
    from app.recs.engine import rebuild_index_from_db, recommend_similar

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            # 1. Build index from DB
            index = await rebuild_index_from_db(session)
            if index.is_empty():
                typer.echo("❌ Catalog index is empty. Please run sync-catalog first.")
                return

            target_anime: Anime | None = None
            if seed_id is not None:
                res = await session.execute(select(Anime).where(Anime.id == seed_id))
                target_anime = res.scalar_one_or_none()
                if not target_anime:
                    typer.echo(f"❌ Anime with id={seed_id} not found in catalog.")
                    return
            else:
                if not title.strip():
                    typer.echo("❌ Either title or --seed-id must be provided.")
                    return
                # Search by title (treating apostrophes flexibly)
                clean_title = title.strip().replace("'", "%").replace("’", "%")
                pattern = f"%{clean_title}%"
                res = await session.execute(
                    select(Anime)
                    .where(
                        (Anime.title_english.ilike(pattern))
                        | (Anime.title_romaji.ilike(pattern))
                    )
                    .order_by(Anime.popularity.desc())
                    .limit(1)
                )
                target_anime = res.scalar_one_or_none()
                if not target_anime:
                    typer.echo(f"❌ No anime matching '{title}' found in catalog.")
                    return

            display_title = (
                target_anime.title_english
                or target_anime.title_romaji
                or f"ID#{target_anime.id}"
            )
            typer.echo(
                f"\n🎯 Matched Seed: {display_title} (id={target_anime.id}, franchise_id={target_anime.franchise_id})"
            )
            typer.echo(
                f"📋 Requesting top-{n} recommendations (include_mature={include_mature})...\n"
            )

            results = recommend_similar(
                anime_id=target_anime.id,
                n=n,
                include_mature=include_mature,
                index=index,
            )

            if not results:
                typer.echo("⚠️ No recommendations found.")
                return

            header = f"{'#':<3} | {'Sim':<6} | {'Title':<40} | {'Year':<6} | {'Genres':<25} | {'Reason'}"
            typer.echo(header)
            typer.echo("-" * len(header))
            for i, r in enumerate(results, 1):
                t_name = (r.title_english or r.title_romaji or "Unknown")[:38]
                year_str = str(r.year) if r.year else "N/A"
                genres_str = ", ".join(r.genres[:3])[:23]
                typer.echo(
                    f"{i:<3} | {r.similarity:<6.3f} | {t_name:<40} | {year_str:<6} | {genres_str:<25} | {r.reason}"
                )

    asyncio.run(_run())


if __name__ == "__main__":
    app()
