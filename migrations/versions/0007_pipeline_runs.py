"""Add the pipeline_runs table (job run history).

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "pipeline_runs" in sa.inspect(op.get_bind()).get_table_names():
        return  # create_all already made it
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job", sa.String(50), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("error", sa.String(300), nullable=False),
    )
    op.create_index("ix_pipeline_runs_job", "pipeline_runs", ["job"])
    op.create_index("ix_pipeline_runs_started_at", "pipeline_runs", ["started_at"])


def downgrade() -> None:
    op.drop_table("pipeline_runs")