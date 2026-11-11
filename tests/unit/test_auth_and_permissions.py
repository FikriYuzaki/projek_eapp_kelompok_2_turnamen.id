"""Unit tests for authentication in mock mode and 5-role RBAC enforcement."""

from __future__ import annotations

import pytest

from backend.contracts.dtos import (
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
    ROLE_PLAYER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_CAPTAIN,
)
from backend.core.exceptions import (
    DomainForbiddenError,
    DomainUnauthorizedError,
)
from backend.modules.auth.permissions import has_permission, require_permission
from backend.modules.auth.service import AuthService
from backend.repositories.mock.mock_repository import MockDataStoreRepository


def test_mock_login_and_session_resolution(mock_repo: MockDataStoreRepository) -> None:
    auth = AuthService(mock_repo)
    res = auth.login("organizer@turnamen.in", "turnamen123")
    assert "token" in res
    assert res["user"]["role"] == ROLE_ORGANIZER
    assert "password_hash" not in res["user"]

    me = auth.get_user_by_token(res["token"])
    assert me is not None
    assert me["email"] == "organizer@turnamen.in"

    assert auth.logout(res["token"]) is True
    assert auth.get_user_by_token(res["token"]) is None


def test_login_rejects_wrong_password(mock_repo: MockDataStoreRepository) -> None:
    auth = AuthService(mock_repo)
    with pytest.raises(DomainUnauthorizedError):
        auth.login("organizer@turnamen.in", "wrong-password")


def test_self_registration_prevents_privilege_escalation(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    with pytest.raises(DomainForbiddenError, match="Pendaftaran mandiri tidak diizinkan"):
        auth.register(
            {
                "email": "hacker@turnamen.in",
                "username": "elevated_user",
                "full_name": "Unauthorized Escalation",
                "password": "password123",
                "role": ROLE_SUPER_ADMIN,
            }
        )


def test_role_permission_matrix() -> None:
    assert has_permission(ROLE_SUPER_ADMIN, "tournament:create") is True
    assert has_permission(ROLE_ORGANIZER, "tournament:create") is True
    assert has_permission(ROLE_COMMITTEE, "tournament:create") is False
    assert has_permission(ROLE_TEAM_CAPTAIN, "tournament:create") is False
    assert has_permission(ROLE_PLAYER, "tournament:create") is False

    assert has_permission(ROLE_COMMITTEE, "match:submit_result") is True
    assert has_permission(ROLE_TEAM_CAPTAIN, "team:create") is True
    assert has_permission(ROLE_PLAYER, "match:submit_result") is False

    player_user = {"id": "u1", "role": ROLE_PLAYER, "is_active": True}
    with pytest.raises(DomainForbiddenError):
        require_permission(player_user, "match:submit_result")
