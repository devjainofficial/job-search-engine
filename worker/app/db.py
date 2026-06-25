"""Supabase access for the worker (service-role client) plus small data helpers.

All DB access goes through here so adapters and the pipeline stay storage-agnostic.
"""

from datetime import datetime, timedelta, timezone
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


_RESUME_BUCKET = "resumes"


def chat_id_in_use_by_other(chat_id: str, user_id: str) -> bool:
    """True if this Telegram chat is already linked to a different account."""
    res = (
        get_client()
        .table("users")
        .select("id")
        .eq("telegram_chat_id", chat_id)
        .neq("id", user_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def set_telegram_chat_id(user_id: str, chat_id: str) -> str | None:
    """Store the chat_id for a user (called after a verified connect token).
    Returns the user_id if the row exists, else None."""
    res = (
        get_client()
        .table("users")
        .update({"telegram_chat_id": chat_id})
        .eq("id", user_id)
        .execute()
    )
    return res.data[0]["id"] if res.data else None


def get_sent_jobs_detail(user_id: str, limit: int = 50) -> list[dict]:
    """Recent jobs sent to a user, joined with their cached details, newest first.
    Powers the dashboard. Cache pruning may drop older rows; those are skipped."""
    client = get_client()
    sent = (
        client.table("sent_jobs")
        .select("canonical_key, sent_at")
        .eq("user_id", user_id)
        .order("sent_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = sent.data or []
    if not rows:
        return []
    keys = [r["canonical_key"] for r in rows]
    cache: dict[str, dict] = {}
    for i in range(0, len(keys), 50):
        chunk = (
            client.table("job_cache")
            .select("canonical_key, title, company, location, apply_url, apply_url_type, source")
            .in_("canonical_key", keys[i : i + 50])
            .execute()
        )
        for c in chunk.data or []:
            cache[c["canonical_key"]] = c
    out = []
    for r in rows:
        job = cache.get(r["canonical_key"])
        if job:
            out.append({**job, "sent_at": r["sent_at"]})
    return out


def get_profile(user_id: str) -> dict | None:
    res = get_client().table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
    return res.data[0] if res.data else None


def get_cached_job(canonical_key: str) -> dict | None:
    res = (
        get_client()
        .table("job_cache")
        .select("title, company, location, description, apply_url, source")
        .eq("canonical_key", canonical_key)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_raw_resume_path(user_id: str) -> str | None:
    res = get_client().table("profiles").select("raw_resume_path").eq("user_id", user_id).execute()
    return res.data[0]["raw_resume_path"] if res.data else None


def download_resume(path: str) -> bytes:
    return get_client().storage.from_(_RESUME_BUCKET).download(path)


def get_unparsed_users() -> list[dict]:
    """Profiles that have an uploaded résumé but never finished parsing (e.g. a
    transient Gemini error). Used to self-heal on the daily run."""
    res = (
        get_client()
        .table("profiles")
        .select("user_id, raw_resume_path")
        .is_("parsed_at", "null")
        .not_.is_("raw_resume_path", "null")
        .execute()
    )
    return res.data or []


def get_user_for_run(user_id: str) -> dict | None:
    """Load one user (with profile + saved searches) for an on-demand run."""
    res = (
        get_client()
        .table("users")
        .select("id, telegram_chat_id, channel_prefs, profiles(*), saved_searches(*)")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_active_users_with_profiles() -> list[dict]:
    """Users who can receive a digest: have a telegram_chat_id and a parsed profile."""
    users = (
        get_client()
        .table("users")
        .select("id, telegram_chat_id, channel_prefs, profiles(*), saved_searches(*)")
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

_UPSERT_CHUNK = 500


def upsert_jobs(jobs: list[CanonicalJob]) -> None:
    """Cache fetched jobs by canonical_key so one fetch serves many users.

    Deduplicate by canonical_key within the batch (board sources can return the
    same job twice) and chunk the upsert so large board pulls stay under request
    size limits.
    """
    if not jobs:
        return
    by_key: dict[str, CanonicalJob] = {j.canonical_key: j for j in jobs}
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
            "description": (j.description or "")[:8000],  # for AI apply-assist
            "raw_payload": j.raw_payload,
            "fetched_at": "now()",
        }
        for j in by_key.values()
    ]
    client = get_client()
    for i in range(0, len(payload), _UPSERT_CHUNK):
        client.table("job_cache").upsert(payload[i : i + _UPSERT_CHUNK]).execute()


# --- sent_jobs (dedup ledger) ----------------------------------------------

def consume_quota(provider: str, cap: int) -> bool:
    """Soft monthly rate guard for metered APIs (JSearch, SerpApi). Returns True
    and increments the counter if under cap, else False (caller should skip).
    cap <= 0 means unlimited."""
    if cap <= 0:
        return True
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    client = get_client()
    res = client.table("api_usage").select("count").eq("provider", provider).eq("yyyymm", yyyymm).limit(1).execute()
    cur = res.data[0]["count"] if res.data else 0
    if cur >= cap:
        return False
    client.table("api_usage").upsert(
        {"provider": provider, "yyyymm": yyyymm, "count": cur + 1},
        on_conflict="provider,yyyymm",
    ).execute()
    return True


def prune_old_jobs(days: int) -> int:
    """Delete job_cache rows older than `days`. Safe for dedup: sent_jobs keeps
    its own canonical_keys, so pruning the cache never causes a resend."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = get_client().table("job_cache").delete().lt("fetched_at", cutoff).execute()
    return len(res.data or [])


# --- delete-my-data (DPDP) --------------------------------------------------

def delete_user_data(user_id: str) -> dict:
    """Erase a user and all derived personal data. Returns what was removed.

    profiles/saved_searches/sent_jobs cascade from the users row; the raw resume
    file in Storage (if any) is removed first since it is not in Postgres."""
    client = get_client()
    removed_resume = False
    prof = client.table("profiles").select("raw_resume_path").eq("user_id", user_id).execute().data
    if prof and prof[0].get("raw_resume_path"):
        try:
            client.storage.from_("resumes").remove([prof[0]["raw_resume_path"]])
            removed_resume = True
        except Exception as exc:
            print(f"[delete_user_data] storage remove failed: {exc}")
    client.table("users").delete().eq("id", user_id).execute()
    return {"user_id": user_id, "deleted": True, "raw_resume_removed": removed_resume}


def get_sent_keys(user_id: str) -> set[str]:
    res = (
        get_client()
        .table("sent_jobs")
        .select("canonical_key")
        .eq("user_id", user_id)
        .execute()
    )
    return {r["canonical_key"] for r in (res.data or [])}


def get_suppressed_keys(user_id: str) -> set[str]:
    """Jobs the user thumbed down — never show these again."""
    res = (
        get_client()
        .table("job_actions")
        .select("canonical_key")
        .eq("user_id", user_id)
        .eq("feedback", "down")
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
