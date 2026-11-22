"""recommendation feedback (not interested)

Revision ID: a8c3e5f1b920
Revises: f2a91c5d7e30
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a8c3e5f1b920"
down_revision: str | Sequence[str] | None = "f2a91c5d7e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rec_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("anime_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["anime_id"], ["anime.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "anime_id", name="uq_rec_feedback_user_anime"),
    )
    op.create_index("ix_rec_feedback_user_id", "rec_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_rec_feedback_user_id", table_name="rec_feedback")
    op.drop_table("rec_feedback")
