"""AniList GraphQL client with rate limiting, retries, and pagination."""

import asyncio
import logging
import random
import time
from typing import Any

import httpx

from app.core.text import strip_html_tags

logger = logging.getLogger(__name__)

ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"

MEDIA_PAGE_QUERY = """
query GetMediaPage(
  $page: Int,
  $perPage: Int,
  $sort: [MediaSort],
  $isAdult: Boolean
) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      total
      currentPage
      lastPage
      hasNextPage
      perPage
    }
    media(
      type: ANIME,
      sort: $sort,
      isAdult: $isAdult
    ) {
      id
      idMal
      title {
        romaji
        english
        native
      }
      synonyms
      description
      coverImage {
        extraLarge
        large
      }
      bannerImage
      format
      episodes
      duration
      status
      season
      seasonYear
      averageScore
      popularity
      isAdult
      source
      studios(isMain: true) {
        nodes {
          name
        }
      }
      genres
      tags {
        id
        name
        category
        isAdult
        rank
        isMediaSpoiler
        isGeneralSpoiler
      }
      updatedAt
      relations {
        edges {
          relationType
          node {
            id
            type
          }
        }
      }
    }
  }
}
"""


class AniListClient:
    """Async client for interacting with the AniList GraphQL API."""

    def __init__(
        self,
        base_url: str = ANILIST_GRAPHQL_URL,
        requests_per_minute: int = 80,
        max_retries: int = 5,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.requests_per_minute = max(1, requests_per_minute)
        self.min_interval = 60.0 / self.requests_per_minute
        self.max_retries = max_retries
        self.timeout = timeout
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(timeout=self.timeout)
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "AniListClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if not self._external_client:
            await self._client.aclose()

    async def close(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    async def _wait_for_rate_limit(self) -> None:
        """Enforces request rate budget under the configured requests_per_minute."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                sleep_needed = self.min_interval - elapsed
                await asyncio.sleep(sleep_needed)
            self._last_request_time = time.monotonic()

    async def execute_query(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Executes a GraphQL query with rate limiting, retries, and backoff."""
        variables = variables or {}
        attempt = 0

        while attempt < self.max_retries:
            attempt += 1
            await self._wait_for_rate_limit()

            try:
                response = await self._client.post(
                    self.base_url,
                    json={"query": query, "variables": variables},
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )

                # Check 429 Too Many Requests
                if response.status_code == 429:
                    retry_after_header = response.headers.get("Retry-After")
                    if retry_after_header:
                        try:
                            retry_after = float(retry_after_header)
                        except ValueError:
                            retry_after = 60.0
                    else:
                        retry_after = 60.0
                    logger.warning(
                        "AniList rate limit 429 hit. Backing off for %.1fs (attempt %d/%d)",
                        retry_after,
                        attempt,
                        self.max_retries,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                # Check AniList X-RateLimit headers
                remaining_header = response.headers.get("X-RateLimit-Remaining")
                if remaining_header and remaining_header.isdigit():
                    remaining = int(remaining_header)
                    if remaining <= 1:
                        reset_header = response.headers.get("X-RateLimit-Reset")
                        if reset_header and reset_header.isdigit():
                            wait_sec = max(0, int(reset_header) - int(time.time()))
                            if wait_sec > 0:
                                logger.info(
                                    "Rate limit nearly exhausted (%d left). Sleeping %ds",
                                    remaining,
                                    wait_sec,
                                )
                                await asyncio.sleep(min(wait_sec, 60))

                # Server error retry (5xx)
                if response.status_code >= 500:
                    delay = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                    logger.warning(
                        "AniList server error %d. Retrying in %.2fs (attempt %d/%d)",
                        response.status_code,
                        delay,
                        attempt,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                data = response.json()

                if "errors" in data and not data.get("data"):
                    raise RuntimeError(f"AniList GraphQL error: {data['errors']}")

                return data.get("data", {})

            except (
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as err:
                if attempt >= self.max_retries:
                    raise
                delay = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                logger.warning(
                    "Network error (%s). Retrying in %.2fs (attempt %d/%d)",
                    err,
                    delay,
                    attempt,
                    self.max_retries,
                )
                await asyncio.sleep(delay)

        raise RuntimeError(f"AniList query failed after {self.max_retries} attempts")

    async def fetch_media_page(
        self,
        page: int = 1,
        per_page: int = 50,
        sort: list[str] | str = "POPULARITY_DESC",
        is_adult: bool | None = None,
        updated_at_greater: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetches a page of anime media from AniList and parses clean fields."""
        # If incremental mode requested without explicit sort, sort by UPDATED_AT_DESC
        if updated_at_greater is not None and sort == "POPULARITY_DESC":
            sort_list = ["UPDATED_AT_DESC"]
        else:
            sort_list = [sort] if isinstance(sort, str) else sort

        variables: dict[str, Any] = {
            "page": page,
            "perPage": per_page,
            "sort": sort_list,
        }
        if is_adult is not None:
            variables["isAdult"] = is_adult

        data = await self.execute_query(MEDIA_PAGE_QUERY, variables)
        page_data = data.get("Page", {})
        page_info = page_data.get("pageInfo", {})
        raw_media = page_data.get("media", [])

        parsed_items: list[dict[str, Any]] = []
        for item in raw_media:
            title_dict = item.get("title") or {}
            cover_dict = item.get("coverImage") or {}
            studios_nodes = (item.get("studios") or {}).get("nodes") or []
            main_studio = studios_nodes[0].get("name") if studios_nodes else None

            # Cover image precedence: extraLarge -> large
            cover_url = cover_dict.get("extraLarge") or cover_dict.get("large")

            # Clean description (plain text, no HTML)
            description = strip_html_tags(item.get("description"))

            # Genres & Tags
            genres = [g for g in item.get("genres") or [] if g]
            tags = [
                {
                    "name": t["name"],
                    "category": t.get("category"),
                    "is_adult": bool(t.get("isAdult", False)),
                    "rank": int(t.get("rank") or 0),
                    "is_spoiler": bool(
                        t.get("isMediaSpoiler", False)
                        or t.get("isGeneralSpoiler", False)
                    ),
                }
                for t in item.get("tags") or []
                if t.get("name")
            ]

            # Relations: keep ALL edge types but only ANIME-type nodes.
            # Downstream, catalog_sync stores every edge so the Union-Find franchise
            # algorithm can run on the full graph (including nodes outside catalog).
            raw_relations = (item.get("relations") or {}).get("edges") or []
            relations: list[dict[str, Any]] = [
                {
                    "related_id": edge["node"]["id"],
                    "rel_type": edge.get("relationType") or "OTHER",
                }
                for edge in raw_relations
                if (edge.get("node") or {}).get("type") == "ANIME"
                and (edge.get("node") or {}).get("id") is not None
            ]

            parsed_anime = {
                "id": item["id"],
                "id_mal": item.get("idMal"),
                "title_romaji": title_dict.get("romaji"),
                "title_english": title_dict.get("english"),
                "title_native": title_dict.get("native"),
                "synonyms": item.get("synonyms") or [],
                "description": description,
                "cover_image_url": cover_url,
                "banner_image_url": item.get("bannerImage"),
                "format": item.get("format"),
                "episodes": item.get("episodes"),
                "duration": item.get("duration"),
                "status": item.get("status"),
                "season": item.get("season"),
                "season_year": item.get("seasonYear"),
                "average_score": item.get("averageScore"),
                "popularity": item.get("popularity") or 0,
                "is_adult": bool(item.get("isAdult", False)),
                "source": item.get("source"),
                "main_studio": main_studio,
                "updated_at_anilist": item.get("updatedAt"),
                "genres": genres,
                "tags": tags,
                "relations": relations,
            }
            parsed_items.append(parsed_anime)

        return parsed_items, page_info
