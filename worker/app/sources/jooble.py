"""Jooble adapter (free API key by request) — broad global + India aggregation.

Query source. OFF unless JOOBLE_API_KEY is set. Jooble returns redirect links
(rung 2 of the ladder), not direct apply URLs.
"""

from datetime import datetime

from app.canonical import canonical_key
from app.config import get_settings
from app.models import APPLY_JOB_DETAIL, CanonicalJob
from app.sources._http import post_json

SOURCE_NAME = "jooble"
_URL = "https://jooble.org/api/"


class JoobleSource:
    name = SOURCE_NAME

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        settings = get_settings()
        if not settings.jooble_api_key:
            return []
        # India-leaning: default to India when no city/location is given (a broad
        # query with no location returns mostly global noise).
        body: dict = {"keywords": query, "location": location or "India"}
        data = post_json(_URL + settings.jooble_api_key, body)
        return [self._to_canonical(j) for j in (data.get("jobs") or [])]

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = j.get("company") or ""
        title = j.get("title") or ""
        location = j.get("location") or ""
        description = j.get("snippet") or ""
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=j.get("link") or "",
            apply_url_type=APPLY_JOB_DETAIL,
            posted_at=_parse(j.get("updated")),
            description=description,
            raw_payload={"id": j.get("id"), "source": j.get("source"), "salary": j.get("salary")},
        )


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")[:26])
    except ValueError:
        return None
