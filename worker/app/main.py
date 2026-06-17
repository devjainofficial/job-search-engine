"""FastAPI entrypoint.

- GET /health doubles as the Supabase keep-alive ping target.
- POST /run-daily is what the scheduler (cron) calls.
- DELETE /users/{user_id} is the DPDP delete-my-data control.

NOTE: these endpoints are unauthenticated and meant for trusted/internal callers
(the scheduler, the Next.js server with the service role). Add auth before
exposing /run-daily or the delete endpoint to the public internet.
"""

from fastapi import FastAPI

from app.db import delete_user_data
from app.pipeline import run_daily

app = FastAPI(title="job-search-app worker")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run-daily")
def run_daily_endpoint() -> dict:
    return run_daily()


@app.delete("/users/{user_id}")
def delete_user_endpoint(user_id: str) -> dict:
    """DPDP delete-my-data: erase the user, profile, searches, sent history, and
    the raw resume file. Cascade handles the dependent rows."""
    return delete_user_data(user_id)
