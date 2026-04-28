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


def downgrade() -> None:
    op.drop_column("tag", "position")
