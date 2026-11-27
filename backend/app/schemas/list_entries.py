"""Explicit API schemas for the authenticated user's watchlist."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.anime import AnimeCard, BaseSchema, PageInfo


class ListStatus(StrEnum):
    PLANNING = "planning"
    WATCHING = "watching"
    COMPLETED = "completed"
    DROPPED = "dropped"
    ON_HOLD = "on_hold"


class ListSort(StrEnum):
    UPDATED = "updated"
    RATING = "rating"
    TITLE = "title"


class ListEntryPut(BaseModel):
    """Partial update semantics for creating and editing list entries.

    Status-only requests update an existing status and retain its rating; for a
    new entry they use the supplied status with a null rating. Rating-only
    requests update an existing rating and retain its status; for a new entry
    they create it with status ``planning``. An omitted rating is retained,
    while an explicit null rating clears it. At least one field is required.
    """

    model_config = ConfigDict(extra="forbid")

    # A non-null enum with a None default makes the field optional in requests,
    # while rejecting an explicit null status.
    status: ListStatus = Field(
        default=None,
        description=(
            "Optional watch status. Omission retains an existing status. On a new "
            "entry, a status-only request uses this status and a null rating."
        ),
    )
    rating: int | None = Field(
        default=None,
        ge=1,
        le=10,
        strict=True,
        description=(
            "Optional 1-10 rating. Omission retains an existing rating; null clears "
            "it. A rating-only request for a new entry creates it as planning."
        ),
    )

    progress: int = Field(
        default=None,
        ge=0,
        strict=True,
        description=(
            "Optional count of episodes watched. Omission retains the existing "
            "value. Cannot exceed the title's episode count when it is known."
        ),
    )

    @model_validator(mode="after")
    def require_update_field(self) -> "ListEntryPut":
        if not self.model_fields_set:
            raise ValueError("At least one of status, rating or progress is required")
        return self


class ListEntryResponse(BaseSchema):
    """Persisted entry shape, serialized with camelCase keys like the rest of the API."""

    id: int
    anime_id: int
    anime: AnimeCard
    status: ListStatus
    rating: int | None
    progress: int
    source: Literal["manual", "mal_import"]
    added_at: datetime
    updated_at: datetime


class ListResponse(BaseSchema):
    items: list[ListEntryResponse]
    page_info: PageInfo


class ListDeleteResponse(BaseModel):
    message: str


class ListAnimeStatus(BaseSchema):
    anime_id: int
    status: ListStatus
    rating: int | None


class ListStatusesResponse(BaseModel):
    items: list[ListAnimeStatus]


class GenreCount(BaseModel):
    genre: str
    count: int


class ListStatsResponse(BaseSchema):
    """Summary of a user's list. Counts exclude mature titles unless requested."""

    total: int
    by_status: dict[str, int]
    rated_count: int
    mean_rating: float | None
    rating_distribution: dict[str, int]
    top_genres: list[GenreCount]
