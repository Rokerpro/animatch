"""normalize apostrophes in FTS title text

Revision ID: d7f13a8c4b20
Revises: c5e9a1b2d3f4
Create Date: 2026-10-31
"""

from alembic import op

revision = "d7f13a8c4b20"
down_revision = "c5e9a1b2d3f4"
branch_labels = None
depends_on = None


def _normalized(value: str) -> str:
    expression = f"coalesce({value}, '')"
    for mark in ("‘", "’", "ʼ", "`"):
        expression = f"replace({expression}, '{mark}', char(39))"
    return f"replace({expression}, char(39), '')"


def _create_normalized_fts() -> None:
    op.execute(
        """CREATE VIRTUAL TABLE anime_fts USING fts5(
            title_romaji, title_english, title_native, synonyms,
            tokenize='unicode61'
        )"""
    )
    values = ", ".join(
        [_normalized(f"new.{name}") for name in (
            "title_romaji",
            "title_english",
            "title_native",
            "synonyms",
        )]
    )
    op.execute(
        f"""CREATE TRIGGER anime_ai AFTER INSERT ON anime BEGIN
            INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
            VALUES (new.id, {values});
        END"""
    )
    op.execute(
        """CREATE TRIGGER anime_ad AFTER DELETE ON anime BEGIN
            DELETE FROM anime_fts WHERE rowid = old.id;
        END"""
    )
    op.execute(
        f"""CREATE TRIGGER anime_au AFTER UPDATE ON anime BEGIN
            DELETE FROM anime_fts WHERE rowid = old.id;
            INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
            VALUES (new.id, {values});
        END"""
    )
    values_for_select = ", ".join(
        [_normalized(name) for name in (
            "title_romaji",
            "title_english",
            "title_native",
            "synonyms",
        )]
    )
    op.execute(
        f"""INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
            SELECT id, {values_for_select} FROM anime"""
    )


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute("DROP TRIGGER IF EXISTS anime_ai")
    op.execute("DROP TRIGGER IF EXISTS anime_ad")
    op.execute("DROP TRIGGER IF EXISTS anime_au")
    op.execute("DROP TABLE IF EXISTS anime_fts")
    _create_normalized_fts()


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute("DROP TRIGGER IF EXISTS anime_ai")
    op.execute("DROP TRIGGER IF EXISTS anime_ad")
    op.execute("DROP TRIGGER IF EXISTS anime_au")
    op.execute("DROP TABLE IF EXISTS anime_fts")
    op.execute(
        """CREATE VIRTUAL TABLE anime_fts USING fts5(
            title_romaji, title_english, title_native, synonyms,
            tokenize='unicode61'
        )"""
    )
    op.execute(
        """CREATE TRIGGER anime_ai AFTER INSERT ON anime BEGIN
            INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
            VALUES (new.id, new.title_romaji, new.title_english, new.title_native, coalesce(new.synonyms, ''));
        END"""
    )
    op.execute(
        """CREATE TRIGGER anime_ad AFTER DELETE ON anime BEGIN
            DELETE FROM anime_fts WHERE rowid = old.id;
        END"""
    )
    op.execute(
        """CREATE TRIGGER anime_au AFTER UPDATE ON anime BEGIN
            DELETE FROM anime_fts WHERE rowid = old.id;
            INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
            VALUES (new.id, new.title_romaji, new.title_english, new.title_native, coalesce(new.synonyms, ''));
        END"""
    )
    op.execute(
        """INSERT INTO anime_fts(rowid, title_romaji, title_english, title_native, synonyms)
            SELECT id, title_romaji, title_english, title_native, coalesce(synonyms, '') FROM anime"""
    )
