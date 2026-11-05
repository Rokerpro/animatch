"""Explicit API schemas for the authenticated user's watchlist."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.schemas.anime import AnimeCard


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

    @model_validator(mode="after")
    def require_update_field(self) -> "ListEntryPut":
        if not self.model_fields_set:
            raise ValueError("At least one of status or rating is required")
        return self


class ListEntryResponse(BaseModel):
    """Persisted entry shape; entry keys remain snake_case by contract."""

    id: int
    anime_id: int
    anime: AnimeCard
    status: ListStatus
    rating: int | None
    source: Literal["manual", "mal_import"]
    added_at: datetime
    updated_at: datetime


class ListPageInfo(BaseModel):
    total: int
    current_page: int
    last_page: int
    per_page: int
    has_next_page: bool


class ListResponse(BaseModel):
    items: list[ListEntryResponse]
    page_info: ListPageInfo


class ListDeleteResponse(BaseModel):
    message: str


class ListAnimeStatus(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    anime_id: int
    status: ListStatus
    rating: int | None


class ListStatusesResponse(BaseModel):
    items: list[ListAnimeStatus]
