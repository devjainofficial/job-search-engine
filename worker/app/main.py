"""FastAPI entrypoint.

- GET /health doubles as the Supabase keep-alive ping target.
- POST /run-daily is what the scheduler (cron) calls.
- POST /parse-resume is called by the web app after it uploads a resume.
- DELETE /users/{user_id} is the DPDP delete-my-data control.

NOTE: these endpoints are unauthenticated and meant for trusted/internal callers
(the scheduler, the Next.js server with the service role). Add auth before
exposing them to the public internet.
"""

import os

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.config import get_settings
from app.apply_assist import generate_application
from app.db import (
    delete_user_data,
    get_cached_job,
    get_profile,
    get_raw_resume_path,
    get_sent_jobs_detail,
)
from app.pipeline import run_daily, run_for_user
from app.services import parse_user_resume
from app.telegram_bot import handle_update

app = FastAPI(title="job-search-app worker")


class ParseRequest(BaseModel):
    user_id: str


def _public_base_url() -> str | None:
    # Render provides RENDER_EXTERNAL_URL; allow an explicit override too.
    return os.environ.get("PUBLIC_BASE_URL") or os.environ.get("RENDER_EXTERNAL_URL")


def _set_telegram_webhook(base_url: str) -> dict:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return {"ok": False, "reason": "no bot token"}
    payload = {"url": f"{base_url.rstrip('/')}/telegram/webhook"}
    if settings.telegram_webhook_secret:
        payload["secret_token"] = settings.telegram_webhook_secret
    resp = httpx.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
        json=payload, timeout=15,
    )
    return resp.json()


@app.on_event("startup")
def _register_webhook_on_startup() -> None:
    """Self-register the Telegram webhook from the cloud (where Telegram is
    reachable), so connect works without registering from a blocked network."""
    base = _public_base_url()
    if base:
        try:
            print("[startup] setWebhook ->", _set_telegram_webhook(base))
        except Exception as exc:
            print(f"[startup] setWebhook failed: {exc}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/telegram/register-webhook")
def register_webhook_endpoint() -> dict:
    """Manually (re)register the webhook using the platform's public URL."""
    base = _public_base_url()
    if not base:
        raise HTTPException(status_code=400, detail="no public base url (set PUBLIC_BASE_URL)")
    return _set_telegram_webhook(base)


@app.post("/run-daily")
def run_daily_endpoint() -> dict:
    return run_daily()


@app.post("/parse-resume")
def parse_resume_endpoint(body: ParseRequest) -> dict:
    """Parse-once: download the user's uploaded resume, extract + parse it, and
    store the structured profile. Called by the web app after upload."""
    if not get_raw_resume_path(body.user_id):
        raise HTTPException(status_code=404, detail="no resume on file for user")
    try:
        profile = parse_user_resume(body.user_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="no text extracted from resume")
    return {
        "user_id": body.user_id,
        "role_titles": profile.role_titles,
        "skills": profile.skills,
        "location": profile.location,
    }


@app.get("/users/{user_id}/jobs")
def user_jobs_endpoint(user_id: str) -> dict:
    """Recent jobs sent to a user (powers the web dashboard)."""
    return {"user_id": user_id, "jobs": get_sent_jobs_detail(user_id)}


class RunUserRequest(BaseModel):
    user_id: str
    limit: int | None = None


@app.post("/run-user")
def run_user_endpoint(body: RunUserRequest, background_tasks: BackgroundTasks) -> dict:
    """On-demand 'find new jobs now' for one user. Runs in the background and acks
    immediately so the caller never blocks on the (multi-source) fetch + cold start.
    New jobs appear in the dashboard / Telegram once it finishes."""
    background_tasks.add_task(run_for_user, body.user_id, body.limit)
    return {"started": True}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Receive Telegram updates for one-tap connect. Verifies the optional shared
    secret Telegram echoes in a header before processing."""
    settings = get_settings()
    if settings.telegram_webhook_secret:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="bad webhook secret")
    update = await request.json()
    return handle_update(update)


class AssistRequest(BaseModel):
    user_id: str
    canonical_key: str


@app.post("/apply-assist")
def apply_assist_endpoint(body: AssistRequest) -> dict:
    """Generate a tailored cover letter + screening answers for one job."""
    profile = get_profile(body.user_id)
    job = get_cached_job(body.canonical_key)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if not job:
        raise HTTPException(status_code=404, detail="job not found (it may have expired)")
    return generate_application(profile, job)


@app.delete("/users/{user_id}")
def delete_user_endpoint(user_id: str) -> dict:
    """DPDP delete-my-data: erase the user, profile, searches, sent history, and
    the raw resume file. Cascade handles the dependent rows."""
    return delete_user_data(user_id)
