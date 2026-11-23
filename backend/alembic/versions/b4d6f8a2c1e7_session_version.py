"""users.session_version for session revocation

Revision ID: b4d6f8a2c1e7
Revises: a8c3e5f1b920
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4d6f8a2c1e7"
down_revision: str | Sequence[str] | None = "a8c3e5f1b920"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("session_version")
