"""Unit tests for authentication (mock & online Supabase modes), 5-role RBAC, client security, and RLS hardening."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.contracts.dtos import (
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
    ROLE_PLAYER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_CAPTAIN,
)
from backend.core.config import AppConfig
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.infrastructure.supabase.client import (
    create_supabase_client,
    validate_supabase_credentials,
)
from backend.modules.auth.permissions import (
    RolePermissionGuard,
    has_permission,
    require_any_role,
    require_authenticated,
    require_permission,
)
from backend.modules.auth.service import AuthService
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository


def _build_test_jwt(payload: dict[str, Any]) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode("ascii").rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    signature = "test_signature_segment_12345"
    return f"{header}.{body}.{signature}"


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
        assert res["token"].startswith("tok_")
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


def test_supabase_client_credential_validation_and_no_monkey_patch() -> None:
    import re as stdlib_re
    from supabase._sync import client as sync_client_mod

    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    service_role_jwt = _build_test_jwt({"role": "service_role", "iss": "supabase"})

    with pytest.raises(RuntimeError, match="SUPABASE_URL dan SUPABASE_ANON_KEY belum tersedia"):
        validate_supabase_credentials("", "")

    with pytest.raises(RuntimeError, match="SUPABASE_URL tidak valid"):
        validate_supabase_credentials("https://your-project-ref.supabase.co", valid_anon_jwt)

    with pytest.raises(RuntimeError, match="service_role"):
        validate_supabase_credentials("https://example.supabase.co", "sb_secret_12345")

    with pytest.raises(RuntimeError, match="service_role"):
        validate_supabase_credentials("https://example.supabase.co", service_role_jwt)

    with pytest.raises(RuntimeError, match="sb_publishable_"):
        validate_supabase_credentials(
            "https://example.supabase.co",
            "sb_publishable_test_key_format",
        )

    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )
    client = create_supabase_client(cfg, access_token="user_jwt_token")
    assert client is not None
    assert sync_client_mod.re.match is stdlib_re.match


class _FakeOnlineSupabaseRepository(MockDataStoreRepository):
    """Test double simulating online Supabase repository with GoTrue Auth methods."""

    is_supabase_mode: bool = True

    def __init__(self) -> None:
        super().__init__()
        self.signed_out_tokens: list[str] = []
        self._jwt_to_auth_user: dict[str, dict[str, str]] = {}
        self._credentials: dict[str, tuple[str, str]] = {
            "organizer@turnamen.in": ("turnamen123", "auth-uuid-organizer-002"),
        }

    def auth_sign_up(
        self,
        email: str,
        password: str,
        user_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        auth_uid = "auth-uuid-new-user-999"
        jwt_token = _build_test_jwt({"sub": auth_uid, "role": "authenticated"})
        self._credentials[email] = (password, auth_uid)
        self._jwt_to_auth_user[jwt_token] = {"auth_user_id": auth_uid, "email": email}
        return {
            "auth_user_id": auth_uid,
            "email": email,
            "access_token": jwt_token,
        }

    def auth_sign_in(self, email: str, password: str) -> dict[str, Any]:
        cred = self._credentials.get(email)
        if not cred or cred[0] != password:
            raise DomainUnauthorizedError("Email atau password tidak sesuai.")
        auth_uid = cred[1]
        jwt_token = _build_test_jwt({"sub": auth_uid, "role": "authenticated"})
        self._jwt_to_auth_user[jwt_token] = {"auth_user_id": auth_uid, "email": email}
        return {
            "auth_user_id": auth_uid,
            "email": email,
            "access_token": jwt_token,
        }

    def auth_get_user(self, access_token: str) -> dict[str, Any] | None:
        return self._jwt_to_auth_user.get(access_token)

    def auth_sign_out(self, access_token: str) -> bool:
        if access_token in self._jwt_to_auth_user:
            del self._jwt_to_auth_user[access_token]
            self.signed_out_tokens.append(access_token)
            return True
        return False


def test_online_supabase_auth_separation_and_session_security() -> None:
    online_repo = _FakeOnlineSupabaseRepository()
    for p in online_repo._store["profiles"]:
        if p["email"] == "organizer@turnamen.in":
            p["auth_user_id"] = None
            p["password_hash"] = ""

    auth = AuthService(online_repo)

    assert auth.get_user_by_mock_header(mock_role=ROLE_SUPER_ADMIN) is None

    reg_res = auth.register(
        {
            "email": "onlineplayer@turnamen.in",
            "username": "online_player",
            "full_name": "Online Player",
            "password": "securepassword",
            "role": ROLE_PLAYER,
        }
    )
    assert reg_res["token"] is not None
    assert not reg_res["token"].startswith("tok_")
    assert auth._sessions == {}
    assert reg_res["user"]["auth_user_id"] == "auth-uuid-new-user-999"
    assert reg_res["user"]["role"] == ROLE_PLAYER

    login_res = auth.login("organizer@turnamen.in", "turnamen123")
    jwt_token = login_res["token"]
    assert not jwt_token.startswith("tok_")
    assert auth._sessions == {}
    assert login_res["user"]["role"] == ROLE_ORGANIZER
    assert login_res["user"]["auth_user_id"] == "auth-uuid-organizer-002"

    assert auth.get_user_by_token("tok_fake_mock_token") is None
    resolved = auth.get_user_by_token(jwt_token)
    assert resolved is not None
    assert resolved["email"] == "organizer@turnamen.in"
    assert resolved["role"] == ROLE_ORGANIZER

    assert auth.logout(jwt_token) is True
    assert jwt_token in online_repo.signed_out_tokens
    assert auth.get_user_by_token(jwt_token) is None


def test_atomic_replace_tournament_matches_preserves_existing_on_failure(
    mock_repo: MockDataStoreRepository,
) -> None:
    tournament_id = "33333333-3333-4333-8333-333333333301"
    before_matches = mock_repo.list_matches_by_tournament(tournament_id)
    assert len(before_matches) > 0

    with pytest.raises(DomainValidationError):
        mock_repo.replace_tournament_matches(
            tournament_id,
            [{"invalid_match_without_round_number": True}],
        )

    after_matches = mock_repo.list_matches_by_tournament(tournament_id)
    assert len(after_matches) == len(before_matches)


def test_supabase_repository_protocol_and_transactional_rpc() -> None:
    assert isinstance(MockDataStoreRepository(), DataStoreRepositoryProtocol)

    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )
    supa_repo = SupabaseDataStoreRepository(cfg)
    assert isinstance(supa_repo, DataStoreRepositoryProtocol)
    assert not hasattr(supa_repo, "_password_hashes")

    fake_client = MagicMock()
    supa_repo._client = fake_client
    supa_repo.get_tournament_by_id = MagicMock(return_value={"id": "t-1"})  # type: ignore[method-assign]
    supa_repo.list_matches_by_tournament = MagicMock(return_value=[{"id": "m-1"}])  # type: ignore[method-assign]

    res = supa_repo.replace_tournament_matches(
        "t-1",
        [{"id": "m-1", "round_number": 1, "match_number": 1}],
    )
    assert res == [{"id": "m-1"}]
    fake_client.rpc.assert_called_once()
    rpc_name, rpc_params = fake_client.rpc.call_args[0]
    assert rpc_name == "replace_tournament_matches"
    assert rpc_params["p_tournament_id"] == "t-1"


def test_rls_security_hardening_migration_policies() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "supabase"
        / "migrations"
        / "0002_security_hardening.sql"
    )
    assert migration_path.exists()
    sql = migration_path.read_text(encoding="utf-8")

    expected_tables = (
        "profiles",
        "games",
        "tournaments",
        "teams",
        "team_members",
        "tournament_staff",
        "registrations",
        "matches",
        "match_results",
        "payments",
        "announcements",
        "activity_logs",
    )
    for table in expected_tables:
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;" in sql

    assert "FOR ALL USING (true)" not in sql
    assert "WITH CHECK (true)" not in sql
    assert 'DROP POLICY IF EXISTS "Manage tournaments" ON public.tournaments;' in sql
    assert 'DROP POLICY IF EXISTS "Public read payments" ON public.payments;' in sql
    assert 'DROP POLICY IF EXISTS "Public read activity_logs" ON public.activity_logs;' in sql
    assert 'DROP POLICY IF EXISTS "Public read registrations" ON public.registrations;' in sql
    assert "CREATE OR REPLACE FUNCTION public.prevent_profile_privilege_escalation()" in sql
    assert "CREATE OR REPLACE FUNCTION public.replace_tournament_matches(" in sql
