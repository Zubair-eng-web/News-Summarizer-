"""Add the api_keys table (extra Gemini keys added from the dashboard).

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "api_keys" in sa.inspect(op.get_bind()).get_table_names():
        return  # create_all already made it
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("key", name="uq_api_key"),
    )


def downgrade() -> None:
    op.drop_table("api_keys")