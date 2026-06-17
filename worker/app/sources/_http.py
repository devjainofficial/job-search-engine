"""Shared HTTP helper for source adapters: consistent User-Agent, timeout, and
back-off on HTTP 429 / transient errors (per CLAUDE.md rate-limit handling)."""

import time

import httpx

_HEADERS = {
    "User-Agent": "job-search-app (+https://github.com/devjainofficial/job-search-engine)",
    "Accept": "application/json",
}


def get_json(url: str, params: dict | None = None, timeout: float = 20.0, retries: int = 2):
    """GET and parse JSON, backing off on 429 and transient network errors."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout, headers=_HEADERS, follow_redirects=True) as client:
                resp = client.get(url, params=params)
            if resp.status_code == 429:
                time.sleep(1.5 * (attempt + 1))  # respect rate limit, then retry
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError(f"GET {url} failed after {retries + 1} attempts (429)")
