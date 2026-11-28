"""Regression tests for Wave 2.2: Security Edge Case Remediation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend.app import create_app
from backend.contracts.dtos import ROLE_COMMITTEE, ROLE_TEAM_CAPTAIN
from backend.core.exceptions import DomainConflictError, DomainForbiddenError
from backend.infrastructure.supabase.client import use_access_token
from backend.modules.matches.service import MatchService
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from tests.unit.test_wave2_1_supabase_rls_remediation import (
    COMMITTEE_ID,
    MLBB_GAME_ID,
    PLAYER_ID,
    TEAM_GRD,
    TEAM_SRW,
    _supabase_setup,
)

ADMIN_EMAIL = "admin@turnamen.in"
ORGANIZER_EMAIL = "organizer@turnamen.in"
COMMITTEE_EMAIL = "committee@turnamen.in"
CAPTAIN_EMAIL = "captain@turnamen.in"
PLAYER_EMAIL = "player@turnamen.in"


def _setup_two_team_completed_tournament(
    client: Any, engine: Any | None = None, repo: Any | None = None
) -> tuple[str, str, dict[str, str]]:
    """Create a 2-team tournament, assign committee, generate bracket, and finish Grand Final."""
    if engine is not None:
        org_jwt = engine.token_for_profile(ORGANIZER_EMAIL)
        comm_jwt = engine.token_for_profile(COMMITTEE_EMAIL)
        cap_jwt = engine.token_for_profile(CAPTAIN_EMAIL)
        org_headers = {"Authorization": f"Bearer {org_jwt}"}
        comm_headers = {"Authorization": f"Bearer {comm_jwt}"}
        cap_headers = {"Authorization": f"Bearer {cap_jwt}"}
    else:
        org_token = client.post(
            "/api/v1/auth/login", json={"email": ORGANIZER_EMAIL, "password": "turnamen123"}
        ).get_json()["data"]["token"]
        comm_token = client.post(
            "/api/v1/auth/login", json={"email": COMMITTEE_EMAIL, "password": "turnamen123"}
        ).get_json()["data"]["token"]
        cap_token = client.post(
            "/api/v1/auth/login", json={"email": CAPTAIN_EMAIL, "password": "turnamen123"}
        ).get_json()["data"]["token"]
        org_headers = {"Authorization": f"Bearer {org_token}"}
        comm_headers = {"Authorization": f"Bearer {comm_token}"}
        cap_headers = {"Authorization": f"Bearer {cap_token}"}

    tour_resp = client.post(
        "/api/v1/tournaments",
        headers=org_headers,
        json={
            "title": "Wave 2.2 Edge Cup",
            "game_id": MLBB_GAME_ID,
            "start_date": "2026-12-22T10:00:00+07:00",
            "max_teams": 4,
            "status": "open_registration",
        },
    )
    assert tour_resp.status_code == 201
    tour_id = tour_resp.get_json()["data"]["id"]

    if engine is not None:
        engine.store["tournament_staff"].append(
            {
                "id": "66666666-6666-4666-8666-666666666701",
                "tournament_id": tour_id,
                "user_id": COMMITTEE_ID,
                "staff_role": "head_committee",
            }
        )
    else:
        assert repo is not None
        repo._store["tournament_staff"].append(
            {
                "id": "66666666-6666-4666-8666-666666666701",
                "tournament_id": tour_id,
                "user_id": COMMITTEE_ID,
                "staff_role": "head_committee",
            }
        )

    for tid in (TEAM_GRD, TEAM_SRW):
        reg = client.post(
            f"/api/v1/tournaments/{tour_id}/registrations",
            headers=cap_headers,
            json={"team_id": tid},
        )
        assert reg.status_code == 201
        reg_id = reg.get_json()["data"]["id"]
        approve = client.patch(
            f"/api/v1/registrations/{reg_id}/status",
            headers=comm_headers,
            json={"status": "approved"},
        )
        assert approve.status_code == 200

    gen = client.post(f"/api/v1/tournaments/{tour_id}/bracket/generate", headers=comm_headers)
    assert gen.status_code == 201
    gf_id = gen.get_json()["data"]["matches"][0]["id"]

    res = client.patch(
        f"/api/v1/matches/{gf_id}/result",
        headers=comm_headers,
        json={"score_a": 2, "score_b": 0, "notes": "Hasil awal final"},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["match"]["status"] == "completed"

    tokens = {
        "org_headers": org_headers,
        "comm_headers": comm_headers,
        "cap_headers": cap_headers,
    }
    return tour_id, gf_id, tokens


@pytest.mark.parametrize("mode", ["mock", "supabase_rls"])
def test_committee_grand_final_force_override_completed_to_completed_idempotent(mode: str) -> None:
    if mode == "supabase_rls":
        engine, repo, cfg = _supabase_setup()
        app = create_app(config=cfg, repository=repo)
        client = app.test_client()
        tour_id, gf_id, headers_map = _setup_two_team_completed_tournament(client, engine=engine)
        engine.store["profiles"].append(
            {
                "id": "11111111-1111-4111-8111-111111111177",
                "auth_user_id": "11111111-1111-4111-8111-111111111177",
                "email": "comm.other@turnamen.in",
                "username": "comm_other",
                "full_name": "Panitia Luar",
                "role": ROLE_COMMITTEE,
                "is_active": True,
            }
        )
        unassigned_headers = {
            "Authorization": f"Bearer {engine.token_for_profile('comm.other@turnamen.in')}"
        }
        comm_jwt = engine.token_for_profile(COMMITTEE_EMAIL)
        org_jwt = engine.token_for_profile(ORGANIZER_EMAIL)
    else:
        repo = MockDataStoreRepository()
        repo._store["profiles"].append(
            {
                "id": "11111111-1111-4111-8111-111111111177",
                "auth_user_id": None,
                "email": "comm.other@turnamen.in",
                "username": "comm_other",
                "full_name": "Panitia Luar",
                "role": ROLE_COMMITTEE,
                "is_active": True,
                "password_hash": repo.get_profile_by_email(COMMITTEE_EMAIL)["password_hash"],
            }
        )
        app = create_app(repository=repo)
        client = app.test_client()
        tour_id, gf_id, headers_map = _setup_two_team_completed_tournament(
            client, engine=None, repo=repo
        )
        other_token = client.post(
            "/api/v1/auth/login", json={"email": "comm.other@turnamen.in", "password": "turnamen123"}
        ).get_json()["data"]["token"]
        unassigned_headers = {"Authorization": f"Bearer {other_token}"}
        comm_jwt = None
        org_jwt = None

    assert repo.get_tournament_by_id(tour_id)["status"] == "completed"

    # Unassigned committee remains blocked from overriding Grand Final
    blocked_unassigned = client.patch(
        f"/api/v1/matches/{gf_id}/result",
        headers=unassigned_headers,
        json={"score_a": 1, "score_b": 2, "force_override": True, "notes": "Coba override liar"},
    )
    assert blocked_unassigned.status_code == 403

    # Assigned committee performs Grand Final force_override (completed -> completed idempotent)
    override_resp = client.patch(
        f"/api/v1/matches/{gf_id}/result",
        headers=headers_map["comm_headers"],
        json={
            "score_a": 1,
            "score_b": 2,
            "force_override": True,
            "notes": "Koreksi skor final setelah review wasit",
        },
    )
    assert override_resp.status_code == 200
    body = override_resp.get_json()["data"]
    assert body["match"]["score_a"] == 1
    assert body["match"]["score_b"] == 2
    assert body["match"]["winner_team_id"] == TEAM_SRW
    assert body["match"]["status"] == "completed"
    assert repo.get_tournament_by_id(tour_id)["status"] == "completed"
    results = repo.list_match_results(gf_id)
    assert len(results) == 1
    assert results[0]["score_a"] == 1
    assert results[0]["score_b"] == 2
    assert results[0]["verified_by"] == COMMITTEE_ID

    # Illegal transitions from completed remain strictly rejected
    if mode == "supabase_rls":
        with use_access_token(comm_jwt):
            for illegal_status in ("ongoing", "cancelled", "draft", "open_registration"):
                with pytest.raises(DomainForbiddenError):
                    repo.transition_tournament_status(tour_id, illegal_status)
        with use_access_token(org_jwt):
            for illegal_status in ("ongoing", "cancelled"):
                with pytest.raises(DomainConflictError):
                    repo.transition_tournament_status(tour_id, illegal_status)
    else:
        for illegal_status in ("ongoing", "cancelled", "draft"):
            with pytest.raises(DomainConflictError):
                repo.transition_tournament_status(tour_id, illegal_status)


@pytest.mark.parametrize("mode", ["mock", "supabase_rls"])
def test_grand_final_rejects_corrupted_bracket_and_unfinished_matches_atomically(mode: str) -> None:
    if mode == "supabase_rls":
        engine, repo, _cfg = _supabase_setup()
        tour_id = "33333333-3333-4333-8333-333333333301"
        comm_jwt = engine.token_for_profile(COMMITTEE_EMAIL)
        with use_access_token(comm_jwt):
            committee = repo.get_profile_by_email(COMMITTEE_EMAIL)
    else:
        repo = MockDataStoreRepository()
        tour_id = "33333333-3333-4333-8333-333333333301"
        committee = repo.get_profile_by_email(COMMITTEE_EMAIL)

    assert committee is not None
    service = MatchService(repo)
    qf4_id = "88888888-8888-4888-8888-888888888804"
    sf1_id = "88888888-8888-4888-8888-888888888805"
    gf_id = "88888888-8888-4888-8888-888888888807"

    def _run_with_comm(fn: Any) -> Any:
        if mode == "supabase_rls":
            with use_access_token(comm_jwt):
                return fn()
        return fn()

    # Give GF both teams temporarily to test guard before semifinal/QF completion
    gf_initial = _run_with_comm(lambda: repo.get_match_by_id(gf_id))
    assert gf_initial is not None
    initial_gf_status = gf_initial["status"]
    _run_with_comm(lambda: repo.update_match(gf_id, {"team_a_id": TEAM_GRD, "team_b_id": TEAM_SRW}))

    # 1. Earlier matches still unfinished -> rejected with 409 and GF remains unchanged
    with pytest.raises(DomainConflictError):
        _run_with_comm(
            lambda: service.submit_match_result(committee, gf_id, {"score_a": 2, "score_b": 0})
        )
    gf_after_fail = _run_with_comm(lambda: repo.get_match_by_id(gf_id))
    assert gf_after_fail["status"] == initial_gf_status
    assert gf_after_fail["winner_team_id"] is None
    assert _run_with_comm(lambda: repo.list_match_results(gf_id)) == []
    assert _run_with_comm(lambda: repo.get_tournament_by_id(tour_id))["status"] == "ongoing"

    # 2. Complete prerequisites cleanly except forge a duplicate next_match_id IS NULL match
    _run_with_comm(lambda: repo.update_match(qf4_id, {"status": "completed", "winner_team_id": TEAM_SRW}))
    _run_with_comm(lambda: repo.update_match(sf1_id, {"status": "completed", "winner_team_id": TEAM_GRD}))
    sf2_id = "88888888-8888-4888-8888-888888888806"
    _run_with_comm(
        lambda: repo.update_match(
            sf2_id,
            {"team_b_id": TEAM_SRW, "status": "completed", "winner_team_id": TEAM_SRW, "next_match_id": None},
        )
    )

    with pytest.raises(DomainConflictError):
        _run_with_comm(
            lambda: service.submit_match_result(committee, gf_id, {"score_a": 2, "score_b": 1})
        )
    gf_after_dup = _run_with_comm(lambda: repo.get_match_by_id(gf_id))
    assert gf_after_dup["status"] == initial_gf_status
    assert gf_after_dup["score_a"] == 0
    assert _run_with_comm(lambda: repo.list_match_results(gf_id)) == []

    # Restore valid GF pointer on SF2 and verify atomic rollback when transition raises
    _run_with_comm(lambda: repo.update_match(sf2_id, {"next_match_id": gf_id}))

    if mode == "supabase_rls":
        def _fail_transition(step: str) -> None:
            if step == "transition_tournament":
                raise DomainForbiddenError("Simulated RLS failure during status transition")

        engine._fail_atomic_hook = _fail_transition  # type: ignore[attr-defined]
        try:
            with pytest.raises(DomainForbiddenError):
                _run_with_comm(
                    lambda: service.submit_match_result(committee, gf_id, {"score_a": 2, "score_b": 1})
                )
        finally:
            engine._fail_atomic_hook = None  # type: ignore[attr-defined]
    else:
        original_transition = repo._atomic_transition_tournament

        def _failing_transition(tid: str, status: str) -> Any:
            raise DomainForbiddenError("Simulated RLS failure during status transition")

        repo._atomic_transition_tournament = _failing_transition  # type: ignore[method-assign]
        try:
            with pytest.raises(DomainForbiddenError):
                _run_with_comm(
                    lambda: service.submit_match_result(committee, gf_id, {"score_a": 2, "score_b": 1})
                )
        finally:
            repo._atomic_transition_tournament = original_transition  # type: ignore[method-assign]

    gf_rolled_back = _run_with_comm(lambda: repo.get_match_by_id(gf_id))
    assert gf_rolled_back["status"] == initial_gf_status
    assert gf_rolled_back["winner_team_id"] is None
    assert gf_rolled_back["score_a"] == 0
    assert _run_with_comm(lambda: repo.list_match_results(gf_id)) == []
    assert _run_with_comm(lambda: repo.get_tournament_by_id(tour_id))["status"] == "ongoing"


def test_get_public_profile_summary_role_and_ownership_matrix_both_modes() -> None:
    # 1. Supabase RLS mode
    engine, supa_repo, cfg = _supabase_setup()
    # Add second captain and a team owned exclusively by that captain
    other_cap_id = "11111111-1111-4111-8111-111111111166"
    other_team_id = "44444444-4444-4444-8444-444444444499"
    engine.store["profiles"].append(
        {
            "id": other_cap_id,
            "auth_user_id": other_cap_id,
            "email": "captain2@turnamen.in",
            "username": "captain2",
            "full_name": "Kapten Dua",
            "role": ROLE_TEAM_CAPTAIN,
            "is_active": True,
        }
    )
    engine.store["teams"].append(
        {
            "id": other_team_id,
            "name": "Tim Kapten Dua",
            "tag": "KD2",
            "game_id": MLBB_GAME_ID,
            "captain_id": other_cap_id,
            "logo_url": None,
            "region": "Jakarta",
            "is_verified": True,
        }
    )
    inactive_player_id = "11111111-1111-4111-8111-111111111155"
    engine.store["profiles"].append(
        {
            "id": inactive_player_id,
            "auth_user_id": inactive_player_id,
            "email": "inactive@turnamen.in",
            "username": "inactive_player",
            "full_name": "Player Nonaktif",
            "role": "player",
            "is_active": False,
        }
    )

    supa_app = create_app(config=cfg, repository=supa_repo)
    supa_client = supa_app.test_client()

    cap_jwt = engine.token_for_profile(CAPTAIN_EMAIL)
    cap2_jwt = engine.token_for_profile("captain2@turnamen.in")
    player_jwt = engine.token_for_profile(PLAYER_EMAIL)
    comm_jwt = engine.token_for_profile(COMMITTEE_EMAIL)
    org_jwt = engine.token_for_profile(ORGANIZER_EMAIL)
    admin_jwt = engine.token_for_profile(ADMIN_EMAIL)

    # Owning team_captain succeeds on owned team and receives non-PII only
    with use_access_token(cap_jwt):
        summary = supa_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD)
        assert summary is not None
        assert set(summary.keys()) == {"id", "username", "full_name", "avatar_url"}
        assert supa_repo.get_public_profile_summary(inactive_player_id, team_id=TEAM_GRD) is None
        with pytest.raises(DomainForbiddenError):
            supa_repo.get_public_profile_summary(PLAYER_ID, team_id=other_team_id)
        with pytest.raises(DomainForbiddenError):
            supa_repo.get_public_profile_summary(PLAYER_ID, team_id=None)

    # Non-owning team_captain, player, committee, organizer are ALL denied
    for denied_jwt in (cap2_jwt, player_jwt, comm_jwt, org_jwt):
        with use_access_token(denied_jwt):
            with pytest.raises(DomainForbiddenError):
                supa_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD)
            with pytest.raises(DomainForbiddenError):
                supa_repo.get_public_profile_summary(PLAYER_ID, team_id=None)
            with pytest.raises(DomainForbiddenError):
                supa_repo.get_public_profile_summary("not-a-uuid", team_id=TEAM_GRD)

    # Unauthenticated direct RPC call denied
    with pytest.raises(DomainForbiddenError):
        supa_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD)

    # Super Admin allowed
    with use_access_token(admin_jwt):
        admin_summary = supa_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD)
        assert admin_summary == summary

    # HTTP endpoint rejects non-owning captain and unknown/inactive user_id cleanly
    assert (
        supa_client.post(
            f"/api/v1/teams/{TEAM_GRD}/members",
            headers={"Authorization": f"Bearer {cap2_jwt}"},
            json={"nickname": "GRD.OtherCap", "ingame_id": "ML-OTHER-1", "user_id": PLAYER_ID},
        ).status_code
        == 403
    )
    assert (
        supa_client.post(
            f"/api/v1/teams/{TEAM_GRD}/members",
            headers={"Authorization": f"Bearer {player_jwt}"},
            json={"nickname": "GRD.PlayerTry", "ingame_id": "ML-PLY-2", "user_id": PLAYER_ID},
        ).status_code
        == 403
    )
    assert (
        supa_client.post(
            f"/api/v1/teams/{TEAM_GRD}/members",
            headers={"Authorization": f"Bearer {cap_jwt}"},
            json={
                "nickname": "GRD.Inactive",
                "ingame_id": "ML-INACT-3",
                "user_id": inactive_player_id,
            },
        ).status_code
        == 404
    )

    # 2. Mock repository enforces identical access matrix
    mock_repo = MockDataStoreRepository()
    mock_repo._store["profiles"].append(
        {
            "id": other_cap_id,
            "auth_user_id": None,
            "email": "captain2@turnamen.in",
            "username": "captain2",
            "full_name": "Kapten Dua",
            "role": ROLE_TEAM_CAPTAIN,
            "is_active": True,
            "password_hash": "",
        }
    )
    mock_repo._store["teams"].append(
        {
            "id": other_team_id,
            "name": "Tim Kapten Dua",
            "tag": "KD2",
            "game_id": MLBB_GAME_ID,
            "captain_id": other_cap_id,
            "logo_url": None,
            "region": "Jakarta",
            "is_verified": True,
        }
    )
    mock_cap = mock_repo.get_profile_by_email(CAPTAIN_EMAIL)["id"]
    mock_player = mock_repo.get_profile_by_email(PLAYER_EMAIL)["id"]
    mock_comm = mock_repo.get_profile_by_email(COMMITTEE_EMAIL)["id"]
    mock_org = mock_repo.get_profile_by_email(ORGANIZER_EMAIL)["id"]
    mock_admin = mock_repo.get_profile_by_email(ADMIN_EMAIL)["id"]

    mock_ok = mock_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD, actor_id=mock_cap)
    assert mock_ok == summary
    assert mock_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD, actor_id=mock_admin) == summary

    for denied_actor in (None, other_cap_id, mock_player, mock_comm, mock_org):
        with pytest.raises(DomainForbiddenError):
            mock_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD, actor_id=denied_actor)
    with pytest.raises(DomainForbiddenError):
        mock_repo.get_public_profile_summary(PLAYER_ID, team_id=other_team_id, actor_id=mock_cap)


def test_wave2_2_migration_and_supa001_plan_artifacts() -> None:
    root = Path(__file__).resolve().parents[2]
    migration_0003 = (root / "supabase" / "migrations" / "0003_wave2_rls_compatibility.sql").read_text(
        encoding="utf-8"
    )
    assert "v_tournament.status IN ('ongoing', 'completed')" in migration_0003
    assert "v_final_match_count <> 1" in migration_0003
    assert "v_has_incomplete_matches" in migration_0003
    assert "p_team_id UUID DEFAULT NULL" in migration_0003
    assert "t.captain_id" in migration_0003
    assert "REVOKE ALL ON FUNCTION public.get_public_profile_summary(UUID, UUID) FROM PUBLIC, anon;" in migration_0003

    plan_doc = root / "docs" / "wave4-supa001-auth-trigger-plan.md"
    assert plan_doc.exists()
    plan_text = plan_doc.read_text(encoding="utf-8")
    assert "LOWER(email)" in plan_text
    assert "auth_user_id IS NULL" in plan_text
    assert "0005_supa001_auth_trigger_hardening.sql" in plan_text
