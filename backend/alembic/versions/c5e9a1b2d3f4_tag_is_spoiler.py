"""tag is_spoiler

Revision ID: c5e9a1b2d3f4
Revises: a3f8c2e91d05
Create Date: 2026-10-26 20:35:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c5e9a1b2d3f4"
down_revision = "a3f8c2e91d05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("anime_tags", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_spoiler", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("anime_tags", schema=None) as batch_op:
        batch_op.drop_column("is_spoiler")
