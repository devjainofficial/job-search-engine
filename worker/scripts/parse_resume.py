"""CLI: parse a local resume once and upsert the structured profile.

Usage (from worker/):
    python scripts/parse_resume.py --file path/to/resume.pdf --user-id <uuid>
    python scripts/parse_resume.py --file resume.pdf --user-id <uuid> --upload

Parse-once: run this when a resume is added. The daily run never re-parses.
"""

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the worker/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_client, upsert_profile  # noqa: E402
from app.parsing.resume_parser import parse_resume_text  # noqa: E402
from app.parsing.text_extract import extract_text  # noqa: E402

_BUCKET = "resumes"


def _upload_raw(user_id: str, path: Path) -> str:
    """Upload the raw file to Supabase Storage and return its object path.

    DPDP note: the raw file is deletable after parsing; we keep a path only so a
    later slice can offer delete-my-data. Storing keywords is what matters.
    """
    object_path = f"{user_id}/{path.name}"
    get_client().storage.from_(_BUCKET).upload(
        object_path,
        path.read_bytes(),
        {"upsert": "true"},
    )
    return object_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a resume into a profile.")
    parser.add_argument("--file", required=True, help="Path to the resume file")
    parser.add_argument("--user-id", required=True, help="users.id (uuid)")
    parser.add_argument("--upload", action="store_true", help="Upload raw file to Storage")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    text = extract_text(path)
    if not text.strip():
        raise SystemExit("No text extracted from resume.")

    profile = parse_resume_text(text)
    raw_path = _upload_raw(args.user_id, path) if args.upload else None
    upsert_profile(args.user_id, profile, raw_path)

    print("Parsed profile:")
    print(f"  role_titles: {profile.role_titles}")
    print(f"  skills:      {profile.skills}")
    print(f"  experience:  {profile.years_experience}")
    print(f"  location:    {profile.location}")
    print(f"  remote_pref: {profile.remote_pref}")
    if raw_path:
        print(f"  raw_resume_path: {raw_path}")


if __name__ == "__main__":
    main()
