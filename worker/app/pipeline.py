"""Daily run orchestration: batch-by-shared-query, match, dedup, notify.

The critical rule here is to NOT loop per user per source. We collect the set of
distinct queries across all users, fetch each query once, cache it, then match the
cached jobs to each user in memory. 500 users sharing a few role clusters cost a
few API calls, not thousands.
"""

from app.config import get_settings
from app.db import (
    get_active_users_with_profiles,
    get_sent_keys,
    record_sent,
    upsert_jobs,
)
from app.matching import match_jobs
from app.models import CanonicalJob, Profile
from app.sources.remotive import RemotiveSource

# Active sources for slice 1. Add adapters here as they are built.
SOURCES = [RemotiveSource()]


def _profile_of(user: dict) -> Profile:
    p = user.get("profiles")
    if isinstance(p, list):
        p = p[0] if p else {}
    p = p or {}
    return Profile(
        role_titles=p.get("role_titles") or [],
        skills=p.get("skills") or [],
        years_experience=p.get("years_experience"),
        location=p.get("location"),
        remote_pref=p.get("remote_pref"),
    )


def _query_for_user(user: dict, profile: Profile) -> str:
    """One search term per user. Saved search wins; else first target role title."""
    for s in user.get("saved_searches") or []:
        if s.get("active") and s.get("query_terms"):
            return " ".join(s["query_terms"])
    return profile.role_titles[0] if profile.role_titles else ""


def run_daily() -> dict:
    settings = get_settings()
    users = get_active_users_with_profiles()

    # 1. Build the set of distinct queries across all users.
    user_queries: dict[str, str] = {}
    for u in users:
        profile = _profile_of(u)
        query = _query_for_user(u, profile)
        if query:
            user_queries[u["id"]] = query
    distinct_queries = sorted(set(user_queries.values()))

    # 2. Fetch each distinct query once, cache results (in memory + job_cache).
    jobs_by_query: dict[str, list[CanonicalJob]] = {}
    jobs_cached = 0
    for query in distinct_queries:
        collected: list[CanonicalJob] = []
        for source in SOURCES:
            try:
                collected.extend(source.fetch(query))
            except Exception as exc:  # one bad source must not kill the run
                print(f"[run_daily] source {source.name} failed for '{query}': {exc}")
        jobs_by_query[query] = collected
        upsert_jobs(collected)
        jobs_cached += len(collected)

    # 3. Match cached jobs to each user in memory, dedup, send.
    users_notified = 0
    jobs_sent = 0
    for u in users:
        user_id = u["id"]
        query = user_queries.get(user_id)
        if not query:
            continue
        profile = _profile_of(u)
        candidates = jobs_by_query.get(query, [])

        sent_keys = get_sent_keys(user_id)
        fresh = [j for j in candidates if j.canonical_key not in sent_keys]
        matches = match_jobs(fresh, profile, settings.max_jobs_per_digest)
        if not matches:
            continue

        from app.notify.telegram import send_digest  # local import: optional dep path

        # Send first, then record. A send failure leaves nothing recorded so the
        # jobs retry next run (better than marking-then-failing and losing them).
        # The composite PK keeps record_sent idempotent against rare double-runs.
        send_digest(u["telegram_chat_id"], matches)
        record_sent(user_id, [m.job.canonical_key for m in matches])
        users_notified += 1
        jobs_sent += len(matches)

    return {
        "distinct_queries": len(distinct_queries),
        "jobs_cached": jobs_cached,
        "users_notified": users_notified,
        "jobs_sent": jobs_sent,
    }
