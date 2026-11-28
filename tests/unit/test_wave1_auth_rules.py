"""Regression tests for registration input validation and auth_user_id linking (BUG-012, SUPA-001 backend)."""

from __future__ import annotations

from typing import Any

import pytest

from backend.contracts.dtos import ROLE_PLAYER
from backend.core.config import AppConfig
from backend.core.exceptions import DomainUnauthorizedError, DomainValidationError
from backend.modules.auth.service import AuthService
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
from tests.unit.test_auth_and_permissions import _build_test_jwt, _RLSEnforcingSupabaseEngine

PLAYER_EMAIL = "player@turnamen.in"


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": "wave1.user@turnamen.in",
        "username": "wave1_user",
        "full_name": "Wave One User",
        "password": "password123",
        "role": ROLE_PLAYER,
    }
    payload.update(overrides)
    return payload


def _online_auth() -> tuple[_RLSEnforcingSupabaseEngine, SupabaseDataStoreRepository, AuthService]:
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=_build_test_jwt({"role": "anon", "iss": "supabase"}),
    )
    engine = _RLSEnforcingSupabaseEngine()
    repo = SupabaseDataStoreRepository(cfg, client_factory=engine.create_client)
    return engine, repo, AuthService(repo)


def _unlink_player(engine: _RLSEnforcingSupabaseEngine) -> dict[str, Any]:
    for profile in engine.store["profiles"]:
        if profile["email"] == PLAYER_EMAIL:
            profile["auth_user_id"] = None
            return profile
    raise AssertionError("player profile missing from seed")


@pytest.mark.parametrize(
    "email",
    ["@", "a@", "@b", "a@b", "a b@c.id", "a@b.", "a@@b.id", "plainaddress", ("x" * 251) + "@a.id"],
)
def test_register_rejects_invalid_email(mock_repo: MockDataStoreRepository, email: str) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        AuthService(mock_repo).register(_payload(email=email))
    assert exc_info.value.details["field"] == "email"


@pytest.mark.parametrize("username", ["ab", "x" * 61, "bad name", "user!", "budi@home", ""])
def test_register_rejects_invalid_username(mock_repo: MockDataStoreRepository, username: str) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        AuthService(mock_repo).register(_payload(username=username))
    assert exc_info.value.details["field"] == "username"


@pytest.mark.parametrize("full_name", ["", "   ", "A", "x" * 121])
def test_register_rejects_invalid_full_name(mock_repo: MockDataStoreRepository, full_name: str) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        AuthService(mock_repo).register(_payload(full_name=full_name))
    assert exc_info.value.details["field"] == "full_name"


@pytest.mark.parametrize("username", ["abc", "a" * 60, "user.name-01_x"])
def test_register_accepts_boundary_usernames(mock_repo: MockDataStoreRepository, username: str) -> None:
    result = AuthService(mock_repo).register(_payload(username=username, email=f"{len(username)}x@turnamen.in"))
    assert result["user"]["username"] == username


def test_mock_login_for_existing_profile_still_works(mock_repo: MockDataStoreRepository) -> None:
    auth = AuthService(mock_repo)
    result = auth.login(PLAYER_EMAIL, "turnamen123")
    assert result["token"].startswith("tok_")
    assert auth.get_user_by_token(result["token"])["email"] == PLAYER_EMAIL


def test_online_login_for_linked_profile_succeeds() -> None:
    _engine, _repo, auth = _online_auth()
    result = auth.login(PLAYER_EMAIL, "turnamen123")
    assert result["user"]["email"] == PLAYER_EMAIL
    assert auth.get_user_by_token(result["token"])["email"] == PLAYER_EMAIL


def test_online_login_without_linked_profile_is_rejected_and_not_auto_linked() -> None:
    engine, repo, auth = _online_auth()
    profile = _unlink_player(engine)
    email_lookups: list[str] = []
    original_lookup = repo.get_profile_by_email

    def _spy_lookup(email: str):
        email_lookups.append(email)
        return original_lookup(email)

    repo.get_profile_by_email = _spy_lookup  # type: ignore[method-assign]

    with pytest.raises(DomainUnauthorizedError, match="belum terhubung") as exc_info:
        auth.login(PLAYER_EMAIL, "turnamen123")

    assert exc_info.value.http_status == 401
    assert exc_info.value.details["reason"] == "profile_not_provisioned"
    assert profile["auth_user_id"] is None
    assert email_lookups == []
    profile_updates = [
        op for op in engine.recorded_operations if op["table"] == "profiles" and op["op"] == "update"
    ]
    assert profile_updates == []


def test_online_token_for_unlinked_profile_does_not_resolve_by_email() -> None:
    engine, _repo, auth = _online_auth()
    profile = _unlink_player(engine)
    token = _build_test_jwt({"sub": profile["id"], "email": PLAYER_EMAIL, "role": "authenticated"})

    assert auth.get_user_by_token(token) is None
    assert profile["auth_user_id"] is None


@pytest.mark.parametrize("bad_password", [123456, True, ["secret"], {"pw": "x"}])
def test_login_rejects_non_string_password_without_500(
    mock_repo: MockDataStoreRepository, bad_password: Any
) -> None:
    with pytest.raises(DomainValidationError):
        AuthService(mock_repo).login(PLAYER_EMAIL, bad_password)


def test_register_rejects_whitespace_password_and_non_string_fields(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    with pytest.raises(DomainValidationError) as exc_info:
        auth.register(_payload(password="      "))
    assert exc_info.value.details["field"] == "password"

    with pytest.raises(DomainValidationError) as exc_info:
        auth.register(_payload(full_name=["Array", "Name"]))
    assert exc_info.value.details["field"] == "full_name"


def test_update_profile_enforces_bounds_and_allows_null_role(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    player = auth.login(PLAYER_EMAIL, "turnamen123")["user"]

    with pytest.raises(DomainValidationError) as exc_info:
        auth.update_profile(player, player["id"], {"full_name": "x" * 121})
    assert exc_info.value.details["field"] == "full_name"

    with pytest.raises(DomainValidationError) as exc_info:
        auth.update_profile(player, player["id"], {"phone": "0" * 31})
    assert exc_info.value.details["field"] == "phone"

    updated = auth.update_profile(player, player["id"], {"full_name": "Pemain Valid", "role": None})
    assert updated["full_name"] == "Pemain Valid"


def test_supabase_repo_non_uuid_lookups_return_none_without_postgrest_error() -> None:
    _engine, repo, _auth = _online_auth()
    assert repo.get_profile_by_id("not-a-uuid") is None
    assert repo.get_profile_by_auth_user_id("not-a-uuid") is None
    assert repo.get_team_by_id("not-a-uuid") is None
    assert repo.get_registration_by_id("not-a-uuid") is None
    assert repo.get_match_by_id("not-a-uuid") is None
