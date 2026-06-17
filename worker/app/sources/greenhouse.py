"""Greenhouse Job Board API adapter (free, no auth, not rate-limited).

Iterates the configured company boards. Each job carries company_name and an
absolute_url that is the direct apply page (rung 1 of the ladder).
"""

from datetime import datetime

from app.canonical import canonical_key
from app.models import APPLY_DIRECT, CanonicalJob
from app.sources._http import fetch_many, get_json
from app.sources.ats_companies import GREENHOUSE

SOURCE_NAME = "greenhouse"
_BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseSource:
    name = SOURCE_NAME

    def fetch_all(self) -> list[CanonicalJob]:
        return fetch_many(GREENHOUSE, self._fetch_board)

    def _fetch_board(self, token: str) -> list[CanonicalJob]:
        try:
            data = get_json(_BOARD_URL.format(token=token))
        except Exception as exc:  # one dead board must not kill the rest
            print(f"[greenhouse] board '{token}' failed: {exc}")
            return []
        return [self._to_canonical(j, token) for j in data.get("jobs", [])]

    def _to_canonical(self, j: dict, token: str) -> CanonicalJob:
        company = j.get("company_name") or token.title()
        title = j.get("title") or ""
        location = (j.get("location") or {}).get("name") or ""
        # No description fetched (content=true bloats payloads); title-based
        # matching is enough for ATS roles and keeps daily runs lean.
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, ""),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=j.get("absolute_url") or "",
            apply_url_type=APPLY_DIRECT,
            posted_at=_parse_iso(j.get("first_published") or j.get("updated_at")),
            description="",
            raw_payload={"id": j.get("id"), "token": token},
        )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
