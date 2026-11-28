"""Integration tests for Wave 2: committee assignment visibility, mutation enforcement, and report/registration privacy."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from backend.contracts.dtos import ROLE_COMMITTEE, ROLE_ORGANIZER, ROLE_TEAM_CAPTAIN
from backend.repositories.mock.mock_repository import MockDataStoreRepository

MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
VAL_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333302"
MLBB_GAME_ID = "22222222-2222-4222-8222-222222222201"
QF4_ID = "88888888-8888-4888-8888-888888888804"
TEAM_GRD = "44444444-4444-4444-8444-444444444401"
TEAM_SRW = "44444444-4444-4444-8444-444444444402"


def _seed_unassigned_staff_and_pending_regs(app: Flask) -> dict[str, str]:
    repo: MockDataStoreRepository = app.config["TURNAMEN_REPO"]

    other_organizer = repo.create_profile(
        {
            "email": "other.eo@turnamen.in",
            "username": "other_eo",
            "full_name": "Other Organizer",
            "role": ROLE_ORGANIZER,
        }
    )
    unassigned_committee = repo.create_profile(
        {
            "email": "unassigned.comm@turnamen.in",
            "username": "unassigned_comm",
            "full_name": "Unassigned Committee",
            "role": ROLE_COMMITTEE,
        }
    )
    other_captain = repo.create_profile(
        {
            "email": "other.capt@turnamen.in",
            "username": "other_capt",
            "full_name": "Other Captain",
            "role": ROLE_TEAM_CAPTAIN,
        }
    )
    other_team = repo.create_team(
        {
            "name": "Nusantara Storm",
            "tag": "NST",
            "game_id": MLBB_GAME_ID,
            "captain_id": other_captain["id"],
            "region": "Medan",
        }
    )
    # Pending registration by captain@turnamen.in on VAL_TOURNAMENT_ID
    captain_reg = repo.create_registration(
        {
            "tournament_id": VAL_TOURNAMENT_ID,
            "team_id": TEAM_GRD,
            "registered_by": "11111111-1111-4111-8111-111111111104",
            "status": "pending",
            "seed_number": 1,
        }
    )
    # Pending registration by other_captain on VAL_TOURNAMENT_ID
    other_pending_reg = repo.create_registration(
        {
            "tournament_id": VAL_TOURNAMENT_ID,
            "team_id": other_team["id"],
            "registered_by": other_captain["id"],
            "status": "pending",
            "seed_number": 2,
        }
    )
    # Approved registration by TEAM_SRW on VAL_TOURNAMENT_ID
    approved_reg = repo.create_registration(
        {
            "tournament_id": VAL_TOURNAMENT_ID,
            "team_id": TEAM_SRW,
            "registered_by": "11111111-1111-4111-8111-111111111104",
            "status": "approved",
            "seed_number": 3,
        }
    )
    return {
        "other_organizer_id": other_organizer["id"],
        "unassigned_committee_id": unassigned_committee["id"],
        "other_captain_id": other_captain["id"],
        "captain_reg_id": captain_reg["id"],
        "other_pending_reg_id": other_pending_reg["id"],
        "approved_reg_id": approved_reg["id"],
    }


def test_committee_assignment_flag_and_backend_mutation_enforcement(
    app: Flask, client: FlaskClient
) -> None:
    ids = _seed_unassigned_staff_and_pending_regs(app)

    # 1. Assigned committee receives is_assigned_committee=True on list and detail
    assigned_list = client.get("/api/v1/tournaments", headers={"X-Mock-Role": "committee"})
    assert assigned_list.status_code == 200
    for item in assigned_list.get_json()["data"]:
        assert item["is_assigned_committee"] is True
        assert "staff_user_ids" not in item

    assigned_detail = client.get(
        f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}", headers={"X-Mock-Role": "committee"}
    )
    assert assigned_detail.status_code == 200
    assert assigned_detail.get_json()["data"]["is_assigned_committee"] is True

    # 2. Unassigned committee receives is_assigned_committee=False
    unassigned_list = client.get(
        "/api/v1/tournaments",
        headers={"X-Mock-User-Id": ids["unassigned_committee_id"]},
    )
    assert unassigned_list.status_code == 200
    for item in unassigned_list.get_json()["data"]:
        assert item["is_assigned_committee"] is False

    unassigned_detail = client.get(
        f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}",
        headers={"X-Mock-User-Id": ids["unassigned_committee_id"]},
    )
    assert unassigned_detail.status_code == 200
    assert unassigned_detail.get_json()["data"]["is_assigned_committee"] is False

    # 3. Guest and Player never receive assignment info or staff list
    for headers in ({}, {"X-Mock-Role": "player"}):
        guest_list = client.get("/api/v1/tournaments", headers=headers)
        assert guest_list.status_code == 200
        for item in guest_list.get_json()["data"]:
            assert "is_assigned_committee" not in item
            assert "staff_user_ids" not in item
            assert "assigned_staff_ids" not in item

        guest_detail = client.get(f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}", headers=headers)
        assert guest_detail.status_code == 200
        assert "is_assigned_committee" not in guest_detail.get_json()["data"]

    # 4. Unassigned committee is rejected (403) on all committee mutation endpoints
    unassigned_headers = {"X-Mock-User-Id": ids["unassigned_committee_id"]}
    assert (
        client.patch(
            f"/api/v1/registrations/{ids['captain_reg_id']}/status",
            json={"status": "approved"},
            headers=unassigned_headers,
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/matches/{QF4_ID}/result",
            json={"score_a": 2, "score_b": 0},
            headers=unassigned_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}/announcements",
            json={"title": "Ilegal", "content": "Tidak ditugaskan."},
            headers=unassigned_headers,
        ).status_code
        == 403
    )

    # 5. Assigned committee succeeds on all authorized mutations
    assert (
        client.patch(
            f"/api/v1/registrations/{ids['captain_reg_id']}/status",
            json={"status": "approved", "notes": "OK"},
            headers={"X-Mock-Role": "committee"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/matches/{QF4_ID}/result",
            json={"score_a": 2, "score_b": 0, "notes": "Sah"},
            headers={"X-Mock-Role": "committee"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}/announcements",
            json={"title": "Info Sah", "content": "Pengumuman resmi panitia."},
            headers={"X-Mock-Role": "committee"},
        ).status_code
        == 201
    )


def test_reports_and_registrations_visibility_across_all_roles(
    app: Flask, client: FlaskClient
) -> None:
    ids = _seed_unassigned_staff_and_pending_regs(app)

    # Guest & Player: public report data intact, no internal recent_activity, no pending_registrations
    for headers in ({}, {"X-Mock-Role": "player"}):
        report_resp = client.get(f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}/reports", headers=headers)
        assert report_resp.status_code == 200
        body = report_resp.get_json()["data"]
        assert body["recent_activity"] == []
        assert "pending_registrations" not in body["summary"]
        assert "total_registrations" not in body["summary"]
        assert body["summary"]["approved_teams"] == 8
        assert body["summary"]["total_matches"] == 7
        assert len(body["standings"]) == 8

        regs_resp = client.get(f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}/registrations", headers=headers)
        assert regs_resp.status_code == 200
        reg_ids = {r["id"] for r in regs_resp.get_json()["data"]}
        assert reg_ids == {ids["approved_reg_id"]}

    # Team Captain: sees approved + own team pending, NOT another captain's pending
    capt_regs = client.get(
        f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}/registrations",
        headers={"X-Mock-Role": "team_captain"},
    )
    assert capt_regs.status_code == 200
    capt_reg_ids = {r["id"] for r in capt_regs.get_json()["data"]}
    assert ids["approved_reg_id"] in capt_reg_ids
    assert ids["captain_reg_id"] in capt_reg_ids
    assert ids["other_pending_reg_id"] not in capt_reg_ids

    other_capt_regs = client.get(
        f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}/registrations",
        headers={"X-Mock-User-Id": ids["other_captain_id"]},
    )
    assert other_capt_regs.status_code == 200
    other_capt_ids = {r["id"] for r in other_capt_regs.get_json()["data"]}
    assert ids["other_pending_reg_id"] in other_capt_ids
    assert ids["captain_reg_id"] not in other_capt_ids

    # Non-owning Organizer & Unassigned Committee: no internal activity logs or pending counts
    for restricted_headers in (
        {"X-Mock-User-Id": ids["other_organizer_id"]},
        {"X-Mock-User-Id": ids["unassigned_committee_id"]},
    ):
        r_resp = client.get(
            f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}/reports", headers=restricted_headers
        )
        assert r_resp.status_code == 200
        r_data = r_resp.get_json()["data"]
        assert r_data["recent_activity"] == []
        assert "pending_registrations" not in r_data["summary"]

        regs_r = client.get(
            f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}/registrations", headers=restricted_headers
        )
        assert {r["id"] for r in regs_r.get_json()["data"]} == {ids["approved_reg_id"]}

    # Owning Organizer, Assigned Committee, Super Admin: full operational report & all registrations
    for manager_headers in (
        {"X-Mock-Role": "organizer"},
        {"X-Mock-Role": "committee"},
        {"X-Mock-Role": "super_admin"},
    ):
        mgr_report = client.get(
            f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}/reports", headers=manager_headers
        )
        assert mgr_report.status_code == 200
        mgr_data = mgr_report.get_json()["data"]
        assert len(mgr_data["recent_activity"]) >= 1
        assert mgr_data["summary"]["total_registrations"] == 8
        assert mgr_data["summary"]["pending_registrations"] == 0

        mgr_regs = client.get(
            f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}/registrations", headers=manager_headers
        )
        assert mgr_regs.status_code == 200
        assert {r["id"] for r in mgr_regs.get_json()["data"]} == {
            ids["approved_reg_id"],
            ids["captain_reg_id"],
            ids["other_pending_reg_id"],
        }
