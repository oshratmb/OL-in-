import jwt
from fastapi import Header, HTTPException, status

from . import config


def _decode(authorization: str) -> tuple[dict, str]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(
            token, config.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc
    return payload, token


def get_current_user(authorization: str = Header(...)) -> dict:
    """Verifies the Supabase-issued access token sent as a Bearer header.

    Returns the decoded JWT payload (contains "sub" = user id, "email", ...).
    """
    payload, _token = _decode(authorization)
    return payload


def get_current_user_with_token(authorization: str = Header(...)) -> tuple[dict, str]:
    """Like get_current_user, but also returns the raw token — needed by the
    MFA endpoints, which must forward the caller's own token to Supabase's
    Factors API to act "as" that user."""
    return _decode(authorization)
