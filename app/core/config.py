from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "AI Briefing Agent"
    debug: bool = True

    # LLM
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    # Email
    email_sender: str = ""
    email_password: str = ""
    email_receiver: str = ""

    # Scheduler (24-hour format, HH:MM, aapke PC ka local time)
    digest_time: str = "08:00"
    # Breaking alert check har kitne minute baad chale
    alert_interval_minutes: int = 30

    # Research chat: embeddings (semantic search)
    use_embeddings: bool = True
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    semantic_min_score: float = 0.55

    # YouTube videos digest me
    include_videos: bool = True
    video_max_per_digest: int = 3

    # Weekly Intelligence Report (day: mon, tue, wed, thu, fri, sat, sun)
    weekly_enabled: bool = True
    weekly_day: str = "sun"
    weekly_time: str = "09:00"

    # Database: default SQLite; hosted deployments can use a PostgreSQL URL
    database_url: str = "sqlite:///briefing.db"

    # Security (khali = band, local development ke liye)
    # Personalization: comma-separated keywords, e.g. cricket, ai, pakistan
    interests: str = ""

    api_key: str = ""
    dashboard_password: str = ""

    # User accounts: token signing secret (khali = login band), token ki umr (ghante)
    auth_secret: str = ""
    auth_token_hours: int = 72

    # Email HTTPS API se (cloud ke liye). Khali = Gmail SMTP (local)
    resend_api_key: str = ""
    resend_from: str = "AI Briefing <onboarding@resend.dev>"

    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 300
    trust_proxy_headers: bool = False
    log_level: str = "INFO"
    log_json: bool = True

    # Data retention: itne din se purane articles/embeddings delete (0 = band)
    retention_days: int = 90

    # Read-only public demo: sirf padhne wale requests chalte hain
    demo_mode: bool = False

    # Error alerts (Telegram + email); ek hi error ka alert cooldown ke baad dobara
    error_alerts: bool = True
    error_alert_cooldown_minutes: int = 60

    # Research agent: khali sub-question ke liye ek follow-up search
    research_followup: bool = True

    # Research report me web sources (billed Gemini key chahiye, default band)
    research_web: bool = False

    # Digest email me web check (billed Gemini key chahiye, default band)
    digest_web_check: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
