"""Unit tests for ReportService standings calculation and tournament summary reports."""

from __future__ import annotations

import pytest

from backend.core.exceptions import DomainNotFoundError
from backend.modules.matches.service import MatchService
from backend.modules.reports.service import ReportService
from backend.repositories.mock.mock_repository import MockDataStoreRepository

MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
VAL_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333302"


def test_report_and_standings_raise_not_found_for_unknown_tournament(
    mock_repo: MockDataStoreRepository,
) -> None:
    svc = ReportService(mock_repo)
    missing_id = "00000000-0000-4000-8000-000000000000"

    with pytest.raises(DomainNotFoundError):
        svc.get_tournament_standings(missing_id)

    with pytest.raises(DomainNotFoundError):
        svc.get_tournament_report(missing_id)


def test_report_for_tournament_without_matches_returns_zero_completion(
    mock_repo: MockDataStoreRepository,
) -> None:
    svc = ReportService(mock_repo)
    report = svc.get_tournament_report(VAL_TOURNAMENT_ID)

    assert report["summary"]["total_matches"] == 0
    assert report["summary"]["completed_matches"] == 0
    assert report["summary"]["completion_percentage"] == 0.0
    assert report["summary"]["champion_team"] is None
    assert isinstance(report["standings"], list)


def test_standings_ranks_bye_champion_above_runner_up_with_higher_game_diff(
    mock_repo: MockDataStoreRepository,
) -> None:
    organizer = mock_repo.get_profile_by_email("organizer@turnamen.in")
    assert organizer is not None

    # Create a 6-team tournament so Seed 1 & 2 receive Round 1 BYEs.
    created_tour = mock_repo.create_tournament(
        {
            "title": "Cup 6 Tim Uji BYE",
            "slug": "cup-6-tim-uji-bye",
            "game_id": "22222222-2222-4222-8222-222222222201",
            "organizer_id": organizer["id"],
            "format": "single_elimination",
            "status": "registration_open",
            "max_teams": 8,
            "best_of": 3,
            "registration_fee": 0,
            "prize_pool": 1000000,
            "venue": "Online",
            "start_date": "2026-12-20T10:00:00+07:00",
        }
    )
    tour_id = created_tour["id"]

    teams = mock_repo.list_teams(game_id="22222222-2222-4222-8222-222222222201")[:6]
    assert len(teams) == 6
    for idx, team in enumerate(teams, start=1):
        reg = mock_repo.create_registration(
            {
                "tournament_id": tour_id,
                "team_id": team["id"],
                "registered_by": organizer["id"],
                "seed_number": idx,
                "notes": "Seed test",
            }
        )
        mock_repo.update_registration_status(reg["id"], "approved", organizer["id"])

    match_svc = MatchService(mock_repo)
    bracket = match_svc.generate_bracket(organizer, tour_id)
    matches = bracket["matches"]

    qf_scheduled = [
        m for m in matches if m["round_number"] == 1 and m["status"] == "scheduled"
    ]
    sf_matches = [m for m in matches if m["round_number"] == 2]
    final_match = [m for m in matches if m["round_number"] == 3][0]

    # Bottom-half team wins QF 2-0 (+2) and SF 2-0 (+2), total +4 before Final.
    for m in qf_scheduled:
        match_svc.submit_match_result(organizer, m["id"], {"score_a": 2, "score_b": 0})

    # SF #1 (two BYE teams): Seed 1 wins narrowly 2-1 (+1).
    match_svc.submit_match_result(organizer, sf_matches[0]["id"], {"score_a": 2, "score_b": 1})
    # SF #2 (two non-BYE teams): Team A wins cleanly 2-0 (+2, cumulative +4).
    match_svc.submit_match_result(organizer, sf_matches[1]["id"], {"score_a": 2, "score_b": 0})
    # Grand Final: Seed 1 (BYE path) wins 2-1 (+1, total +2); Runner-Up has +3 game diff & same 2 wins.
    match_svc.submit_match_result(organizer, final_match["id"], {"score_a": 2, "score_b": 1})

    report_svc = ReportService(mock_repo)
    standings = report_svc.get_tournament_standings(tour_id)

    assert standings[0]["team_id"] == teams[0]["id"]
    assert standings[0]["rank"] == 1
    assert standings[0]["placement_label"] == "Juara 1 (Champion)"
    assert standings[1]["rank"] == 2
    assert standings[1]["placement_label"] == "Juara 2 (Runner-Up)"
