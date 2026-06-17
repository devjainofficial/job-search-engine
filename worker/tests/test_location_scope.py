"""Location-scope filtering and balanced-mix tests."""

from app.canonical import canonical_key
from app.matching import SCOPE_IN, SCOPE_MIX, SCOPE_OUT, match_jobs
from app.models import CanonicalJob, Profile

ME = Profile(role_titles=["Software Engineer"], location="Gandhinagar, Gujarat")


def _job(company: str, location: str) -> CanonicalJob:
    return CanonicalJob(
        canonical_key=canonical_key(company, "Software Engineer", location, company),
        source="test", title="Software Engineer", company=company,
        location=location, apply_url="https://x", description="Software Engineer",
    )


POOL = [
    _job("AcmeIN", "Bengaluru, India"),
    _job("BharatCo", "Pune, India"),
    _job("RemoteCo", "Remote"),
    _job("UsCo", "San Francisco, CA"),
    _job("EuCo", "Berlin, Germany"),
    _job("UkCo", "London, UK"),
]


def test_in_country_excludes_foreign():
    locs = [m.job.location for m in match_jobs(POOL, ME, limit=10, location_scope=SCOPE_IN)]
    assert all("India" in l or l == "Remote" for l in locs)
    assert not any(c in str(locs) for c in ("San Francisco", "Berlin", "London"))


def test_outside_only_excludes_home_and_remote():
    locs = [m.job.location for m in match_jobs(POOL, ME, limit=10, location_scope=SCOPE_OUT)]
    assert locs and all("India" not in l and l != "Remote" for l in locs)


def test_mix_balances_inside_and_outside():
    matches = match_jobs(POOL, ME, limit=4, location_scope=SCOPE_MIX)
    outside = sum(1 for m in matches if m.job.location in ("San Francisco, CA", "Berlin, Germany", "London, UK"))
    inside = len(matches) - outside
    assert len(matches) == 4
    # Equal split for an even limit when both sides have enough candidates.
    assert inside == 2 and outside == 2
