"""Remote-mode filtering tests, including combination with location scope."""

from app.canonical import canonical_key
from app.matching import (
    REMOTE_NO,
    REMOTE_ONLY,
    SCOPE_IN,
    match_jobs,
)
from app.models import CanonicalJob, Profile

ME = Profile(role_titles=["Software Engineer"], location="Gandhinagar, Gujarat")


def _job(company: str, location: str) -> CanonicalJob:
    return CanonicalJob(
        canonical_key=canonical_key(company, "Software Engineer", location, company),
        source="test", title="Software Engineer", company=company,
        location=location, apply_url="https://x", description="Software Engineer",
    )


POOL = [
    _job("OnsiteIN", "Bengaluru, India"),
    _job("RemoteIN", "Remote, India"),
    _job("OpenRemote", "Remote"),
    _job("OnsiteUS", "San Francisco, CA"),
]


def test_only_remote_keeps_remote_roles():
    locs = [m.job.location for m in match_jobs(POOL, ME, 10, remote_mode=REMOTE_ONLY)]
    assert set(locs) == {"Remote, India", "Remote"}


def test_no_remote_keeps_onsite_roles():
    locs = [m.job.location for m in match_jobs(POOL, ME, 10, remote_mode=REMOTE_NO)]
    assert set(locs) == {"Bengaluru, India", "San Francisco, CA"}


def test_only_remote_within_country_combines_both_filters():
    # only_remote AND in_country -> remote roles takeable from India.
    locs = [m.job.location for m in
            match_jobs(POOL, ME, 10, location_scope=SCOPE_IN, remote_mode=REMOTE_ONLY)]
    assert set(locs) == {"Remote, India", "Remote"}


def test_no_remote_within_country_is_india_onsite():
    locs = [m.job.location for m in
            match_jobs(POOL, ME, 10, location_scope=SCOPE_IN, remote_mode=REMOTE_NO)]
    assert set(locs) == {"Bengaluru, India"}
