"""SerpApi Google Jobs adapter — pulls the Google "Jobs" tab results directly.

Query source, India-leaning (gl=in). OFF unless SERPAPI_KEY is set.

Cost/ToS note (see docs/RESEARCH.md): SerpApi is a paid service with a free tier
(~250 searches/month). Reads the same Google-for-Jobs data as JSearch, so the
canonical-key dedup merges overlapping listings. PAID beyond the free tier.
"""

import re
from datetime import datetime, timedelta, timezone

from app.canonical import canonical_key
from app.config import get_settings
from app.models import APPLY_JOB_DETAIL, CanonicalJob
from app.sources._http import get_json

SOURCE_NAME = "google_jobs"  # surfaced to users as "Google Jobs"
_URL = "https://serpapi.com/search.json"
_DEFAULT_GL = "in"


class SerpApiJobsSource:
    name = SOURCE_NAME

    def __init__(self, gl: str = _DEFAULT_GL):
        self.gl = gl

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        settings = get_settings()
        if not settings.serpapi_key:
            return []
        params = {
            "engine": "google_jobs",
            "q": query,
            "gl": self.gl,
            "hl": "en",
            "api_key": settings.serpapi_key,
        }
        if location:
            params["location"] = location
        data = get_json(_URL, params=params)
        return [self._to_canonical(j) for j in (data.get("jobs_results") or [])]

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = j.get("company_name") or ""
        title = j.get("title") or ""
        location = j.get("location") or ""
        description = j.get("description") or ""
        apply_opts = j.get("apply_options") or []
        apply_url = (apply_opts[0].get("link") if apply_opts else None) or j.get("share_link") or ""
        posted = (j.get("detected_extensions") or {}).get("posted_at")
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=apply_url,
            apply_url_type=APPLY_JOB_DETAIL,
            posted_at=_parse_relative(posted),
            description=description,
            raw_payload={"via": j.get("via"), "job_id": j.get("job_id")},
        )


def _parse_relative(text: str | None) -> datetime | None:
    """Google shows relative dates ('3 days ago'); convert to an approx datetime."""
    if not text:
        return None
    t = text.lower()
    now = datetime.now(timezone.utc)
    if any(k in t for k in ("just", "today", "hour", "minute")):
        return now
    for unit, days in (("day", 1), ("week", 7), ("month", 30)):
        m = re.search(rf"(\d+)\s*{unit}", t)
        if m:
            return now - timedelta(days=int(m.group(1)) * days)
    return None
