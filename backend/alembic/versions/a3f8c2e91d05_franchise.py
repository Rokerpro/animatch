"""franchise

Revision ID: a3f8c2e91d05
Revises: 5b1d4e7a892c
Create Date: 2026-10-25 11:15:00.000000

Adds:
  - anime_relations table: stores ALL AniList relation edges (prequel, sequel,
    parent, side_story, spin_off, alternative, and others).  related_id has no
    FK intentionally — nodes outside the local catalog are allowed so connected-
    component franchise detection works on the full AniList relation graph.
  - anime.franchise_id: nullable INT assigned by the catalog sync's Union-Find
    pass.  franchise_id = min(component AniList id).  NULL = no known relations.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f8c2e91d05"
down_revision: str | Sequence[str] | None = "5b1d4e7a892c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. anime_relations — stores every AniList relation edge we encounter.
    #    related_id deliberately has no FK: titles outside the catalog must be
    #    stored so the full connected-component franchise graph is correct even
    #    when the catalog is a subset of AniList.
    op.create_table(
        "anime_relations",
        sa.Column("__pk", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("anime_id", sa.Integer(), nullable=False),
        sa.Column("related_id", sa.Integer(), nullable=False),  # no FK — intentional
        sa.Column("rel_type", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(
            ["anime_id"],
            ["anime.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("__pk"),
    )
    op.create_index("ix_anime_relations_anime_id", "anime_relations", ["anime_id"])
    op.create_index(
        "ix_anime_relations_related_id", "anime_relations", ["related_id"]
    )
    op.create_index(
        "ix_anime_relations_pair",
        "anime_relations",
        ["anime_id", "related_id"],
        unique=True,
    )

    # 2. franchise_id on anime — computed by the catalog sync after every batch.
    op.add_column(
        "anime",
        sa.Column("franchise_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_anime_franchise_id", "anime", ["franchise_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_anime_franchise_id", table_name="anime")
    op.drop_column("anime", "franchise_id")
    op.drop_index("ix_anime_relations_pair", table_name="anime_relations")
    op.drop_index("ix_anime_relations_related_id", table_name="anime_relations")
    op.drop_index("ix_anime_relations_anime_id", table_name="anime_relations")
    op.drop_table("anime_relations")
