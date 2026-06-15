"""Remotive adapter (free, no key) for remote/global jobs.

Remotive ToS constraints (see docs/RESEARCH.md): poll at most ~4x/day (more than
2x/minute is blocked), you must attribute and link back to Remotive, and jobs are
delayed 24h. The pipeline must respect the daily cap; this adapter just fetches.
"""

from datetime import datetime

import httpx

from app.canonical import canonical_key
from app.models import APPLY_JOB_DETAIL, CanonicalJob

API_URL = "https://remotive.com/api/remote-jobs"
SOURCE_NAME = "remotive"
_TIMEOUT = 20.0


class RemotiveSource:
    name = SOURCE_NAME

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        params = {"search": query} if query else {}
        # back off once on a rate-limit response rather than hammering
        resp = self._get(params)
        payload = resp.json()
        jobs = payload.get("jobs", [])
        return [self._to_canonical(j) for j in jobs]

    def _get(self, params: dict) -> httpx.Response:
        with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": "job-search-app"}) as client:
            resp = client.get(API_URL, params=params)
            if resp.status_code == 429:
                # respect the documented limit; let the caller skip this query today
                raise RuntimeError("Remotive rate limit hit (429); back off and retry later")
            resp.raise_for_status()
            return resp

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = j.get("company_name", "")
        title = j.get("title", "")
        location = j.get("candidate_required_location") or "Remote"
        description = j.get("description", "")
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            # Remotive's url is the posting page (links onward to apply), not a raw
            # ATS apply URL, so this is rung 2 of the fallback ladder.
            apply_url=j.get("url", ""),
            apply_url_type=APPLY_JOB_DETAIL,
            posted_at=_parse_date(j.get("publication_date")),
            description=description,
            raw_payload={
                "id": j.get("id"),
                "category": j.get("category"),
                "salary": j.get("salary"),
                "job_type": j.get("job_type"),
            },
        )


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
