"""RemoteOK adapter (free, no key). Returns a firehose of recent remote jobs;
filtering happens in memory during matching."""

from datetime import datetime, timezone

from app.canonical import canonical_key
from app.models import APPLY_JOB_DETAIL, CanonicalJob
from app.sources._http import get_json

API_URL = "https://remoteok.com/api"
SOURCE_NAME = "remoteok"


class RemoteOKSource:
    name = SOURCE_NAME

    def fetch_all(self) -> list[CanonicalJob]:
        data = get_json(API_URL)
        # The first array element is a legal/disclaimer object; real jobs have a
        # "position". Attribution to RemoteOK is required by their terms.
        jobs = [j for j in data if isinstance(j, dict) and j.get("position")]
        return [self._to_canonical(j) for j in jobs]

    def _to_canonical(self, j: dict) -> CanonicalJob:
        company = j.get("company") or ""
        title = j.get("position") or ""
        location = j.get("location") or "Remote"
        description = j.get("description") or ""
        # apply_url/url point to the RemoteOK posting page (which links onward to
        # apply), so this is rung 2 of the ladder, not a raw ATS apply URL.
        url = j.get("apply_url") or j.get("url") or ""
        return CanonicalJob(
            canonical_key=canonical_key(company, title, location, description),
            source=SOURCE_NAME,
            title=title,
            company=company,
            location=location,
            apply_url=url,
            apply_url_type=APPLY_JOB_DETAIL,
            posted_at=_parse_epoch(j.get("epoch")),
            description=description,
            raw_payload={"tags": j.get("tags"), "salary_min": j.get("salary_min"),
                         "salary_max": j.get("salary_max")},
        )


def _parse_epoch(epoch) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc) if epoch else None
    except (ValueError, TypeError):
        return None
