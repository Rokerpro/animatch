from pydantic import BaseModel, ConfigDict, Field

from app.models.list_entry import LIST_SOURCES, LIST_STATUSES
from app.schemas.anime import AnimeCard


class ListEntryBase(BaseModel):
    anime_id: int
    status: str = Field(..., pattern=f"^({'|'.join(LIST_STATUSES)})$")
    rating: int | None = Field(default=None, ge=1, le=10)
    source: str = Field(default="manual", pattern=f"^({'|'.join(LIST_SOURCES)})$")


class ListEntryUpdate(BaseModel):
    status: str | None = Field(default=None, pattern=f"^({'|'.join(LIST_STATUSES)})$")
    rating: int | None = Field(default=None, ge=1, le=10)


class ListEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    anime_id: int
    anime: AnimeCard
    status: str
    rating: int | None
    source: str
    added_at: str
    updated_at: str
