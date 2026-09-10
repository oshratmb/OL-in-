"""Signs/verifies a short-lived state token carrying a user id through the
Gmail-connect OAuth round-trip. Needed because the callback is reached via a
top-level browser redirect from Google — no Authorization header survives
that, so this is how /gmail/connect/callback knows which logged-in user
initiated the connection. Keyed with the existing Supabase JWT secret rather
than adding a new env var for what's purely an internal-integrity check.
"""

import base64
import hmac
import time
from hashlib import sha256

from . import config

_TTL_SECONDS = 600


def sign_state(user_id: str) -> str:
    expiry = int(time.time()) + _TTL_SECONDS
    payload = f"{user_id}:{expiry}"
    signature = _sign(payload)
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()


def verify_state(state: str) -> str:
    """Returns the user id, or raises ValueError if invalid/expired/tampered."""
    try:
        payload = base64.urlsafe_b64decode(state.encode()).decode()
        user_id, expiry_str, signature = payload.rsplit(":", 2)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Malformed state") from exc

    expected = _sign(f"{user_id}:{expiry_str}")
    if not hmac.compare_digest(signature, expected):
        raise ValueError("State signature mismatch")
    if int(expiry_str) < time.time():
        raise ValueError("State expired")
    return user_id


def _sign(payload: str) -> str:
    digest = hmac.new(config.SUPABASE_JWT_SECRET.encode(), payload.encode(), sha256).digest()
    return base64.urlsafe_b64encode(digest).decode()
