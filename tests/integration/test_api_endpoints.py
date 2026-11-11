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
