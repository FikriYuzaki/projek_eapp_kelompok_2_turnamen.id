"""Integration tests for `/api/v1/*` Flask REST API endpoints."""

from __future__ import annotations

from flask.testing import FlaskClient


def test_health_endpoint_and_response_format(client: FlaskClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert "message" in body
    assert body["data"]["status"] == "healthy"
    assert body["data"]["app_mode"] == "mock"
    assert body["data"]["is_simulation"] is True


def test_auth_login_and_me_flow(client: FlaskClient) -> None:
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "organizer@turnamen.in", "password": "turnamen123"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.get_json()["data"]
    token = login_data["token"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.get_json()["data"]["user"]["role"] == "organizer"


def test_auth_logout_requires_authentication_and_revokes_token(client: FlaskClient) -> None:
    unauth_resp = client.post("/api/v1/auth/logout")
    assert unauth_resp.status_code == 401
    unauth_body = unauth_resp.get_json()
    assert unauth_body["success"] is False
    assert unauth_body["error"]["code"] == "UNAUTHORIZED"

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "organizer@turnamen.in", "password": "turnamen123"},
    )
    token = login_resp.get_json()["data"]["token"]

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.get_json()["data"]["logged_out"] is True

    me_after_logout = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_after_logout.status_code == 401


def test_http_errors_return_standardized_json(client: FlaskClient) -> None:
    not_found = client.get("/api/v1/does-not-exist")
    assert not_found.status_code == 404
    nf_body = not_found.get_json()
    assert nf_body["success"] is False
    assert nf_body["error"]["code"] == "NOT_FOUND"

    method_not_allowed = client.delete("/api/v1/health")
    assert method_not_allowed.status_code == 405
    mna_body = method_not_allowed.get_json()
    assert mna_body["success"] is False
    assert mna_body["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_tournament_creation_and_permission_enforcement(client: FlaskClient) -> None:
    payload = {
        "title": "Liga Mahasiswa VALORANT 2026",
        "game_id": "22222222-2222-4222-8222-222222222202",
        "max_teams": 8,
        "best_of": 3,
        "start_date": "2026-12-10T10:00:00+07:00",
    }

    # Player role must be forbidden from creating a tournament
    forbidden_resp = client.post(
        "/api/v1/tournaments",
        json=payload,
        headers={"X-Mock-Role": "player"},
    )
    assert forbidden_resp.status_code == 403
    err_body = forbidden_resp.get_json()
    assert err_body["success"] is False
    assert err_body["error"]["code"] == "FORBIDDEN"

    # Organizer role succeeds
    ok_resp = client.post(
        "/api/v1/tournaments",
        json=payload,
        headers={"X-Mock-Role": "organizer"},
    )
    assert ok_resp.status_code == 201
    created = ok_resp.get_json()["data"]
    assert created["title"] == "Liga Mahasiswa VALORANT 2026"


def test_team_registration_and_verification_flow(client: FlaskClient) -> None:
    # Create a new team for VALORANT as team_captain
    team_resp = client.post(
        "/api/v1/teams",
        json={
            "name": "Andalas Valiant",
            "tag": "AND",
            "game_id": "22222222-2222-4222-8222-222222222202",
            "region": "Padang",
        },
        headers={"X-Mock-Role": "team_captain"},
    )
    assert team_resp.status_code == 201
    team_id = team_resp.get_json()["data"]["id"]

    # Register the team to the open VALORANT tournament
    val_tour_id = "33333333-3333-4333-8333-333333333302"
    reg_resp = client.post(
        f"/api/v1/tournaments/{val_tour_id}/registrations",
        json={"team_id": team_id, "notes": "Siap bertanding"},
        headers={"X-Mock-Role": "team_captain"},
    )
    assert reg_resp.status_code == 201
    reg_id = reg_resp.get_json()["data"]["id"]
    assert reg_resp.get_json()["data"]["status"] == "pending"

    # Committee approves the registration
    approve_resp = client.patch(
        f"/api/v1/registrations/{reg_id}/status",
        json={"status": "approved", "notes": "Lunas"},
        headers={"X-Mock-Role": "committee"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.get_json()["data"]["status"] == "approved"


def test_full_8_team_bracket_progression_and_reports(client: FlaskClient) -> None:
    tour_id = "33333333-3333-4333-8333-333333333301"

    # Complete QF #4 -> Semi Final #1 -> Semi Final #2 -> Grand Final
    qf4_resp = client.patch(
        "/api/v1/matches/88888888-8888-4888-8888-888888888804/result",
        json={"score_a": 2, "score_b": 1, "notes": "Mataram menang 2-1"},
        headers={"X-Mock-Role": "committee"},
    )
    assert qf4_resp.status_code == 200

    sf1_resp = client.patch(
        "/api/v1/matches/88888888-8888-4888-8888-888888888805/result",
        json={"score_a": 2, "score_b": 0, "notes": "Garuda ke Grand Final"},
        headers={"X-Mock-Role": "committee"},
    )
    assert sf1_resp.status_code == 200

    sf2_resp = client.patch(
        "/api/v1/matches/88888888-8888-4888-8888-888888888806/result",
        json={"score_a": 2, "score_b": 1, "notes": "Pasundan ke Grand Final"},
        headers={"X-Mock-Role": "committee"},
    )
    assert sf2_resp.status_code == 200

    final_resp = client.patch(
        "/api/v1/matches/88888888-8888-4888-8888-888888888807/result",
        json={"score_a": 2, "score_b": 1, "notes": "Garuda Juara Nusantara Campus Cup!"},
        headers={"X-Mock-Role": "committee"},
    )
    assert final_resp.status_code == 200

    # Verify Reports & Standings reflect 100% completion and Champion
    report_resp = client.get(f"/api/v1/tournaments/{tour_id}/reports")
    assert report_resp.status_code == 200
    report_data = report_resp.get_json()["data"]
    assert report_data["summary"]["completion_percentage"] == 100.0
    assert report_data["summary"]["champion_team"] == "Garuda Esports"

    standings_resp = client.get(f"/api/v1/tournaments/{tour_id}/standings")
    assert standings_resp.status_code == 200
    standings = standings_resp.get_json()["data"]
    assert standings[0]["team_name"] == "Garuda Esports"
    assert standings[0]["rank"] == 1


def test_auth_register_validation_and_privilege_escalation(client: FlaskClient) -> None:
    empty_resp = client.post("/api/v1/auth/register", json={})
    assert empty_resp.status_code == 400
    assert empty_resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    escalate_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker@turnamen.in",
            "username": "attacker01",
            "full_name": "Attacker",
            "password": "password123",
            "role": "super_admin",
        },
    )
    assert escalate_resp.status_code == 403
    assert escalate_resp.get_json()["error"]["code"] == "FORBIDDEN"

    ok_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "kapten.baru@turnamen.in",
            "username": "kapten_baru",
            "full_name": "Kapten Baru",
            "password": "password123",
            "role": "team_captain",
        },
    )
    assert ok_resp.status_code == 201
    assert ok_resp.get_json()["data"]["user"]["role"] == "team_captain"


def test_games_catalog_list_detail_and_not_found(client: FlaskClient) -> None:
    list_resp = client.get("/api/v1/games")
    assert list_resp.status_code == 200
    games = list_resp.get_json()["data"]
    assert len(games) >= 3

    detail_resp = client.get(f"/api/v1/games/{games[0]['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["data"]["id"] == games[0]["id"]

    missing_resp = client.get("/api/v1/games/00000000-0000-4000-8000-000000000000")
    assert missing_resp.status_code == 404
    assert missing_resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_tournaments_crud_filters_and_validation(client: FlaskClient) -> None:
    bad_resp = client.post(
        "/api/v1/tournaments",
        json={},
        headers={"X-Mock-Role": "organizer"},
    )
    assert bad_resp.status_code == 400
    assert bad_resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    create_resp = client.post(
        "/api/v1/tournaments",
        json={
            "title": "Turnamen Draft Uji",
            "game_id": "22222222-2222-4222-8222-222222222201",
            "max_teams": 4,
            "best_of": 3,
            "status": "draft",
            "start_date": "2026-12-25T10:00:00+07:00",
        },
        headers={"X-Mock-Role": "organizer"},
    )
    assert create_resp.status_code == 201
    tour_id = create_resp.get_json()["data"]["id"]

    list_resp = client.get(
        "/api/v1/tournaments?status=draft&game_id=22222222-2222-4222-8222-222222222201"
    )
    assert list_resp.status_code == 200
    assert any(t["id"] == tour_id for t in list_resp.get_json()["data"])

    detail_resp = client.get(f"/api/v1/tournaments/{tour_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["data"]["title"] == "Turnamen Draft Uji"

    patch_resp = client.patch(
        f"/api/v1/tournaments/{tour_id}",
        json={"venue": "Jakarta Convention Center"},
        headers={"X-Mock-Role": "organizer"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["data"]["venue"] == "Jakarta Convention Center"

    delete_resp = client.delete(
        f"/api/v1/tournaments/{tour_id}",
        headers={"X-Mock-Role": "organizer"},
    )
    assert delete_resp.status_code == 200

    after_delete = client.get(f"/api/v1/tournaments/{tour_id}")
    assert after_delete.status_code == 404


def test_teams_list_detail_update_and_add_member(client: FlaskClient) -> None:
    list_resp = client.get("/api/v1/teams")
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()["data"]) >= 8

    create_resp = client.post(
        "/api/v1/teams",
        json={
            "name": "Borneo Phoenix",
            "tag": "BPH",
            "game_id": "22222222-2222-4222-8222-222222222201",
            "region": "Balikpapan",
        },
        headers={"X-Mock-Role": "team_captain"},
    )
    assert create_resp.status_code == 201
    team_id = create_resp.get_json()["data"]["id"]

    patch_resp = client.patch(
        f"/api/v1/teams/{team_id}",
        json={"region": "Samarinda"},
        headers={"X-Mock-Role": "team_captain"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["data"]["region"] == "Samarinda"

    bad_member = client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"nickname": "BPH.Ace"},
        headers={"X-Mock-Role": "team_captain"},
    )
    assert bad_member.status_code == 400

    add_member = client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"nickname": "BPH.Ace", "ingame_id": "ML-778899", "member_role": "starter"},
        headers={"X-Mock-Role": "team_captain"},
    )
    assert add_member.status_code == 201

    detail_resp = client.get(f"/api/v1/teams/{team_id}")
    assert detail_resp.status_code == 200
    assert any(m["nickname"] == "BPH.Ace" for m in detail_resp.get_json()["data"]["members"])


def test_bracket_generation_registrations_list_and_match_errors(client: FlaskClient) -> None:
    tour_id = "33333333-3333-4333-8333-333333333301"

    regs_resp = client.get(f"/api/v1/tournaments/{tour_id}/registrations")
    assert regs_resp.status_code == 200
    assert len(regs_resp.get_json()["data"]) >= 8

    matches_resp = client.get(f"/api/v1/tournaments/{tour_id}/matches")
    assert matches_resp.status_code == 200
    assert len(matches_resp.get_json()["data"]["matches"]) == 7

    # Tie score on scheduled QF #4 must fail with 400 VALIDATION_ERROR.
    tie_resp = client.patch(
        "/api/v1/matches/88888888-8888-4888-8888-888888888804/result",
        json={"score_a": 1, "score_b": 1},
        headers={"X-Mock-Role": "committee"},
    )
    assert tie_resp.status_code == 400
    assert tie_resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Completed QF #1 is locked and rejects overwrite without force_override (409 CONFLICT).
    conflict_resp = client.patch(
        "/api/v1/matches/88888888-8888-4888-8888-888888888801/result",
        json={"score_a": 2, "score_b": 1},
        headers={"X-Mock-Role": "committee"},
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.get_json()["error"]["code"] == "CONFLICT"

    # Player cannot generate a bracket.
    forbidden_gen = client.post(
        f"/api/v1/tournaments/{tour_id}/bracket/generate",
        headers={"X-Mock-Role": "player"},
    )
    assert forbidden_gen.status_code == 403

    # Create a new 2-team tournament and generate its bracket via HTTP.
    new_tour_resp = client.post(
        "/api/v1/tournaments",
        json={
            "title": "Mini Showmatch 2 Tim",
            "game_id": "22222222-2222-4222-8222-222222222201",
            "max_teams": 4,
            "best_of": 3,
            "status": "open_registration",
            "start_date": "2026-12-28T10:00:00+07:00",
        },
        headers={"X-Mock-Role": "organizer"},
    )
    assert new_tour_resp.status_code == 201
    new_tour_id = new_tour_resp.get_json()["data"]["id"]

    for team_id in (
        "44444444-4444-4444-8444-444444444401",
        "44444444-4444-4444-8444-444444444402",
    ):
        reg = client.post(
            f"/api/v1/tournaments/{new_tour_id}/registrations",
            json={"team_id": team_id},
            headers={"X-Mock-Role": "super_admin"},
        )
        assert reg.status_code == 201
        reg_id = reg.get_json()["data"]["id"]
        approve = client.patch(
            f"/api/v1/registrations/{reg_id}/status",
            json={"status": "approved"},
            headers={"X-Mock-Role": "organizer"},
        )
        assert approve.status_code == 200

    gen_resp = client.post(
        f"/api/v1/tournaments/{new_tour_id}/bracket/generate",
        headers={"X-Mock-Role": "organizer"},
    )
    assert gen_resp.status_code == 201
    assert len(gen_resp.get_json()["data"]["matches"]) == 1


def test_announcements_endpoints_and_permissions(client: FlaskClient) -> None:
    tour_id = "33333333-3333-4333-8333-333333333301"

    list_resp = client.get(f"/api/v1/tournaments/{tour_id}/announcements")
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()["data"]) >= 1

    forbidden_resp = client.post(
        f"/api/v1/tournaments/{tour_id}/announcements",
        json={"title": "Pengumuman Ilegal", "content": "Tidak boleh dipublikasikan player."},
        headers={"X-Mock-Role": "player"},
    )
    assert forbidden_resp.status_code == 403

    invalid_resp = client.post(
        f"/api/v1/tournaments/{tour_id}/announcements",
        json={"title": "OK", "content": "Isi pengumuman valid."},
        headers={"X-Mock-Role": "committee"},
    )
    assert invalid_resp.status_code == 400
    assert invalid_resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    ok_resp = client.post(
        f"/api/v1/tournaments/{tour_id}/announcements",
        json={
            "title": "Jadwal Grand Final",
            "content": "Pertandingan dimulai pukul 20.00 WIB.",
            "priority": "important",
            "is_pinned": True,
        },
        headers={"X-Mock-Role": "committee"},
    )
    assert ok_resp.status_code == 201
    assert ok_resp.get_json()["data"]["title"] == "Jadwal Grand Final"
