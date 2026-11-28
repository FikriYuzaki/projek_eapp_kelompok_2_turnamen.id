"""Regression tests for match override, score typing, and bracket generation guards (BUG-001, BUG-014, BUG-015)."""

from __future__ import annotations

import pytest

from backend.core.exceptions import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.matches.bracket_engine import (
    SingleEliminationBracketEngine,
    validate_match_score,
)
from backend.modules.matches.service import MatchService
from backend.repositories.mock.mock_repository import MockDataStoreRepository

MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
VAL_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333302"
QF1_ID = "88888888-8888-4888-8888-888888888801"
QF4_ID = "88888888-8888-4888-8888-888888888804"
SF1_ID = "88888888-8888-4888-8888-888888888805"
TEAM_GRD = "44444444-4444-4444-8444-444444444401"
TEAM_SRW = "44444444-4444-4444-8444-444444444402"


@pytest.fixture()
def committee(mock_repo: MockDataStoreRepository) -> dict:
    user = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert user is not None
    return user


def _override(service: MatchService, actor: dict, match_id: str, score_a: int, score_b: int, notes: str = "Koreksi panitia"):
    return service.submit_match_result(
        actor=actor,
        match_id=match_id,
        payload={"score_a": score_a, "score_b": score_b, "force_override": True, "notes": notes},
    )


def test_override_with_same_winner_is_allowed_even_when_next_match_completed(
    mock_repo: MockDataStoreRepository, committee: dict
) -> None:
    service = MatchService(mock_repo)
    service.submit_match_result(committee, SF1_ID, {"score_a": 2, "score_b": 1})

    result = _override(service, committee, QF1_ID, 2, 1)

    assert result["match"]["winner_team_id"] == TEAM_GRD
    assert result["match"]["score_b"] == 1
    sf1 = mock_repo.get_match_by_id(SF1_ID)
    assert sf1["status"] == "completed"
    assert sf1["team_a_id"] == TEAM_GRD


def test_override_winner_while_next_match_scheduled_moves_new_winner(
    mock_repo: MockDataStoreRepository, committee: dict
) -> None:
    service = MatchService(mock_repo)

    result = _override(service, committee, QF1_ID, 0, 2)

    assert result["match"]["winner_team_id"] == TEAM_SRW
    assert mock_repo.get_match_by_id(SF1_ID)["team_a_id"] == TEAM_SRW


@pytest.mark.parametrize("next_status", ["ongoing", "completed"])
def test_override_winner_rejected_when_next_match_started(
    mock_repo: MockDataStoreRepository, committee: dict, next_status: str
) -> None:
    service = MatchService(mock_repo)
    if next_status == "completed":
        service.submit_match_result(committee, SF1_ID, {"score_a": 2, "score_b": 0})
    else:
        mock_repo.update_match(SF1_ID, {"status": "ongoing"})
    sf1_before = mock_repo.get_match_by_id(SF1_ID)

    with pytest.raises(DomainConflictError, match="babak berikutnya") as exc_info:
        _override(service, committee, QF1_ID, 0, 2)

    assert exc_info.value.http_status == 409
    qf1 = mock_repo.get_match_by_id(QF1_ID)
    assert qf1["winner_team_id"] == TEAM_GRD
    assert (qf1["score_a"], qf1["score_b"]) == (2, 0)
    sf1_after = mock_repo.get_match_by_id(SF1_ID)
    assert sf1_after["team_a_id"] == sf1_before["team_a_id"] == TEAM_GRD
    assert sf1_after["winner_team_id"] == sf1_before["winner_team_id"]


@pytest.mark.parametrize("notes", ["", "   ", "ok", None])
def test_override_without_audit_reason_is_rejected(
    mock_repo: MockDataStoreRepository, committee: dict, notes
) -> None:
    service = MatchService(mock_repo)
    payload = {"score_a": 0, "score_b": 2, "force_override": True}
    if notes is not None:
        payload["notes"] = notes

    with pytest.raises(DomainValidationError) as exc_info:
        service.submit_match_result(committee, QF1_ID, payload)

    assert exc_info.value.http_status == 400
    assert exc_info.value.details["field"] == "notes"
    assert mock_repo.get_match_by_id(QF1_ID)["winner_team_id"] == TEAM_GRD


@pytest.mark.parametrize(
    "score_a,score_b",
    [(2.0, 0), (2.9, 1), (True, 0), (2, False), ("2.5", 0), ("abc", 1), (None, 1)],
)
def test_score_rejects_float_boolean_and_decimal_strings(
    mock_repo: MockDataStoreRepository, committee: dict, score_a, score_b
) -> None:
    service = MatchService(mock_repo)

    with pytest.raises(DomainValidationError) as exc_info:
        service.submit_match_result(committee, QF4_ID, {"score_a": score_a, "score_b": score_b})

    assert exc_info.value.http_status == 400
    qf4 = mock_repo.get_match_by_id(QF4_ID)
    assert qf4["status"] == "scheduled"
    assert qf4["winner_team_id"] is None


def test_score_accepts_digit_strings_for_form_compatibility(
    mock_repo: MockDataStoreRepository, committee: dict
) -> None:
    result = MatchService(mock_repo).submit_match_result(
        committee, QF4_ID, {"score_a": "2", "score_b": "1"}
    )
    assert (result["match"]["score_a"], result["match"]["score_b"]) == (2, 1)


def test_validate_match_score_rejects_boolean_values() -> None:
    with pytest.raises(DomainValidationError):
        validate_match_score(True, False, best_of=1)
    with pytest.raises(DomainValidationError):
        validate_match_score(1, 0, best_of=True)


@pytest.mark.parametrize("best_of", [99, 0, 2, True, False, 3.0, "3.5", "abc"])
def test_bracket_engine_rejects_invalid_best_of(best_of) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        SingleEliminationBracketEngine.generate_bracket(
            tournament_id="tour-x", team_ids=["t1", "t2"], best_of=best_of
        )
    assert exc_info.value.details["field"] == "best_of"


@pytest.mark.parametrize("best_of", [99, True, 3.0])
def test_generate_bracket_service_rejects_invalid_best_of(
    mock_repo: MockDataStoreRepository, best_of
) -> None:
    admin = mock_repo.get_profile_by_email("admin@turnamen.in")
    matches_before = mock_repo.list_matches_by_tournament(VAL_TOURNAMENT_ID)

    with pytest.raises(DomainValidationError):
        MatchService(mock_repo).generate_bracket(
            admin, VAL_TOURNAMENT_ID, {"team_ids": ["t1", "t2"], "best_of": best_of}
        )

    assert mock_repo.list_matches_by_tournament(VAL_TOURNAMENT_ID) == matches_before


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_generate_bracket_rejected_for_finished_tournaments(
    mock_repo: MockDataStoreRepository, status: str
) -> None:
    admin = mock_repo.get_profile_by_email("admin@turnamen.in")
    mock_repo.update_tournament(MLBB_TOURNAMENT_ID, {"status": status})
    matches_before = mock_repo.list_matches_by_tournament(MLBB_TOURNAMENT_ID)

    with pytest.raises(DomainConflictError) as exc_info:
        MatchService(mock_repo).generate_bracket(admin, MLBB_TOURNAMENT_ID)

    assert exc_info.value.http_status == 409
    assert mock_repo.list_matches_by_tournament(MLBB_TOURNAMENT_ID) == matches_before


def test_generate_bracket_rejected_when_matches_already_started_or_completed(
    mock_repo: MockDataStoreRepository,
) -> None:
    admin = mock_repo.get_profile_by_email("admin@turnamen.in")
    assert admin is not None
    matches_before = mock_repo.list_matches_by_tournament(MLBB_TOURNAMENT_ID)

    with pytest.raises(DomainConflictError, match="berjalan atau selesai") as exc_info:
        MatchService(mock_repo).generate_bracket(admin, MLBB_TOURNAMENT_ID)

    assert exc_info.value.http_status == 409
    assert mock_repo.list_matches_by_tournament(MLBB_TOURNAMENT_ID) == matches_before


def test_generate_bracket_validates_explicit_team_ids(
    mock_repo: MockDataStoreRepository,
) -> None:
    admin = mock_repo.get_profile_by_email("admin@turnamen.in")
    assert admin is not None
    service = MatchService(mock_repo)

    with pytest.raises(DomainValidationError) as exc_info:
        service.generate_bracket(admin, VAL_TOURNAMENT_ID, {"team_ids": "not-a-list"})
    assert exc_info.value.details["field"] == "team_ids"

    with pytest.raises(DomainValidationError):
        service.generate_bracket(admin, VAL_TOURNAMENT_ID, {"team_ids": []})

    with pytest.raises(DomainNotFoundError):
        service.generate_bracket(admin, VAL_TOURNAMENT_ID, {"team_ids": ["missing-1", "missing-2"]})


def test_submit_match_result_rejects_bye_match_and_cancelled_tournament(
    mock_repo: MockDataStoreRepository, committee: dict
) -> None:
    service = MatchService(mock_repo)

    mock_repo.update_match(QF4_ID, {"status": "bye", "team_b_id": None})
    with pytest.raises(DomainConflictError, match="BYE") as bye_exc:
        service.submit_match_result(committee, QF4_ID, {"score_a": 2, "score_b": 0})
    assert bye_exc.value.http_status == 409

    mock_repo.update_tournament(MLBB_TOURNAMENT_ID, {"status": "cancelled"})
    with pytest.raises(DomainConflictError, match="dibatalkan") as cancel_exc:
        service.submit_match_result(
            committee, QF1_ID, {"score_a": 0, "score_b": 2, "force_override": True, "notes": "Koreksi"}
        )
    assert cancel_exc.value.http_status == 409
