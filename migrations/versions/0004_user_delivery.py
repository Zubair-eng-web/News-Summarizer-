"""Add user_prefs.telegram_chat_id and user_prefs.digest_hour.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: create_all ne naye models se ye columns pehle bana diye ho sakte hain
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("user_prefs")}
    if "telegram_chat_id" not in columns:
        op.add_column(
            "user_prefs",
            sa.Column("telegram_chat_id", sa.String(64), nullable=False, server_default=""),
        )
    if "digest_hour" not in columns:
        op.add_column("user_prefs", sa.Column("digest_hour", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_prefs") as batch:
        batch.drop_column("digest_hour")
        batch.drop_column("telegram_chat_id")
