"""Request and response schemas for importing a MyAnimeList XML export."""

from pydantic import BaseModel, ConfigDict, Field


class MALImportOptions(BaseModel):
    """The only supported import query option."""

    model_config = ConfigDict(extra="forbid")

    dry_run: bool = Field(
        default=False,
        description="Report the import without writing entries.",
    )


class MALUnmatchedEntry(BaseModel):
    title: str
    mal_id: int


class MALImportResponse(BaseModel):
    total_entries: int = Field(
        description="Number of anime entries in the XML, including duplicate MAL IDs."
    )
    to_import: int = Field(
        description="Number of new list entries imported, or that would be imported in dry-run mode."
    )
    skipped_existing: int = Field(
        description="Entries already present on this user's list."
    )
    unmatched_count: int = Field(
        description="Anime MAL IDs not found in the local catalog."
    )
    unmatched: list[MALUnmatchedEntry] = Field(
        description="First 50 unmatched anime entries."
    )
