"""Unit tests for Single Elimination Bracket Engine, score validation, BYEs, and round progression."""

from __future__ import annotations

import pytest

from backend.core.exceptions import DomainConflictError, DomainValidationError
from backend.modules.matches.bracket_engine import (
    SingleEliminationBracketEngine,
    validate_match_score,
)
from backend.modules.matches.service import MatchService
from backend.repositories.mock.mock_repository import MockDataStoreRepository


def test_generate_8_team_bracket_structure() -> None:
    team_ids = [f"team-{i}" for i in range(1, 9)]
    matches = SingleEliminationBracketEngine.generate_bracket(
        tournament_id="tour-8",
        team_ids=team_ids,
        best_of=3,
    )

    # 8 teams -> 4 QF + 2 SF + 1 Grand Final = 7 matches
    assert len(matches) == 7
    qf = [m for m in matches if m["round_number"] == 1]
    sf = [m for m in matches if m["round_number"] == 2]
    final = [m for m in matches if m["round_number"] == 3]

    assert len(qf) == 4
    assert len(sf) == 2
    assert len(final) == 1
    assert qf[0]["round_name"] == "Quarter Final"
    assert sf[0]["round_name"] == "Semi Final"
    assert final[0]["round_name"] == "Grand Final"

    # Unplayed matches must not have a winner
    for m in matches:
        assert m["status"] == "scheduled"
        assert m["winner_team_id"] is None

    # Verify next_match_id and next_slot links
    assert qf[0]["next_match_id"] == sf[0]["id"]
    assert qf[0]["next_slot"] == "A"
    assert qf[1]["next_match_id"] == sf[0]["id"]
    assert qf[1]["next_slot"] == "B"
    assert sf[0]["next_match_id"] == final[0]["id"]
    assert sf[0]["next_slot"] == "A"
    assert sf[1]["next_match_id"] == final[0]["id"]
    assert sf[1]["next_slot"] == "B"


def test_generate_non_power_of_two_bracket_assigns_byes() -> None:
    # 6 teams -> padded to 8 slots -> 2 BYEs in Round 1
    team_ids = [f"team-{i}" for i in range(1, 7)]
    matches = SingleEliminationBracketEngine.generate_bracket(
        tournament_id="tour-6",
        team_ids=team_ids,
        best_of=3,
    )
    assert len(matches) == 7
    qf = [m for m in matches if m["round_number"] == 1]
    sf = [m for m in matches if m["round_number"] == 2]

    byes = [m for m in qf if m["status"] == "bye"]
    scheduled = [m for m in qf if m["status"] == "scheduled"]
    assert len(byes) == 2
    assert len(scheduled) == 2

    # The 2 BYE winners in QF #1 and QF #2 must already be promoted to SF #1 (slot A and B)
    assert byes[0]["winner_team_id"] == "team-1"
    assert byes[1]["winner_team_id"] == "team-2"
    assert sf[0]["team_a_id"] == "team-1"
    assert sf[0]["team_b_id"] == "team-2"


def test_score_validation_rules() -> None:
    assert validate_match_score(2, 0, best_of=3) == "A"
    assert validate_match_score(1, 2, best_of=3) == "B"

    # Ties/draws are rejected
    with pytest.raises(DomainValidationError, match="seri"):
        validate_match_score(1, 1, best_of=3)

    # Impossible Bo3 scores (e.g., 3-0 or 1-0) are rejected
    with pytest.raises(DomainValidationError):
        validate_match_score(3, 0, best_of=3)

    with pytest.raises(DomainValidationError):
        validate_match_score(1, 0, best_of=3)

    # Negative scores are rejected
    with pytest.raises(DomainValidationError):
        validate_match_score(-1, 2, best_of=3)


def test_match_winner_advancement_and_audit_lock(
    mock_repo: MockDataStoreRepository,
) -> None:
    match_service = MatchService(mock_repo)
    committee_user = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert committee_user is not None

    # QF #4 (`88888888-8888-4888-8888-888888888804`) is currently scheduled
    qf4_id = "88888888-8888-4888-8888-888888888804"
    sf2_id = "88888888-8888-4888-8888-888888888806"

    res = match_service.submit_match_result(
        actor=committee_user,
        match_id=qf4_id,
        payload={"score_a": 1, "score_b": 2, "notes": "Dewata menang tipis 2-1"},
    )
    assert res["match"]["status"] == "completed"
    assert res["match"]["winner_team_id"] == "44444444-4444-4444-8444-444444444408"

    # Winner must automatically advance to Semi Final #2 Slot B
    sf2 = mock_repo.get_match_by_id(sf2_id)
    assert sf2 is not None
    assert sf2["team_b_id"] == "44444444-4444-4444-8444-444444444408"

    # Attempting to overwrite a completed match without force_override must fail
    with pytest.raises(DomainConflictError, match="sudah disahkan dan dikunci"):
        match_service.submit_match_result(
            actor=committee_user,
            match_id=qf4_id,
            payload={"score_a": 2, "score_b": 0},
        )
