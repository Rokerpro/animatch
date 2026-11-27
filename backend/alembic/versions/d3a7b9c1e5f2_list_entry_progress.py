"""list_entries.progress (episodes watched)

Revision ID: d3a7b9c1e5f2
Revises: c9e2f4a6b8d1
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d3a7b9c1e5f2"
down_revision: str | Sequence[str] | None = "c9e2f4a6b8d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "list_entries",
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    with op.batch_alter_table("list_entries") as batch:
        batch.drop_column("progress")
