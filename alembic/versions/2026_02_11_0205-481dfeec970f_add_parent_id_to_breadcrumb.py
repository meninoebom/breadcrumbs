"""add parent_id to breadcrumb

Revision ID: 481dfeec970f
Revises: 7a311dbc2507
Create Date: 2026-02-11 02:05:44.353375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '481dfeec970f'
down_revision: Union[str, Sequence[str], None] = '7a311dbc2507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "breadcrumb",
        sa.Column("parent_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_breadcrumb_parent_id",
        "breadcrumb",
        "breadcrumb",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_breadcrumb_parent_id", "breadcrumb", ["parent_id"])


def downgrade() -> None:
    op.drop_index("idx_breadcrumb_parent_id", table_name="breadcrumb")
    op.drop_constraint("fk_breadcrumb_parent_id", "breadcrumb", type_="foreignkey")
    op.drop_column("breadcrumb", "parent_id")
