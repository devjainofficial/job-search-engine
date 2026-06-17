"""Arbeitnow adapter (free, no key). Firehose of recent jobs (Europe-leaning
remote); filtered in memory during matching."""

from datetime import datetime, timezone

from app.canonical import canonical_key
from app.models import APPLY_JOB_DETAIL, CanonicalJob
from app.sources._http import get_json

API_URL = "https://www.arbeitnow.com/api/job-board-api"
SOURCE_NAME = "arbeitnow"


class ArbeitnowSource:
    name = SOURCE_NAME

    def fetch_all(self) -> list[CanonicalJob]:
        data = get_json(API_URL)
        return [self._to_canonical(j) for j in data.get("data", [])]

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = j.get("company_name") or ""
        title = j.get("title") or ""
        location = j.get("location") or ("Remote" if j.get("remote") else "")
        description = j.get("description") or ""
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            # url is the Arbeitnow posting page (rung 2), not a raw apply URL.
            apply_url=j.get("url") or "",
            apply_url_type=APPLY_JOB_DETAIL,
            posted_at=_parse_epoch(j.get("created_at")),
            description=description,
            raw_payload={"tags": j.get("tags"), "job_types": j.get("job_types"),
                         "remote": j.get("remote")},
        )


def _parse_epoch(epoch) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc) if epoch else None
    except (ValueError, TypeError):
        return None
