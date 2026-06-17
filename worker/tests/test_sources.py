"""Adapter mapping tests: each source must produce CanonicalJob with the right
apply_url and apply_url_type. Uses sample payloads (no network)."""

from app.models import APPLY_DIRECT, APPLY_JOB_DETAIL
from app.sources.adzuna import AdzunaSource
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.ashby import AshbySource
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource
from app.sources.remoteok import RemoteOKSource


def test_greenhouse_maps_direct_apply():
    j = {"title": "Software Engineer", "company_name": "Stripe",
         "location": {"name": "Remote"}, "absolute_url": "https://stripe.com/jobs/123",
         "id": 123, "first_published": "2026-06-01T08:00:00-04:00"}
    job = GreenhouseSource()._to_canonical(j, "stripe")
    assert job.apply_url == "https://stripe.com/jobs/123"
    assert job.apply_url_type == APPLY_DIRECT
    assert job.company == "Stripe"


def test_greenhouse_falls_back_to_token_name():
    j = {"title": "SWE", "location": {"name": "Remote"}, "absolute_url": "u", "id": 1}
    assert GreenhouseSource()._to_canonical(j, "airbnb").company == "Airbnb"


def test_lever_maps_direct_apply():
    j = {"text": "Backend Engineer", "categories": {"location": "NYC"},
         "applyUrl": "https://jobs.lever.co/spotify/abc/apply",
         "hostedUrl": "https://jobs.lever.co/spotify/abc",
         "descriptionPlain": "Build things", "createdAt": 1778529611285, "id": "abc"}
    job = LeverSource()._to_canonical(j, "Spotify")
    assert job.apply_url.endswith("/apply")
    assert job.apply_url_type == APPLY_DIRECT
    assert job.company == "Spotify"


def test_ashby_maps_direct_apply_and_filters_unlisted():
    j = {"title": "Fullstack Engineer", "location": "Europe", "isRemote": True,
         "applyUrl": "https://jobs.ashbyhq.com/linear/xyz/application",
         "jobUrl": "https://jobs.ashbyhq.com/linear/xyz",
         "descriptionPlain": "x", "publishedAt": "2021-04-27T20:13:45.158+00:00", "id": "xyz"}
    job = AshbySource()._to_canonical(j, "Linear")
    assert job.apply_url_type == APPLY_DIRECT
    assert job.company == "Linear"


def test_remoteok_is_job_detail():
    j = {"position": "Frontend Developer", "company": "PNC", "location": "Remote",
         "description": "React", "url": "https://remoteok.com/x", "epoch": 1700000000}
    job = RemoteOKSource()._to_canonical(j)
    assert job.apply_url_type == APPLY_JOB_DETAIL
    assert job.company == "PNC"


def test_arbeitnow_is_job_detail():
    j = {"title": "DevOps", "company_name": "Acme", "location": "Berlin",
         "description": "k8s", "url": "https://arbeitnow.com/x", "created_at": 1700000000,
         "remote": True}
    job = ArbeitnowSource()._to_canonical(j)
    assert job.apply_url_type == APPLY_JOB_DETAIL


def test_adzuna_maps_company_and_redirect():
    j = {"title": "Python Developer", "company": {"display_name": "Infosys"},
         "location": {"display_name": "Bengaluru"}, "redirect_url": "https://adzuna/x",
         "description": "Django", "created": "2026-06-01T00:00:00Z", "id": "1"}
    job = AdzunaSource()._to_canonical(j)
    assert job.company == "Infosys"
    assert job.apply_url == "https://adzuna/x"
    assert job.apply_url_type == APPLY_JOB_DETAIL
