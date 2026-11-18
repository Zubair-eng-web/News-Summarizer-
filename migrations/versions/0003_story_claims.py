"""Add stories.claims_json (per-claim support).

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: create_all ne naye models se ye column pehle bana diya ho sakta hai
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("stories")}
    if "claims_json" in columns:
        return
    op.add_column(
        "stories",
        sa.Column("claims_json", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    with op.batch_alter_table("stories") as batch:
        batch.drop_column("claims_json")