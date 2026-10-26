"""Catalog synchronization service for AniList anime catalog."""

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import bindparam, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.anime import (
    Anime,
    Genre,
    Tag,
    anime_genres,
    anime_relations,
    anime_tags,
)
from app.services.anilist import AniListClient

logger = logging.getLogger(__name__)

STATE_FILE_PATH = Path(__file__).resolve().parent.parent.parent / ".sync_state.json"

# ---------------------------------------------------------------------------
# Relation types that form a franchise (shared content universe).
# All other types (ADAPTATION, CHARACTER, SUMMARY, OTHER) link across different
# media types or are too loosely related to group together.
# ---------------------------------------------------------------------------
FRANCHISE_RELATION_TYPES = frozenset(
    {"PREQUEL", "SEQUEL", "PARENT", "SIDE_STORY", "SPIN_OFF", "ALTERNATIVE"}
)


# ---------------------------------------------------------------------------
# Union-Find (disjoint-set) for connected-component franchise grouping.
# Works over all node IDs in the edge list, including those not in the catalog.
# ---------------------------------------------------------------------------
class UnionFind:
    """Path-compressed, union-by-rank disjoint-set structure."""

    def __init__(self) -> None:
        self.parent: dict[int, int] = {}
        self.rank: dict[int, int] = {}

    def find(self, x: int) -> int:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


class CatalogSyncService:
    """Orchestrates syncing catalog from AniList into SQLite/PostgreSQL."""

    def __init__(
        self,
        client: AniListClient | None = None,
        state_file: Path = STATE_FILE_PATH,
    ) -> None:
        self.client = client or AniListClient()
        self.state_file = state_file

    def load_state(self) -> dict[str, Any] | None:
        """Loads sync resume state from backend/.sync_state.json if it exists."""
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as err:
            logger.warning("Failed to read sync state file: %s", err)
            return None

    def save_state(self, state: dict[str, Any]) -> None:
        """Saves sync state to backend/.sync_state.json."""
        state["last_updated"] = datetime.now(UTC).isoformat()
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as err:
            logger.warning("Failed to save sync state file: %s", err)

    def clear_state(self) -> None:
        """Removes the sync state file."""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except Exception as err:
                logger.warning("Failed to delete sync state file: %s", err)

    async def upsert_batch(
        self, session: AsyncSession, media_items: list[dict[str, Any]]
    ) -> int:
        """Idempotent upsert of anime items with genre/tag/relation links.

        Strategy:
        1. Query or create Genre and Tag master records.
        2. Fetch existing Anime by ID; update existing or insert new.
        3. Replace anime_genres, anime_tags, and anime_relations associations.
        4. Relations include all edge types to all ANIME-type nodes, even those
           not (yet) in the catalog.
        """
        if not media_items:
            return 0

        # 1. Resolve / Upsert Genres
        all_genre_names = {g for item in media_items for g in item.get("genres", [])}
        genre_map: dict[str, int] = {}
        if all_genre_names:
            stmt = select(Genre).where(Genre.name.in_(all_genre_names))
            res = await session.execute(stmt)
            existing_genres = res.scalars().all()
            for g in existing_genres:
                genre_map[g.name] = g.id

            for name in all_genre_names:
                if name not in genre_map:
                    new_g = Genre(name=name)
                    session.add(new_g)
                    await session.flush()
                    genre_map[name] = new_g.id

        # 2. Resolve / Upsert Tags
        all_tag_items = {
            t["name"]: t for item in media_items for t in item.get("tags", [])
        }
        tag_map: dict[str, int] = {}
        if all_tag_items:
            stmt = select(Tag).where(Tag.name.in_(list(all_tag_items.keys())))
            res = await session.execute(stmt)
            existing_tags = res.scalars().all()
            for t in existing_tags:
                tag_map[t.name] = t.id
                meta = all_tag_items[t.name]
                if meta.get("category") and t.category != meta["category"]:
                    t.category = meta["category"]
                if t.is_adult != meta.get("is_adult", False):
                    t.is_adult = meta.get("is_adult", False)

            for name, meta in all_tag_items.items():
                if name not in tag_map:
                    new_t = Tag(
                        name=name,
                        category=meta.get("category"),
                        is_adult=meta.get("is_adult", False),
                    )
                    session.add(new_t)
                    await session.flush()
                    tag_map[name] = new_t.id

        # 3. Upsert Anime items
        anime_ids = [m["id"] for m in media_items]
        stmt = select(Anime).where(Anime.id.in_(anime_ids))
        res = await session.execute(stmt)
        existing_animes = {a.id: a for a in res.scalars().all()}

        new_genre_links: list[dict[str, int]] = []
        new_tag_links: list[dict[str, Any]] = []
        new_relation_links: list[dict[str, Any]] = []

        for m in media_items:
            aid = m["id"]
            if aid in existing_animes:
                anime_obj = existing_animes[aid]
                anime_obj.id_mal = m.get("id_mal")
                anime_obj.title_romaji = m.get("title_romaji")
                anime_obj.title_english = m.get("title_english")
                anime_obj.title_native = m.get("title_native")
                anime_obj.synonyms = m.get("synonyms") or []
                anime_obj.description = m.get("description")
                anime_obj.cover_image_url = m.get("cover_image_url")
                anime_obj.banner_image_url = m.get("banner_image_url")
                anime_obj.format = m.get("format")
                anime_obj.episodes = m.get("episodes")
                anime_obj.duration = m.get("duration")
                anime_obj.status = m.get("status")
                anime_obj.season = m.get("season")
                anime_obj.season_year = m.get("season_year")
                anime_obj.average_score = m.get("average_score")
                anime_obj.popularity = m.get("popularity") or 0
                anime_obj.is_adult = m.get("is_adult", False)
                anime_obj.source = m.get("source")
                anime_obj.main_studio = m.get("main_studio")
                anime_obj.updated_at_anilist = m.get("updated_at_anilist")
            else:
                anime_obj = Anime(
                    id=aid,
                    id_mal=m.get("id_mal"),
                    title_romaji=m.get("title_romaji"),
                    title_english=m.get("title_english"),
                    title_native=m.get("title_native"),
                    synonyms=m.get("synonyms") or [],
                    description=m.get("description"),
                    cover_image_url=m.get("cover_image_url"),
                    banner_image_url=m.get("banner_image_url"),
                    format=m.get("format"),
                    episodes=m.get("episodes"),
                    duration=m.get("duration"),
                    status=m.get("status"),
                    season=m.get("season"),
                    season_year=m.get("season_year"),
                    average_score=m.get("average_score"),
                    popularity=m.get("popularity") or 0,
                    is_adult=m.get("is_adult", False),
                    source=m.get("source"),
                    main_studio=m.get("main_studio"),
                    updated_at_anilist=m.get("updated_at_anilist"),
                )
                session.add(anime_obj)

            for gname in m.get("genres", []):
                gid = genre_map.get(gname)
                if gid:
                    new_genre_links.append({"anime_id": aid, "genre_id": gid})

            for t_item in m.get("tags", []):
                tid = tag_map.get(t_item["name"])
                if tid:
                    new_tag_links.append(
                        {
                            "anime_id": aid,
                            "tag_id": tid,
                            "rank": t_item.get("rank", 0),
                        }
                    )

            # Relation edges — stored for ALL relation types, including edges to
            # nodes not in the catalog (no FK constraint on related_id).
            for rel in m.get("relations", []):
                related_id = rel.get("related_id")
                rel_type = rel.get("rel_type") or "OTHER"
                if related_id and related_id != aid:
                    new_relation_links.append(
                        {
                            "anime_id": aid,
                            "related_id": related_id,
                            "rel_type": rel_type,
                        }
                    )

        await session.flush()

        # Replace association links (idempotent)
        await session.execute(
            delete(anime_genres).where(anime_genres.c.anime_id.in_(anime_ids))
        )
        await session.execute(
            delete(anime_tags).where(anime_tags.c.anime_id.in_(anime_ids))
        )
        # Replace relation edges for this batch
        await session.execute(
            delete(anime_relations).where(anime_relations.c.anime_id.in_(anime_ids))
        )

        if new_genre_links:
            unique_genre_links = {
                (link["anime_id"], link["genre_id"]): link for link in new_genre_links
            }.values()
            await session.execute(insert(anime_genres).values(list(unique_genre_links)))

        if new_tag_links:
            unique_tag_links = {
                (link["anime_id"], link["tag_id"]): link for link in new_tag_links
            }.values()
            await session.execute(insert(anime_tags).values(list(unique_tag_links)))

        if new_relation_links:
            # Deduplicate by (anime_id, related_id) pair
            unique_rel_links = {
                (r["anime_id"], r["related_id"]): r for r in new_relation_links
            }.values()
            await session.execute(
                insert(anime_relations).values(list(unique_rel_links))
            )

        await session.commit()
        session.expire_all()
        return len(media_items)

    async def compute_franchise_ids(self, session: AsyncSession) -> dict[str, Any]:
        """Runs Union-Find over ALL relation edges to assign franchise_id to every
        catalog anime that shares at least one franchise-forming relation with another
        ANIME node (in catalog or not).

        franchise_id = minimum AniList id in the connected component.

        This is idempotent: re-running overwrites previous assignments.

        Returns a summary dict with the five largest franchises and the count of
        catalog titles that share a franchise with at least one other catalog title.
        """
        # Load all franchise-forming edges from the relation table
        rel_rows = await session.execute(
            select(
                anime_relations.c.anime_id,
                anime_relations.c.related_id,
            ).where(anime_relations.c.rel_type.in_(list(FRANCHISE_RELATION_TYPES)))
        )
        edges = rel_rows.fetchall()

        if not edges:
            logger.info(
                "No franchise relation edges found; skipping franchise_id pass."
            )
            return {"titles_with_shared_franchise": 0, "largest_franchises": []}

        # Build Union-Find over all nodes (both endpoints of every edge)
        uf = UnionFind()
        for anime_id, related_id in edges:
            uf.union(anime_id, related_id)

        # Load all catalog anime IDs
        catalog_ids_res = await session.execute(select(Anime.id))
        catalog_ids: list[int] = list(catalog_ids_res.scalars().all())

        # Map each catalog anime to its component root (= franchise_id)
        # Items with no relation edges get franchise_id = NULL
        anime_in_uf = set(uf.parent.keys())
        updates: list[dict[str, Any]] = []
        for aid in catalog_ids:
            if aid in anime_in_uf:
                root = uf.find(aid)
                updates.append({"_id": aid, "franchise_id": root})
            else:
                updates.append({"_id": aid, "franchise_id": None})

        # Bulk update franchise_id on all catalog items
        if updates:
            await session.execute(
                update(Anime.__table__)
                .where(Anime.__table__.c.id == bindparam("_id"))
                .values(franchise_id=bindparam("franchise_id")),
                updates,
            )
            await session.commit()

        # --- Franchise report ---
        # Count catalog titles whose franchise_id appears more than once in catalog
        fid_to_ids: dict[int, list[int]] = defaultdict(list)
        for u in updates:
            fid = u["franchise_id"]
            if fid is not None:
                fid_to_ids[fid].append(u["_id"])

        shared_fids = {fid: ids for fid, ids in fid_to_ids.items() if len(ids) > 1}
        titles_with_shared = sum(len(v) for v in shared_fids.values())

        # Five largest by catalog-member count
        top5 = sorted(shared_fids.items(), key=lambda kv: -len(kv[1]))[:5]

        # Fetch a display title for each root franchise_id
        top5_info = []
        for fid, members in top5:
            root_res = await session.execute(
                select(Anime.title_english, Anime.title_romaji).where(Anime.id == fid)
            )
            row = root_res.one_or_none()
            if row:
                title = row[0] or row[1] or f"AniList#{fid}"
            else:
                title = f"AniList#{fid} (outside catalog)"
            top5_info.append(
                {
                    "franchise_id": fid,
                    "catalog_count": len(members),
                    "root_title": title,
                }
            )

        summary = {
            "titles_with_shared_franchise": titles_with_shared,
            "largest_franchises": top5_info,
        }
        return summary

    async def sync_catalog(
        self,
        limit: int = 1000,
        since: int | None = None,
        sort: str = "POPULARITY_DESC",
        batch_size: int = 50,
        reset: bool = False,
        adult_ratio: float = 0.05,
    ) -> dict[str, Any]:
        """Runs the catalog sync from AniList with resume and idempotency.

        Includes adult titles proportional to limit (default ~5%).
        After the sync, runs the franchise connected-component pass and prints
        a franchise summary.
        """
        if reset:
            self.clear_state()

        adult_target = max(2, int(limit * adult_ratio)) if limit >= 20 else 1
        sfw_target = max(1, limit - adult_target)

        state = self.load_state() or {}
        params_matched = (
            state.get("limit") == limit
            and state.get("since") == since
            and state.get("sort") == sort
        )

        if not params_matched or state.get("is_complete"):
            state = {
                "limit": limit,
                "since": since,
                "sort": sort,
                "batch_size": batch_size,
                "adult_target": adult_target,
                "sfw_target": sfw_target,
                "sfw_page": 1,
                "adult_page": 1,
                "sfw_synced": 0,
                "adult_synced": 0,
                "total_synced": 0,
                "is_complete": False,
            }

        total_synced = state.get("total_synced", 0)
        sfw_synced = state.get("sfw_synced", 0)
        adult_synced = state.get("adult_synced", 0)
        sfw_page = state.get("sfw_page", 1)
        adult_page = state.get("adult_page", 1)

        logger.info(
            "Starting catalog sync: limit=%d (sfw=%d, adult=%d), resume at sfw_page=%d, adult_page=%d",
            limit,
            sfw_target,
            adult_target,
            sfw_page,
            adult_page,
        )

        async with AsyncSessionLocal() as session:
            # 1. Sync SFW stream
            while sfw_synced < sfw_target:
                per_page = min(batch_size, sfw_target - sfw_synced)
                items, page_info = await self.client.fetch_media_page(
                    page=sfw_page,
                    per_page=per_page,
                    sort=sort,
                    is_adult=False,
                    updated_at_greater=since,
                )

                if not items:
                    logger.info("No more SFW items available at page %d", sfw_page)
                    break

                count = await self.upsert_batch(session, items)
                sfw_synced += count
                total_synced += count
                sfw_page += 1

                state.update(
                    {
                        "sfw_page": sfw_page,
                        "sfw_synced": sfw_synced,
                        "total_synced": total_synced,
                    }
                )
                self.save_state(state)
                logger.info(
                    "SFW synced: %d/%d (page %d)", sfw_synced, sfw_target, sfw_page - 1
                )

                if not page_info.get("hasNextPage"):
                    break

            # 2. Sync Adult stream
            while adult_synced < adult_target:
                per_page = min(batch_size, adult_target - adult_synced)
                items, page_info = await self.client.fetch_media_page(
                    page=adult_page,
                    per_page=per_page,
                    sort=sort,
                    is_adult=True,
                    updated_at_greater=since,
                )

                if not items:
                    logger.info("No more adult items available at page %d", adult_page)
                    break

                count = await self.upsert_batch(session, items)
                adult_synced += count
                total_synced += count
                adult_page += 1

                state.update(
                    {
                        "adult_page": adult_page,
                        "adult_synced": adult_synced,
                        "total_synced": total_synced,
                    }
                )
                self.save_state(state)
                logger.info(
                    "Adult synced: %d/%d (page %d)",
                    adult_synced,
                    adult_target,
                    adult_page - 1,
                )

                if not page_info.get("hasNextPage"):
                    break

            # 3. Franchise connected-component pass
            logger.info("Running franchise connected-component pass…")
            franchise_summary = await self.compute_franchise_ids(session)

        state["is_complete"] = True
        self.save_state(state)
        logger.info(
            "Sync complete. Total: %d titles (sfw=%d, adult=%d)",
            total_synced,
            sfw_synced,
            adult_synced,
        )

        return {
            "total_synced": total_synced,
            "sfw_synced": sfw_synced,
            "adult_synced": adult_synced,
            "is_complete": True,
            "franchise_summary": franchise_summary,
        }
