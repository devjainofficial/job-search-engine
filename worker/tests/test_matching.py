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
    # One company posts several DISTINCT software roles (distinct titles -> distinct
    # keys, so dedupe keeps them); the per-company cap should still limit to 2.
    flood = [_job("LawnStarter", f"Software Engineer {team}", "Remote")
             for team in ("Payments", "Search", "Growth", "Platform", "Mobile", "Data")]
    others = [_job("Acme", "Software Engineer", "Remote"),
              _job("Globex", "Software Engineer", "Remote")]
    profile = Profile(role_titles=["Software Engineer"])

    matches = match_jobs(flood + others, profile, limit=10, max_per_company=2)

    companies = [m.job.company for m in matches]
    assert companies.count("LawnStarter") == 2  # capped, not 6
    assert "Acme" in companies and "Globex" in companies


def test_same_role_from_two_sources_dedupes_to_one():
    # Same company+title from two providers (different apply types) -> one entry,
    # keeping the direct-apply variant.
    a = _job("Zoom", "Software Engineer", "India")          # job_detail by default
    a.apply_url_type = "job_detail"; a.apply_url = "https://serpapi/x"
    b = _job("Zoom", "Software Engineer", "Bengaluru, IN")
    b.apply_url_type = "direct_apply"; b.apply_url = "https://zoom.us/apply"
    profile = Profile(role_titles=["Software Engineer"])
    matches = match_jobs([a, b], profile, limit=10)
    assert len(matches) == 1
    assert matches[0].job.apply_url == "https://zoom.us/apply"  # best variant kept


def test_limit_is_respected_after_cap():
    jobs = [_job(f"Co{i}", "Software Engineer", "Remote") for i in range(10)]
    profile = Profile(role_titles=["Software Engineer"])
    matches = match_jobs(jobs, profile, limit=3, max_per_company=2)
    assert len(matches) == 3


def test_skill_only_match_does_not_qualify():
    # Unrelated title, but the description name-drops the user's skills.
    job = CanonicalJob(
        canonical_key="k",
        source="test",
        title="Business Transformation Lead",
        company="Acme",
        location="Remote",
        apply_url="https://example.com",
        description="We use Python, Django, AWS, React every day.",
    )
    profile = Profile(role_titles=["Software Engineer"], skills=["Python", "Django", "AWS", "React"])
    assert match_jobs([job], profile, limit=10) == []


def test_short_generic_token_does_not_leak():
    # "ai" must not match an unrelated "AI ..." title.
    job = _job("EverAI", "AI Cinematic Video Editor", "Remote")
    profile = Profile(role_titles=["AI/LLM Developer"])
    assert match_jobs([job], profile, limit=10) == []


def test_specific_token_in_title_qualifies():
    job = _job("Acme", "Senior Full-Stack Engineer", "Remote")
    profile = Profile(role_titles=["Full-Stack Developer"])
    matches = match_jobs([job], profile, limit=10)
    assert len(matches) == 1


def test_tech_title_with_skills_qualifies_tier2():
    # "Frontend Developer" is not a stated role, but it is a technical IC title
    # and the description matches the user's skills -> should qualify.
    job = CanonicalJob(
        canonical_key="k",
        source="test",
        title="Frontend Developer",
        company="Acme",
        location="Remote",
        apply_url="https://example.com",
        description="React, TypeScript, Next.js and Redux experience required.",
    )
    profile = Profile(
        role_titles=["Full-Stack Developer"],
        skills=["React.js", "TypeScript", "Next.js", "Redux"],
    )
    assert len(match_jobs([job], profile, limit=10)) == 1


def test_tech_title_without_skill_overlap_is_dropped():
    job = CanonicalJob(
        canonical_key="k",
        source="test",
        title="Embedded Firmware Developer",
        company="Acme",
        location="Remote",
        apply_url="https://example.com",
        description="C, C++, RTOS, hardware bring-up.",
    )
    profile = Profile(role_titles=["Full-Stack Developer"], skills=["React", "Node.js"])
    assert match_jobs([job], profile, limit=10) == []


def test_non_technical_title_never_qualifies_on_skills():
    job = CanonicalJob(
        canonical_key="k",
        source="test",
        title="Head of Sales",
        company="Acme",
        location="Remote",
        apply_url="https://example.com",
        description="We are a React and Node.js shop.",
    )
    profile = Profile(role_titles=["Software Engineer"], skills=["React", "Node.js"])
    assert match_jobs([job], profile, limit=10) == []


def test_full_role_phrase_outranks_partial():
    exact = _job("Acme", "Backend Developer", "Remote")
    partial = _job("Globex", "Backend Operations Manager", "Remote")
    profile = Profile(role_titles=["Backend Developer"])
    matches = match_jobs([partial, exact], profile, limit=10)
    assert matches[0].job.company == "Acme"  # exact phrase ranks first
