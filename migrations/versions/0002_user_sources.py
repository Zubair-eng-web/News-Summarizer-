"""Add user_sources (users ke apne RSS feeds aur YouTube channels).

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: app startup ka create_all ye table pehle bana sakta hai
    if sa.inspect(op.get_bind()).has_table("user_sources"):
        return
    op.create_table(
        "user_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "kind", "url", name="uq_user_source"),
    )
    op.create_index(op.f("ix_user_sources_user_id"), "user_sources", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_sources_user_id"), table_name="user_sources")
    op.drop_table("user_sources")