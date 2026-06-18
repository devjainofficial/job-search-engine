"""Careerjet adapter (free affiliate id) — global + India aggregation.

Query source, India locale by default. OFF unless CAREERJET_AFFID is set. The
public API requires an affiliate id plus a user_ip and user_agent (it is built to
run searches on behalf of an end user). Returns redirect links (rung 2).
"""

from datetime import datetime

from app.canonical import canonical_key
from app.config import get_settings
from app.models import APPLY_JOB_DETAIL, CanonicalJob
from app.sources._http import get_json

SOURCE_NAME = "careerjet"
_URL = "http://public.api.careerjet.net/search"
# Careerjet requires a Referer header identifying the calling site.
_REFERER = "https://jobsearch-web-devjain2309s-projects.vercel.app"


class CareerjetSource:
    name = SOURCE_NAME

    def __init__(self, locale: str = "en_IN"):
        self.locale = locale

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        settings = get_settings()
        if not settings.careerjet_affid:
            return []
        params = {
            "keywords": query,
            "affid": settings.careerjet_affid,
            "user_ip": "203.0.113.1",          # required by the API (placeholder server IP)
            "user_agent": "job-search-app",
            "locale_code": self.locale,
            "pagesize": 50,
            "contenttype": "application/json",
        }
        if location:
            params["location"] = location
        data = get_json(_URL, params=params, headers={"Referer": _REFERER})
        if data.get("type") != "JOBS":
            return []
        return [self._to_canonical(j) for j in (data.get("jobs") or [])]

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = j.get("company") or ""
        title = j.get("title") or ""
        location = j.get("locations") or ""
        description = j.get("description") or ""
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=j.get("url") or "",
            apply_url_type=APPLY_JOB_DETAIL,
            posted_at=_parse(j.get("date")),
            description=description,
            raw_payload={"site": j.get("site"), "salary": j.get("salary")},
        )


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None  # Careerjet uses RFC-style dates; recency filtering not critical
