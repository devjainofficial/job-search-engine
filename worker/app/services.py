"""Shared orchestration used by the API and the pipeline."""

from app.db import download_resume, get_raw_resume_path, upsert_profile
from app.models import Profile
from app.parsing.resume_parser import parse_resume_text
from app.parsing.text_extract import extract_text_from_bytes


def parse_user_resume(user_id: str) -> Profile | None:
    """Parse a user's uploaded résumé and store the structured profile (sets
    parsed_at). Returns None if there's no résumé on file; raises on empty text."""
    path = get_raw_resume_path(user_id)
    if not path:
        return None
    text = extract_text_from_bytes(download_resume(path), path)
    if not text.strip():
        raise ValueError("no text extracted from resume")
    profile = parse_resume_text(text)
    upsert_profile(user_id, profile, path)
    return profile
