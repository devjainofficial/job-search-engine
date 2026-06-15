"""Source adapter interface. One adapter per file, all returning CanonicalJob."""

from typing import Protocol

from app.models import CanonicalJob


class JobSource(Protocol):
    """Every source adapter implements this so the pipeline stays source-agnostic."""

    name: str

    def fetch(self, query: str, location: str | None = None) -> list[CanonicalJob]:
        """Return canonical jobs for a single query. Must set apply_url_type."""
        ...
