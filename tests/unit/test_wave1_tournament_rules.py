"""Regression tests for tournament input, status transition, and registration rules (BUG-002/003/005/010/011/014)."""

from __future__ import annotations

from typing import Any

import pytest

from backend.core.exceptions import DomainConflictError, DomainValidationError
from backend.modules.matches.service import MatchService
from backend.modules.tournaments.service import TournamentService
from backend.repositories.mock.mock_repository import MockDataStoreRepository

MLBB_GAME_ID = "22222222-2222-4222-8222-222222222201"
MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
VAL_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333302"
MLBB_REGISTRATION_ID = "77777777-7777-4777-8777-777777777701"
MLBB_TEAMS = [f"44444444-4444-4444-8444-44444444440{i}" for i in range(1, 7)]


@pytest.fixture()
def organizer(mock_repo: MockDataStoreRepository) -> dict:
    user = mock_repo.get_profile_by_email("organizer@turnamen.in")
    assert user is not None
    return user


@pytest.fixture()
def captain(mock_repo: MockDataStoreRepository) -> dict:
    user = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert user is not None
    return user


def _base_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": "Wave One Regression Cup",
        "game_id": MLBB_GAME_ID,
        "start_date": "2026-12-20T10:00:00+07:00",
        "max_teams": 4,
        "status": "open_registration",
    }
    payload.update(overrides)
    return payload


def _register(service: TournamentService, captain: dict, tournament_id: str, count: int) -> list[dict]:
    return [
        service.register_team(captain, tournament_id, {"team_id": team_id})
        for team_id in MLBB_TEAMS[:count]
    ]


@pytest.mark.parametrize("max_teams", ["abc", "", True, False, 8.5, 8.0, [], {}])
def test_create_rejects_non_integer_max_teams(
    mock_repo: MockDataStoreRepository, organizer: dict, max_teams
) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        TournamentService(mock_repo).create_tournament(organizer, _base_payload(max_teams=max_teams))
    assert exc_info.value.http_status == 400
    assert exc_info.value.details["field"] == "max_teams"


def test_create_accepts_integer_string_max_teams(
    mock_repo: MockDataStoreRepository, organizer: dict
) -> None:
    created = TournamentService(mock_repo).create_tournament(organizer, _base_payload(max_teams="8"))
    assert created["max_teams"] == 8


@pytest.mark.parametrize("best_of", [True, 3.0, 99, "3.5"])
def test_create_rejects_invalid_best_of(
    mock_repo: MockDataStoreRepository, organizer: dict, best_of
) -> None:
    with pytest.raises(DomainValidationError):
        TournamentService(mock_repo).create_tournament(organizer, _base_payload(best_of=best_of))


@pytest.mark.parametrize("fee", [True, "abc", -1, float("nan"), float("inf")])
def test_create_rejects_invalid_money_values(
    mock_repo: MockDataStoreRepository, organizer: dict, fee
) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        TournamentService(mock_repo).create_tournament(organizer, _base_payload(registration_fee=fee))
    assert exc_info.value.details["field"] == "registration_fee"


@pytest.mark.parametrize("title", ["", "   ", "abc", "x" * 181])
def test_create_and_update_reject_invalid_titles(
    mock_repo: MockDataStoreRepository, organizer: dict, title: str
) -> None:
    service = TournamentService(mock_repo)
    with pytest.raises(DomainValidationError):
        service.create_tournament(organizer, _base_payload(title=title))

    with pytest.raises(DomainValidationError) as exc_info:
        service.update_tournament(organizer, VAL_TOURNAMENT_ID, {"title": title})
    assert exc_info.value.details["field"] == "title"
    assert mock_repo.get_tournament_by_id(VAL_TOURNAMENT_ID)["title"].strip()


def test_update_rejects_max_teams_below_approved_count(
    mock_repo: MockDataStoreRepository, organizer: dict, captain: dict
) -> None:
    service = TournamentService(mock_repo)
    tour = service.create_tournament(organizer, _base_payload(max_teams=4))
    for reg in _register(service, captain, tour["id"], 3):
        service.update_registration_status(organizer, reg["id"], {"status": "approved"})

    with pytest.raises(DomainValidationError) as exc_info:
        service.update_tournament(organizer, tour["id"], {"max_teams": 2})
    assert exc_info.value.details["approved_count"] == 3
    assert mock_repo.get_tournament_by_id(tour["id"])["max_teams"] == 4

    assert service.update_tournament(organizer, tour["id"], {"max_teams": 3})["max_teams"] == 3


def test_update_rejects_non_integer_max_teams(
    mock_repo: MockDataStoreRepository, organizer: dict
) -> None:
    with pytest.raises(DomainValidationError):
        TournamentService(mock_repo).update_tournament(organizer, VAL_TOURNAMENT_ID, {"max_teams": "abc"})


def test_end_date_before_start_date_is_rejected(
    mock_repo: MockDataStoreRepository, organizer: dict
) -> None:
    service = TournamentService(mock_repo)
    with pytest.raises(DomainValidationError) as exc_info:
        service.create_tournament(
            organizer,
            _base_payload(start_date="2026-12-20T10:00:00+07:00", end_date="2026-12-19T10:00:00+07:00"),
        )
    assert exc_info.value.details["field"] == "end_date"

    tour = service.create_tournament(organizer, _base_payload(end_date="2026-12-22"))
    with pytest.raises(DomainValidationError):
        service.update_tournament(organizer, tour["id"], {"end_date": "2026-12-01T00:00:00Z"})
    with pytest.raises(DomainValidationError):
        service.update_tournament(organizer, tour["id"], {"start_date": "2026-12-30T00:00:00Z"})


@pytest.mark.parametrize("bad_date", ["besok", "2026-13-01", "20-12-2026"])
def test_invalid_dates_are_rejected(
    mock_repo: MockDataStoreRepository, organizer: dict, bad_date: str
) -> None:
    service = TournamentService(mock_repo)
    with pytest.raises(DomainValidationError) as exc_info:
        service.create_tournament(organizer, _base_payload(start_date=bad_date))
    assert exc_info.value.details["field"] == "start_date"

    with pytest.raises(DomainValidationError):
        service.create_tournament(organizer, _base_payload(end_date=bad_date))
    with pytest.raises(DomainValidationError):
        service.update_tournament(organizer, VAL_TOURNAMENT_ID, {"start_date": bad_date})


def test_registration_into_draft_tournament_is_rejected(
    mock_repo: MockDataStoreRepository, organizer: dict, captain: dict
) -> None:
    service = TournamentService(mock_repo)
    tour = service.create_tournament(organizer, _base_payload(status="draft"))

    with pytest.raises(DomainConflictError) as exc_info:
        service.register_team(captain, tour["id"], {"team_id": MLBB_TEAMS[0]})
    assert exc_info.value.http_status == 409
    assert mock_repo.list_registrations_by_tournament(tour["id"]) == []


def test_approval_beyond_quota_is_rejected(
    mock_repo: MockDataStoreRepository, organizer: dict, captain: dict
) -> None:
    service = TournamentService(mock_repo)
    tour = service.create_tournament(organizer, _base_payload(max_teams=3))
    regs = _register(service, captain, tour["id"], 3)
    service.update_tournament(organizer, tour["id"], {"max_teams": 2})

    service.update_registration_status(organizer, regs[0]["id"], {"status": "approved"})
    service.update_registration_status(organizer, regs[1]["id"], {"status": "approved"})
    with pytest.raises(DomainConflictError, match="Kuota") as exc_info:
        service.update_registration_status(organizer, regs[2]["id"], {"status": "approved"})

    assert exc_info.value.details["approved_count"] == 2
    assert mock_repo.get_registration_by_id(regs[2]["id"])["status"] == "pending"
    # Re-approving an already approved registration does not count against the quota.
    service.update_registration_status(organizer, regs[0]["id"], {"status": "approved"})


@pytest.mark.parametrize("new_status", ["rejected", "pending", "withdrawn", "approved"])
def test_registration_change_after_tournament_started_is_rejected(
    mock_repo: MockDataStoreRepository, organizer: dict, new_status: str
) -> None:
    with pytest.raises(DomainConflictError) as exc_info:
        TournamentService(mock_repo).update_registration_status(
            organizer, MLBB_REGISTRATION_ID, {"status": new_status}
        )
    assert exc_info.value.http_status == 409
    assert mock_repo.get_registration_by_id(MLBB_REGISTRATION_ID)["status"] == "approved"


def test_registration_change_rejected_once_bracket_exists(
    mock_repo: MockDataStoreRepository, organizer: dict, captain: dict
) -> None:
    service = TournamentService(mock_repo)
    tour = service.create_tournament(organizer, _base_payload(max_teams=2))
    regs = _register(service, captain, tour["id"], 2)
    for reg in regs:
        service.update_registration_status(organizer, reg["id"], {"status": "approved"})
    MatchService(mock_repo).generate_bracket(organizer, tour["id"])
    mock_repo.update_tournament(tour["id"], {"status": "registration_closed"})

    with pytest.raises(DomainConflictError, match="bracket"):
        service.update_registration_status(organizer, regs[0]["id"], {"status": "rejected"})


@pytest.mark.parametrize(
    "current,target",
    [
        ("ongoing", "draft"),
        ("ongoing", "open_registration"),
        ("ongoing", "registration_closed"),
        ("completed", "ongoing"),
        ("completed", "draft"),
        ("cancelled", "open_registration"),
        ("draft", "completed"),
    ],
)
def test_illegal_status_transitions_are_rejected(
    mock_repo: MockDataStoreRepository, organizer: dict, current: str, target: str
) -> None:
    mock_repo.update_tournament(VAL_TOURNAMENT_ID, {"status": current})

    with pytest.raises(DomainConflictError) as exc_info:
        TournamentService(mock_repo).update_tournament(organizer, VAL_TOURNAMENT_ID, {"status": target})

    assert exc_info.value.http_status == 409
    assert mock_repo.get_tournament_by_id(VAL_TOURNAMENT_ID)["status"] == current


def test_legal_status_transitions_are_allowed(
    mock_repo: MockDataStoreRepository, organizer: dict
) -> None:
    service = TournamentService(mock_repo)
    tour = service.create_tournament(organizer, _base_payload(status="draft"))
    for target in ("open_registration", "registration_closed", "ongoing"):
        assert service.update_tournament(organizer, tour["id"], {"status": target})["status"] == target

    # Transitioning ongoing -> completed must pass bracket integrity via transition_tournament_status.
    with pytest.raises(DomainConflictError, match="bracket"):
        service.update_tournament(organizer, tour["id"], {"status": "completed"})

    matches = mock_repo.replace_tournament_matches(
        tour["id"],
        [
            {
                "round_number": 1,
                "round_name": "Grand Final",
                "match_number": 1,
                "team_a_id": "44444444-4444-4444-8444-444444444401",
                "team_b_id": "44444444-4444-4444-8444-444444444402",
                "score_a": 2,
                "score_b": 0,
                "winner_team_id": "44444444-4444-4444-8444-444444444401",
                "status": "completed",
                "best_of": 3,
                "next_match_id": None,
                "next_slot": None,
            }
        ],
    )
    assert len(matches) == 1
    assert service.update_tournament(organizer, tour["id"], {"status": "completed"})["status"] == "completed"


@pytest.mark.parametrize("status", ["ongoing", "completed"])
def test_delete_ongoing_or_completed_tournament_is_rejected(
    mock_repo: MockDataStoreRepository, organizer: dict, status: str
) -> None:
    mock_repo.update_tournament(VAL_TOURNAMENT_ID, {"status": status})

    with pytest.raises(DomainConflictError) as exc_info:
        TournamentService(mock_repo).delete_tournament(organizer, VAL_TOURNAMENT_ID)

    assert exc_info.value.http_status == 409
    assert mock_repo.get_tournament_by_id(VAL_TOURNAMENT_ID) is not None


def test_delete_draft_tournament_writes_audit_log(
    mock_repo: MockDataStoreRepository, organizer: dict
) -> None:
    service = TournamentService(mock_repo)
    tour = service.create_tournament(organizer, _base_payload(status="draft"))

    service.delete_tournament(organizer, tour["id"])

    assert mock_repo.get_tournament_by_id(tour["id"]) is None
    deleted_logs = [
        log for log in mock_repo.list_activity_logs()
        if log["action"] == "TOURNAMENT_DELETED" and log["entity_id"] == tour["id"]
    ]
    assert len(deleted_logs) == 1
    assert deleted_logs[0]["actor_id"] == organizer["id"]


def test_create_and_update_tournament_validate_allow_draw_venue_and_empty_patch(
    mock_repo: MockDataStoreRepository, organizer: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = TournamentService(mock_repo)
    with pytest.raises(DomainValidationError) as exc_info:
        service.create_tournament(organizer, _base_payload(allow_draw="false"))
    assert exc_info.value.details["field"] == "allow_draw"

    with pytest.raises(DomainValidationError) as exc_info:
        service.create_tournament(organizer, _base_payload(venue="x" * 181))
    assert exc_info.value.details["field"] == "venue"

    def _fail_update(*_args, **_kwargs):
        raise AssertionError("update_tournament repository method must not be called with empty updates")

    monkeypatch.setattr(mock_repo, "update_tournament", _fail_update)
    unchanged = service.update_tournament(organizer, VAL_TOURNAMENT_ID, {})
    assert unchanged["id"] == VAL_TOURNAMENT_ID


def test_supabase_update_registration_status_records_verified_at() -> None:
    from backend.core.config import AppConfig
    from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
    from tests.unit.test_auth_and_permissions import _build_test_jwt

    captured: list[dict[str, Any]] = []

    class _Query:
        def update(self, payload: dict[str, Any]):
            captured.append(payload)
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            return type("Resp", (), {"data": [{"id": "reg-1", **captured[-1]}]})()

    class _Client:
        def table(self, _name: str):
            return _Query()

    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=_build_test_jwt({"role": "anon", "iss": "supabase"}),
    )
    repo = SupabaseDataStoreRepository(cfg, client_factory=lambda *_args, **_kwargs: _Client())
    reg_id = "77777777-7777-4777-8777-777777777701"
    updated = repo.update_registration_status(reg_id, "approved", "ver-1", "OK")
    assert updated is not None
    assert updated["verified_by"] == "ver-1"
    assert isinstance(updated["verified_at"], str) and len(updated["verified_at"]) > 10
    assert repo.update_registration_status("not-a-uuid", "approved", "ver-1", "OK") is None
