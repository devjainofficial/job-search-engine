"""Lever postings API adapter (free, no auth, ~10 req/s).

Iterates configured company boards. applyUrl is the direct apply page (rung 1).
"""

from datetime import datetime, timezone

from app.canonical import canonical_key
from app.models import APPLY_DIRECT, CanonicalJob
from app.sources._http import get_json
from app.sources.ats_companies import LEVER

SOURCE_NAME = "lever"
_BOARD_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"


class LeverSource:
    name = SOURCE_NAME

    def fetch_all(self) -> list[CanonicalJob]:
        jobs: list[CanonicalJob] = []
        for slug, display in LEVER:
            try:
                data = get_json(_BOARD_URL.format(slug=slug))
            except Exception as exc:
                print(f"[lever] board '{slug}' failed: {exc}")
                continue
            for j in data:
                jobs.append(self._to_canonical(j, display))
        return jobs

    def _to_canonical(self, j: dict, company: str) -> CanonicalJob:
        title = j.get("text") or ""
        location = (j.get("categories") or {}).get("location") or ""
        description = j.get("descriptionPlain") or ""
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=j.get("applyUrl") or j.get("hostedUrl") or "",
            apply_url_type=APPLY_DIRECT,
            posted_at=_parse_ms(j.get("createdAt")),
            description=description,
            raw_payload={"id": j.get("id"), "team": (j.get("categories") or {}).get("team")},
        )


def _parse_ms(ms) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc) if ms else None
    except (ValueError, TypeError):
        return None
