"""add position to tag

Revision ID: 598878310987
Revises: 6998ce81619a
Create Date: 2026-04-27 18:29:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "598878310987"
down_revision: Union[str, None] = "6998ce81619a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tag", sa.Column("position", sa.Integer(), nullable=True))
    # Backfill existing tags in alphabetical order so no tag starts as NULL.
    # Uses a subquery-based row_number pattern compatible with both SQLite and PostgreSQL.
    conn = op.get_bind()
    tags = conn.execute(sa.text("SELECT id FROM tag ORDER BY name")).fetchall()
    for i, row in enumerate(tags):
        conn.execute(
            sa.text("UPDATE tag SET position = :pos WHERE id = :id"),
            {"pos": i, "id": row[0]},
        )


def downgrade() -> None:
    op.drop_column("tag", "position")
