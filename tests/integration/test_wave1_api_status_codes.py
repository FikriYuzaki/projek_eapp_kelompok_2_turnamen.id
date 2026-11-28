"""HTTP status regressions for Wave 1 domain rules: invalid input must be 400/409, never 500."""

from __future__ import annotations

from flask.testing import FlaskClient

MLBB_GAME_ID = "22222222-2222-4222-8222-222222222201"
MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
QF1_ID = "88888888-8888-4888-8888-888888888801"
QF4_ID = "88888888-8888-4888-8888-888888888804"
TEAM_GRD = "44444444-4444-4444-8444-444444444401"


def _error_code(resp) -> str:
    return resp.get_json()["error"]["code"]


def test_create_tournament_with_non_numeric_max_teams_returns_400(client: FlaskClient) -> None:
    resp = client.post(
        "/api/v1/tournaments",
        json={"title": "Turnamen Kuota Huruf", "game_id": MLBB_GAME_ID, "start_date": "2026-12-20", "max_teams": "abc"},
        headers={"X-Mock-Role": "organizer"},
    )
    assert resp.status_code == 400
    assert _error_code(resp) == "VALIDATION_ERROR"


def test_ongoing_tournament_cannot_revert_or_be_deleted(client: FlaskClient) -> None:
    revert = client.patch(
        f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}",
        json={"status": "draft"},
        headers={"X-Mock-Role": "organizer"},
    )
    assert revert.status_code == 409
    assert _error_code(revert) == "CONFLICT"

    delete = client.delete(f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}", headers={"X-Mock-Role": "organizer"})
    assert delete.status_code == 409
    assert client.get(f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}").status_code == 200


def test_register_into_draft_tournament_returns_409(client: FlaskClient) -> None:
    created = client.post(
        "/api/v1/tournaments",
        json={"title": "Draft Tertutup", "game_id": MLBB_GAME_ID, "start_date": "2026-12-20", "status": "draft"},
        headers={"X-Mock-Role": "organizer"},
    )
    assert created.status_code == 201
    resp = client.post(
        f"/api/v1/tournaments/{created.get_json()['data']['id']}/registrations",
        json={"team_id": TEAM_GRD},
        headers={"X-Mock-Role": "team_captain"},
    )
    assert resp.status_code == 409


def test_match_result_with_decimal_score_returns_400(client: FlaskClient) -> None:
    resp = client.patch(
        f"/api/v1/matches/{QF4_ID}/result",
        json={"score_a": 2.5, "score_b": 0},
        headers={"X-Mock-Role": "committee"},
    )
    assert resp.status_code == 400
    assert _error_code(resp) == "VALIDATION_ERROR"


def test_force_override_without_notes_returns_400(client: FlaskClient) -> None:
    resp = client.patch(
        f"/api/v1/matches/{QF1_ID}/result",
        json={"score_a": 0, "score_b": 2, "force_override": True},
        headers={"X-Mock-Role": "committee"},
    )
    assert resp.status_code == 400
    assert _error_code(resp) == "VALIDATION_ERROR"


def test_update_team_with_blank_name_returns_400(client: FlaskClient) -> None:
    resp = client.patch(
        f"/api/v1/teams/{TEAM_GRD}",
        json={"name": "   "},
        headers={"X-Mock-Role": "team_captain"},
    )
    assert resp.status_code == 400
    assert _error_code(resp) == "VALIDATION_ERROR"


def test_login_with_non_string_password_returns_400_not_500(client: FlaskClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "player@turnamen.in", "password": 123456},
    )
    assert resp.status_code == 400
    assert _error_code(resp) == "VALIDATION_ERROR"


def test_announcement_rejects_oversized_title_with_400(client: FlaskClient) -> None:
    resp = client.post(
        f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}/announcements",
        json={"title": "x" * 181, "content": "Pengumuman uji batas panjang judul."},
        headers={"X-Mock-Role": "committee"},
    )
    assert resp.status_code == 400
    assert _error_code(resp) == "VALIDATION_ERROR"


def test_empty_patch_on_team_and_tournament_returns_200(client: FlaskClient) -> None:
    team_resp = client.patch(
        f"/api/v1/teams/{TEAM_GRD}",
        json={},
        headers={"X-Mock-Role": "team_captain"},
    )
    assert team_resp.status_code == 200

    tour_resp = client.patch(
        f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}",
        json={},
        headers={"X-Mock-Role": "organizer"},
    )
    assert tour_resp.status_code == 200
