"""Canonical data shapes shared across adapters, matching, and notifications.

Every source adapter must return CanonicalJob so the rest of the pipeline never
needs to know which board a job came from.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Profile(BaseModel):
    """Structured resume result. Produced once by the parser, then cached in DB."""

    role_titles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    years_experience: Optional[int] = None
    location: Optional[str] = None
    # one of: "remote", "onsite", "hybrid", "any"
    remote_pref: Optional[str] = None


# Apply-link fallback ladder (best to worst). Always label which rung we send.
APPLY_DIRECT = "direct_apply"
APPLY_JOB_DETAIL = "job_detail"
APPLY_COMPANY_CAREERS = "company_careers"
APPLY_SOURCE_SEARCH = "source_search"


class CanonicalJob(BaseModel):
    """Normalized job shape returned by every adapter and stored in job_cache."""

    canonical_key: str
    source: str
    title: str
    company: str
    location: Optional[str] = None
    apply_url: str
    apply_url_type: str = APPLY_JOB_DETAIL
    posted_at: Optional[datetime] = None
    # kept for debugging / later enrichment; not used for matching
    description: str = ""
    raw_payload: Optional[dict] = None


class MatchedJob(BaseModel):
    """A job paired with the relevance score the matcher assigned it for a user."""

    job: CanonicalJob
    score: float
