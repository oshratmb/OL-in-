"""Direct Google OAuth for Gmail access — separate from Supabase's own Google
provider (used only for login identity, with no first-class way to capture
and store an extra API scope's refresh token for backend use). Reuses the
same Google Cloud OAuth Client as login; just needs its own redirect URI and
the Gmail scope enabled on the consent screen.
"""

from urllib.parse import urlencode

import httpx

from . import config

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
_SCOPES = "openid email https://www.googleapis.com/auth/gmail.readonly"


class GoogleOAuthNotConfigured(Exception):
    pass


def _require_credentials() -> None:
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        raise GoogleOAuthNotConfigured(
            "GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are not set — Gmail integration isn't configured"
        )


def _redirect_uri() -> str:
    return f"{config.AI_SERVICE_URL}/gmail/connect/callback"


def build_authorize_url(state: str) -> str:
    _require_credentials()
    params = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",  # guarantees a refresh_token even on reconnect
        "state": state,
    }
    return f"{_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """Returns {access_token, refresh_token, expires_in, google_email}."""
    _require_credentials()
    with httpx.Client() as client:
        resp = client.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

        userinfo = client.get(
            _USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        userinfo.raise_for_status()

    tokens["google_email"] = userinfo.json().get("email", "")
    return tokens


def get_gmail_access_token(refresh_token: str) -> str:
    """Mints a fresh access token from a stored refresh token for Gmail API calls."""
    _require_credentials()
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]
