from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.rbac import require_active_user


@patch("app.rbac.supabase_client.get_profile")
def test_require_active_user_allows_active_account(mock_get_profile):
    mock_get_profile.return_value = {"is_paused": False}
    result = require_active_user(user={"sub": "u1"})
    assert result == {"sub": "u1"}


@patch("app.rbac.supabase_client.get_profile")
def test_require_active_user_rejects_paused_account(mock_get_profile):
    mock_get_profile.return_value = {"is_paused": True}
    with pytest.raises(HTTPException) as exc_info:
        require_active_user(user={"sub": "u1"})
    assert exc_info.value.status_code == 403


@patch("app.rbac.supabase_client.get_profile")
def test_require_active_user_fails_open_if_profile_missing(mock_get_profile):
    # A missing profile shouldn't lock someone out with a confusing "paused"
    # error — that's a data problem, not an active pause decision.
    mock_get_profile.return_value = None
    result = require_active_user(user={"sub": "u1"})
    assert result == {"sub": "u1"}
