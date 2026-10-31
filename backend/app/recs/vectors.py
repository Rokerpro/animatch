"""Feature vector index for the AniMatch recommendation engine.

Architecture
------------
Each anime is represented as a single float32 numpy vector built from three
feature blocks:

  v = concat(
        W_genre  * idf_genre  ⊙ l2(raw_genre),   # binary genre presence
        W_tag    * idf_tag    ⊙ l2(raw_tag),      # tag rank/100 weights
        W_format * l2(raw_format),                # one-hot format (no IDF)
      )

After concatenation, each row is L2-normalised once more so
  dot(matrix[i], matrix[j]) == cosine_similarity(i, j)

IDF formula (additive smoothing, always ≥ 1):
  idf(j) = log((N + 1) / (df_j + 1)) + 1

Quality percentile (stored per item, not in cosine vector):
  quality_pct(x) = 0.6 * pct_rank(average_score) + 0.4 * pct_rank(log1p(popularity))

The index is built synchronously and held in process memory.  It must be
rebuilt after a catalog sync via VectorIndex.rebuild().
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from sklearn.preprocessing import normalize

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Format vocabulary — kept fixed so vectors are stable across rebuilds
# ---------------------------------------------------------------------------
FORMAT_VOCAB: list[str] = ["TV", "MOVIE", "OVA", "ONA", "SPECIAL", "OTHER"]
FORMAT_INDEX: dict[str, int] = {f: i for i, f in enumerate(FORMAT_VOCAB)}


def _percentile_rank(value: float | None, sorted_vals: np.ndarray) -> float:
    """Returns the fraction of sorted_vals strictly less than value (0-1 range).

    Items with NULL values receive 0.0.
    """
    if value is None or math.isnan(value):
        return 0.0
    idx = np.searchsorted(sorted_vals, value, side="left")
    n = len(sorted_vals)
    return float(idx) / n if n > 0 else 0.0


@dataclass
class AnimeRecord:
    """Minimal per-item record held in the index."""

    id: int
    title: str
    franchise_id: int | None
    average_score: int | None
    popularity: int
    cover_image: str | None = None
    episodes: int | None
    duration: int | None = None
    season_year: int | None = None
    status: str | None = (
        None  # AniList status string, e.g. "FINISHED", "NOT_YET_RELEASED"
    )
    is_adult: bool = False
    genres: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)  # names only (rank encoded in vector)
    tag_ranks: dict[str, float] = field(default_factory=dict)  # tag_name -> rank/100
    raw_tag_ranks: dict[str, int] = field(
        default_factory=dict
    )  # tag_name -> rank 0-100
    tag_spoilers: set[str] = field(default_factory=set)  # set of spoiler tag names
    format: str | None = None
    has_prequel: bool = False
    quality_pct: float = 0.0


@dataclass
class VectorIndex:
    """In-memory feature vector index built from the anime catalog.

    Thread-safety: build() is called at startup and after syncs.  The
    resulting index is treated as read-only during serving.
    """

    # Vocabulary (ordered lists so dims are stable)
    all_genres: list[str] = field(default_factory=list)
    all_tags: list[str] = field(default_factory=list)

    # IDF weights (length = len(all_genres) or len(all_tags))
    genre_idf: np.ndarray = field(default_factory=lambda: np.array([]))
    tag_idf: np.ndarray = field(default_factory=lambda: np.array([]))

    # Final normalised matrix (shape: N × D)
    matrix: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 0), dtype=np.float32)
    )

    # Ordered list of anime records parallel to matrix rows
    records: list[AnimeRecord] = field(default_factory=list)

    # Fast lookup: anime_id → row index
    id_to_idx: dict[int, int] = field(default_factory=dict)

    # Block dimension offsets (for contribution extraction in explain.py)
    genre_start: int = 0
    genre_end: int = 0
    tag_start: int = 0
    tag_end: int = 0
    format_start: int = 0
    format_end: int = 0

    # Canonical entry point anime ID per franchise in catalog: franchise_id -> anime_id
    franchise_entry_points: dict[int, int] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.records)

    def is_empty(self) -> bool:
        return len(self.records) == 0

    @classmethod
    def build(
        cls,
        items: list[dict[str, Any]],
        *,
        w_genre: float = 3.0,
        w_tag: float = 2.0,
        w_format: float = 1.0,
    ) -> VectorIndex:
        """Build the index from a list of raw anime dicts.

        Each dict must have at minimum:
          id, title, franchise_id, average_score, popularity,
          episodes, season_year, is_adult, format,
          genres: [str], tags: [{name, rank}]

        Returns a fully built VectorIndex.
        """
        if not items:
            return cls()

        # --- Collect vocabulary ---
        genre_set: set[str] = set()
        tag_set: set[str] = set()
        for item in items:
            genre_set.update(item.get("genres") or [])
            for t in item.get("tags") or []:
                tag_set.add(t["name"] if isinstance(t, dict) else t)

        all_genres = sorted(genre_set)
        all_tags = sorted(tag_set)
        genre_idx: dict[str, int] = {g: i for i, g in enumerate(all_genres)}
        tag_idx: dict[str, int] = {t: i for i, t in enumerate(all_tags)}

        G = len(all_genres)
        T = len(all_tags)
        F = len(FORMAT_VOCAB)
        N = len(items)

        # --- Raw feature blocks ---
        raw_genre = np.zeros((N, G), dtype=np.float32)
        raw_tag = np.zeros((N, T), dtype=np.float32)
        raw_format = np.zeros((N, F), dtype=np.float32)

        records: list[AnimeRecord] = []

        for row_i, item in enumerate(items):
            # Genre block
            for gname in item.get("genres") or []:
                j = genre_idx.get(gname)
                if j is not None:
                    raw_genre[row_i, j] = 1.0

            # Tag block: value = rank/100
            tag_ranks: dict[str, float] = {}
            raw_tag_ranks: dict[str, int] = {}
            tag_spoilers: set[str] = set()
            for t in item.get("tags") or []:
                if isinstance(t, dict):
                    tname = t["name"]
                    raw_r = int(t.get("rank", 0))
                    trank = float(raw_r) / 100.0
                    if t.get("is_spoiler"):
                        tag_spoilers.add(tname)
                else:
                    tname = t
                    raw_r = 0
                    trank = 0.0
                j = tag_idx.get(tname)
                if j is not None:
                    raw_tag[row_i, j] = trank
                tag_ranks[tname] = trank
                raw_tag_ranks[tname] = raw_r

            # Format block (one-hot)
            fmt = (item.get("format") or "OTHER").upper()
            if fmt not in FORMAT_INDEX:
                fmt = "OTHER"
            raw_format[row_i, FORMAT_INDEX[fmt]] = 1.0

            # Friendly tag-name list for explanations
            tag_names = [
                (t["name"] if isinstance(t, dict) else t)
                for t in (item.get("tags") or [])
            ]

            records.append(
                AnimeRecord(
                    id=item["id"],
                    title=(
                        item.get("title_english")
                        or item.get("title_romaji")
                        or item.get("title_native")
                        or "Unknown"
                    ),
                    cover_image=item.get("cover_image_url"),
                    franchise_id=item.get("franchise_id"),
                    average_score=item.get("average_score"),
                    popularity=item.get("popularity") or 0,
                    episodes=item.get("episodes"),
                    duration=item.get("duration"),
                    season_year=item.get("season_year"),
                    status=item.get("status"),
                    is_adult=bool(item.get("is_adult", False)),
                    genres=list(item.get("genres") or []),
                    tags=tag_names,
                    tag_ranks=tag_ranks,
                    raw_tag_ranks=raw_tag_ranks,
                    tag_spoilers=tag_spoilers,
                    format=item.get("format"),
                    has_prequel=bool(item.get("has_prequel", False)),
                )
            )

        # --- IDF weights ---
        # genre
        genre_df = (raw_genre > 0).sum(axis=0)  # (G,)
        genre_idf = np.log((N + 1) / (genre_df + 1)) + 1.0  # (G,)

        # tag
        tag_df = (raw_tag > 0).sum(axis=0)  # (T,)
        tag_idf = np.log((N + 1) / (tag_df + 1)) + 1.0  # (T,)

        # --- Per-item L2 normalise each block, then apply IDF weight ---
        l2_genre = normalize(raw_genre, norm="l2", axis=1)  # (N, G)
        l2_tag = normalize(raw_tag, norm="l2", axis=1)  # (N, T)
        l2_format = normalize(raw_format, norm="l2", axis=1)  # (N, F)

        weighted_genre = w_genre * (l2_genre * genre_idf)  # broadcast idf row
        weighted_tag = w_tag * (l2_tag * tag_idf)
        weighted_format = w_format * l2_format

        # --- Concatenate blocks ---
        matrix_raw = np.concatenate(
            [weighted_genre, weighted_tag, weighted_format], axis=1
        ).astype(np.float32)

        # --- Final row-wise L2 normalisation (enables dot == cosine) ---
        matrix = normalize(matrix_raw, norm="l2", axis=1)

        # --- Quality percentile (stored per item, not in cosine vector) ---
        scores = np.array(
            [
                r.average_score if r.average_score is not None else np.nan
                for r in records
            ],
            dtype=np.float64,
        )
        log_pops = np.array(
            [math.log1p(r.popularity) for r in records], dtype=np.float64
        )

        valid_scores = np.sort(scores[~np.isnan(scores)])
        sorted_log_pops = np.sort(log_pops)

        for i, rec in enumerate(records):
            sp = _percentile_rank(rec.average_score, valid_scores)
            pp = _percentile_rank(log_pops[i], sorted_log_pops)
            rec.quality_pct = 0.6 * sp + 0.4 * pp

        # --- Build id_to_idx lookup ---
        id_to_idx = {rec.id: i for i, rec in enumerate(records)}

        # --- Record block offsets ---
        gs = 0
        ge = G
        ts = ge
        te = ts + T
        fs = te
        fe = fs + F

        # --- Compute franchise entry points (one entry point per franchise) ---
        from collections import defaultdict

        franchise_members: dict[int, list[AnimeRecord]] = defaultdict(list)
        for rec in records:
            if rec.franchise_id is not None:
                franchise_members[rec.franchise_id].append(rec)

        franchise_entry_points: dict[int, int] = {}
        for fid, members in franchise_members.items():
            # Entry-point rule: earliest-aired TV title (by season_year);
            # if no TV title, the earliest movie; if no movie, the earliest title.
            # We do NOT use has_prequel / story-order relations to pick the entry
            # point — only the absolute start date decides.

            # 1. Format preference: TV -> MOVIE -> any
            tv_cands = [m for m in members if (m.format or "").upper() == "TV"]
            if tv_cands:
                cands = tv_cands
            else:
                movie_cands = [
                    m for m in members if (m.format or "").upper() == "MOVIE"
                ]
                cands = movie_cands if movie_cands else members

            # 2. Sort by earliest season_year (None = 9999 sentinel), then lowest id
            cands.sort(
                key=lambda m: (
                    m.season_year if m.season_year is not None else 9999,
                    m.id,
                )
            )
            franchise_entry_points[fid] = cands[0].id

        index = cls(
            all_genres=all_genres,
            all_tags=all_tags,
            genre_idf=genre_idf,
            tag_idf=tag_idf,
            matrix=matrix,
            records=records,
            id_to_idx=id_to_idx,
            genre_start=gs,
            genre_end=ge,
            tag_start=ts,
            tag_end=te,
            format_start=fs,
            format_end=fe,
            franchise_entry_points=franchise_entry_points,
        )
        logger.info(
            "VectorIndex built: %d items, %d genres, %d tags, %d dims",
            N,
            G,
            T,
            G + T + F,
        )
        return index

    def get(self, anime_id: int) -> AnimeRecord | None:
        """Returns the AnimeRecord for the given id, or None."""
        idx = self.id_to_idx.get(anime_id)
        return self.records[idx] if idx is not None else None

    def vec(self, anime_id: int) -> np.ndarray | None:
        """Returns the normalised feature vector for the given anime_id, or None."""
        idx = self.id_to_idx.get(anime_id)
        return self.matrix[idx] if idx is not None else None

    def validate_vocabulary(self, names: list[str]) -> list[str]:
        """Returns the subset of names NOT found in either all_genres or all_tags.

        Used by the quiz loader to verify all weight-dict keys exist in vocabulary.
        """
        known = set(self.all_genres) | set(self.all_tags)
        return [n for n in names if n not in known]

    def build_query_vec(
        self, genre_weights: dict[str, float], tag_weights: dict[str, float]
    ) -> np.ndarray:
        """Build a query vector from explicit genre/tag weight dicts.

        Applies the same IDF weighting as the item vectors so the dot product
        (cosine similarity) is meaningful.

        genre_weights: {genre_name: weight}
        tag_weights:   {tag_name:   weight}

        Returns a 1-D float32 array of dimension D (same as matrix columns).
        """
        G = len(self.all_genres)
        T = len(self.all_tags)
        F = len(FORMAT_VOCAB)

        raw = np.zeros(G + T + F, dtype=np.float32)

        for gname, w in genre_weights.items():
            idx = next((i for i, g in enumerate(self.all_genres) if g == gname), None)
            if idx is not None:
                raw[self.genre_start + idx] = float(w)

        for tname, w in tag_weights.items():
            idx = next((i for i, t in enumerate(self.all_tags) if t == tname), None)
            if idx is not None:
                raw[self.tag_start + idx] = float(w)

        # Apply block-level IDF to genre and tag portions
        raw[self.genre_start : self.genre_end] *= self.genre_idf
        raw[self.tag_start : self.tag_end] *= self.tag_idf

        # L2-normalise
        norm = np.linalg.norm(raw)
        if norm > 0:
            raw /= norm
        return raw


# ---------------------------------------------------------------------------
# Module-level singleton — rebuilt by the engine on startup and after syncs.
# ---------------------------------------------------------------------------
_INDEX: VectorIndex = VectorIndex()


def get_index() -> VectorIndex:
    """Returns the current global VectorIndex."""
    return _INDEX


def set_index(index: VectorIndex) -> None:
    """Replaces the global VectorIndex (called after sync or at startup)."""
    global _INDEX
    _INDEX = index
