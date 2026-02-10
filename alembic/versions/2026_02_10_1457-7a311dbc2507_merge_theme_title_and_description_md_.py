"""merge theme title and description_md into body_md

Revision ID: 7a311dbc2507
Revises: 18ff604473fb
Create Date: 2026-02-10 14:57:20.726441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7a311dbc2507'
down_revision: Union[str, Sequence[str], None] = '18ff604473fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add body_md as nullable first (so we can populate it)
    op.add_column('theme', sa.Column('body_md', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # 2. Migrate data: merge title + description_md into body_md
    op.execute("""
        UPDATE theme
        SET body_md = CASE
            WHEN description_md IS NOT NULL AND description_md != ''
            THEN title || E'\\n\\n' || description_md
            ELSE title
        END
    """)

    # 3. Make body_md non-nullable now that all rows have data
    op.alter_column('theme', 'body_md', nullable=False)

    # 4. Drop old columns and index
    op.drop_index(op.f('idx_theme_title'), table_name='theme')
    op.drop_column('theme', 'title')
    op.drop_column('theme', 'description_md')


def downgrade() -> None:
    # Reverse: split body_md back into title (first line) + description_md (rest)
    op.add_column('theme', sa.Column('title', sa.VARCHAR(length=200), nullable=True))
    op.add_column('theme', sa.Column('description_md', sa.VARCHAR(), nullable=True))

    # Take first 200 chars of body_md as title
    op.execute("""
        UPDATE theme
        SET title = LEFT(body_md, 200),
            description_md = NULL
    """)

    op.alter_column('theme', 'title', nullable=False)
    op.create_index(op.f('idx_theme_title'), 'theme', ['title'], unique=False)
    op.drop_column('theme', 'body_md')
