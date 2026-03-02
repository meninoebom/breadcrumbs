"""add digest_type column and update unique constraint

Revision ID: ded91ca4b249
Revises: 7ca08bafef26
Create Date: 2026-03-01 20:09:39.458565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ded91ca4b249'
down_revision: Union[str, Sequence[str], None] = '7ca08bafef26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE digesttype AS ENUM ('weekly', 'monthly')")
    op.add_column('digest', sa.Column(
        'digest_type',
        sa.Enum('weekly', 'monthly', name='digesttype', create_type=False),
        nullable=False,
        server_default='weekly',
    ))
    op.drop_constraint('uq_digest_period_start', 'digest', type_='unique')
    op.create_unique_constraint('uq_digest_period_start_type', 'digest', ['period_start', 'digest_type'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_digest_period_start_type', 'digest', type_='unique')
    op.create_unique_constraint('uq_digest_period_start', 'digest', ['period_start'])
    op.drop_column('digest', 'digest_type')
    op.execute("DROP TYPE digesttype")
