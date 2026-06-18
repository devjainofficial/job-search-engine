"""Mapping tests for Jooble and Careerjet adapters (no network)."""

from app.models import APPLY_JOB_DETAIL
from app.sources.careerjet import CareerjetSource
from app.sources.jooble import JoobleSource


def test_jooble_mapping():
    j = {"title": "Full Stack Developer", "company": "Acme", "location": "Ahmedabad",
         "snippet": "React Node", "link": "https://jooble.org/x", "id": "1", "updated": "2026-06-01T00:00:00.0000000"}
    job = JoobleSource()._to_canonical(j)
    assert job.company == "Acme" and job.title == "Full Stack Developer"
    assert job.apply_url == "https://jooble.org/x"
    assert job.apply_url_type == APPLY_JOB_DETAIL


def test_careerjet_mapping():
    j = {"title": "Backend Engineer", "company": "Globex", "locations": "Pune",
         "description": "Django", "url": "https://careerjet/x", "site": "naukri.com"}
    job = CareerjetSource()._to_canonical(j)
    assert job.company == "Globex" and job.location == "Pune"
    assert job.apply_url == "https://careerjet/x"
    assert job.apply_url_type == APPLY_JOB_DETAIL
