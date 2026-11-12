"""Unit tests for authentication in mock mode, 5-role RBAC enforcement, and repository integrity."""

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
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.modules.auth.permissions import (
    RolePermissionGuard,
    has_permission,
    require_any_role,
    require_authenticated,
    require_permission,
)
from backend.modules.auth.service import AuthService
from backend.repositories.mock.mock_repository import MockDataStoreRepository


def test_mock_login_and_session_resolution(mock_repo: MockDataStoreRepository) -> None:
    auth = AuthService(mock_repo)
    demo_accounts = [
        ("admin@turnamen.in", ROLE_SUPER_ADMIN),
        ("organizer@turnamen.in", ROLE_ORGANIZER),
        ("committee@turnamen.in", ROLE_COMMITTEE),
        ("captain@turnamen.in", ROLE_TEAM_CAPTAIN),
        ("player@turnamen.in", ROLE_PLAYER),
    ]
    for email, expected_role in demo_accounts:
        res = auth.login(email, "turnamen123")
        assert "token" in res
        assert res["user"]["role"] == expected_role
        assert "password_hash" not in res["user"]

        me = auth.get_user_by_token(res["token"])
        assert me is not None
        assert me["email"] == email
        assert me["role"] == expected_role

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
    for privileged_role in (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE):
        with pytest.raises(DomainForbiddenError, match="Pendaftaran mandiri tidak diizinkan"):
            auth.register(
                {
                    "email": f"hacker_{privileged_role}@turnamen.in",
                    "username": f"elevated_{privileged_role}",
                    "full_name": "Unauthorized Escalation",
                    "password": "password123",
                    "role": privileged_role,
                }
            )


def test_self_registration_allows_player_and_captain_and_checks_conflicts(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    captain_res = auth.register(
        {
            "email": "newcaptain@turnamen.in",
            "username": "new_capt",
            "full_name": "Kapten Baru",
            "password": "password123",
            "role": ROLE_TEAM_CAPTAIN,
        }
    )
    assert captain_res["user"]["role"] == ROLE_TEAM_CAPTAIN
    assert "password_hash" not in captain_res["user"]

    with pytest.raises(DomainConflictError, match="Email sudah terdaftar"):
        auth.register(
            {
                "email": "newcaptain@turnamen.in",
                "username": "other_user",
                "full_name": "Duplikat Email",
                "password": "password123",
            }
        )

    with pytest.raises(DomainConflictError, match="Username sudah digunakan"):
        auth.register(
            {
                "email": "unique@turnamen.in",
                "username": "new_capt",
                "full_name": "Duplikat Username",
                "password": "password123",
            }
        )


def test_update_profile_and_role_assignment_security(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    player_login = auth.login("player@turnamen.in", "turnamen123")
    player_user = player_login["user"]
    admin_login = auth.login("admin@turnamen.in", "turnamen123")
    admin_user = admin_login["user"]

    updated = auth.update_profile(
        actor=player_user,
        target_user_id=player_user["id"],
        payload={"full_name": "Rizky Maulana Pro", "phone": "081299998888"},
    )
    assert updated["full_name"] == "Rizky Maulana Pro"
    assert updated["phone"] == "081299998888"
    assert "password_hash" not in updated

    with pytest.raises(DomainForbiddenError, match="tidak diizinkan mengubah role"):
        auth.update_profile(
            actor=player_user,
            target_user_id=player_user["id"],
            payload={"role": ROLE_SUPER_ADMIN},
        )

    with pytest.raises(DomainForbiddenError, match="milik sendiri"):
        auth.update_profile(
            actor=player_user,
            target_user_id=admin_user["id"],
            payload={"full_name": "Bajak Admin"},
        )

    with pytest.raises(DomainForbiddenError):
        auth.assign_role(actor=player_user, target_user_id=player_user["id"], new_role=ROLE_COMMITTEE)

    promoted = auth.assign_role(
        actor=admin_user,
        target_user_id=player_user["id"],
        new_role=ROLE_COMMITTEE,
    )
    assert promoted["role"] == ROLE_COMMITTEE


def test_role_permission_matrix() -> None:
    assert has_permission(ROLE_SUPER_ADMIN, "tournament:create") is True
    assert has_permission(ROLE_ORGANIZER, "tournament:create") is True
    assert has_permission(ROLE_COMMITTEE, "tournament:create") is False
    assert has_permission(ROLE_TEAM_CAPTAIN, "tournament:create") is False
    assert has_permission(ROLE_PLAYER, "tournament:create") is False

    assert has_permission(ROLE_COMMITTEE, "match:submit_result") is True
    assert has_permission(ROLE_COMMITTEE, "registration:verify") is True
    assert has_permission(ROLE_COMMITTEE, "announcement:create") is True
    assert has_permission(ROLE_TEAM_CAPTAIN, "team:create") is True
    assert has_permission(ROLE_TEAM_CAPTAIN, "registration:create") is True
    assert has_permission(ROLE_PLAYER, "match:submit_result") is False
    assert has_permission(ROLE_SUPER_ADMIN, "user:assign_role") is True
    assert has_permission(ROLE_ORGANIZER, "user:assign_role") is False

    player_user = {"id": "u1", "role": ROLE_PLAYER, "is_active": True}
    with pytest.raises(DomainForbiddenError):
        require_permission(player_user, "match:submit_result")

    with pytest.raises(DomainForbiddenError):
        require_any_role(player_user, (ROLE_SUPER_ADMIN, ROLE_ORGANIZER))

    inactive_user = {"id": "u2", "role": ROLE_SUPER_ADMIN, "is_active": False}
    with pytest.raises(DomainForbiddenError, match="dinonaktifkan"):
        require_authenticated(inactive_user)

    assert RolePermissionGuard.has_permission(ROLE_SUPER_ADMIN, "game:manage") is True


def test_repository_foreign_key_integrity(mock_repo: MockDataStoreRepository) -> None:
    organizer = mock_repo.get_profile_by_email("organizer@turnamen.in")
    captain = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert organizer is not None and captain is not None

    with pytest.raises(DomainNotFoundError, match="Game tidak ditemukan"):
        mock_repo.create_tournament(
            {
                "slug": "invalid-game-tour",
                "title": "Invalid Game Tournament",
                "game_id": "non-existent-game",
                "organizer_id": organizer["id"],
                "start_date": "2026-12-01T10:00:00+07:00",
            }
        )

    with pytest.raises(DomainNotFoundError, match="Game tidak ditemukan"):
        mock_repo.create_team(
            {
                "name": "Ghost Team",
                "tag": "GHT",
                "game_id": "non-existent-game",
                "captain_id": captain["id"],
            }
        )

    with pytest.raises(DomainNotFoundError, match="Turnamen tidak ditemukan"):
        mock_repo.create_registration(
            {
                "tournament_id": "non-existent-tournament",
                "team_id": "44444444-4444-4444-8444-444444444401",
                "registered_by": captain["id"],
            }
        )

    with pytest.raises(DomainNotFoundError, match="Tim tidak ditemukan"):
        mock_repo.create_registration(
            {
                "tournament_id": "33333333-3333-4333-8333-333333333301",
                "team_id": "non-existent-team",
                "registered_by": captain["id"],
            }
        )

    with pytest.raises(DomainNotFoundError, match="Pertandingan tidak ditemukan"):
        mock_repo.record_match_result(
            {
                "match_id": "non-existent-match",
                "score_a": 2,
                "score_b": 0,
                "winner_team_id": "44444444-4444-4444-8444-444444444401",
                "verified_by": organizer["id"],
            }
        )
