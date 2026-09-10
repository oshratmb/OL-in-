from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.rbac import require_role


@patch("app.rbac.supabase_client.get_profile")
def test_require_role_allows_exact_match(mock_get_profile):
    mock_get_profile.return_value = {"role": "super_admin"}
    dependency = require_role("super_admin")
    result = dependency(user={"sub": "u1"})
    assert result["role"] == "super_admin"


@patch("app.rbac.supabase_client.get_profile")
def test_require_role_allows_role_in_multi_role_set(mock_get_profile):
    mock_get_profile.return_value = {"role": "support"}
    dependency = require_role("support", "super_admin")
    result = dependency(user={"sub": "u1"})
    assert result["role"] == "support"


@patch("app.rbac.supabase_client.get_profile")
def test_require_role_rejects_role_outside_set(mock_get_profile):
    mock_get_profile.return_value = {"role": "regular"}
    dependency = require_role("support", "super_admin")
    with pytest.raises(HTTPException) as exc_info:
        dependency(user={"sub": "u1"})
    assert exc_info.value.status_code == 403


@patch("app.rbac.supabase_client.get_profile")
def test_require_role_rejects_missing_profile(mock_get_profile):
    mock_get_profile.return_value = None
    dependency = require_role("super_admin")
    with pytest.raises(HTTPException) as exc_info:
        dependency(user={"sub": "u1"})
    assert exc_info.value.status_code == 403
