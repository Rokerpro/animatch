from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Association table for Anime <-> Genre
anime_genres = Table(
    "anime_genres",
    Base.metadata,
    Column(
        "anime_id",
        Integer,
        ForeignKey("anime.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        Integer,
        ForeignKey("genre.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# Association table for Anime <-> Tag with rank 0-100
anime_tags = Table(
    "anime_tags",
    Base.metadata,
    Column(
        "anime_id",
        Integer,
        ForeignKey("anime.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tag.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("rank", Integer, nullable=False, default=0),
)


class Genre(Base):
    """Anime genre (e.g. Action, Comedy, Fantasy)."""

    __tablename__ = "genre"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

    animes: Mapped[list["Anime"]] = relationship(
        "Anime",
        secondary=anime_genres,
        back_populates="genres",
    )


class Tag(Base):
    """Anime tag (e.g. Isekai, Time Skip) with maturity flag."""

    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_adult: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    animes: Mapped[list["Anime"]] = relationship(
        "Anime",
        secondary=anime_tags,
        back_populates="tags",
    )


class Anime(Base):
    """Catalog anime record synced from AniList."""

    __tablename__ = "anime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # AniList ID
    id_mal: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title_romaji: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_english: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_native: Mapped[str | None] = mapped_column(Text, nullable=True)
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    episodes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    season: Mapped[str | None] = mapped_column(String(20), nullable=True)
    season_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    average_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    popularity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, index=True
    )
    is_adult: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    main_studio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at_anilist: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    genres: Mapped[list[Genre]] = relationship(
        "Genre",
        secondary=anime_genres,
        back_populates="animes",
        lazy="selectin",
    )
    tags: Mapped[list[Tag]] = relationship(
        "Tag",
        secondary=anime_tags,
        back_populates="animes",
        lazy="selectin",
    )
