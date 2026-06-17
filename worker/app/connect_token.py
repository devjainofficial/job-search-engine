"""Stateless, signed Telegram-connect tokens (no DB column needed).

token = uuid-hex(32) + hmac_sha256(service_key, uuid-hex)[:16]  -> 48 hex chars,
which fits Telegram's deep-link start parameter (<=64 chars, [A-Za-z0-9_-]).

The web app and the worker share the same secret (the Supabase service-role key,
already present on both server sides) and the same construction, so the worker can
verify a token the web app generated without any shared state. The TS twin of this
file is web/lib/connectToken.ts; keep them in sync.
"""

import hashlib
import hmac

from app.config import get_settings

_SIG_LEN = 16


def _secret() -> bytes:
    return get_settings().supabase_service_role_key.encode()


def _sign(uuid_hex: str) -> str:
    return hmac.new(_secret(), uuid_hex.encode(), hashlib.sha256).hexdigest()[:_SIG_LEN]


def make_token(user_id: str) -> str:
    uuid_hex = user_id.replace("-", "")
    return uuid_hex + _sign(uuid_hex)


def verify_token(token: str) -> str | None:
    """Return the user_id (uuid) if the token is valid, else None."""
    if not token or len(token) != 32 + _SIG_LEN:
        return None
    uuid_hex, sig = token[:32], token[32:]
    if not hmac.compare_digest(sig, _sign(uuid_hex)):
        return None
    # Re-hyphenate into canonical uuid form.
    h = uuid_hex
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
