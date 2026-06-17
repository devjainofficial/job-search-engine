"""Ashby posting API adapter (free, no auth).

Iterates configured company boards. applyUrl is the direct apply page (rung 1).
Only listed jobs are included.
"""

from datetime import datetime

from app.canonical import canonical_key
from app.models import APPLY_DIRECT, CanonicalJob
from app.sources._http import get_json
from app.sources.ats_companies import ASHBY

SOURCE_NAME = "ashby"
_BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


class AshbySource:
    name = SOURCE_NAME

    def fetch_all(self) -> list[CanonicalJob]:
        jobs: list[CanonicalJob] = []
        for slug, display in ASHBY:
            try:
                data = get_json(_BOARD_URL.format(slug=slug))
            except Exception as exc:
                print(f"[ashby] board '{slug}' failed: {exc}")
                continue
            for j in data.get("jobs", []):
                if j.get("isListed", True):
                    jobs.append(self._to_canonical(j, display))
        return jobs

    def _to_canonical(self, j: dict, company: str) -> CanonicalJob:
        title = j.get("title") or ""
        location = j.get("location") or ("Remote" if j.get("isRemote") else "")
        description = j.get("descriptionPlain") or ""
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=j.get("applyUrl") or j.get("jobUrl") or "",
            apply_url_type=APPLY_DIRECT,
            posted_at=_parse_iso(j.get("publishedAt")),
            description=description,
            raw_payload={"id": j.get("id"), "team": j.get("team"),
                         "employmentType": j.get("employmentType")},
        )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
