"""Supabase access for the worker (service-role client) plus small data helpers.

All DB access goes through here so adapters and the pipeline stay storage-agnostic.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings
from app.models import CanonicalJob, Profile


@lru_cache
def get_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


# --- users / profiles -------------------------------------------------------

def upsert_profile(user_id: str, profile: Profile, raw_resume_path: str | None) -> None:
    """Store the parsed resume once. parsed_at marks it so daily runs never re-parse."""
    get_client().table("profiles").upsert(
        {
            "user_id": user_id,
            "role_titles": profile.role_titles,
            "skills": profile.skills,
            "years_experience": profile.years_experience,
            "location": profile.location,
            "remote_pref": profile.remote_pref,
            "raw_resume_path": raw_resume_path,
            "parsed_at": "now()",
        }
    ).execute()


def get_active_users_with_profiles() -> list[dict]:
    """Users who can receive a digest: have a telegram_chat_id and a parsed profile."""
    users = (
        get_client()
        .table("users")
        .select("id, telegram_chat_id, profiles(*), saved_searches(*)")
        .not_.is_("telegram_chat_id", "null")
        .execute()
    )
    rows = []
    for u in users.data or []:
        profile = u.get("profiles")
        # supabase returns embedded one-to-one as a list or object depending on FK
        if isinstance(profile, list):
            profile = profile[0] if profile else None
        if profile and profile.get("parsed_at"):
            rows.append(u)
    return rows


# --- job_cache --------------------------------------------------------------

def upsert_jobs(jobs: list[CanonicalJob]) -> None:
    """Cache fetched jobs by canonical_key so one query serves many users."""
    if not jobs:
        return
    payload = [
        {
            "canonical_key": j.canonical_key,
            "source": j.source,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "apply_url": j.apply_url,
            "apply_url_type": j.apply_url_type,
            "posted_at": j.posted_at.isoformat() if j.posted_at else None,
            "raw_payload": j.raw_payload,
            "fetched_at": "now()",
        }
        for j in jobs
    ]
    get_client().table("job_cache").upsert(payload).execute()


# --- sent_jobs (dedup ledger) ----------------------------------------------

def get_sent_keys(user_id: str) -> set[str]:
    res = (
        get_client()
        .table("sent_jobs")
        .select("canonical_key")
        .eq("user_id", user_id)
        .execute()
    )
    return {r["canonical_key"] for r in (res.data or [])}


def record_sent(user_id: str, canonical_keys: list[str], channel: str = "telegram") -> None:
    """Mark jobs as sent. Composite PK makes repeated inserts idempotent."""
    if not canonical_keys:
        return
    payload = [
        {"user_id": user_id, "canonical_key": k, "channel": channel}
        for k in canonical_keys
    ]
    # ignore_duplicates: a concurrent run must not error on the PK conflict
    get_client().table("sent_jobs").upsert(payload, ignore_duplicates=True).execute()
