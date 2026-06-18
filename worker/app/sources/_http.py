"""Shared HTTP helper for source adapters: consistent User-Agent, timeout, and
back-off on HTTP 429 / transient errors (per CLAUDE.md rate-limit handling)."""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

import httpx

_T = TypeVar("_T")
_R = TypeVar("_R")

_HEADERS = {
    "User-Agent": "job-search-app (+https://github.com/devjainofficial/job-search-engine)",
    "Accept": "application/json",
}


def get_json(url: str, params: dict | None = None, timeout: float = 20.0, retries: int = 2,
             headers: dict | None = None):
    """GET and parse JSON, backing off on 429 and transient network errors.
    Extra headers (e.g. API keys) are merged over the defaults."""
    merged = {**_HEADERS, **(headers or {})}
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout, headers=merged, follow_redirects=True) as client:
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


def post_json(url: str, json_body: dict, timeout: float = 20.0, retries: int = 2,
              headers: dict | None = None):
    """POST JSON and parse the JSON response, backing off on 429/transient errors."""
    merged = {**_HEADERS, **(headers or {})}
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout, headers=merged, follow_redirects=True) as client:
                resp = client.post(url, json=json_body)
            if resp.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
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
    raise RuntimeError(f"POST {url} failed after {retries + 1} attempts (429)")


def fetch_many(items: list[_T], fetch_one: Callable[[_T], list[_R]], max_workers: int = 8) -> list[_R]:
    """Run fetch_one over items concurrently and flatten the results. fetch_one
    must handle its own errors (return [] on failure) so one bad item is skipped."""
    out: list[_R] = []
    if not items:
        return out
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        for result in pool.map(fetch_one, items):
            out.extend(result)
    return out
