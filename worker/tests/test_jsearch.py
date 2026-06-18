"""JSearch adapter mapping tests (no network)."""

from app.models import APPLY_DIRECT, APPLY_JOB_DETAIL
from app.sources.jsearch import JSearchSource


def test_prefers_direct_apply_option():
    j = {
        "employer_name": "Acme", "job_title": "Full Stack Developer",
        "job_city": "Ahmedabad", "job_state": "Gujarat", "job_country": "IN",
        "job_apply_link": "https://indeed.com/x", "job_apply_is_direct": False,
        "apply_options": [{"publisher": "LinkedIn", "apply_link": "https://lnkd.in/x", "is_direct": True}],
        "job_description": "React, Node", "job_posted_at_datetime_utc": "2026-06-01T00:00:00Z", "job_id": "1",
    }
    job = JSearchSource()._to_canonical(j)
    assert job.company == "Acme"
    assert job.apply_url == "https://lnkd.in/x"
    assert job.apply_url_type == APPLY_DIRECT
    assert "Ahmedabad" in job.location and "Gujarat" in job.location


def test_falls_back_to_main_link():
    j = {
        "employer_name": "Globex", "job_title": "Backend Engineer", "job_country": "IN",
        "job_apply_link": "https://indeed.com/y", "job_apply_is_direct": False,
        "apply_options": [], "job_id": "2",
    }
    job = JSearchSource()._to_canonical(j)
    assert job.apply_url == "https://indeed.com/y"
    assert job.apply_url_type == APPLY_JOB_DETAIL


def test_remote_location():
    j = {"employer_name": "Remote Co", "job_title": "SRE", "job_is_remote": True,
         "job_apply_link": "https://x", "apply_options": [], "job_id": "3"}
    assert JSearchSource()._to_canonical(j).location == "Remote"
