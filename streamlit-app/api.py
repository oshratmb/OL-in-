"""HTTP clients for ``ai-service`` and Supabase.

Mirrors ``web/src/apiClient.js`` and ``web/src/auth.js``:

* One :class:`requests.Session` per Streamlit session, so the ``sb_refresh_token``
  HttpOnly cookie that ``/auth/*`` sets is captured and replayed automatically –
  the server-side equivalent of the browser's ``credentials: "include"``.
* The short-lived access token lives in ``st.session_state`` (server side, never
  handed to the browser).
* A ``401`` triggers one silent ``/auth/refresh`` and a single retry.
"""

from __future__ import annotations

import base64
import json

import requests
import streamlit as st

from config import AI_SERVICE_URL, SUPABASE_ANON_KEY, SUPABASE_URL

TIMEOUT = 180


class ApiError(Exception):
    """Carries a user-facing Hebrew message."""


# --------------------------------------------------------------------------- #
# session plumbing
# --------------------------------------------------------------------------- #
def _http() -> requests.Session:
    if "http_session" not in st.session_state:
        st.session_state.http_session = requests.Session()
    return st.session_state.http_session


def get_token():
    return st.session_state.get("access_token")


def set_token(token):
    st.session_state.access_token = token


def clear_session():
    st.session_state.pop("access_token", None)
    st.session_state.http_session = requests.Session()


def current_user_id():
    """Decode ``sub`` from our own already-trusted access token (no verification –
    real checks happen in ai-service / Supabase RLS). Same idea as web/src/jwt.js."""
    token = get_token()
    if not token:
        return None
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("sub")
    except Exception:
        return None


def _parse(resp: requests.Response):
    try:
        body = resp.json() if resp.content else {}
    except ValueError:
        body = {"detail": resp.text or "תגובה לא צפויה מהשרת"}
    return resp.ok, body, resp.status_code


def _refresh() -> bool:
    try:
        resp = _http().post(f"{AI_SERVICE_URL}/auth/refresh", timeout=TIMEOUT)
    except requests.RequestException:
        return False
    if resp.status_code != 200:
        st.session_state.pop("access_token", None)
        return False
    try:
        set_token(resp.json().get("access_token"))
    except ValueError:
        return False
    return True


restore_session = _refresh


# --------------------------------------------------------------------------- #
# generic fetch helpers -> (ok: bool, body: dict|list, status: int)
# --------------------------------------------------------------------------- #
def ai_fetch(method, path, json_body=None, data=None, headers=None, _retry=True):
    hdrs = dict(headers or {})
    token = get_token()
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    try:
        resp = _http().request(
            method,
            f"{AI_SERVICE_URL}{path}",
            json=json_body,
            data=data,
            headers=hdrs,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return False, {"detail": f"לא ניתן להתחבר לשרת ה-AI: {exc}"}, 0

    if resp.status_code == 401 and _retry and _refresh():
        return ai_fetch(method, path, json_body, data, headers, _retry=False)
    return _parse(resp)


def ai_upload(path, files, _retry=True):
    """Like ``ai_fetch`` but for multipart file uploads (e.g. a recorded
    interview answer) — ``requests`` needs a separate ``files=`` kwarg rather
    than ``json=``/``data=`` for these."""
    hdrs = {}
    token = get_token()
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    try:
        resp = _http().request(
            "POST", f"{AI_SERVICE_URL}{path}", files=files, headers=hdrs, timeout=TIMEOUT
        )
    except requests.RequestException as exc:
        return False, {"detail": f"לא ניתן להתחבר לשרת ה-AI: {exc}"}, 0

    if resp.status_code == 401 and _retry and _refresh():
        return ai_upload(path, files, _retry=False)
    return _parse(resp)


def supabase_fetch(method, path, json_body=None, data=None, headers=None, _retry=True):
    if not SUPABASE_URL:
        return False, {"detail": "SUPABASE_URL אינו מוגדר"}, 0
    hdrs = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {get_token() or ''}",
    }
    if json_body is not None:
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})
    try:
        resp = _http().request(
            method,
            f"{SUPABASE_URL}{path}",
            json=json_body,
            data=data,
            headers=hdrs,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return False, {"detail": f"שגיאת רשת מול Supabase: {exc}"}, 0

    if resp.status_code == 401 and _retry and _refresh():
        return supabase_fetch(method, path, json_body, data, headers, _retry=False)
    return _parse(resp)


# --------------------------------------------------------------------------- #
# auth (see web/src/auth.js)
# --------------------------------------------------------------------------- #
def sign_up(email, password, name, remember=False):
    ok, data, _ = ai_fetch(
        "POST",
        "/auth/signup",
        {"email": email, "password": password, "name": name, "remember": remember},
    )
    if not ok:
        raise ApiError(data.get("detail", "משהו השתבש"))
    set_token(data["access_token"])
    return {"user": data.get("user"), "remember_token": data.get("refresh_token")}


def log_in(email, password, remember=False):
    """``{"status": "ok", ...}`` for a normal login, or an ``mfa_*`` branch for a
    Super Admin whose session isn't at aal2 yet."""
    ok, data, _ = ai_fetch(
        "POST", "/auth/login", {"email": email, "password": password, "remember": remember}
    )
    if not ok:
        raise ApiError(data.get("detail", "משהו השתבש"))
    if data.get("mfa_enrollment_required") or data.get("mfa_challenge_required"):
        return {
            "status": "mfa_enrollment_required"
            if data.get("mfa_enrollment_required")
            else "mfa_challenge_required",
            "temp_access_token": data.get("temp_access_token"),
            "factor_id": data.get("factor_id"),
        }
    set_token(data["access_token"])
    return {
        "status": "ok",
        "user": data.get("user"),
        "remember_token": data.get("refresh_token"),
    }


def restore_remember_token(token: str) -> str | None:
    """Exchanges a browser-persisted refresh token for a fresh session in this
    brand new Streamlit session — see ui.py's "stay signed in" note. Returns
    the newly rotated refresh token to re-persist, or None if it's stale."""
    ok, data, _ = ai_fetch("POST", "/auth/refresh", {"refresh_token": token}, _retry=False)
    if not ok:
        return None
    set_token(data.get("access_token"))
    return data.get("refresh_token")


def log_out():
    ai_fetch("POST", "/auth/logout")
    clear_session()


def has_completed_onboarding() -> bool:
    ok, rows, _ = supabase_fetch("GET", "/rest/v1/core_profiles?select=id&limit=1")
    return bool(ok and isinstance(rows, list) and rows)


def google_start_url() -> str:
    return f"{AI_SERVICE_URL}/auth/google/start"


def redeem_google_login(code: str) -> tuple[bool, str | None]:
    """Exchanges the one-time code from the google/callback redirect for a
    real session, over this same requests.Session — so the refresh cookie
    that call sets is the one future /auth/refresh calls will actually see.
    Returns (ok, remember_token) — a Google sign-in always persists, same as
    the checked-by-default case for password login."""
    ok, data, _ = ai_fetch("POST", "/auth/google/redeem", {"code": code}, _retry=False)
    if not ok:
        return False, None
    set_token(data["access_token"])
    return True, data.get("refresh_token")
