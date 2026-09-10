from fastapi import APIRouter, Depends

from .. import supabase_client
from ..models import AdminStats, AdminUser, ErrorLogEntry, PauseUserRequest
from ..rbac import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def stats(_admin: dict = Depends(require_role("support", "super_admin"))):
    return AdminStats(
        total_users=supabase_client.count_users(),
        total_document_generations=supabase_client.count_applications(),
        total_completed_simulations=supabase_client.count_completed_simulations(),
        gmail_sync_errors_24h=supabase_client.count_recent_errors("sync_gmail"),
    )


@router.get("/users", response_model=list[AdminUser])
async def users(search: str | None = None, _admin: dict = Depends(require_role("support", "super_admin"))):
    return supabase_client.list_users(search)


@router.patch("/users/{user_id}/pause")
async def pause_user(
    user_id: str, body: PauseUserRequest, _admin: dict = Depends(require_role("super_admin"))
):
    supabase_client.set_user_paused(user_id, body.paused)
    return {"ok": True}


@router.get("/errors", response_model=list[ErrorLogEntry])
async def errors(_admin: dict = Depends(require_role("super_admin"))):
    return supabase_client.list_errors()
