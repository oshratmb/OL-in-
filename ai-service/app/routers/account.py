from fastapi import APIRouter, Depends

from .. import supabase_client
from ..auth_dependency import get_current_user

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/pause")
async def pause(user: dict = Depends(get_current_user)):
    supabase_client.set_user_paused(user["sub"], True)
    return {"ok": True}


@router.post("/resume")
async def resume(user: dict = Depends(get_current_user)):
    supabase_client.set_user_paused(user["sub"], False)
    return {"ok": True}
