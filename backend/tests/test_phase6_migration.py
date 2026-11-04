"""The list-entry migration creates and removes its schema on a disposable DB."""

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


def test_list_entry_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database = tmp_path / "phase6-migration.sqlite"
    url = f"sqlite+aiosqlite:///{database}"
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    inspector = inspect(engine)
    assert (
        "list_entries" in inspector.get_table_names()
    ), "upgrade payload: list_entries table missing"
    constraints = inspector.get_unique_constraints("list_entries")
    assert any(
        c["column_names"] == ["user_id", "anime_id"] for c in constraints
    ), f"unique constraint payload: {constraints}"
    foreign_keys = inspector.get_foreign_keys("list_entries")
    assert {
        (
            fk["constrained_columns"][0],
            fk["referred_table"],
            fk["options"].get("ondelete"),
        )
        for fk in foreign_keys
    } == {
        ("user_id", "users", "CASCADE"),
        ("anime_id", "anime", "CASCADE"),
    }, f"foreign key payload: {foreign_keys}"
    indexes = {
        idx["name"]: idx["column_names"]
        for idx in inspector.get_indexes("list_entries")
    }
    assert indexes == {
        "ix_list_entries_user_id": ["user_id"],
        "ix_list_entries_anime_id": ["anime_id"],
    }, f"index payload: {indexes}"
    engine.dispose()
    command.downgrade(config, "d7f13a8c4b20")
    engine = create_engine(f"sqlite:///{database}")
    assert (
        "list_entries" not in inspect(engine).get_table_names()
    ), "downgrade payload: list_entries table remains"
    engine.dispose()
