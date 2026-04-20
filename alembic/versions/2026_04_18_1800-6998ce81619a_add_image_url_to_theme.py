"""add image_url to theme

Revision ID: 6998ce81619a
Revises: ded91ca4b249
Create Date: 2026-04-18 18:00:33.038004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '6998ce81619a'
down_revision: Union[str, Sequence[str], None] = 'ded91ca4b249'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'theme',
        sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('theme', 'image_url')
