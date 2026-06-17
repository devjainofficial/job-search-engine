"""In-memory keyword matching of cached jobs to a profile.

Deliberately simple and deterministic for slice 1. Semantic matching (pgvector)
is deferred. Runs against already-cached jobs so it never hits an external API.

Relevance model: a job must be TITLE-relevant to one of the target roles to
qualify. Skills only influence ranking, never qualification, so a job whose
title is unrelated cannot sneak in just because its description mentions a skill.
"""

from app.canonical import _slug, normalize_company
from app.geo import OUT_COUNTRY, classify_location, location_boost
from app.models import CanonicalJob, MatchedJob, Profile
from app.seniority import seniority_ok

# Default cap on how many jobs one company may contribute to a single digest, so
# a company posting the same role across many locations cannot flood it.
DEFAULT_MAX_PER_COMPANY = 2

# Location preferences. "in_country" = user's country + remote (no relocation);
# "outside_only" = foreign-located roles; "mix" = balanced ~50/50; "any" = no
# location filter (rank only).
SCOPE_IN = "in_country"
SCOPE_OUT = "outside_only"
SCOPE_MIX = "mix"
SCOPE_ANY = "any"

# Tokens too generic to signal role fit on their own. A bare overlap on these
# (e.g. "developer", or "ai" matching "AI Cinematic Video Editor") must not
# qualify a job. Seniority words are stripped here too.
GENERIC_ROLE_TOKENS = {
    "developer", "engineer", "dev", "programmer", "architect",
    "senior", "snr", "sr", "junior", "jr", "lead", "staff", "principal",
    "mid", "intern", "manager", "specialist", "associate", "consultant",
    "i", "ii", "iii", "iv", "v",
}

# Title tokens that mark a technical individual-contributor role. Such a title can
# qualify on skill alignment alone (tier 2), which lets in Frontend/Backend/Web
# roles that fit the skills but are not spelled out in the user's role titles,
# while still excluding non-technical titles (sales, writer, analyst, etc.).
TECH_ROLE_TOKENS = {"developer", "engineer", "programmer", "dev", "sde", "swe"}

# How many of the user's skills a tier-2 technical title must hit to qualify.
MIN_SKILLS_FOR_TECH = 2


def _tokens(*texts: str | None) -> set[str]:
    out: set[str] = set()
    for t in texts:
        if t:
            out.update(_slug(t).split("-"))
    out.discard("")
    return out


def _specific_tokens(role: str) -> set[str]:
    """Role tokens that actually identify the role: drop generic and very short
    (<=2 char) tokens like "ai"/"ml"/"ui" that match far too broadly."""
    return {t for t in _tokens(role) if len(t) > 2 and t not in GENERIC_ROLE_TOKENS}


def title_is_relevant(job: CanonicalJob, profile: Profile) -> bool:
    """Tier 1: the job TITLE meaningfully overlaps at least one target role."""
    title_tokens = _tokens(job.title)
    for role in profile.role_titles:
        specific = _specific_tokens(role)
        if specific:
            if specific & title_tokens:
                return True
        else:
            # Role has no specific tokens (e.g. "Senior Engineer"); fall back to
            # requiring at least two raw tokens to overlap.
            if len(_tokens(role) & title_tokens) >= 2:
                return True
    return False


def qualifies(job: CanonicalJob, profile: Profile) -> bool:
    """A job qualifies if its title matches a target role (tier 1) OR it is a
    technical IC role backed by enough of the user's skills (tier 2)."""
    if title_is_relevant(job, profile):
        return True
    title_tokens = _tokens(job.title)
    if title_tokens & TECH_ROLE_TOKENS:
        body_tokens = _tokens(job.title, job.description)
        skill_tokens = _tokens(*profile.skills)
        if len(skill_tokens & body_tokens) >= MIN_SKILLS_FOR_TECH:
            return True
    return False


def score_job(job: CanonicalJob, profile: Profile) -> float:
    """Rank score for an already title-relevant job. Full role-phrase matches
    rank above specific-token matches; skills add a smaller ranking boost."""
    title_tokens = _tokens(job.title)
    body_tokens = _tokens(job.title, job.description)

    score = 0.0
    for role in profile.role_titles:
        role_tokens = _tokens(role)
        if role_tokens and role_tokens <= title_tokens:
            score += 3.0  # full role title appears in the job title
        elif _specific_tokens(role) & title_tokens:
            score += 1.5  # a specific (non-generic) role token is in the title

    skill_tokens = _tokens(*profile.skills)
    score += 0.5 * len(skill_tokens & body_tokens)

    # Prefer roles the user can realistically take (remote / India-based).
    score += location_boost(job.location, profile.location, profile.remote_pref)

    return score


def _take_with_company_cap(
    candidates: list[MatchedJob],
    limit: int,
    max_per_company: int,
    per_company: dict[str, int],
    selected: list[MatchedJob],
) -> None:
    """Append from candidates into selected, honoring the per-company cap and limit."""
    for m in candidates:
        if len(selected) >= limit:
            return
        company = normalize_company(m.job.company)
        if per_company.get(company, 0) >= max_per_company:
            continue
        selected.append(m)
        per_company[company] = per_company.get(company, 0) + 1


def _is_outside(job: CanonicalJob, profile: Profile) -> bool:
    return classify_location(job.location, profile.location) == OUT_COUNTRY


def match_jobs(
    jobs: list[CanonicalJob],
    profile: Profile,
    limit: int,
    max_per_company: int = DEFAULT_MAX_PER_COMPANY,
    location_scope: str = SCOPE_ANY,
) -> list[MatchedJob]:
    """Return up to `limit` title-relevant jobs, ranked, with at most
    `max_per_company` from any single company. Roles below the candidate's
    seniority are dropped, and results are filtered/balanced by location_scope:
    in_country (country + remote), outside_only (foreign), mix (~50/50), or any."""
    relevant = [
        j for j in jobs
        if qualifies(j, profile) and seniority_ok(j.title, profile.years_experience)
    ]
    scored = [MatchedJob(job=j, score=score_job(j, profile)) for j in relevant]
    scored.sort(key=lambda m: m.score, reverse=True)

    if location_scope == SCOPE_IN:
        scored = [m for m in scored if not _is_outside(m.job, profile)]
    elif location_scope == SCOPE_OUT:
        scored = [m for m in scored if _is_outside(m.job, profile)]

    selected: list[MatchedJob] = []
    per_company: dict[str, int] = {}

    if location_scope == SCOPE_MIX:
        # Alternate in-country/remote and outside roles toward an equal split,
        # falling through to whichever side still has candidates.
        inside = [m for m in scored if not _is_outside(m.job, profile)]
        outside = [m for m in scored if _is_outside(m.job, profile)]
        i = o = 0
        turn_inside = True
        while len(selected) < limit and (i < len(inside) or o < len(outside)):
            if turn_inside and i < len(inside):
                _take_with_company_cap(inside[i:i + 1], limit, max_per_company, per_company, selected); i += 1
            elif not turn_inside and o < len(outside):
                _take_with_company_cap(outside[o:o + 1], limit, max_per_company, per_company, selected); o += 1
            elif i < len(inside):
                _take_with_company_cap(inside[i:i + 1], limit, max_per_company, per_company, selected); i += 1
            elif o < len(outside):
                _take_with_company_cap(outside[o:o + 1], limit, max_per_company, per_company, selected); o += 1
            turn_inside = not turn_inside
        return selected

    _take_with_company_cap(scored, limit, max_per_company, per_company, selected)
    return selected
