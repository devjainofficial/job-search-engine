"""Worker configuration loaded from the environment (.env at repo root or worker/)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env by absolute path (worker/.env, then repo-root .env) so settings
# load no matter which directory a script is launched from.
_WORKER_DIR = Path(__file__).resolve().parents[1]
_ENV_FILES = (_WORKER_DIR / ".env", _WORKER_DIR.parent / ".env")


class Settings(BaseSettings):
    # Supabase: the worker uses the service-role key because there are no RLS
    # policies yet (see migration note). Keep this key server-side only.
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key: str = Field("", alias="SUPABASE_ANON_KEY")

    # Gemini via LiteLLM for resume parsing (parse-once, never on daily runs).
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")

    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    # Optional shared secret Telegram echoes back on each webhook call.
    telegram_webhook_secret: str = Field("", alias="TELEGRAM_WEBHOOK_SECRET")

    # Adzuna (India + global). Optional: the adapter is disabled unless both are set.
    adzuna_app_id: str = Field("", alias="ADZUNA_APP_ID")
    adzuna_app_key: str = Field("", alias="ADZUNA_APP_KEY")

    # JSearch via RapidAPI (Indeed/LinkedIn/Glassdoor coverage). Optional, off
    # unless set. Free ~500 req/mo then PAID (see docs/RESEARCH.md).
    rapidapi_key: str = Field("", alias="RAPIDAPI_KEY")

    # Jooble + Careerjet: free-key India/global aggregators. Off unless set.
    jooble_api_key: str = Field("", alias="JOOBLE_API_KEY")
    careerjet_affid: str = Field("", alias="CAREERJET_AFFID")

    # Cap jobs per digest so a single run cannot spam a user.
    max_jobs_per_digest: int = Field(10, alias="MAX_JOBS_PER_DIGEST")

    # Cap jobs from any one company per digest so a single employer posting the
    # same role across many locations cannot dominate the digest.
    max_per_company: int = Field(2, alias="MAX_PER_COMPANY")

    # Delete job_cache rows older than this many days at the end of each run.
    cache_ttl_days: int = Field(14, alias="CACHE_TTL_DAYS")

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
