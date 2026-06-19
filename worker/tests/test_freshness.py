"""Recency ranking + max-age filtering tests."""

from datetime import datetime, timedelta, timezone

from app.canonical import canonical_key
from app.matching import match_jobs, recency_boost
from app.models import CanonicalJob, Profile

NOW = datetime.now(timezone.utc)
ME = Profile(role_titles=["Software Engineer"])


def _job(company: str, days_old: int | None) -> CanonicalJob:
    posted = None if days_old is None else NOW - timedelta(days=days_old)
    return CanonicalJob(
        canonical_key=canonical_key(company, "Software Engineer", "Remote", company),
        source="test", title="Software Engineer", company=company, location="Remote",
        apply_url="https://x", description="Software Engineer", posted_at=posted,
    )


def test_recency_boost_tiers():
    assert recency_boost(NOW, NOW) == 3.0
    assert recency_boost(NOW - timedelta(days=2), NOW) == 2.0
    assert recency_boost(NOW - timedelta(days=5), NOW) == 1.0
    assert recency_boost(NOW - timedelta(days=30), NOW) == 0.0
    assert recency_boost(None, NOW) == 0.0


def test_max_age_drops_stale():
    jobs = [_job("FreshCo", 2), _job("StaleCo", 40)]
    locs = [m.job.company for m in match_jobs(jobs, ME, 10, max_age_days=30)]
    assert "FreshCo" in locs and "StaleCo" not in locs


def test_recent_ranks_first():
    jobs = [_job("OldCo", 12), _job("NewCo", 1)]
    matches = match_jobs(jobs, ME, 10)
    assert matches[0].job.company == "NewCo"  # fresh leads


def test_unknown_date_is_kept():
    jobs = [_job("NoDateCo", None)]
    assert len(match_jobs(jobs, ME, 10, max_age_days=30)) == 1
