"""FastAPI entrypoint.

- GET /health doubles as the Supabase keep-alive ping target.
- POST /run-daily is what the scheduler (cron) calls.
- POST /parse-resume is called by the web app after it uploads a resume.
- DELETE /users/{user_id} is the DPDP delete-my-data control.

NOTE: these endpoints are unauthenticated and meant for trusted/internal callers
(the scheduler, the Next.js server with the service role). Add auth before
exposing them to the public internet.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.db import (
    delete_user_data,
    download_resume,
    get_raw_resume_path,
    upsert_profile,
)
from app.parsing.resume_parser import parse_resume_text
from app.parsing.text_extract import extract_text_from_bytes
from app.pipeline import run_daily

app = FastAPI(title="job-search-app worker")


class ParseRequest(BaseModel):
    user_id: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run-daily")
def run_daily_endpoint() -> dict:
    return run_daily()


@app.post("/parse-resume")
def parse_resume_endpoint(body: ParseRequest) -> dict:
    """Parse-once: download the user's uploaded resume, extract + parse it, and
    store the structured profile. Called by the web app after upload."""
    path = get_raw_resume_path(body.user_id)
    if not path:
        raise HTTPException(status_code=404, detail="no resume on file for user")
    text = extract_text_from_bytes(download_resume(path), path)
    if not text.strip():
        raise HTTPException(status_code=422, detail="no text extracted from resume")
    profile = parse_resume_text(text)
    upsert_profile(body.user_id, profile, path)
    return {
        "user_id": body.user_id,
        "role_titles": profile.role_titles,
        "skills": profile.skills,
        "location": profile.location,
    }


@app.delete("/users/{user_id}")
def delete_user_endpoint(user_id: str) -> dict:
    """DPDP delete-my-data: erase the user, profile, searches, sent history, and
    the raw resume file. Cascade handles the dependent rows."""
    return delete_user_data(user_id)
