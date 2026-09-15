from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse

from .. import config, google_oauth, oauth_state, supabase_client
from ..auth_dependency import get_current_user
from ..jobs.sync_gmail import sync_user_by_id
from ..models import GmailConnectStartResponse, GmailStatusResponse
from ..rbac import require_active_user

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post("/connect/start", response_model=GmailConnectStartResponse)
async def connect_start(user: dict = Depends(get_current_user)):
    try:
        state = oauth_state.sign_state(user["sub"])
        url = google_oauth.build_authorize_url(state)
    except google_oauth.GoogleOAuthNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    return GmailConnectStartResponse(authorize_url=url)


@router.get("/connect/callback")
async def connect_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code or not state:
        return RedirectResponse(f"{config.FRONTEND_URL}/settings.html?gmail_error=1")

    try:
        user_id = oauth_state.verify_state(state)
        tokens = google_oauth.exchange_code_for_tokens(code)
    except Exception:
        # Invalid/expired/tampered state, or the code exchange failed —
        # either way there's nothing actionable to tell the user beyond retry.
        return RedirectResponse(f"{config.FRONTEND_URL}/settings.html?gmail_error=1")

    if "refresh_token" not in tokens:
        # Google only returns a refresh_token on first-ever consent for this
        # client+user; prompt=consent (set in build_authorize_url) forces a
        # fresh one each time, so this shouldn't normally happen.
        return RedirectResponse(f"{config.FRONTEND_URL}/settings.html?gmail_error=1")

    supabase_client.upsert_gmail_connection(
        user_id, tokens["refresh_token"], tokens.get("google_email", ""), datetime.now(timezone.utc).isoformat()
    )
    return RedirectResponse(f"{config.FRONTEND_URL}/settings.html?gmail=connected")


@router.post("/disconnect")
async def disconnect(user: dict = Depends(get_current_user)):
    supabase_client.delete_gmail_connection(user["sub"])
    return {"ok": True}


@router.get("/status", response_model=GmailStatusResponse)
async def status(user: dict = Depends(get_current_user)):
    connection = supabase_client.get_gmail_connection(user["sub"])
    if connection is None:
        return GmailStatusResponse(connected=False)
    return GmailStatusResponse(
        connected=True,
        google_email=connection.get("google_email"),
        last_synced_at=connection.get("last_synced_at"),
        needs_reconnect=connection.get("needs_reconnect", False),
    )


@router.post("/sync-now")
async def sync_now(
    user: dict = Depends(get_current_user), _active: dict = Depends(require_active_user)
):
    try:
        await run_in_threadpool(sync_user_by_id, user["sub"])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"ok": True}
