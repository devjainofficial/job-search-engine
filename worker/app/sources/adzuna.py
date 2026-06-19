"""Adzuna adapter (free developer key) for broad India + global coverage.

Query source: supports what/where search, fetched once per distinct user query.
Off unless ADZUNA_APP_ID and ADZUNA_APP_KEY are set.

Cost/ToS note (see docs/RESEARCH.md): Adzuna's free API is intended for ad
listings; commercial reuse beyond a 14-day trial may require a paid licence.
Review before relying on it as a core source for a public product. redirect_url
routes through Adzuna (rung 2), not a clean apply page.
"""

from datetime import datetime

from app.canonical import canonical_key
from app.config import get_settings
from app.models import APPLY_JOB_DETAIL, CanonicalJob
from app.sources._http import get_json

SOURCE_NAME = "adzuna"
# Default to India; the service is India-leaning. Country is an Adzuna code (in, gb, us...).
_DEFAULT_COUNTRY = "in"
_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
_RESULTS = 50


class AdzunaSource:
    name = SOURCE_NAME

    def __init__(self, country: str = _DEFAULT_COUNTRY):
        self.country = country

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        settings = get_settings()
        if not (settings.adzuna_app_id and settings.adzuna_app_key):
            return []  # adapter disabled until keys are provided
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "what": query,
            "results_per_page": _RESULTS,
            "max_days_old": settings.adzuna_max_days_old,  # freshness: recent postings only
            "sort_by": "date",  # newest first
            "content-type": "application/json",
        }
        if location:
            params["where"] = location
        data = get_json(_URL.format(country=self.country), params=params)
        return [self._to_canonical(j) for j in data.get("results", [])]

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = (j.get("company") or {}).get("display_name") or ""
        title = j.get("title") or ""
        location = (j.get("location") or {}).get("display_name") or ""
        description = j.get("description") or ""
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=j.get("redirect_url") or "",
            apply_url_type=APPLY_JOB_DETAIL,
            posted_at=_parse_iso(j.get("created")),
            description=description,
            raw_payload={"id": j.get("id"), "category": (j.get("category") or {}).get("label")},
        )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
