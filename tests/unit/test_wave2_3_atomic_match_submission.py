"""Regression & failure-injection tests for Wave 2.3: Atomic Match Submission & Graph Integrity."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
import re
from typing import Any

import pytest

from backend.app import create_app
from backend.contracts.dtos import ROLE_COMMITTEE, ROLE_ORGANIZER
from backend.core.exceptions import DomainConflictError, DomainForbiddenError
from backend.infrastructure.supabase.client import use_access_token
from backend.modules.matches.bracket_engine import (
    SingleEliminationBracketEngine,
    validate_bracket_graph,
)
from backend.modules.matches.service import MatchService
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from tests.unit.test_wave2_1_supabase_rls_remediation import (
    COMMITTEE_ID,
    MLBB_GAME_ID,
    TEAM_GRD,
    TEAM_SRW,
    _supabase_setup,
)

ADMIN_EMAIL = "admin@turnamen.in"
ORGANIZER_EMAIL = "organizer@turnamen.in"
ORGANIZER2_EMAIL = "organizer2@turnamen.in"
COMMITTEE_EMAIL = "committee@turnamen.in"
CAPTAIN_EMAIL = "captain@turnamen.in"
PLAYER_EMAIL = "player@turnamen.in"

SEED_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
QF4_ID = "88888888-8888-4888-8888-888888888804"
SF1_ID = "88888888-8888-4888-8888-888888888805"
SF2_ID = "88888888-8888-4888-8888-888888888806"
GF_ID = "88888888-8888-4888-8888-888888888807"


def _prepare_ready_grand_final(repo: Any, run_ctx: Any) -> dict[str, Any]:
    """Complete prerequisite QF4/SF1/SF2 so Grand Final is ready to settle."""
    committee = run_ctx(lambda: repo.get_profile_by_email(COMMITTEE_EMAIL))
    assert committee is not None
    service = MatchService(repo)
    run_ctx(lambda: service.submit_match_result(committee, QF4_ID, {"score_a": 2, "score_b": 0}))
    run_ctx(lambda: service.submit_match_result(committee, SF1_ID, {"score_a": 2, "score_b": 1}))
    run_ctx(lambda: service.submit_match_result(committee, SF2_ID, {"score_a": 2, "score_b": 0}))
    return committee


@pytest.mark.parametrize("mode", ["mock", "supabase_rls"])
def test_f1_f2_atomic_rollback_on_transition_or_upsert_failure(mode: str) -> None:
    """F1 (transition fails) & F2 (transition completed succeeds, upsert fails) both roll back cleanly."""
    if mode == "supabase_rls":
        engine, repo, _cfg = _supabase_setup()
        comm_jwt = engine.token_for_profile(COMMITTEE_EMAIL)

        def run_ctx(fn: Any) -> Any:
            with use_access_token(comm_jwt):
                return fn()
    else:
        engine = None
        repo = MockDataStoreRepository()

        def run_ctx(fn: Any) -> Any:
            return fn()

    committee = _prepare_ready_grand_final(repo, run_ctx)
    service = MatchService(repo)

    before_gf = run_ctx(lambda: repo.get_match_by_id(GF_ID))
    before_tour = run_ctx(lambda: repo.get_tournament_by_id(SEED_TOURNAMENT_ID))
    before_logs_count = len(run_ctx(lambda: repo.list_activity_logs(SEED_TOURNAMENT_ID)))
    assert before_gf is not None and before_tour is not None
    assert before_tour["status"] == "ongoing"

    # F1: update_match succeeds, then tournament transition fails
    if mode == "supabase_rls":
        assert engine is not None
        engine._fail_atomic_hook = lambda step: (  # type: ignore[attr-defined]
            (_ for _ in ()).throw(DomainConflictError("Simulated F1 transition failure"))
            if step == "transition_tournament"
            else None
        )
    else:
        orig_trans = repo._atomic_transition_tournament

        def _fail_f1(tid: str, status: str) -> Any:
            raise DomainConflictError("Simulated F1 transition failure")

        repo._atomic_transition_tournament = _fail_f1  # type: ignore[method-assign]

    try:
        with pytest.raises(DomainConflictError, match="Simulated F1"):
            run_ctx(lambda: service.submit_match_result(committee, GF_ID, {"score_a": 2, "score_b": 1}))
    finally:
        if mode == "supabase_rls":
            engine._fail_atomic_hook = None  # type: ignore[attr-defined]
        else:
            repo._atomic_transition_tournament = orig_trans  # type: ignore[method-assign]

    assert run_ctx(lambda: repo.get_match_by_id(GF_ID))["status"] == before_gf["status"]
    assert run_ctx(lambda: repo.get_match_by_id(GF_ID))["winner_team_id"] is None
    assert run_ctx(lambda: repo.get_tournament_by_id(SEED_TOURNAMENT_ID))["status"] == "ongoing"
    assert run_ctx(lambda: repo.list_match_results(GF_ID)) == []
    assert len(run_ctx(lambda: repo.list_activity_logs(SEED_TOURNAMENT_ID))) == before_logs_count

    # F2: transition to 'completed' SUCCEEDS, then match_results upsert intentionally FAILS!
    if mode == "supabase_rls":
        assert engine is not None
        engine._fail_atomic_hook = lambda step: (  # type: ignore[attr-defined]
            (_ for _ in ()).throw(RuntimeError("Simulated F2 match_results upsert failure"))
            if step == "upsert_match_result"
            else None
        )
    else:
        orig_upsert = repo._atomic_upsert_match_result

        def _fail_f2(data: dict[str, Any]) -> Any:
            raise RuntimeError("Simulated F2 match_results upsert failure")

        repo._atomic_upsert_match_result = _fail_f2  # type: ignore[method-assign]

    try:
        with pytest.raises(RuntimeError, match="Simulated F2"):
            run_ctx(lambda: service.submit_match_result(committee, GF_ID, {"score_a": 2, "score_b": 0}))
    finally:
        if mode == "supabase_rls":
            engine._fail_atomic_hook = None  # type: ignore[attr-defined]
        else:
            repo._atomic_upsert_match_result = orig_upsert  # type: ignore[method-assign]

    # Critical F2 invariant: tournament must NOT be stuck in 'completed' when upsert failed!
    assert run_ctx(lambda: repo.get_tournament_by_id(SEED_TOURNAMENT_ID))["status"] == "ongoing"
    gf_after_f2 = run_ctx(lambda: repo.get_match_by_id(GF_ID))
    assert gf_after_f2["status"] == before_gf["status"]
    assert gf_after_f2["winner_team_id"] is None
    assert gf_after_f2["score_a"] == 0
    assert run_ctx(lambda: repo.list_match_results(GF_ID)) == []
    assert len(run_ctx(lambda: repo.list_activity_logs(SEED_TOURNAMENT_ID))) == before_logs_count


def test_f3_isolated_rollback_continues_when_first_rollback_fails_and_logs_critical(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """F3: Failure in one compensating rollback step still runs remaining rollbacks and preserves primary error."""
    repo = MockDataStoreRepository()
    committee = _prepare_ready_grand_final(repo, lambda fn: fn())
    service = MatchService(repo)

    before_tour_status = repo.get_tournament_by_id(SEED_TOURNAMENT_ID)["status"]
    assert before_tour_status == "ongoing"

    orig_insert_log = repo._atomic_insert_activity_log
    orig_rb_results = repo._rollback_match_results

    def _fail_primary_log(**kwargs: Any) -> Any:
        raise DomainConflictError("Primary audit log failure")

    def _fail_secondary_rollback(*args: Any, **kwargs: Any) -> None:
        raise OSError("Secondary rollback failure on match_results")

    repo._atomic_insert_activity_log = _fail_primary_log  # type: ignore[method-assign]
    repo._rollback_match_results = _fail_secondary_rollback  # type: ignore[method-assign]

    with caplog.at_level(logging.CRITICAL):
        try:
            with pytest.raises(DomainConflictError, match="Primary audit log failure") as exc_info:
                service.submit_match_result(committee, GF_ID, {"score_a": 2, "score_b": 0})
        finally:
            repo._atomic_insert_activity_log = orig_insert_log  # type: ignore[method-assign]
            repo._rollback_match_results = orig_rb_results  # type: ignore[method-assign]

    # Primary error is preserved & documents unrecovered target; secondary rollback error logged at CRITICAL
    assert exc_info.value.details.get("rollback_incomplete") is True
    assert "match_results" in exc_info.value.details.get("unrecovered_targets", [])
    assert isinstance(exc_info.value.__cause__, OSError)
    assert any(
        record.levelno == logging.CRITICAL
        and "match_results" in record.getMessage()
        and "Primary audit log failure" in record.getMessage()
        for record in caplog.records
    )

    # Subsequent rollbacks AFTER failed match_results rollback STILL ran!
    assert repo.get_tournament_by_id(SEED_TOURNAMENT_ID)["status"] == "ongoing"
    gf_restored = repo.get_match_by_id(GF_ID)
    assert gf_restored is not None
    assert gf_restored["status"] == "scheduled"
    assert gf_restored["winner_team_id"] is None


@pytest.mark.parametrize("mode", ["mock", "supabase_rls"])
def test_f4_post_commit_timeout_retry_with_idempotency_key_no_duplication(mode: str) -> None:
    """F4: Timeout after DB commit -> retry with same Idempotency-Key replays cleanly without side effects."""
    if mode == "supabase_rls":
        engine, repo, cfg = _supabase_setup()
        app = create_app(config=cfg, repository=repo)
        comm_headers = {"Authorization": f"Bearer {engine.token_for_profile(COMMITTEE_EMAIL)}"}
        comm_jwt = engine.token_for_profile(COMMITTEE_EMAIL)

        def run_ctx(fn: Any) -> Any:
            with use_access_token(comm_jwt):
                return fn()
    else:
        engine = None
        repo = MockDataStoreRepository()
        app = create_app(repository=repo)
        login = app.test_client().post(
            "/api/v1/auth/login", json={"email": COMMITTEE_EMAIL, "password": "turnamen123"}
        )
        comm_headers = {"Authorization": f"Bearer {login.get_json()['data']['token']}"}

        def run_ctx(fn: Any) -> Any:
            return fn()

    _prepare_ready_grand_final(repo, run_ctx)
    client = app.test_client()
    logs_before = len(run_ctx(lambda: repo.list_activity_logs(SEED_TOURNAMENT_ID)))

    # Inject post-commit response timeout on attempt 1
    if mode == "supabase_rls":
        assert engine is not None
        engine._post_commit_timeout_once = True  # type: ignore[attr-defined]
    else:
        orig_atomic = repo.submit_match_result_atomic

        def _commit_then_timeout(**kwargs: Any) -> dict[str, Any]:
            orig_atomic(**kwargs)
            repo.submit_match_result_atomic = orig_atomic  # type: ignore[method-assign]
            raise TimeoutError("Simulated network timeout reading response after commit")

        repo.submit_match_result_atomic = _commit_then_timeout  # type: ignore[method-assign]

    idem_key = "wave23-gf-submit-001"
    # Client sees HTTP 500 error response after response timeout, even though DB committed
    timeout_resp = client.patch(
        f"/api/v1/matches/{GF_ID}/result",
        headers={**comm_headers, "Idempotency-Key": idem_key},
        json={"score_a": 2, "score_b": 1, "notes": "Final submission"},
    )
    assert timeout_resp.status_code == 500
    assert timeout_resp.get_json()["success"] is False

    # DB actually already committed Grand Final -> tournament completed, 1 match_result, +1 activity_log
    assert run_ctx(lambda: repo.get_tournament_by_id(SEED_TOURNAMENT_ID))["status"] == "completed"
    assert len(run_ctx(lambda: repo.list_match_results(GF_ID))) == 1
    assert len(run_ctx(lambda: repo.list_activity_logs(SEED_TOURNAMENT_ID))) == logs_before + 1

    # Client retries exact same request with same Idempotency-Key -> succeeds with replay=True and ZERO duplicates
    retry_resp = client.patch(
        f"/api/v1/matches/{GF_ID}/result",
        headers={**comm_headers, "Idempotency-Key": idem_key},
        json={"score_a": 2, "score_b": 1, "notes": "Final submission"},
    )
    assert retry_resp.status_code == 200
    retry_data = retry_resp.get_json()["data"]
    assert retry_data["idempotent_replay"] is True
    assert retry_data["match"]["score_a"] == 2
    assert retry_data["match"]["score_b"] == 1
    assert len(run_ctx(lambda: repo.list_match_results(GF_ID))) == 1
    assert len(run_ctx(lambda: repo.list_activity_logs(SEED_TOURNAMENT_ID))) == logs_before + 1

    # Reusing the same Idempotency-Key for a DIFFERENT score must fail with 409 Conflict
    mismatch_resp = client.patch(
        f"/api/v1/matches/{GF_ID}/result",
        headers={**comm_headers, "Idempotency-Key": idem_key},
        json={"score_a": 0, "score_b": 2, "force_override": True, "notes": "Ubah skor pakai key lama"},
    )
    assert mismatch_resp.status_code == 409

    # New Idempotency-Key WITHOUT force_override cannot alter already-completed final
    no_override_resp = client.patch(
        f"/api/v1/matches/{GF_ID}/result",
        headers={**comm_headers, "Idempotency-Key": "wave23-gf-submit-002"},
        json={"score_a": 0, "score_b": 2},
    )
    assert no_override_resp.status_code == 409


def test_f5_full_bracket_graph_rejects_cycles_disconnects_dup_slots_and_accepts_4_to_8_teams() -> None:
    """F5: Graph traversal proves cycle/disconnect/slot safety and passes valid 4,5,6,7,8-team brackets."""
    tour_id = "33333333-3333-4333-8333-333333333399"
    base_teams = [f"44444444-4444-4444-8444-44444444440{i}" for i in range(1, 9)]

    def _completed_bracket(team_count: int) -> list[dict[str, Any]]:
        matches = SingleEliminationBracketEngine.generate_bracket(
            tour_id, base_teams[:team_count], best_of=3
        )
        # Simulate playing through rounds using real slot wiring
        by_id = {m["id"]: m for m in matches}
        rounds = sorted({m["round_number"] for m in matches})
        for r in rounds:
            for m in matches:
                if m["round_number"] == r and m["status"] != "bye":
                    winner = m["team_a_id"]
                    m["status"] = "completed"
                    m["score_a"] = 2
                    m["score_b"] = 0
                    m["winner_team_id"] = winner
                    if m["next_match_id"] and m["next_slot"]:
                        nxt = by_id[m["next_match_id"]]
                        if m["next_slot"] == "A":
                            nxt["team_a_id"] = winner
                        else:
                            nxt["team_b_id"] = winner
        return matches

    # Valid Single Elimination brackets with 4, 5, 6, 7, and 8 teams (including BYEs)
    for count in (4, 5, 6, 7, 8):
        valid_matches = _completed_bracket(count)
        gf = validate_bracket_graph(tour_id, valid_matches)
        assert gf["next_match_id"] is None

    # 1. Zero Grand Finals (every node points onward in a 2-node cycle)
    m4 = _completed_bracket(4)
    m4[2]["next_match_id"] = m4[0]["id"]
    m4[2]["next_slot"] = "A"
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m4)

    # 2. More than one terminal Grand Final
    m4 = _completed_bracket(4)
    m4[1]["next_match_id"] = None
    m4[1]["next_slot"] = None
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m4)

    # 3. Self-loop
    m4 = _completed_bracket(4)
    m4[0]["next_match_id"] = m4[0]["id"]
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m4)

    # 4. 2-node cycle (R1_A <-> R1_B, while R2 GF remains the sole next_match_id=None node!)
    m4 = _completed_bracket(4)
    m4[0]["next_match_id"] = m4[1]["id"]
    m4[0]["next_slot"] = "A"
    m4[1]["next_match_id"] = m4[0]["id"]
    m4[1]["next_slot"] = "B"
    m4[0]["round_number"] = 1
    m4[1]["round_number"] = 1
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m4)

    # 5. 3-node cycle in 8-team bracket + valid 1-node GF still next_match_id=None
    m8 = _completed_bracket(8)
    m8[0]["next_match_id"] = m8[1]["id"]
    m8[0]["next_slot"] = "A"
    m8[1]["next_match_id"] = m8[2]["id"]
    m8[1]["next_slot"] = "B"
    m8[2]["next_match_id"] = m8[0]["id"]
    m8[2]["next_slot"] = "A"
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m8)

    # 6. Duplicate feeder slot (two feeders both targeting GF slot 'A')
    m4 = _completed_bracket(4)
    m4[1]["next_slot"] = "A"
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m4)

    # 7. Invalid next_slot & cross-tournament target
    m4 = _completed_bracket(4)
    m4[0]["next_slot"] = "Z"
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m4)

    m4 = _completed_bracket(4)
    m4[0]["next_match_id"] = "99999999-9999-4999-8999-999999999999"
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m4)

    # 8. Unfinished feeder even with valid wiring
    m5 = _completed_bracket(5)
    non_bye_feeder = next(m for m in m5 if m["next_match_id"] is not None and m["status"] == "completed")
    non_bye_feeder["status"] = "scheduled"
    with pytest.raises(DomainConflictError):
        validate_bracket_graph(tour_id, m5)


@pytest.mark.parametrize("mode", ["mock", "supabase_rls"])
def test_f6_concurrent_committee_force_override_consistent_no_interleaving(mode: str) -> None:
    """F6: Two committee staff submitting concurrent force_override never interleave match/results state."""
    comm2_id = "11111111-1111-4111-8111-111111111179"
    if mode == "supabase_rls":
        engine, repo, _cfg = _supabase_setup()
        engine.store["profiles"].append(
            {
                "id": comm2_id,
                "auth_user_id": comm2_id,
                "email": "comm2@turnamen.in",
                "username": "comm2",
                "full_name": "Panitia Dua",
                "role": ROLE_COMMITTEE,
                "is_active": True,
            }
        )
        engine.store["tournament_staff"].append(
            {
                "id": "66666666-6666-4666-8666-666666666779",
                "tournament_id": SEED_TOURNAMENT_ID,
                "user_id": comm2_id,
                "staff_role": "referee",
            }
        )
        comm1_jwt = engine.token_for_profile(COMMITTEE_EMAIL)
        comm2_jwt = engine.token_for_profile("comm2@turnamen.in")

        def run_comm1(fn: Any) -> Any:
            with use_access_token(comm1_jwt):
                return fn()

        def run_comm2(fn: Any) -> Any:
            with use_access_token(comm2_jwt):
                return fn()
    else:
        repo = MockDataStoreRepository()
        repo._store["profiles"].append(
            {
                "id": comm2_id,
                "auth_user_id": None,
                "email": "comm2@turnamen.in",
                "username": "comm2",
                "full_name": "Panitia Dua",
                "role": ROLE_COMMITTEE,
                "is_active": True,
                "password_hash": "",
            }
        )
        repo._store["tournament_staff"].append(
            {
                "id": "66666666-6666-4666-8666-666666666779",
                "tournament_id": SEED_TOURNAMENT_ID,
                "user_id": comm2_id,
                "staff_role": "referee",
            }
        )

        def run_comm1(fn: Any) -> Any:
            return fn()

        def run_comm2(fn: Any) -> Any:
            return fn()

    comm1 = _prepare_ready_grand_final(repo, run_comm1)
    comm2 = run_comm2(lambda: repo.get_profile_by_email("comm2@turnamen.in"))
    assert comm2 is not None
    service = MatchService(repo)

    # First settle GF cleanly
    run_comm1(lambda: service.submit_match_result(comm1, GF_ID, {"score_a": 2, "score_b": 0}))
    assert run_comm1(lambda: repo.get_tournament_by_id(SEED_TOURNAMENT_ID))["status"] == "completed"

    def _override_a() -> dict[str, Any]:
        return run_comm1(
            lambda: service.submit_match_result(
                comm1,
                GF_ID,
                {"score_a": 2, "score_b": 1, "force_override": True, "notes": "Koreksi panitia satu"},
            )
        )

    def _override_b() -> dict[str, Any]:
        return run_comm2(
            lambda: service.submit_match_result(
                comm2,
                GF_ID,
                {"score_a": 1, "score_b": 2, "force_override": True, "notes": "Koreksi panitia dua"},
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(_override_a)
        fut_b = pool.submit(_override_b)
        fut_a.result()
        fut_b.result()

    final_match = run_comm1(lambda: repo.get_match_by_id(GF_ID))
    final_results = run_comm1(lambda: repo.list_match_results(GF_ID))
    assert final_match is not None
    assert len(final_results) == 1
    # Crucial: match row and match_results row belong to the EXACT SAME serialized transaction!
    res_row = final_results[0]
    assert (final_match["score_a"], final_match["score_b"]) == (res_row["score_a"], res_row["score_b"])
    assert final_match["winner_team_id"] == res_row["winner_team_id"]
    if res_row["verified_by"] == comm1["id"]:
        assert (res_row["score_a"], res_row["score_b"]) == (2, 1)
    else:
        assert res_row["verified_by"] == comm2["id"]
        assert (res_row["score_a"], res_row["score_b"]) == (1, 2)
    assert run_comm1(lambda: repo.get_tournament_by_id(SEED_TOURNAMENT_ID))["status"] == "completed"


def test_atomic_submission_role_authorization_both_modes() -> None:
    """Super Admin, owning Organizer, and assigned Committee allowed; unassigned/player/captain denied."""
    engine, supa_repo, _cfg = _supabase_setup()
    # Add unassigned committee and a second organizer who does NOT own seed tournament
    unassigned_id = "11111111-1111-4111-8111-111111111171"
    other_org_id = "11111111-1111-4111-8111-111111111172"
    engine.store["profiles"].extend(
        [
            {
                "id": unassigned_id,
                "auth_user_id": unassigned_id,
                "email": "comm.unassigned@turnamen.in",
                "username": "comm_unassigned",
                "full_name": "Panitia Tak Ditugaskan",
                "role": ROLE_COMMITTEE,
                "is_active": True,
            },
            {
                "id": other_org_id,
                "auth_user_id": other_org_id,
                "email": ORGANIZER2_EMAIL,
                "username": "org_other",
                "full_name": "Organizer Lain",
                "role": ROLE_ORGANIZER,
                "is_active": True,
            },
        ]
    )

    for denied_email in (PLAYER_EMAIL, CAPTAIN_EMAIL, ORGANIZER2_EMAIL, "comm.unassigned@turnamen.in"):
        jwt = engine.token_for_profile(denied_email)
        with use_access_token(jwt):
            with pytest.raises(DomainForbiddenError):
                supa_repo.submit_match_result_atomic(
                    match_id=QF4_ID,
                    score_a=2,
                    score_b=0,
                    winner_team_id="44444444-4444-4444-8444-444444444407",
                )

    with pytest.raises(DomainForbiddenError):
        supa_repo.submit_match_result_atomic(
            match_id=QF4_ID,
            score_a=2,
            score_b=0,
            winner_team_id="44444444-4444-4444-8444-444444444407",
        )

    with use_access_token(engine.token_for_profile(ADMIN_EMAIL)):
        out = supa_repo.submit_match_result_atomic(
            match_id=QF4_ID,
            score_a=2,
            score_b=0,
            winner_team_id="44444444-4444-4444-8444-444444444407",
            notes="Admin verified",
        )
        assert out["match"]["status"] == "completed"


def test_wave2_3_migration_0004_static_security_invariants() -> None:
    root = Path(__file__).resolve().parents[2]
    sql_path = root / "supabase" / "migrations" / "0004_wave2_3_atomic_match_submission.sql"
    assert sql_path.exists()
    sql = sql_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS public.match_submission_requests" in sql
    assert "CONSTRAINT uq_match_submission_idempotency UNIQUE (match_id, actor_id, idempotency_key)" in sql
    assert "REVOKE INSERT, UPDATE, DELETE ON TABLE public.match_submission_requests FROM authenticated;" in sql
    assert "CREATE OR REPLACE FUNCTION private.validate_tournament_bracket_integrity(" in sql
    assert "WITH RECURSIVE reachable AS" in sql
    assert "CREATE OR REPLACE FUNCTION private.submit_match_result_atomic(" in sql
    assert "FOR UPDATE" in sql
    assert "ON CONFLICT (match_id, game_number)" in sql
    assert "INSERT INTO public.activity_logs" in sql
    assert "SELECT auth.uid()" in sql
    assert "SET search_path = ''" in sql
    assert "REVOKE ALL ON FUNCTION public.submit_match_result_atomic(UUID, INT, INT, BOOLEAN, TEXT, INT, VARCHAR)" in sql
    assert "GRANT EXECUTE ON FUNCTION public.submit_match_result_atomic(UUID, INT, INT, BOOLEAN, TEXT, INT, VARCHAR)" in sql

    public_blocks = re.findall(
        r"CREATE OR REPLACE FUNCTION public\.[^\n]+.*?AS \$\$.*?\$\$;",
        sql,
        flags=re.DOTALL,
    )
    assert len(public_blocks) == 1
    assert "SECURITY INVOKER" in public_blocks[0]
    assert "SECURITY DEFINER" not in public_blocks[0]
