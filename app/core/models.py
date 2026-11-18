from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ArticleDB(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(100))
    published: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    image_url: Mapped[str] = mapped_column(String(1000), default="")


class AlertDB(Base):
    """Jin stories ka breaking alert ja chuka hai (dobara na bhejne ke liye)."""

    __tablename__ = "alerts_sent"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_key: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DigestedDB(Base):
    """Jo articles kisi daily digest me ja chuke hain."""

    __tablename__ = "digested_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    link: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    digested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StoryDB(Base):
    """Digest ki stories (API, dashboard aur research chat ke liye)."""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    credibility: Mapped[str] = mapped_column(String(50), default="Single source")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    claims_json: Mapped[str] = mapped_column(Text, default="[]")
    image_url: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class EmbeddingDB(Base):
    """Documents ke embeddings ka cache (dobara API call se bachne ke liye)."""

    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    text_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(100))
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VideoDB(Base):
    """YouTube videos ki summaries."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(1000))
    channel: Mapped[str] = mapped_column(String(100))
    published: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    key_points_json: Mapped[str] = mapped_column(Text, default="[]")
    takeaway: Mapped[str] = mapped_column(Text, default="")
    has_transcript: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SettingDB(Base):
    """Chhoti key/value settings jo dashboard se badalti hain (jaise interests)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserDB(Base):
    """Registered users (email, password hash, apni interests)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    interests: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserPrefDB(Base):
    """Per-user delivery settings (abhi: daily digest email on/off)."""

    __tablename__ = "user_prefs"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    digest_enabled: Mapped[bool] = mapped_column(default=False)
    telegram_chat_id: Mapped[str] = mapped_column(String(64), default="")
    digest_hour: Mapped[Optional[int]] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserSourceDB(Base):
    """User ke apne RSS feeds aur YouTube channels."""

    __tablename__ = "user_sources"
    __table_args__ = (UniqueConstraint("user_id", "kind", "url", name="uq_user_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BookmarkDB(Base):
    """Stories a user saved."""

    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_user_bookmark"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    story_id: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PipelineRunDB(Base):
    """History of scheduler, API and CLI job runs (digest, alerts, videos, weekly...)."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job: Mapped[str] = mapped_column(String(50), index=True)
    ok: Mapped[bool] = mapped_column(default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    duration_ms: Mapped[int] = mapped_column(default=0)
    detail: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(String(300), default="")


class StoryReadDB(Base):
    """Stories a user marked as read."""

    __tablename__ = "story_reads"
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_user_story_read"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    story_id: Mapped[int] = mapped_column(index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceHealthDB(Base):
    """Last collection result per source (feed or channel)."""

    __tablename__ = "source_health"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_ok_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_items: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str] = mapped_column(String(300), default="")


class ApiKeyDB(Base):
    """Extra Gemini API keys added from the dashboard."""

    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("key", name="uq_api_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
