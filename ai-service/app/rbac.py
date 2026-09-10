from fastapi import Depends, HTTPException

from . import supabase_client
from .auth_dependency import get_current_user


def require_role(*allowed_roles: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        profile = supabase_client.get_profile(user["sub"])
        if profile is None or profile["role"] not in allowed_roles:
            raise HTTPException(403, "You don't have permission to access this")
        return profile

    return dependency


def require_active_user(user: dict = Depends(get_current_user)) -> dict:
    profile = supabase_client.get_profile(user["sub"])
    if profile is not None and profile.get("is_paused"):
        raise HTTPException(403, "Account is paused — resume it in Settings to use this feature")
    return user
