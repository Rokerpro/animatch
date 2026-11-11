"""natural language daily request counts

Revision ID: e71b4a2c9d10
Revises: bc72dda16832
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e71b4a2c9d10"
down_revision: str | Sequence[str] | None = "bc72dda16832"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "natural_language_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_nl_usage_user_date"),
    )
    op.create_index(
        "ix_natural_language_usage_user_id", "natural_language_usage", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_natural_language_usage_user_id", table_name="natural_language_usage"
    )
    op.drop_table("natural_language_usage")
