"""Source adapter interfaces. One adapter per file, all returning CanonicalJob.

Two shapes, by how a source is queried:
- QuerySource: supports server-side keyword search; fetched once per distinct
  user query (batch-by-shared-query).
- BulkSource: returns a fixed firehose or a company's whole board; fetched once
  per day and matched to every user in memory.
"""

from typing import Protocol

from app.models import CanonicalJob


class QuerySource(Protocol):
    name: str

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        """Return canonical jobs for one query. Must set apply_url_type."""
        ...


class BulkSource(Protocol):
    name: str

    def fetch_all(self) -> list[CanonicalJob]:
        """Return all currently available canonical jobs. Must set apply_url_type."""
        ...
