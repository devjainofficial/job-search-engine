"""Location helpers for an India-leaning, remote-friendly product.

Used to rank jobs: remote and India-based roles are boosted for users in India
or who prefer remote, without hard-dropping others (board listings often show an
HQ city even for remote-eligible roles, so a hard filter would lose good jobs).
"""

_REMOTE = ("remote", "worldwide", "anywhere", "global", "distributed", "wfh")

_INDIA = (
    "india", "bengaluru", "bangalore", "mumbai", "delhi", "new delhi", "hyderabad",
    "pune", "chennai", "kolkata", "gurgaon", "gurugram", "noida", "ahmedabad",
    "gandhinagar", "gujarat", "jaipur", "kochi", "indore", "remote india",
)


def is_remote(location: str | None) -> bool:
    if not location:
        return False
    loc = location.lower()
    return any(k in loc for k in _REMOTE)


def is_india(location: str | None) -> bool:
    if not location:
        return False
    loc = location.lower()
    return any(k in loc for k in _INDIA)


# Location buckets for the in/out/mix preference.
IN_COUNTRY = "in"      # in the user's country
REMOTE = "remote"      # remote/worldwide (feasible without relocating)
OUT_COUNTRY = "out"    # a specific foreign location (would mean relocating)


# Open remote = takeable from anywhere; region-locked remote ("Remote - US",
# "Remote - Poland") is not, so it is treated as outside for an India user.
_OPEN_REMOTE = ("worldwide", "anywhere", "global")


def classify_location(location: str | None, profile_location: str | None) -> str:
    """Bucket a job by where it is relative to the user. Open/worldwide remote
    counts as in-reach; region-locked remote that names a foreign place does not.
    Non-India users only get remote vs out for now."""
    if not location or not location.strip():
        return REMOTE  # unknown location: assume open rather than exclude
    if is_india(profile_location) and is_india(location):
        return IN_COUNTRY
    if is_remote(location):
        loc = location.lower().strip()
        if loc in ("remote", "wfh") or any(k in loc for k in _OPEN_REMOTE):
            return REMOTE
        return OUT_COUNTRY  # region-locked remote tied to a foreign place
    return OUT_COUNTRY


def location_boost(location: str | None, profile_location: str | None, remote_pref: str | None) -> float:
    """Ranking boost for jobs the user can realistically take."""
    user_in_india = is_india(profile_location)
    wants_remote = (remote_pref or "").lower() in ("remote", "any", "")

    boost = 0.0
    if is_remote(location) and wants_remote:
        boost += 1.0
    if user_in_india and is_india(location):
        boost += 1.5
    return boost
