"""Add the story_reads table (read/unread status per user).

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "story_reads" in sa.inspect(op.get_bind()).get_table_names():
        return  # create_all already made it
    op.create_table(
        "story_reads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "story_id", name="uq_user_story_read"),
    )
    op.create_index("ix_story_reads_user_id", "story_reads", ["user_id"])
    op.create_index("ix_story_reads_story_id", "story_reads", ["story_id"])


def downgrade() -> None:
    op.drop_table("story_reads")