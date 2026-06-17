"""Infer a job's seniority from its title and decide if it fits the candidate.

Goal: stop surfacing internships and new-grad/entry roles to experienced users
(a 5-year engineer should not get "Software Engineer, New Grad").
"""

import re

# Levels, low to high.
INTERN = 0
ENTRY = 1   # new grad / junior / entry level
MID = 2
SENIOR = 3  # senior / staff / principal / lead

_INTERN = re.compile(r"\b(intern|internship|co-?op|trainee|apprentice|working student)\b", re.I)
_ENTRY = re.compile(r"\b(new[\s-]?grad|graduate|entry[\s-]?level|early[\s-]?career|junior|jr)\b", re.I)
_SENIOR = re.compile(r"\b(senior|sr|staff|principal|lead|head|director|vp|distinguished)\b", re.I)


def job_level(title: str) -> int:
    """Best-effort seniority of a job from its title (defaults to MID)."""
    if not title:
        return MID
    if _INTERN.search(title):
        return INTERN
    if _SENIOR.search(title):
        return SENIOR
    if _ENTRY.search(title):
        return ENTRY
    return MID


def seniority_ok(title: str, years_experience: int | None) -> bool:
    """True if the job's level is acceptable for the candidate's experience.

    Unknown experience accepts everything. Otherwise: 1+ years drops internships;
    3+ years also drops new-grad/entry/junior roles. The upper bound is left open
    (an experienced IC may still want a staff/lead role)."""
    if years_experience is None:
        return True
    level = job_level(title)
    if years_experience >= 1 and level == INTERN:
        return False
    if years_experience >= 3 and level <= ENTRY:
        return False
    return True
