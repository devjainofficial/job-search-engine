"""In-memory keyword matching of cached jobs to a profile.

Deliberately simple and deterministic for slice 1. Semantic matching (pgvector)
is deferred. Runs against already-cached jobs so it never hits an external API.
"""

from app.canonical import _slug
from app.models import CanonicalJob, MatchedJob, Profile

# A job must clear this score to be considered a match.
MIN_SCORE = 1.0


def _tokens(*texts: str | None) -> set[str]:
    out: set[str] = set()
    for t in texts:
        if t:
            out.update(_slug(t).split("-"))
    out.discard("")
    return out


def score_job(job: CanonicalJob, profile: Profile) -> float:
    """Higher is better. Title hits on a target role weigh more than skill hits."""
    title_tokens = _tokens(job.title)
    body_tokens = _tokens(job.title, job.description)

    score = 0.0
    for role in profile.role_titles:
        role_tokens = _tokens(role)
        if role_tokens and role_tokens <= title_tokens:
            score += 3.0  # full role title appears in the job title
        elif role_tokens & title_tokens:
            score += 1.5  # partial role overlap in the title

    skill_tokens = _tokens(*profile.skills)
    score += 0.5 * len(skill_tokens & body_tokens)

    return score


def match_jobs(jobs: list[CanonicalJob], profile: Profile, limit: int) -> list[MatchedJob]:
    """Rank jobs for a profile and return the top `limit` above MIN_SCORE."""
    scored = [MatchedJob(job=j, score=score_job(j, profile)) for j in jobs]
    scored = [m for m in scored if m.score >= MIN_SCORE]
    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:limit]
