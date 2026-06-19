"""JSearch adapter (Google-for-Jobs via RapidAPI) for Indeed/LinkedIn/Glassdoor/
ZipRecruiter coverage, including India. This is the legal way to surface those
boards' listings (they have no public job-search API of their own).

Query source, India-leaning by default. OFF unless RAPIDAPI_KEY is set.

Cost/ToS note (see docs/RESEARCH.md): JSearch on RapidAPI is free up to ~500
requests/month, paid beyond. Kept behind a flag, off by default. Our daily
batch-by-query caching keeps request counts low. PAID TIER would be required at
higher volume.
"""

from datetime import datetime

from app.canonical import canonical_key
from app.config import get_settings
from app.db import consume_quota
from app.models import APPLY_DIRECT, APPLY_JOB_DETAIL, CanonicalJob
from app.sources._http import get_json

SOURCE_NAME = "jsearch"
_HOST = "jsearch.p.rapidapi.com"
_URL = f"https://{_HOST}/search"
_DEFAULT_COUNTRY = "in"  # India-leaning


class JSearchSource:
    name = SOURCE_NAME

    def __init__(self, country: str = _DEFAULT_COUNTRY):
        self.country = country

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        settings = get_settings()
        if not settings.rapidapi_key:
            return []  # adapter disabled until a key is provided
        if not consume_quota("jsearch", settings.jsearch_monthly_cap):
            print("[jsearch] monthly cap reached; skipping")
            return []
        what = f"{query} in {location}" if location else query
        params = {"query": what, "page": "1", "num_pages": "1", "country": self.country,
                  "date_posted": settings.jsearch_date_posted}  # today|3days|week|month|all
        headers = {"X-RapidAPI-Key": settings.rapidapi_key, "X-RapidAPI-Host": _HOST}
        data = get_json(_URL, params=params, headers=headers)
        return [self._to_canonical(j) for j in (data.get("data") or [])]

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = j.get("employer_name") or ""
        title = j.get("job_title") or ""
        location = _location(j)
        description = j.get("job_description") or ""
        apply_url, is_direct = _best_apply(j)
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=apply_url,
            apply_url_type=APPLY_DIRECT if is_direct else APPLY_JOB_DETAIL,
            posted_at=_parse_iso(j.get("job_posted_at_datetime_utc")),
            description=description,
            raw_payload={"id": j.get("job_id"), "publisher": j.get("job_publisher")},
        )


def _location(j: dict) -> str:
    if j.get("job_is_remote"):
        return "Remote"
    parts = [j.get("job_city"), j.get("job_state"), j.get("job_country")]
    return ", ".join(p for p in parts if p)


def _best_apply(j: dict) -> tuple[str, bool]:
    """Prefer a direct apply option, else the main apply link."""
    for opt in j.get("apply_options") or []:
        if opt.get("is_direct") and opt.get("apply_link"):
            return opt["apply_link"], True
    link = j.get("job_apply_link") or ""
    return link, bool(j.get("job_apply_is_direct"))


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
