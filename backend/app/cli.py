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


@app.command("quiz-demo")
def quiz_demo() -> None:
    """Print six fixed quiz evaluation sets against the local catalog."""
    from app.db.session import AsyncSessionLocal
    from app.recs.engine import rebuild_index_from_db, recommend_from_quiz

    sets = [
        (
            "Dark psychological thrillers",
            {
                "mood": "tense",
                "pacing": "balanced",
                "tone": "dark",
                "themes": "mystery",
                "intensity": "intense",
                "length": "any",
                "era": "any",
            },
        ),
        (
            "Cozy slice of life",
            {
                "mood": "cozy",
                "pacing": "slow",
                "tone": "hopeful",
                "themes": "slice_of_life",
                "intensity": "chill",
                "length": "any",
                "era": "any",
            },
        ),
        (
            "Epic fantasy adventure",
            {
                "mood": "epic",
                "pacing": "fast",
                "tone": "hopeful",
                "themes": "fantasy",
                "intensity": "intense",
                "length": "long",
                "era": "any",
            },
        ),
        (
            "Romance and school life",
            {
                "mood": "emotional",
                "pacing": "balanced",
                "tone": "romantic",
                "themes": "slice_of_life",
                "intensity": "moderate",
                "length": "medium",
                "era": "any",
            },
        ),
        (
            "Action-packed shounen",
            {
                "mood": "epic",
                "pacing": "fast",
                "tone": "hopeful",
                "themes": "mystery",
                "intensity": "intense",
                "length": "long",
                "era": "any",
            },
        ),
        (
            "Sci-fi and mecha",
            {
                "mood": "epic",
                "pacing": "fast",
                "tone": "dark",
                "themes": "sci_fi",
                "intensity": "intense",
                "length": "medium",
                "era": "any",
            },
        ),
    ]

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            index = await rebuild_index_from_db(session)
            for i, (name, answers) in enumerate(sets, 1):
                typer.echo(f"\n## {i}. {name}\nChosen answer IDs: {answers}")
                for rank, result in enumerate(
                    recommend_from_quiz(
                        answers, n=10, include_mature=False, index=index
                    ),
                    1,
                ):
                    typer.echo(
                        f"{rank}. {result.title} | {result.year or 'N/A'} | {result.format or 'N/A'} | {', '.join(result.genres)} | {result.reason}"
                    )

    asyncio.run(_run())


@app.command("start-demo")
def start_demo(
    liked: Annotated[list[str] | None, typer.Option("--liked")] = None,
    quiz_set: Annotated[int | None, typer.Option("--quiz-set", min=1, max=6)] = None,
) -> None:
    """Print top 10 combined recommendations for title names."""
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.anime import Anime
    from app.recs.engine import rebuild_index_from_db, recommend_from_start

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            index = await rebuild_index_from_db(session)
            ids: list[int] = []
            for name in liked or []:
                found = await session.execute(
                    select(Anime)
                    .where(
                        (Anime.title_english.ilike(f"%{name}%"))
                        | (Anime.title_romaji.ilike(f"%{name}%"))
                    )
                    .order_by(Anime.popularity.desc())
                    .limit(1)
                )
                row = found.scalar_one_or_none()
                if row is None:
                    typer.echo(f"Title not found: {name}")
                    return
                ids.append(row.id)
            quiz = None
            if quiz_set:
                quiz = [
                    {
                        "mood": "tense",
                        "pacing": "balanced",
                        "tone": "dark",
                        "themes": "mystery",
                        "intensity": "intense",
                        "length": "any",
                        "era": "any",
                    },
                    {
                        "mood": "cozy",
                        "pacing": "slow",
                        "tone": "hopeful",
                        "themes": "slice_of_life",
                        "intensity": "chill",
                        "length": "any",
                        "era": "any",
                    },
                    {
                        "mood": "epic",
                        "pacing": "fast",
                        "tone": "hopeful",
                        "themes": "fantasy",
                        "intensity": "intense",
                        "length": "long",
                        "era": "any",
                    },
                    {
                        "mood": "emotional",
                        "pacing": "balanced",
                        "tone": "romantic",
                        "themes": "slice_of_life",
                        "intensity": "moderate",
                        "length": "medium",
                        "era": "any",
                    },
                    {
                        "mood": "epic",
                        "pacing": "fast",
                        "tone": "hopeful",
                        "themes": "mystery",
                        "intensity": "intense",
                        "length": "long",
                        "era": "any",
                    },
                    {
                        "mood": "epic",
                        "pacing": "fast",
                        "tone": "dark",
                        "themes": "sci_fi",
                        "intensity": "intense",
                        "length": "medium",
                        "era": "any",
                    },
                ][quiz_set - 1]
            typer.echo(
                f"Liked: {liked or []}; quiz-set={quiz_set}; scoring methods A and B"
            )
            for method in ("A", "B"):
                typer.echo(f"\nMethod {method}")
                for rank, result in enumerate(
                    recommend_from_start(
                        quiz,
                        ids,
                        n=10,
                        include_mature=False,
                        method=method,
                        index=index,
                    ),
                    1,
                ):
                    typer.echo(
                        f"{rank}. {result.title} | {result.year or 'N/A'} | {result.format or 'N/A'} | {', '.join(result.genres)} | {result.reason}"
                    )

    asyncio.run(_run())


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

            header = (
                f"{'#':<3} | {'PreMMR':<6} | {'Final':<6} | {'RawCos':<6} | {'Quality':<7} | "
                f"{'Title':<35} | {'Year':<5} | {'Fmt':<7} | {'Reason'}"
            )
            typer.echo(header)
            typer.echo("-" * 125)
            mmr_changes: list[str] = []
            for i, r in enumerate(results, 1):
                t_name = (r.title_english or r.title_romaji or "Unknown")[:33]
                year_str = str(r.year) if r.year else "N/A"
                fmt_str = (r.format or "N/A")[:7]
                final_str = (
                    f"{r.final_score:.4f}"
                    if r.final_score is not None
                    else f"{r.similarity:.4f}"
                )
                pre_mmr_str = (
                    f"#{r.pre_mmr_rank}" if r.pre_mmr_rank is not None else "N/A"
                )
                raw_cos_str = (
                    f"{r.raw_cosine:.4f}" if r.raw_cosine is not None else "N/A"
                )
                quality_str = (
                    f"{r.quality_score:.4f}" if r.quality_score is not None else "N/A"
                )

                mmr_note = ""
                if r.pre_mmr_rank is not None and r.pre_mmr_rank != i:
                    mmr_note = f" [MMR: #{r.pre_mmr_rank}→#{i}]"
                    mmr_changes.append(
                        f"'{t_name}' moved from pre-MMR #{r.pre_mmr_rank} to #{i}"
                    )

                reason_str = r.reason or "(no reason)"
                typer.echo(
                    f"{i:<3} | {pre_mmr_str:<6} | {final_str:<6} | {raw_cos_str:<6} | {quality_str:<7} | "
                    f"{t_name:<35} | {year_str:<5} | {fmt_str:<7} | {reason_str}{mmr_note}"
                )

            typer.echo("-" * 125)
            if mmr_changes:
                typer.echo(
                    f"🔄 MMR Diversity adjustments ({len(mmr_changes)} reordered):"
                )
                for change in mmr_changes:
                    typer.echo(f"   • {change}")
            else:
                typer.echo(
                    "🔄 MMR Diversity: top candidates selected in original score order without position changes."
                )

    asyncio.run(_run())


@app.command("explain-pair")
def explain_pair(
    id_a: Annotated[
        int,
        typer.Argument(help="First anime AniList ID."),
    ],
    id_b: Annotated[
        int,
        typer.Argument(help="Second anime AniList ID."),
    ],
    top_k: Annotated[
        int,
        typer.Option(
            "--top-k",
            "-k",
            help="Number of top contributing features to show.",
            min=1,
            max=50,
        ),
    ] = 10,
) -> None:
    """Show the top-k contributing features (query × item weighted dot-product) for a pair.

    Useful for diagnosing spurious high-similarity pairs, e.g.:
      animatch-cli explain-pair 21459 98478  # Fate/Zero vs Laid-Back Camp
    """
    from app.db.session import AsyncSessionLocal
    from app.recs.engine import explain_pair_debug, rebuild_index_from_db

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            index = await rebuild_index_from_db(session)
            if index.is_empty():
                typer.echo("❌ Catalog index is empty. Please run sync-catalog first.")
                return

            rows, cosine, title_a, title_b = explain_pair_debug(
                id_a, id_b, index, top_k
            )
            if not rows:
                typer.echo(f"❌ One or both IDs not found in catalog: {id_a}, {id_b}")
                return

            typer.echo(
                f"\n🔍 Feature contributions: {title_a!r} (id={id_a}) vs {title_b!r} (id={id_b})"
            )
            typer.echo(f"   Raw cosine similarity: {cosine:.4f}\n")
            header = f"{'#':<3} | {'Block':<7} | {'Feature':<35} | {'Contrib':>8} | {'A-weight':>9} | {'B-weight':>9}"
            typer.echo(header)
            typer.echo("-" * 80)
            for i, row in enumerate(rows, 1):
                typer.echo(
                    f"{i:<3} | {row['block']:<7} | {row['feature']:<35} | "
                    f"{row['contrib']:>8.5f} | {row['q_val']:>9.5f} | {row['i_val']:>9.5f}"
                )
            typer.echo("-" * 80)

    asyncio.run(_run())


if __name__ == "__main__":
    app()
