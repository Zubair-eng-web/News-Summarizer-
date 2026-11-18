"""Baseline: schema jaisa abhi models.py me hai.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("link", sa.String(length=1000), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("published", sa.DateTime(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_articles_link"), "articles", ["link"], unique=True)

    op.create_table(
        "alerts_sent",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("story_key", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_sent_story_key"), "alerts_sent", ["story_key"], unique=True)

    op.create_table(
        "digested_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link", sa.String(length=1000), nullable=False),
        sa.Column("digested_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_digested_articles_link"), "digested_articles", ["link"], unique=True
    )

    op.create_table(
        "stories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=False),
        sa.Column("credibility", sa.String(length=50), nullable=False),
        sa.Column("sources_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stories_created_at"), "stories", ["created_at"], unique=False)

    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_embeddings_text_hash"), "embeddings", ["text_hash"], unique=True)

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("link", sa.String(length=1000), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=False),
        sa.Column("published", sa.DateTime(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_points_json", sa.Text(), nullable=False),
        sa.Column("takeaway", sa.Text(), nullable=False),
        sa.Column("has_transcript", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_videos_video_id"), "videos", ["video_id"], unique=True)

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=300), nullable=False),
        sa.Column("interests", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "user_prefs",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_prefs")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("app_settings")
    op.drop_index(op.f("ix_videos_video_id"), table_name="videos")
    op.drop_table("videos")
    op.drop_index(op.f("ix_embeddings_text_hash"), table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index(op.f("ix_stories_created_at"), table_name="stories")
    op.drop_table("stories")
    op.drop_index(op.f("ix_digested_articles_link"), table_name="digested_articles")
    op.drop_table("digested_articles")
    op.drop_index(op.f("ix_alerts_sent_story_key"), table_name="alerts_sent")
    op.drop_table("alerts_sent")
    op.drop_index(op.f("ix_articles_link"), table_name="articles")
    op.drop_table("articles")