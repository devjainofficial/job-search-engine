"""Worker configuration loaded from the environment (.env at repo root or worker/)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Supabase: the worker uses the service-role key because there are no RLS
    # policies yet (see migration note). Keep this key server-side only.
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key: str = Field("", alias="SUPABASE_ANON_KEY")

    # Gemini via LiteLLM for resume parsing (parse-once, never on daily runs).
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")

    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")

    # Cap jobs per digest so a single run cannot spam a user.
    max_jobs_per_digest: int = Field(10, alias="MAX_JOBS_PER_DIGEST")

    model_config = SettingsConfigDict(
        # Look for .env in worker/ first, then the repo root.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
