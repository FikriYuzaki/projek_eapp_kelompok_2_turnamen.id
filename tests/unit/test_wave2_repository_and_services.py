"""Regression tests for Wave 2 repository rules: match_results upsert, cascade delete, and Supabase parity."""

from __future__ import annotations

from typing import Any

import pytest

from backend.core.config import AppConfig
from backend.modules.matches.service import MatchService
from backend.modules.tournaments.service import TournamentService
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
from tests.unit.test_auth_and_permissions import _build_test_jwt

MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
VAL_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333302"
QF1_ID = "88888888-8888-4888-8888-888888888801"
QF4_ID = "88888888-8888-4888-8888-888888888804"
TEAM_GRD = "44444444-4444-4444-8444-444444444401"
TEAM_SRW = "44444444-4444-4444-8444-444444444402"
TEAM_MTR = "44444444-4444-4444-8444-444444444407"
TEAM_DWT = "44444444-4444-4444-8444-444444444408"


def test_mock_record_match_result_upserts_by_match_and_game_number(
    mock_repo: MockDataStoreRepository,
) -> None:
    committee = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert committee is not None

    # Insert new result for QF4 game 1
    first = mock_repo.record_match_result(
        {
            "match_id": QF4_ID,
            "game_number": 1,
            "score_a": 1,
            "score_b": 0,
            "winner_team_id": TEAM_MTR,
            "notes": "Game 1",
            "verified_by": committee["id"],
        }
    )
    assert len(mock_repo.list_match_results(QF4_ID)) == 1

    # Update same (match_id, game_number=1) in-place without appending a duplicate
    updated = mock_repo.record_match_result(
        {
            "match_id": QF4_ID,
            "game_number": 1,
            "score_a": 0,
            "score_b": 1,
            "winner_team_id": TEAM_DWT,
            "notes": "Koreksi Game 1",
            "verified_by": committee["id"],
        }
    )
    results_after_update = mock_repo.list_match_results(QF4_ID)
    assert len(results_after_update) == 1
    assert updated["id"] == first["id"]
    assert results_after_update[0]["winner_team_id"] == TEAM_DWT
    assert results_after_update[0]["notes"] == "Koreksi Game 1"

    # Insert different game_number=2 -> preserves game 1 and adds game 2
    mock_repo.record_match_result(
        {
            "match_id": QF4_ID,
            "game_number": 2,
            "score_a": 1,
            "score_b": 0,
            "winner_team_id": TEAM_MTR,
            "notes": "Game 2",
            "verified_by": committee["id"],
        }
    )
    all_games = mock_repo.list_match_results(QF4_ID)
    assert len(all_games) == 2
    assert {r["game_number"] for r in all_games} == {1, 2}


def test_match_service_force_override_does_not_duplicate_match_results(
    mock_repo: MockDataStoreRepository,
) -> None:
    committee = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert committee is not None
    service = MatchService(mock_repo)

    assert len(mock_repo.list_match_results(QF1_ID)) == 1
    service.submit_match_result(
        committee,
        QF1_ID,
        {"score_a": 0, "score_b": 2, "force_override": True, "notes": "Koreksi resmi panitia"},
    )
    results = mock_repo.list_match_results(QF1_ID)
    assert len(results) == 1
    assert results[0]["winner_team_id"] == TEAM_SRW
    assert results[0]["score_a"] == 0
    assert results[0]["score_b"] == 2


def test_supabase_repository_upsert_match_result_and_consistency_guards() -> None:
    calls: list[dict[str, Any]] = []
    match_results_store: list[dict[str, Any]] = []

    class _Query:
        def __init__(self, table: str) -> None:
            self._table = table
            self._op = "select"
            self._payload: Any = None
            self._on_conflict = ""
            self._filters: list[tuple[str, Any]] = []

        def select(self, *_args):
            self._op = "select"
            return self

        def upsert(self, payload: dict[str, Any], on_conflict: str = ""):
            self._op = "upsert"
            self._payload = dict(payload)
            self._on_conflict = on_conflict
            return self

        def update(self, payload: dict[str, Any]):
            self._op = "update"
            self._payload = dict(payload)
            return self

        def eq(self, col: str, val: Any):
            self._filters.append((col, val))
            return self

        def limit(self, *_args):
            return self

        def execute(self):
            calls.append(
                {
                    "table": self._table,
                    "op": self._op,
                    "payload": self._payload,
                    "on_conflict": self._on_conflict,
                    "filters": list(self._filters),
                }
            )
            if self._table == "match_results" and self._op == "upsert":
                assert self._on_conflict == "match_id,game_number"
                for existing in match_results_store:
                    if (
                        existing["match_id"] == self._payload["match_id"]
                        and existing["game_number"] == self._payload["game_number"]
                    ):
                        existing.update(self._payload)
                        return type("Resp", (), {"data": [dict(existing)]})()
                new_row = {"id": f"mr-{len(match_results_store) + 1}", **self._payload}
                match_results_store.append(new_row)
                return type("Resp", (), {"data": [dict(new_row)]})()
            if self._table == "tournament_staff" and self._op == "select":
                return type(
                    "Resp",
                    (),
                    {
                        "data": [
                            {"tournament_id": MLBB_TOURNAMENT_ID},
                            {"tournament_id": MLBB_TOURNAMENT_ID},
                            {"tournament_id": VAL_TOURNAMENT_ID},
                        ]
                    },
                )()
            return type("Resp", (), {"data": []})()

    class _Client:
        def table(self, name: str):
            return _Query(name)

    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=_build_test_jwt({"role": "anon", "iss": "supabase"}),
    )
    repo = SupabaseDataStoreRepository(cfg, client_factory=lambda *_args, **_kwargs: _Client())
    assert isinstance(repo, DataStoreRepositoryProtocol)

    repo.record_match_result(
        {
            "match_id": QF1_ID,
            "game_number": 1,
            "score_a": 2,
            "score_b": 0,
            "winner_team_id": TEAM_GRD,
            "verified_by": "11111111-1111-4111-8111-111111111103",
        }
    )
    repo.record_match_result(
        {
            "match_id": QF1_ID,
            "game_number": 1,
            "score_a": 0,
            "score_b": 2,
            "winner_team_id": TEAM_SRW,
            "verified_by": "11111111-1111-4111-8111-111111111103",
        }
    )
    repo.record_match_result(
        {
            "match_id": QF1_ID,
            "game_number": 2,
            "score_a": 2,
            "score_b": 1,
            "winner_team_id": TEAM_GRD,
            "verified_by": "11111111-1111-4111-8111-111111111103",
        }
    )
    assert len(match_results_store) == 2
    assert match_results_store[0]["winner_team_id"] == TEAM_SRW

    assigned = repo.list_assigned_tournament_ids("11111111-1111-4111-8111-111111111103")
    assert assigned == [MLBB_TOURNAMENT_ID, VAL_TOURNAMENT_ID]
    assert repo.list_assigned_tournament_ids("not-a-uuid") == []

    # Empty updates must not send PostgREST `.update({})`
    calls.clear()
    repo.update_profile("11111111-1111-4111-8111-111111111103", {})
    repo.update_tournament(MLBB_TOURNAMENT_ID, {})
    repo.update_team(TEAM_GRD, {})
    repo.update_match(QF1_ID, {})
    assert not any(c["op"] == "update" for c in calls)


def test_delete_tournament_cascades_child_records_without_affecting_other_tournaments(
    mock_repo: MockDataStoreRepository,
) -> None:
    organizer = mock_repo.get_profile_by_email("organizer@turnamen.in")
    captain = mock_repo.get_profile_by_email("captain@turnamen.in")
    committee = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert organizer and captain and committee

    # Prepare child records on VAL_TOURNAMENT_ID while keeping MLBB_TOURNAMENT_ID populated
    reg = mock_repo.create_registration(
        {
            "tournament_id": VAL_TOURNAMENT_ID,
            "team_id": TEAM_GRD,
            "registered_by": captain["id"],
            "status": "approved",
        }
    )
    mock_repo._store["payments"].append(
        {
            "id": "pay-val-1",
            "registration_id": reg["id"],
            "amount": 75000.0,
            "status": "verified",
            "submitted_by": captain["id"],
        }
    )
    match = MatchService(mock_repo).generate_bracket(
        organizer, VAL_TOURNAMENT_ID, {"team_ids": [TEAM_GRD, TEAM_SRW]}
    )["matches"][0]
    mock_repo.record_match_result(
        {
            "match_id": match["id"],
            "game_number": 1,
            "score_a": 2,
            "score_b": 0,
            "winner_team_id": TEAM_GRD,
            "verified_by": committee["id"],
        }
    )
    mock_repo.create_announcement(
        {
            "tournament_id": VAL_TOURNAMENT_ID,
            "author_id": organizer["id"],
            "title": "Pengumuman VAL",
            "content": "Akan dihapus bersama turnamen.",
        }
    )
    # Move VAL back to cancelled so deletion is legally allowed by TournamentService
    mock_repo.update_tournament(VAL_TOURNAMENT_ID, {"status": "cancelled"})

    mlbb_matches_before = len(mock_repo.list_matches_by_tournament(MLBB_TOURNAMENT_ID))
    mlbb_regs_before = len(mock_repo.list_registrations_by_tournament(MLBB_TOURNAMENT_ID))
    mlbb_anns_before = len(mock_repo.list_announcements_by_tournament(MLBB_TOURNAMENT_ID))
    mlbb_logs_before = len(mock_repo.list_activity_logs(MLBB_TOURNAMENT_ID))

    TournamentService(mock_repo).delete_tournament(organizer, VAL_TOURNAMENT_ID)

    assert mock_repo.get_tournament_by_id(VAL_TOURNAMENT_ID) is None
    assert not any(s["tournament_id"] == VAL_TOURNAMENT_ID for s in mock_repo._store["tournament_staff"])
    assert mock_repo.list_registrations_by_tournament(VAL_TOURNAMENT_ID) == []
    assert not any(p["id"] == "pay-val-1" for p in mock_repo._store["payments"])
    assert mock_repo.list_matches_by_tournament(VAL_TOURNAMENT_ID) == []
    assert mock_repo.list_match_results(match["id"]) == []
    assert mock_repo.list_announcements_by_tournament(VAL_TOURNAMENT_ID) == []
    assert mock_repo.list_activity_logs(VAL_TOURNAMENT_ID) == []

    # Audit log for deletion exists exactly once with tournament_id=None
    deletion_logs = [
        log
        for log in mock_repo.list_activity_logs()
        if log["action"] == "TOURNAMENT_DELETED" and log["entity_id"] == VAL_TOURNAMENT_ID
    ]
    assert len(deletion_logs) == 1
    assert deletion_logs[0]["tournament_id"] is None

    # Unrelated MLBB tournament and its child records remain untouched
    assert mock_repo.get_tournament_by_id(MLBB_TOURNAMENT_ID) is not None
    assert len(mock_repo.list_matches_by_tournament(MLBB_TOURNAMENT_ID)) == mlbb_matches_before
    assert len(mock_repo.list_registrations_by_tournament(MLBB_TOURNAMENT_ID)) == mlbb_regs_before
    assert len(mock_repo.list_announcements_by_tournament(MLBB_TOURNAMENT_ID)) == mlbb_anns_before
    assert len(mock_repo.list_activity_logs(MLBB_TOURNAMENT_ID)) == mlbb_logs_before
    assert any(p["id"] == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01" for p in mock_repo._store["payments"])
