"""anime.cover_color from AniList coverImage.color

Revision ID: c9e2f4a6b8d1
Revises: b4d6f8a2c1e7
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9e2f4a6b8d1"
down_revision: str | Sequence[str] | None = "b4d6f8a2c1e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "anime", sa.Column("cover_color", sa.String(length=16), nullable=True)
    )


def downgrade() -> None:
    with op.batch_alter_table("anime") as batch:
        batch.drop_column("cover_color")
