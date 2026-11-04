"""User watchlist / list entry SQLAlchemy model.

A ListEntry ties a registered user to a catalog anime with a watchlist
status, an optional 1-10 rating, and a provenance flag (manual or imported
from MyAnimeList).  One row per (user, anime) thanks to the unique
constraint; deleting a user cascades to their entries via the FK.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Canonical watchlist statuses.  Kept as a tuple so it can be reused by the
# schema layer for validation without importing SQLAlchemy internals.
LIST_STATUSES: tuple[str, ...] = (
    "planning",
    "watching",
    "completed",
    "dropped",
    "on_hold",
)

# Provenance of the row: user-created or copied from a MAL import.
LIST_SOURCES: tuple[str, ...] = ("manual", "mal_import")


class ListEntry(Base):
    """A single title on a user's watchlist."""

    __tablename__ = "list_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    anime_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("anime.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planning",
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Eager path for serializing the card fields (cover image, genres, ...).
    # selectin so a list endpoint fetches genres/tags in a single extra query.
    anime: Mapped[Anime] = relationship(
        "Anime",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "anime_id",
            name="uq_list_entries_user_anime",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ListEntry id={self.id} user_id={self.user_id} "
            f"anime_id={self.anime_id} status='{self.status}' rating={self.rating}>"
        )


# Late import to avoid a circular dependency at module load time.
from app.models.anime import Anime  # noqa: E402  (needed for relationship target)
