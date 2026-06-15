"""FastAPI entrypoint. /health doubles as the Supabase keep-alive ping target;
/run-daily is what the scheduler (cron) will call in a later slice."""

from fastapi import FastAPI

from app.pipeline import run_daily

app = FastAPI(title="job-search-app worker")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run-daily")
def run_daily_endpoint() -> dict:
    return run_daily()
