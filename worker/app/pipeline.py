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
    get_suppressed_keys,
    get_user_for_run,
    prune_old_jobs,
    record_sent,
    upsert_jobs,
)
from app.matching import REMOTE_INCLUDE, SCOPE_MIX, match_jobs
from app.models import CanonicalJob, Profile
from app.sources._http import fetch_many
from app.sources.adzuna import AdzunaSource
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.ashby import AshbySource
from app.sources.careerjet import CareerjetSource
from app.sources.greenhouse import GreenhouseSource
from app.sources.jooble import JoobleSource
from app.sources.jsearch import JSearchSource
from app.sources.lever import LeverSource
from app.sources.remoteok import RemoteOKSource
from app.sources.remotive import RemotiveSource
from app.sources.serpapi_jobs import SerpApiJobsSource

# Query sources support server-side keyword search (fetched per distinct query).
# Adzuna, JSearch, Jooble, Careerjet, SerpApi are off unless their keys are set.
QUERY_SOURCES = [RemotiveSource(), AdzunaSource(), JSearchSource(), JoobleSource(),
                 CareerjetSource(), SerpApiJobsSource()]

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


_FRESHNESS_DAYS = {"24h": 1, "3days": 3, "week": 7}


def _max_age(prefs: dict, settings) -> int:
    """Map the user's freshness preference to a max posting age in days."""
    return _FRESHNESS_DAYS.get(prefs.get("freshness", ""), settings.max_job_age_days)


def _query_for_user(user: dict, profile: Profile) -> str:
    """One search term per user. Saved search wins; else first target role title."""
    for s in user.get("saved_searches") or []:
        if s.get("active") and s.get("query_terms"):
            return " ".join(s["query_terms"])
    return profile.role_titles[0] if profile.role_titles else ""


def _fetch_one_bulk(source) -> list[CanonicalJob]:
    try:
        return source.fetch_all()
    except Exception as exc:
        print(f"[run_daily] bulk source {source.name} failed: {exc}")
        return []


def _fetch_bulk() -> list[CanonicalJob]:
    """Fetch every bulk source once, concurrently. A failing source yields []."""
    return fetch_many(BULK_SOURCES, _fetch_one_bulk, max_workers=len(BULK_SOURCES))


def _fetch_query(query: str) -> list[CanonicalJob]:
    collected: list[CanonicalJob] = []
    for source in QUERY_SOURCES:
        try:
            collected.extend(source.fetch(query))
        except Exception as exc:
            print(f"[run_daily] query source {source.name} failed for '{query}': {exc}")
    return collected


def _fetch_adzuna_city(query: str, city: str) -> list[CanonicalJob]:
    """Fetch Adzuna for a specific city (where=city) to deepen city coverage.
    No-op if Adzuna keys are unset (the adapter returns [])."""
    try:
        return AdzunaSource().fetch(query, location=city)
    except Exception as exc:
        print(f"[run_daily] adzuna city fetch failed for '{query}'/'{city}': {exc}")
        return []


def run_for_user(user_id: str, limit: int | None = None, send: bool = True) -> dict:
    """On-demand run for a single user ("Find new jobs now"). Fetches the pools
    for their query + cities, matches with their prefs, dedups against history,
    optionally sends to Telegram, and records. Never resends old jobs."""
    settings = get_settings()
    u = get_user_for_run(user_id)
    if not u:
        return {"error": "user not found"}
    profile = _profile_of(u)
    query = _query_for_user(u, profile)
    if not query:
        return {"new_jobs": 0, "reason": "no parsed profile yet"}

    prefs = u.get("channel_prefs") or {}
    scope = prefs.get("location_scope", SCOPE_MIX)
    remote_mode = prefs.get("remote_mode", REMOTE_INCLUDE)
    cities = prefs.get("preferred_locations") or []

    candidates = _fetch_bulk() + _fetch_query(query)
    for city in cities:
        if city.strip():
            candidates += _fetch_adzuna_city(query, city.strip())
    upsert_jobs(candidates)

    skip = get_sent_keys(user_id) | get_suppressed_keys(user_id)
    fresh = [j for j in candidates if j.canonical_key not in skip]
    matches = match_jobs(
        fresh, profile, limit or settings.max_jobs_per_digest,
        max_per_company=settings.max_per_company,
        location_scope=scope, remote_mode=remote_mode, preferred_locations=cities,
        max_age_days=_max_age(prefs, settings),
    )

    delivered = False
    if matches:
        if send and u.get("telegram_chat_id"):
            from app.notify.telegram import send_digest
            send_digest(u["telegram_chat_id"], matches)
            delivered = True
        record_sent(user_id, [m.job.canonical_key for m in matches])
    return {"new_jobs": len(matches), "sent_to_telegram": delivered}


def _heal_unparsed() -> int:
    """Retry parsing for users whose résumé never finished parsing, so a transient
    failure at signup doesn't permanently exclude them from the daily digest."""
    from app.db import get_unparsed_users
    from app.services import parse_user_resume

    healed = 0
    for u in get_unparsed_users():
        try:
            if parse_user_resume(u["user_id"]):
                healed += 1
        except Exception as exc:
            print(f"[heal] parse retry failed for {u['user_id']}: {exc}")
    return healed


def run_daily() -> dict:
    settings = get_settings()
    _heal_unparsed()  # self-heal failed parses before matching
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

    # 2b. City-specific fetches: for users with preferred cities, pull Adzuna with
    # where=<city> so city filtering has real depth. Batched by (query, city).
    city_pairs: set[tuple[str, str]] = set()
    for u in users:
        q = user_queries.get(u["id"])
        if not q:
            continue
        for city in (u.get("channel_prefs") or {}).get("preferred_locations") or []:
            if city.strip():
                city_pairs.add((q, city.strip()))
    jobs_by_city: dict[tuple[str, str], list[CanonicalJob]] = {
        pair: _fetch_adzuna_city(*pair) for pair in city_pairs
    }

    all_jobs = list(bulk_pool)
    for jobs in jobs_by_query.values():
        all_jobs.extend(jobs)
    for jobs in jobs_by_city.values():
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

        # Location + remote preferences live in channel_prefs.
        prefs = u.get("channel_prefs") or {}
        scope = prefs.get("location_scope", SCOPE_MIX)
        remote_mode = prefs.get("remote_mode", REMOTE_INCLUDE)
        preferred_locations = prefs.get("preferred_locations") or []

        candidates = bulk_pool + jobs_by_query.get(query, [])
        for city in preferred_locations:
            candidates = candidates + jobs_by_city.get((query, city.strip()), [])

        skip = get_sent_keys(user_id) | get_suppressed_keys(user_id)
        fresh = [j for j in candidates if j.canonical_key not in skip]
        matches = match_jobs(
            fresh,
            profile,
            settings.max_jobs_per_digest,
            max_per_company=settings.max_per_company,
            location_scope=scope,
            remote_mode=remote_mode,
            preferred_locations=preferred_locations,
            max_age_days=_max_age(prefs, settings),
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

    # Keep job_cache bounded; safe because sent_jobs holds its own keys.
    pruned = prune_old_jobs(settings.cache_ttl_days)

    return {
        "distinct_queries": len(distinct_queries),
        "bulk_jobs": len(bulk_pool),
        "jobs_cached": len(all_jobs),
        "users_notified": users_notified,
        "jobs_sent": jobs_sent,
        "cache_pruned": pruned,
    }
