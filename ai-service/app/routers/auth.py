import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from .. import config, supabase_auth, supabase_client
from ..auth_dependency import get_current_user_with_token

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "sb_refresh_token"
VERIFIER_COOKIE = "sb_oauth_verifier"


class SignUpBody(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class MfaVerifyEnrollBody(BaseModel):
    factor_id: str
    code: str


class MfaChallengeBody(BaseModel):
    factor_id: str


class MfaVerifyBody(BaseModel):
    factor_id: str
    challenge_id: str
    code: str


async def _mfa_gate(session: dict) -> dict | None:
    """Returns a dict describing the MFA step still needed before `session`
    is usable, or None if it's already fully authenticated. Only Super Admins
    are gated (AC 5.4) — everyone else's session is returned as-is."""
    profile = supabase_client.get_profile(session["user"]["id"])
    if profile is None or profile["role"] != "super_admin":
        return None

    try:
        payload = jwt.decode(
            session["access_token"],
            config.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        return None  # shouldn't happen with a token Supabase itself just issued
    if payload.get("aal") == "aal2":
        return None

    factors = await supabase_auth.list_verified_totp_factors(session["access_token"])
    if not factors:
        return {"mfa_enrollment_required": True, "temp_access_token": session["access_token"]}
    return {
        "mfa_challenge_required": True,
        "factor_id": factors[0]["id"],
        "temp_access_token": session["access_token"],
    }


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="strict",
        max_age=60 * 60 * 24 * 7,
        path="/auth",
    )


def _session_response(session: dict, response: Response) -> dict:
    _set_refresh_cookie(response, session["refresh_token"])
    return {
        "access_token": session["access_token"],
        "expires_in": session["expires_in"],
        "user": session["user"],
    }


@router.post("/signup")
async def signup(body: SignUpBody, response: Response):
    try:
        session = await supabase_auth.sign_up(body.email, body.password, body.name)
    except supabase_auth.AuthError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    return _session_response(session, response)


@router.post("/login")
async def login(body: LoginBody, response: Response):
    try:
        session = await supabase_auth.sign_in_with_password(body.email, body.password)
    except supabase_auth.AuthError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    gate = await _mfa_gate(session)
    if gate:
        return gate  # refresh cookie intentionally NOT set until MFA clears
    return _session_response(session, response)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(401, "No session")
    try:
        session = await supabase_auth.refresh_session(refresh_token)
    except supabase_auth.AuthError as exc:
        response.delete_cookie(REFRESH_COOKIE, path="/auth")
        raise HTTPException(exc.status_code, exc.detail) from exc
    return _session_response(session, response)


@router.post("/logout")
async def logout(response: Response, authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        await supabase_auth.sign_out(authorization.removeprefix("Bearer "))
    response.delete_cookie(REFRESH_COOKIE, path="/auth")
    return {"ok": True}


@router.get("/google/start")
async def google_start():
    verifier, challenge = supabase_auth.generate_pkce_pair()
    redirect_to = f"{config.AI_SERVICE_URL}/auth/google/callback"
    url = supabase_auth.google_authorize_url(redirect_to, challenge)
    resp = RedirectResponse(url)
    resp.set_cookie(
        VERIFIER_COOKIE,
        verifier,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=300,
        path="/auth",
    )
    return resp


@router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None, error: str | None = None):
    if error or not code:
        return RedirectResponse(f"{config.FRONTEND_URL}/index.html?auth_error=1")

    verifier = request.cookies.get(VERIFIER_COOKIE)
    if not verifier:
        return RedirectResponse(f"{config.FRONTEND_URL}/index.html?auth_error=1")

    try:
        session = await supabase_auth.exchange_pkce_code(code, verifier)
    except supabase_auth.AuthError:
        return RedirectResponse(f"{config.FRONTEND_URL}/index.html?auth_error=1")

    gate = await _mfa_gate(session)
    if gate:
        # A redirect can't carry a JSON body, and this token must never sit in
        # a query string (server logs). The URL fragment is never sent to any
        # server on the follow-up navigation, so it's the least-bad place for
        # a short-lived, narrowly-scoped (aal1-only) token to ride along.
        mode = "enroll" if gate.get("mfa_enrollment_required") else "challenge"
        fragment = f"mode={mode}&temp_access_token={gate['temp_access_token']}"
        if gate.get("factor_id"):
            fragment += f"&factor_id={gate['factor_id']}"
        return RedirectResponse(f"{config.FRONTEND_URL}/mfa.html#{fragment}")

    # index.html's own init() calls /auth/refresh on load, which reads the
    # HttpOnly cookie we're about to set — no need to hand the token through
    # the URL at all.
    resp = RedirectResponse(f"{config.FRONTEND_URL}/index.html")
    _set_refresh_cookie(resp, session["refresh_token"])
    resp.delete_cookie(VERIFIER_COOKIE, path="/auth")
    return resp


@router.post("/mfa/enroll")
async def mfa_enroll(auth: tuple[dict, str] = Depends(get_current_user_with_token)):
    _, token = auth
    factor = await supabase_auth.enroll_totp_factor(token)
    totp = factor.get("totp", {})
    return {"factor_id": factor["id"], "qr_code": totp.get("qr_code"), "secret": totp.get("secret")}


@router.post("/mfa/verify-enroll")
async def mfa_verify_enroll(
    body: MfaVerifyEnrollBody,
    response: Response,
    auth: tuple[dict, str] = Depends(get_current_user_with_token),
):
    _, token = auth
    challenge = await supabase_auth.create_challenge(token, body.factor_id)
    try:
        session = await supabase_auth.verify_factor(token, body.factor_id, challenge["id"], body.code)
    except supabase_auth.AuthError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    return _session_response(session, response)


@router.post("/mfa/challenge")
async def mfa_challenge(
    body: MfaChallengeBody, auth: tuple[dict, str] = Depends(get_current_user_with_token)
):
    _, token = auth
    challenge = await supabase_auth.create_challenge(token, body.factor_id)
    return {"challenge_id": challenge["id"]}


@router.post("/mfa/verify")
async def mfa_verify(
    body: MfaVerifyBody, response: Response, auth: tuple[dict, str] = Depends(get_current_user_with_token)
):
    _, token = auth
    try:
        session = await supabase_auth.verify_factor(token, body.factor_id, body.challenge_id, body.code)
    except supabase_auth.AuthError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    return _session_response(session, response)
