"""Add the bookmarks table (saved stories per user).

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "bookmarks" in sa.inspect(op.get_bind()).get_table_names():
        return  # create_all already made it (fresh database)
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "story_id", name="uq_user_bookmark"),
    )
    op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])
    op.create_index("ix_bookmarks_story_id", "bookmarks", ["story_id"])


def downgrade() -> None:
    op.drop_table("bookmarks")