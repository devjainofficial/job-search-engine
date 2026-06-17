"""Daily run orchestration: batch-by-shared-query, match, dedup, notify.

The critical rule is to NOT loop per user per source. Query sources are fetched
once per distinct user query; bulk sources (firehoses and ATS boards) are fetched
once total. Everything is cached, then matched to each user in memory. 500 users
sharing a few role clusters cost a handful of fetches, not thousands.
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
from app.sources.adzuna import AdzunaSource
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.ashby import AshbySource
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource
from app.sources.remoteok import RemoteOKSource
from app.sources.remotive import RemotiveSource

# Query sources support server-side keyword search (fetched per distinct query).
QUERY_SOURCES = [RemotiveSource(), AdzunaSource()]

# Bulk sources return a firehose or whole company boards (fetched once per run).
BULK_SOURCES = [RemoteOKSource(), ArbeitnowSource(),
                GreenhouseSource(), LeverSource(), AshbySource()]


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


def _fetch_bulk() -> list[CanonicalJob]:
    """Fetch every bulk source once. One failing source must not kill the run."""
    pool: list[CanonicalJob] = []
    for source in BULK_SOURCES:
        try:
            pool.extend(source.fetch_all())
        except Exception as exc:
            print(f"[run_daily] bulk source {source.name} failed: {exc}")
    return pool


def _fetch_query(query: str) -> list[CanonicalJob]:
    collected: list[CanonicalJob] = []
    for source in QUERY_SOURCES:
        try:
            collected.extend(source.fetch(query))
        except Exception as exc:
            print(f"[run_daily] query source {source.name} failed for '{query}': {exc}")
    return collected


def run_daily() -> dict:
    settings = get_settings()
    users = get_active_users_with_profiles()

    # 1. Distinct queries across all users.
    user_queries: dict[str, str] = {}
    for u in users:
        query = _query_for_user(u, _profile_of(u))
        if query:
            user_queries[u["id"]] = query
    distinct_queries = sorted(set(user_queries.values()))

    # 2. Fetch bulk sources once, query sources once per distinct query. Cache all.
    bulk_pool = _fetch_bulk()
    jobs_by_query: dict[str, list[CanonicalJob]] = {q: _fetch_query(q) for q in distinct_queries}

    all_jobs = list(bulk_pool)
    for jobs in jobs_by_query.values():
        all_jobs.extend(jobs)
    upsert_jobs(all_jobs)

    # 3. Match the combined pool to each user in memory, dedup, send.
    users_notified = 0
    jobs_sent = 0
    for u in users:
        user_id = u["id"]
        query = user_queries.get(user_id)
        if not query:
            continue
        profile = _profile_of(u)
        candidates = bulk_pool + jobs_by_query.get(query, [])

        sent_keys = get_sent_keys(user_id)
        fresh = [j for j in candidates if j.canonical_key not in sent_keys]
        matches = match_jobs(
            fresh,
            profile,
            settings.max_jobs_per_digest,
            max_per_company=settings.max_per_company,
        )
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
        "bulk_jobs": len(bulk_pool),
        "jobs_cached": len(all_jobs),
        "users_notified": users_notified,
        "jobs_sent": jobs_sent,
    }
