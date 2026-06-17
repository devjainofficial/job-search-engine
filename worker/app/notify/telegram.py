"""Telegram Bot API digest delivery (free, any volume).

The bot can only message a user after that user has messaged it once, so the
user's telegram_chat_id must already be captured (manually seeded in slice 1).
"""

import httpx

from app.config import get_settings
from app.models import MatchedJob

# Telegram hard-caps a single message at 4096 chars; stay under it and chunk.
_MAX_MESSAGE = 3500

# Human-readable label for each apply-link ladder rung we attach to a job.
_APPLY_LABELS = {
    "direct_apply": "Apply",
    "job_detail": "View posting",
    "company_careers": "Careers page",
    "source_search": "Search",
}


def _escape(text: str) -> str:
    """Escape the characters that break Telegram HTML parse_mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_digest(matches: list[MatchedJob]) -> str:
    lines = [f"<b>{len(matches)} new job(s) for you today</b>", ""]
    sources: set[str] = set()
    for m in matches:
        job = m.job
        sources.add(job.source)
        label = _APPLY_LABELS.get(job.apply_url_type, "Open")
        title = _escape(job.title)
        company = _escape(job.company)
        loc = _escape(job.location or "")
        loc_part = f" - {loc}" if loc else ""
        lines.append(f"<b>{title}</b> @ {company}{loc_part}")
        lines.append(f'<a href="{job.apply_url}">{label}</a>')
        lines.append("")
    # Attribution: Remotive and RemoteOK both require crediting the source.
    lines.append(f"<i>Jobs via {', '.join(sorted(s.title() for s in sources))}</i>")
    return "\n".join(lines)


def _chunks(text: str) -> list[str]:
    if len(text) <= _MAX_MESSAGE:
        return [text]
    out, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > _MAX_MESSAGE:
            out.append(current)
            current = ""
        current += line + "\n"
    if current:
        out.append(current)
    return out


def send_digest(chat_id: str, matches: list[MatchedJob]) -> None:
    if not matches:
        return
    settings = get_settings()
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    with httpx.Client(timeout=20.0) as client:
        for chunk in _chunks(format_digest(matches)):
            resp = client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            resp.raise_for_status()
