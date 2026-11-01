"""AniMatch CLI application for administrative and seeding commands."""

import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Annotated, Any

import typer

from app.core.config import setup_logging
from app.services.anilist import AniListClient
from app.services.catalog_sync import CatalogSyncService

app = typer.Typer(
    name="animatch-cli",
    help="AniMatch Command Line Interface",
    add_completion=False,
)


def _report_title_not_found(title: str, suggestions: list[Any]) -> None:
    typer.echo(f"Title not found: {title}")
    if not suggestions:
        typer.echo("No close catalog matches found.")
        return
    typer.echo("Closest matches:")
    for anime in suggestions:
        candidate = (
            anime.title_english or anime.title_romaji or anime.title_native or "Unknown"
        )
        typer.echo(f"  {candidate} (id={anime.id})")


def _format_catalog_vocab(genres: list[str], tags: list[tuple[str, int]]) -> str:
    """Format the catalog vocabulary report for both stdout and Markdown."""
    lines = ["# Catalog vocabulary", "", "## Genres"]
    lines.extend(f"- {genre}" for genre in genres)
    lines.extend(["", "## Top 250 non-adult, non-spoiler tags by title count"])
    lines.extend(f"- {name}: {count} titles" for name, count in tags)
    return "\n".join(lines) + "\n"


@app.command("quiz-demo")
def quiz_demo() -> None:
    """Print six fixed quiz evaluation sets against the local catalog."""
    from app.db.session import AsyncSessionLocal
    from app.recs.engine import rebuild_index_from_db, recommend_from_quiz

    def progress(message: str) -> None:
        typer.echo(message)
        sys.stdout.flush()

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
                "themes": "action",
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
            progress("Building recommendation index from the local catalog...")
            started = time.perf_counter()
            try:
                index = await rebuild_index_from_db(session)
            except Exception as err:
                progress(f"quiz-demo failed while building the catalog index: {err}")
                raise
            elapsed = time.perf_counter() - started
            progress(f"Catalog index ready in {elapsed:.1f}s.")
            if elapsed >= 10:
                progress(f"Slow catalog index build: took {elapsed:.1f}s.")
            for i, (name, answers) in enumerate(sets, 1):
                started = time.perf_counter()
                progress(f"\nStarting quiz set {i}/6: {name}; answers={answers}")
                try:
                    results = recommend_from_quiz(
                        answers, n=10, include_mature=False, index=index
                    )
                    for rank, result in enumerate(results, 1):
                        typer.echo(
                            f"{rank}. {result.title} | {result.year or 'N/A'} | {result.episodes or 'N/A'} eps | {result.format or 'N/A'} | {', '.join(result.genres)} | {result.reason}"
                        )
                    elapsed = time.perf_counter() - started
                    progress(
                        f"Finished quiz set {i}/6 in {elapsed:.1f}s ({len(results)} results)."
                    )
                    if elapsed >= 10:
                        progress(f"Slow quiz set {i}/6: {name} took {elapsed:.1f}s.")
                except Exception as err:
                    elapsed = time.perf_counter() - started
                    progress(
                        f"quiz-demo failed on quiz set {i}/6 ({name}) after {elapsed:.1f}s: {err}"
                    )

    asyncio.run(_run())


@app.command("quiz-vocab-check")
def quiz_vocab_check() -> None:
    """Report quiz vocabulary names missing from the local genre/tag tables."""
    from difflib import get_close_matches

    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.anime import Genre, Tag
    from app.recs.quiz import load_quiz_data

    quiz = load_quiz_data()

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            genres = set((await session.execute(select(Genre.name))).scalars().all())
            tags = set((await session.execute(select(Tag.name))).scalars().all())
            known = {"genres": genres, "tags": tags}
            known_folded = {
                category: {name.casefold(): name for name in names}
                for category, names in known.items()
            }
            for question in quiz.get("questions", []):
                for answer in question.get("answers", []):
                    typer.echo(
                        f"{question['id']} / {answer['id']} ({answer.get('label', answer['id'])})"
                    )
                    weights = answer.get("weights") or {}
                    missing_count = 0
                    for category in ("genres", "tags"):
                        for name in weights.get(category) or {}:
                            if name.casefold() in known_folded[category]:
                                continue
                            missing_count += 1
                            closest = get_close_matches(
                                name,
                                sorted(known[category]),
                                n=3,
                                cutoff=0.25,
                            )
                            suggestion = (
                                ", ".join(closest) if closest else "no close match"
                            )
                            typer.echo(
                                f"  unknown {category[:-1]} '{name}'; closest: {suggestion}"
                            )
                    if not missing_count:
                        typer.echo("  no unknown genres or tags")

    asyncio.run(_run())


@app.command("catalog-vocab")
def catalog_vocab() -> None:
    """Print and save catalog genres and the most-used eligible tags."""
    from pathlib import Path

    from sqlalchemy import func, select

    from app.db.session import AsyncSessionLocal
    from app.models.anime import Anime, Genre, Tag, anime_tags

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            genres = list(
                (
                    await session.execute(select(Genre.name).order_by(Genre.name.asc()))
                ).scalars()
            )
            title_count = func.count(func.distinct(anime_tags.c.anime_id))
            tag_rows = await session.execute(
                select(Tag.name, title_count.label("title_count"))
                .join(anime_tags, anime_tags.c.tag_id == Tag.id)
                .join(Anime, Anime.id == anime_tags.c.anime_id)
                .where(
                    Tag.is_adult.is_(False),
                    Anime.is_adult.is_(False),
                    anime_tags.c.is_spoiler.is_(False),
                )
                .group_by(Tag.id, Tag.name)
                .order_by(title_count.desc(), Tag.name.asc())
                .limit(250)
            )
            output = _format_catalog_vocab(
                genres, [(name, count) for name, count in tag_rows.all()]
            )
            typer.echo(output, nl=False)
            docs_path = (
                Path(__file__).resolve().parents[2] / "docs" / "catalog-vocab.md"
            )
            docs_path.write_text(output, encoding="utf-8")

    asyncio.run(_run())


@app.command("start-demo")
def start_demo(
    liked: Annotated[list[str] | None, typer.Option("--liked")] = None,
    quiz_set: Annotated[int | None, typer.Option("--quiz-set", min=1, max=6)] = None,
) -> None:
    """Print top 10 combined recommendations for title names."""
    from app.db.session import AsyncSessionLocal
    from app.recs.engine import rebuild_index_from_db, recommend_from_start
    from app.services.title_search import closest_title_matches, find_title_matches

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            index = await rebuild_index_from_db(session)
            ids: list[int] = []
            for name in liked or []:
                matches = await find_title_matches(session, name, limit=1)
                if not matches:
                    suggestions = await closest_title_matches(session, name, limit=5)
                    _report_title_not_found(name, suggestions)
                    return
                row = matches[0]
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
                        "themes": "action",
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
    from app.services.title_search import closest_title_matches, find_title_matches

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
                matches = await find_title_matches(session, title, limit=1)
                target_anime = matches[0] if matches else None
                if not target_anime:
                    suggestions = await closest_title_matches(session, title, limit=5)
                    _report_title_not_found(title, suggestions)
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
