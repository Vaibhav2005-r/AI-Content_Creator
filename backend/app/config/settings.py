# Application settings
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Centralised application settings loaded from environment variables."""

    # ── Server ────────────────────────────────────────
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # ── Database ──────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bharat_content_ai.db")

    # ── Google Gemini (currently active) ──────────────
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    # ── OpenAI (optional fallback) ────────────────────
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

    # ── AWS Core ──────────────────────────────────────
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_BEARER_TOKEN_BEDROCK: str | None = os.getenv("AWS_BEARER_TOKEN_BEDROCK")

    # ── AWS Service Regions ───────────────────────────
    BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", "us-east-1")
    TRANSLATE_REGION: str = os.getenv("TRANSLATE_REGION", "us-east-1")
    TRANSCRIBE_REGION: str = os.getenv("TRANSCRIBE_REGION", "us-east-1")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

    # ── S3 ────────────────────────────────────────────
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "bharat-content-ai-media")

    # ── Social Media API Keys ─────────────────────────
    TWITTER_API_KEY: str | None = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET: str | None = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN: str | None = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET: str | None = os.getenv("TWITTER_ACCESS_SECRET")

    FACEBOOK_API_KEY: str | None = os.getenv("FACEBOOK_API_KEY")
    INSTAGRAM_API_KEY: str | None = os.getenv("INSTAGRAM_API_KEY")
    LINKEDIN_API_KEY: str | None = os.getenv("LINKEDIN_API_KEY")
    YOUTUBE_API_KEY: str | None = os.getenv("YOUTUBE_API_KEY")

    # ── Helper flags ──────────────────────────────────
    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY != "your_gemini_api_key_here")

    @property
    def has_aws_credentials(self) -> bool:
        return bool(self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY)

    @property
    def has_bedrock_bearer(self) -> bool:
        return bool(self.AWS_BEARER_TOKEN_BEDROCK)

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)


# Singleton instance used across the app
settings = Settings()
