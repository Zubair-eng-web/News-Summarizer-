"""Add the source_health table (last collection result per source).

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "source_health" in sa.inspect(op.get_bind()).get_table_names():
        return  # create_all already made it
    op.create_table(
        "source_health",
        sa.Column("name", sa.String(100), primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_ok_at", sa.DateTime(), nullable=True),
        sa.Column("last_items", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(300), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("source_health")