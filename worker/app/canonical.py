"""Canonical key + fuzzy description hash for cross-source, cross-day dedup.

Pure and deterministic (no I/O) so it is cheap to unit test. The same job seen on
two boards or on two days must collapse to one key; genuinely different jobs must
not. Test this before trusting it (see tests/test_canonical.py).
"""

import hashlib
import re

# Title noise we strip so "Sr. Software Engineer (Remote)" and
# "Software Engineer" collapse to the same normalized title.
_SENIORITY = re.compile(
    r"\b(sr|snr|senior|jr|junior|lead|staff|principal|i{1,3}|iv|v)\b",
    re.IGNORECASE,
)
_PAREN = re.compile(r"\([^)]*\)")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# How many hex chars of the description hash to keep. Long enough to avoid
# collisions, short enough to keep the key readable.
_DESC_HASH_LEN = 12


def _slug(text: str | None) -> str:
    """Lowercase, drop punctuation, collapse whitespace to single hyphens."""
    if not text:
        return ""
    text = text.lower().strip()
    text = _NON_ALNUM.sub(" ", text)
    return _WS.sub("-", text.strip())


def normalize_company(company: str | None) -> str:
    return _slug(company)


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    t = title.lower()
    t = _PAREN.sub(" ", t)      # drop "(remote)", "(contract)", etc.
    t = _SENIORITY.sub(" ", t)  # drop seniority words and roman-numeral levels
    return _slug(t)


def normalize_location(location: str | None) -> str:
    return _slug(location)


def description_hash(description: str | None) -> str:
    """Stable short hash of the description, robust to html/case/whitespace noise."""
    if not description:
        return "0" * _DESC_HASH_LEN
    text = _HTML_TAG.sub(" ", description.lower())
    text = _NON_ALNUM.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return digest[:_DESC_HASH_LEN]


def canonical_key(
    company: str | None,
    title: str | None,
    location: str | None,
    description: str | None = None,
) -> str:
    """Build the dedup key: company + normalized title + location + desc hash."""
    return "|".join(
        [
            normalize_company(company),
            normalize_title(title),
            normalize_location(location),
            description_hash(description),
        ]
    )
