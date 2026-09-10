"""Thin wrapper around Supabase's own Auth (GoTrue) REST API.

We proxy through this service (instead of calling Supabase directly from the
browser) purely so the refresh token can be set as a real HttpOnly cookie —
something client-side JS can never do on its own. All actual auth logic
(password hashing, token issuance, OAuth) still happens inside Supabase.
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

from . import config

AUTH_URL = f"{config.SUPABASE_URL}/auth/v1"


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _headers() -> dict:
    return {"apikey": config.SUPABASE_ANON_KEY, "Content-Type": "application/json"}


def _raise_for_auth_error(resp: httpx.Response) -> dict:
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        detail = body.get("error_description") or body.get("msg") or resp.text
        raise AuthError(resp.status_code, detail)
    return resp.json()


async def sign_up(email: str, password: str, name: str | None) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_URL}/signup",
            headers=_headers(),
            json={"email": email, "password": password, "data": {"name": name}},
        )
    return _raise_for_auth_error(resp)


async def sign_in_with_password(email: str, password: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_URL}/token?grant_type=password",
            headers=_headers(),
            json={"email": email, "password": password},
        )
    return _raise_for_auth_error(resp)


async def refresh_session(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_URL}/token?grant_type=refresh_token",
            headers=_headers(),
            json={"refresh_token": refresh_token},
        )
    return _raise_for_auth_error(resp)


async def exchange_pkce_code(auth_code: str, code_verifier: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_URL}/token?grant_type=pkce",
            headers=_headers(),
            json={"auth_code": auth_code, "code_verifier": code_verifier},
        )
    return _raise_for_auth_error(resp)


async def sign_out(access_token: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{AUTH_URL}/logout",
            headers={**_headers(), "Authorization": f"Bearer {access_token}"},
        )


async def get_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{AUTH_URL}/user", headers={**_headers(), "Authorization": f"Bearer {access_token}"}
        )
    return _raise_for_auth_error(resp)


async def list_verified_totp_factors(access_token: str) -> list[dict]:
    # ponytail: GoTrue's MFA REST shape is the one part of this file I
    # couldn't fully confirm without live API docs access — verify against
    # https://supabase.com/docs/reference/javascript/auth-mfa-listfactors
    # (which itself calls GET /auth/v1/user and reads `.factors`) before
    # relying on this in production.
    user = await get_user(access_token)
    return [f for f in user.get("factors", []) if f.get("status") == "verified" and f.get("factor_type") == "totp"]


async def enroll_totp_factor(access_token: str) -> dict:
    """Returns {id, totp: {qr_code, secret, uri}} for an unverified factor —
    the caller must confirm it via verify_factor before it's usable."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_URL}/factors",
            headers={**_headers(), "Authorization": f"Bearer {access_token}"},
            json={"factor_type": "totp"},
        )
    return _raise_for_auth_error(resp)


async def create_challenge(access_token: str, factor_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_URL}/factors/{factor_id}/challenge",
            headers={**_headers(), "Authorization": f"Bearer {access_token}"},
        )
    return _raise_for_auth_error(resp)


async def verify_factor(access_token: str, factor_id: str, challenge_id: str, code: str) -> dict:
    """Returns a full new session (access_token/refresh_token) at aal2 —
    used both for confirming a brand-new enrollment and for a login challenge."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_URL}/factors/{factor_id}/verify",
            headers={**_headers(), "Authorization": f"Bearer {access_token}"},
            json={"challenge_id": challenge_id, "code": code},
        )
    return _raise_for_auth_error(resp)


def generate_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def google_authorize_url(redirect_to: str, code_challenge: str) -> str:
    params = {
        "provider": "google",
        "redirect_to": redirect_to,
        "code_challenge": code_challenge,
        "code_challenge_method": "s256",
    }
    return f"{AUTH_URL}/authorize?{urlencode(params)}"
