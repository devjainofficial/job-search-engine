"""City-specific (preferred_locations) filtering tests."""

from app.canonical import canonical_key
from app.matching import REMOTE_NO, match_jobs
from app.models import CanonicalJob, Profile

ME = Profile(role_titles=["Software Engineer"], location="Ahmedabad, Gujarat")


def _job(company: str, location: str) -> CanonicalJob:
    return CanonicalJob(
        canonical_key=canonical_key(company, "Software Engineer", location, company),
        source="test", title="Software Engineer", company=company,
        location=location, apply_url="https://x", description="Software Engineer",
    )


POOL = [
    _job("AmdCo", "Ahmedabad, Gujarat"),
    _job("AmdTwo", "Ahmedabad"),
    _job("PuneCo", "Pune, India"),
    _job("RemoteCo", "Remote"),
    _job("UsCo", "San Francisco, CA"),
]


def test_city_filter_keeps_city_plus_remote():
    locs = [m.job.location for m in match_jobs(POOL, ME, 10, preferred_locations=["Ahmedabad"])]
    assert "Ahmedabad, Gujarat" in locs and "Ahmedabad" in locs
    assert "Remote" in locs  # remote is takeable from the city
    assert "Pune, India" not in locs and "San Francisco, CA" not in locs


def test_city_matches_rank_above_remote():
    matches = match_jobs(POOL, ME, 10, preferred_locations=["ahmedabad"])
    # The two Ahmedabad roles should come before the generic remote one.
    amd = [i for i, m in enumerate(matches) if "Ahmedabad" in (m.job.location or "")]
    remote = [i for i, m in enumerate(matches) if m.job.location == "Remote"]
    assert max(amd) < min(remote)


def test_city_with_no_remote_is_city_onsite_only():
    locs = [m.job.location for m in
            match_jobs(POOL, ME, 10, preferred_locations=["Ahmedabad"], remote_mode=REMOTE_NO)]
    assert set(locs) == {"Ahmedabad, Gujarat", "Ahmedabad"}


def test_multiple_cities():
    locs = [m.job.location for m in match_jobs(POOL, ME, 10, preferred_locations=["pune", "ahmedabad"])]
    assert "Pune, India" in locs and "Ahmedabad" in locs
