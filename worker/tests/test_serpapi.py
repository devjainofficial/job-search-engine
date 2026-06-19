"""SerpApi Google Jobs adapter mapping tests (no network)."""

from app.models import APPLY_JOB_DETAIL
from app.sources.serpapi_jobs import SerpApiJobsSource, _parse_relative


def test_mapping_uses_first_apply_option():
    j = {
        "title": "Software Engineer", "company_name": "Zoom", "location": "India",
        "description": "Build stuff", "via": "via Zoom Careers", "job_id": "abc",
        "apply_options": [{"title": "Zoom Careers", "link": "https://zoom.us/jobs/1"}],
        "detected_extensions": {"posted_at": "2 days ago"},
    }
    job = SerpApiJobsSource()._to_canonical(j)
    assert job.company == "Zoom" and job.title == "Software Engineer"
    assert job.apply_url == "https://zoom.us/jobs/1"
    assert job.apply_url_type == APPLY_JOB_DETAIL
    assert job.source == "google_jobs"
    assert job.posted_at is not None


def test_parse_relative():
    assert _parse_relative("today") is not None
    assert _parse_relative("5 hours ago") is not None
    assert _parse_relative("3 days ago") is not None
    assert _parse_relative(None) is None
