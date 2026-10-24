"""Database initialization and schema migration helper."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

import app.models  # noqa: F401
from app.db.session import Base

FTS5_STATEMENTS = [
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS anime_fts USING fts5(
        title_romaji,
        title_english,
        title_native,
        synonyms,
        tokenize='unicode61'
    );
    """,
    """
    CREATE TRIGGER IF NOT EXISTS anime_ai AFTER INSERT ON anime BEGIN
        INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
        VALUES (new.id, new.title_romaji, new.title_english, new.title_native, coalesce(new.synonyms, ''));
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS anime_ad AFTER DELETE ON anime BEGIN
        DELETE FROM anime_fts WHERE rowid = old.id;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS anime_au AFTER UPDATE ON anime BEGIN
        DELETE FROM anime_fts WHERE rowid = old.id;
        INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
        VALUES (new.id, new.title_romaji, new.title_english, new.title_native, coalesce(new.synonyms, ''));
    END;
    """,
]


async def init_db(engine: AsyncEngine) -> None:
    """Creates all metadata tables and SQLite FTS5 table + triggers if on SQLite."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "sqlite":
            for stmt in FTS5_STATEMENTS:
                await conn.execute(text(stmt.strip()))
