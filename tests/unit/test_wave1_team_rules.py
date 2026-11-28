"""Regression tests for team update validation and uniqueness (BUG-004)."""

from __future__ import annotations

import pytest

from backend.core.exceptions import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.teams.service import TeamService
from backend.repositories.mock.mock_repository import MockDataStoreRepository

TEAM_GRD = "44444444-4444-4444-8444-444444444401"
MLBB_GAME_ID = "22222222-2222-4222-8222-222222222201"


@pytest.fixture()
def captain(mock_repo: MockDataStoreRepository) -> dict:
    user = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert user is not None
    return user


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"name": "A"}, "name"),
        ({"name": "x" * 121}, "name"),
        ({"name": 123}, "name"),
        ({"tag": "A"}, "tag"),
        ({"tag": "TOOLONG"}, "tag"),
        ({"tag": "  "}, "tag"),
        ({"region": ""}, "region"),
        ({"region": "J"}, "region"),
        ({"region": "x" * 101}, "region"),
    ],
)
def test_update_team_rejects_invalid_fields(
    mock_repo: MockDataStoreRepository, captain: dict, payload: dict, field: str
) -> None:
    before = mock_repo.get_team_by_id(TEAM_GRD)

    with pytest.raises(DomainValidationError) as exc_info:
        TeamService(mock_repo).update_team(captain, TEAM_GRD, payload)

    assert exc_info.value.http_status == 400
    assert exc_info.value.details["field"] == field
    after = mock_repo.get_team_by_id(TEAM_GRD)
    assert (after["name"], after["tag"], after["region"]) == (before["name"], before["tag"], before["region"])


def test_update_team_rejects_case_insensitive_duplicate_name(
    mock_repo: MockDataStoreRepository, captain: dict
) -> None:
    with pytest.raises(DomainConflictError, match="Nama tim") as exc_info:
        TeamService(mock_repo).update_team(captain, TEAM_GRD, {"name": "  sriwijaya VANGUARD "})
    assert exc_info.value.http_status == 409
    assert mock_repo.get_team_by_id(TEAM_GRD)["name"] == "Garuda Esports"


def test_update_team_rejects_duplicate_tag(mock_repo: MockDataStoreRepository, captain: dict) -> None:
    with pytest.raises(DomainConflictError, match="Tag tim"):
        TeamService(mock_repo).update_team(captain, TEAM_GRD, {"tag": "srw"})
    assert mock_repo.get_team_by_id(TEAM_GRD)["tag"] == "GRD"


def test_update_team_with_own_identity_is_not_a_false_duplicate(
    mock_repo: MockDataStoreRepository, captain: dict
) -> None:
    updated = TeamService(mock_repo).update_team(
        captain, TEAM_GRD, {"name": " GARUDA ESPORTS ", "tag": "grd", "region": " Jakarta "}
    )
    assert updated["name"] == "GARUDA ESPORTS"
    assert updated["tag"] == "GRD"
    assert updated["region"] == "Jakarta"


def test_update_team_ignores_absent_and_null_fields(
    mock_repo: MockDataStoreRepository, captain: dict
) -> None:
    updated = TeamService(mock_repo).update_team(captain, TEAM_GRD, {"name": None, "region": "Bandung"})
    assert updated["name"] == "Garuda Esports"
    assert updated["region"] == "Bandung"


def test_create_team_enforces_maximum_lengths(mock_repo: MockDataStoreRepository, captain: dict) -> None:
    service = TeamService(mock_repo)
    with pytest.raises(DomainValidationError) as exc_info:
        service.create_team(captain, {"name": "x" * 121, "tag": "LNG", "game_id": MLBB_GAME_ID})
    assert exc_info.value.details["field"] == "name"

    with pytest.raises(DomainValidationError) as exc_info:
        service.create_team(
            captain, {"name": "Region Test", "tag": "RGN", "game_id": MLBB_GAME_ID, "region": "x" * 101}
        )
    assert exc_info.value.details["field"] == "region"


def test_create_team_rejects_non_string_inputs_and_blank_region(
    mock_repo: MockDataStoreRepository, captain: dict
) -> None:
    service = TeamService(mock_repo)
    with pytest.raises(DomainValidationError) as exc_info:
        service.create_team(captain, {"name": 1234, "tag": "NUM", "game_id": MLBB_GAME_ID})
    assert exc_info.value.details["field"] == "name"

    with pytest.raises(DomainValidationError) as exc_info:
        service.create_team(
            captain, {"name": "Blank Region", "tag": "BLR", "game_id": MLBB_GAME_ID, "region": "   "}
        )
    assert exc_info.value.details["field"] == "region"


def test_update_team_empty_payload_skips_repository_update(
    mock_repo: MockDataStoreRepository, captain: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail_update(*_args, **_kwargs):
        raise AssertionError("update_team repository method must not be called with empty updates")

    monkeypatch.setattr(mock_repo, "update_team", _fail_update)
    result = TeamService(mock_repo).update_team(captain, TEAM_GRD, {})
    assert result["id"] == TEAM_GRD


def test_add_member_enforces_max_lengths_and_validates_user_id(
    mock_repo: MockDataStoreRepository, captain: dict
) -> None:
    service = TeamService(mock_repo)
    with pytest.raises(DomainValidationError) as exc_info:
        service.add_member(
            captain, TEAM_GRD, {"nickname": "x" * 81, "ingame_id": "ML-889900"}
        )
    assert exc_info.value.details["field"] == "nickname"

    with pytest.raises(DomainValidationError) as exc_info:
        service.add_member(
            captain, TEAM_GRD, {"nickname": "ValidNick", "ingame_id": "x" * 101}
        )
    assert exc_info.value.details["field"] == "ingame_id"

    with pytest.raises(DomainNotFoundError) as exc_info:
        service.add_member(
            captain,
            TEAM_GRD,
            {
                "nickname": "GhostUser",
                "ingame_id": "ML-889901",
                "user_id": "00000000-0000-4000-8000-000000000099",
            },
        )
    assert exc_info.value.http_status == 404
