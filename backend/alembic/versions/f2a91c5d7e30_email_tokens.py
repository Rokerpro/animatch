"""email tokens and email_verified_at

Revision ID: f2a91c5d7e30
Revises: e71b4a2c9d10
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2a91c5d7e30"
down_revision: str | Sequence[str] | None = "e71b4a2c9d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])
    op.create_index(
        "ix_email_tokens_token_hash", "email_tokens", ["token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_email_tokens_token_hash", table_name="email_tokens")
    op.drop_index("ix_email_tokens_user_id", table_name="email_tokens")
    op.drop_table("email_tokens")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified_at")
