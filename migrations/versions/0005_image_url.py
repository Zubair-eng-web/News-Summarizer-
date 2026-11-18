"""Add articles.image_url and stories.image_url (thumbnails from real feed data).

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _add(table: str) -> None:
    # Idempotent: create_all may already have made the column on a fresh database
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    if "image_url" not in columns:
        op.add_column(
            table,
            sa.Column("image_url", sa.String(1000), nullable=False, server_default=""),
        )


def upgrade() -> None:
    _add("stories")
    _add("articles")


def downgrade() -> None:
    for table in ("stories", "articles"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("image_url")