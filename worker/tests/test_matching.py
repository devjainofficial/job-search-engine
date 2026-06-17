"""Matching tests, focused on the per-company diversity cap."""

from app.canonical import canonical_key
from app.matching import match_jobs
from app.models import CanonicalJob, Profile


def _job(company: str, title: str, location: str) -> CanonicalJob:
    return CanonicalJob(
        canonical_key=canonical_key(company, title, location, title),
        source="test",
        title=title,
        company=company,
        location=location,
        apply_url="https://example.com",
        description=title,
    )


def test_per_company_cap_limits_one_employer():
    # One company posts the same role across six cities.
    flood = [_job("LawnStarter", "Software Engineer", city)
             for city in ("Belo", "Floria", "Porto", "Sao Paulo", "Campinas", "Recife")]
    others = [_job("Acme", "Software Engineer", "Remote"),
              _job("Globex", "Software Engineer", "Remote")]
    profile = Profile(role_titles=["Software Engineer"])

    matches = match_jobs(flood + others, profile, limit=10, max_per_company=2)

    companies = [m.job.company for m in matches]
    assert companies.count("LawnStarter") == 2  # capped, not 6
    assert "Acme" in companies and "Globex" in companies


def test_limit_is_respected_after_cap():
    jobs = [_job(f"Co{i}", "Software Engineer", "Remote") for i in range(10)]
    profile = Profile(role_titles=["Software Engineer"])
    matches = match_jobs(jobs, profile, limit=3, max_per_company=2)
    assert len(matches) == 3
