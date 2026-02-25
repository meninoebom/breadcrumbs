"""add indexes on subscriber token columns

Revision ID: 7ca08bafef26
Revises: 1ac706c0dce9
Create Date: 2026-02-24 12:47:15.253731

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7ca08bafef26'
down_revision: Union[str, Sequence[str], None] = '1ac706c0dce9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_subscriber_confirmation_token'), 'subscriber', ['confirmation_token'], unique=False)
    op.create_index(op.f('ix_subscriber_unsubscribe_token'), 'subscriber', ['unsubscribe_token'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_subscriber_unsubscribe_token'), table_name='subscriber')
    op.drop_index(op.f('ix_subscriber_confirmation_token'), table_name='subscriber')
