"""Telegram webhook handling for one-tap connect.

Flow: the web app shows t.me/<bot>?start=<token>. When the user taps Start,
Telegram POSTs an update to our webhook with text "/start <token>". We match the
token to a user, store their chat_id, and confirm.
"""

import httpx

from app.config import get_settings
from app.connect_token import verify_token
from app.db import chat_id_in_use_by_other, set_telegram_chat_id


def parse_start_token(update: dict) -> str | None:
    """Extract the deep-link token from a /start message, if present. Pure."""
    message = update.get("message") or update.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    if not text.startswith("/start"):
        return None
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 and parts[1].strip() else None


def _chat_id(update: dict) -> str | None:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    cid = chat.get("id")
    return str(cid) if cid is not None else None


def send_message(chat_id: str, text: str) -> None:
    settings = get_settings()
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    with httpx.Client(timeout=15.0) as client:
        client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


def handle_update(update: dict) -> dict:
    """Process one webhook update. Returns a small status dict (for logging)."""
    chat_id = _chat_id(update)
    token = parse_start_token(update)

    if token and chat_id:
        user_id = verify_token(token)
        if not user_id:
            send_message(chat_id, "That link looks invalid. Please re-open the connect link from the site.")
            return {"action": "invalid_token"}
        # One Telegram per account: refuse to link a chat already used elsewhere.
        if chat_id_in_use_by_other(chat_id, user_id):
            send_message(chat_id, "⚠️ This Telegram is already connected to another account. Each Telegram can be linked to only one account.")
            return {"action": "chat_in_use"}
        if set_telegram_chat_id(user_id, chat_id):
            send_message(chat_id, "✅ Connected. You'll get your daily job digest here.")
            return {"action": "connected", "user_id": user_id}
        send_message(chat_id, "That link looks invalid. Please re-open the connect link from the site.")
        return {"action": "invalid_token"}

    if chat_id:
        # Plain /start with no token, or any other message.
        send_message(chat_id, "Hi! Upload your resume on the site, then tap the Connect button to link this chat.")
    return {"action": "noop"}
