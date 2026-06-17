"""Register (or delete) the Telegram webhook for one-tap connect.

Usage (from worker/):
    python scripts/set_webhook.py --url https://your-worker.example.com
    python scripts/set_webhook.py --delete

The webhook secret (if set in .env as TELEGRAM_WEBHOOK_SECRET) is registered so
the worker can verify incoming updates. Telegram must be reachable from where you
run this (use a VPN locally if your network blocks api.telegram.org).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Set or delete the Telegram webhook.")
    parser.add_argument("--url", help="Public base URL of the worker (no trailing slash)")
    parser.add_argument("--delete", action="store_true", help="Remove the webhook")
    args = parser.parse_args()

    settings = get_settings()
    base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    if args.delete:
        r = httpx.post(f"{base}/deleteWebhook", timeout=15)
        print(r.json())
        return

    if not args.url:
        raise SystemExit("--url is required unless --delete is given")
    payload = {"url": f"{args.url}/telegram/webhook"}
    if settings.telegram_webhook_secret:
        payload["secret_token"] = settings.telegram_webhook_secret
    r = httpx.post(f"{base}/setWebhook", json=payload, timeout=15)
    print(r.json())


if __name__ == "__main__":
    main()
