"""Pydantic schemas for Anime API responses."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PageInfo(BaseSchema):
    total: int
    current_page: int
    last_page: int
    per_page: int
    has_next_page: bool


class AnimeCard(BaseSchema):
    id: int
    title: str
    title_romaji: str | None = None
    title_english: str | None = None
    title_native: str | None = None
    cover_image: str | None = None
    banner_image: str | None = None
    format: str | None = None
    status: str | None = None
    episodes: int | None = None
    duration: int | None = None
    year: int | None = None
    score: int | None = None
    popularity: int = 0
    is_adult: bool = False
    genres: list[str] = Field(default_factory=list)


class AnimeDetail(AnimeCard):
    synopsis: str | None = None
    season: str | None = None
    season_year: int | None = None
    studio: str | None = None
    source: str | None = None
    id_mal: int | None = None
    synonyms: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class AnimeListResponse(BaseSchema):
    items: list[AnimeCard]
    page_info: PageInfo


class FiltersResponse(BaseSchema):
    genres: list[str]
    tags: list[str]
