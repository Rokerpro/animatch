"""list_entry

Revision ID: bc72dda16832
Revises: d7f13a8c4b20
Create Date: 2026-11-03 19:29:22.107210

Adds the list_entries table for user watchlists:
  - user_id FK to users (cascade delete)
  - anime_id FK to anime (cascade delete)
  - status: planning, watching, completed, dropped, on_hold
  - rating: nullable 1-10 integer
  - source: manual or mal_import (default manual)
  - added_at, updated_at timestamps
  - unique constraint on (user_id, anime_id)
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bc72dda16832"
down_revision: Union[str, Sequence[str], None] = "d7f13a8c4b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "list_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("anime_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="planning"),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["anime_id"],
            ["anime.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "anime_id", name="uq_list_entries_user_anime"),
    )
    op.create_index("ix_list_entries_user_id", "list_entries", ["user_id"])
    op.create_index("ix_list_entries_anime_id", "list_entries", ["anime_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_list_entries_anime_id", table_name="list_entries")
    op.drop_index("ix_list_entries_user_id", table_name="list_entries")
    op.drop_table("list_entries")