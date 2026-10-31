"""Database initialization and schema migration helper."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

import app.models  # noqa: F401
from app.db.session import Base

def normalized_fts_value(column: str) -> str:
    """SQLite expression that removes normalized apostrophes before indexing."""
    expression = f"coalesce({column}, '')"
    for mark in ("‘", "’", "ʼ", "`"):
        expression = f"replace({expression}, '{mark}', char(39))"
    return f"replace({expression}, char(39), '')"


_title_values = [
    normalized_fts_value(f"new.{column}")
    for column in ("title_romaji", "title_english", "title_native")
]
_synonyms_value = normalized_fts_value("new.synonyms")

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
        VALUES (new.id, {_title_values[0]}, {_title_values[1]}, {_title_values[2]}, {_synonyms_value});
    END;
    """.format(
        _title_values=_title_values,
        _synonyms_value=_synonyms_value,
    ),
    """
    CREATE TRIGGER IF NOT EXISTS anime_ad AFTER DELETE ON anime BEGIN
        DELETE FROM anime_fts WHERE rowid = old.id;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS anime_au AFTER UPDATE ON anime BEGIN
        DELETE FROM anime_fts WHERE rowid = old.id;
        INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
        VALUES (new.id, {_title_values[0]}, {_title_values[1]}, {_title_values[2]}, {_synonyms_value});
    END;
    """.format(
        _title_values=_title_values,
        _synonyms_value=_synonyms_value,
    ),
]


async def init_db(engine: AsyncEngine) -> None:
    """Creates all metadata tables and SQLite FTS5 table + triggers if on SQLite."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "sqlite":
            for stmt in FTS5_STATEMENTS:
                await conn.execute(text(stmt.strip()))
