"""REST API v1 Blueprint (`/api/v1`) implementing all contract endpoints.

Owner: Anisa (REST API, Reporting & Testing Developer)
"""

from __future__ import annotations

from typing import Any
from flask import Blueprint, current_app, request

from backend.api.schemas.responses import api_success
from backend.api.schemas.validators import parse_json_body
from backend.core.exceptions import DomainUnauthorizedError


def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def _resolve_current_actor() -> dict[str, Any] | None:
    """Resolve authenticated user from Bearer token or mock testing headers."""
    services = current_app.config["TURNAMEN_SERVICES"]
    app_config = current_app.config["TURNAMEN_CONFIG"]
    auth_service = services["auth"]

    token = _extract_bearer_token()
    if token:
        user = auth_service.get_user_by_token(token)
        if user:
            return user

    if app_config.is_mock_mode:
        mock_user_id = request.headers.get("X-Mock-User-Id", "").strip() or None
        mock_role = request.headers.get("X-Mock-Role", "").strip() or None
        if mock_user_id or mock_role:
            return auth_service.get_user_by_mock_header(
                mock_user_id=mock_user_id, mock_role=mock_role
            )

    return None


def create_v1_blueprint() -> Blueprint:
    bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------
    @bp.get("/health")
    def get_health() -> Any:
        cfg = current_app.config["TURNAMEN_CONFIG"]
        return api_success(
            data={
                "app_name": cfg.app_name,
                "version": cfg.app_version,
                "app_mode": cfg.app_mode,
                "is_simulation": cfg.is_mock_mode,
                "status": "healthy",
            },
            message="Layanan API Turnamen.in berjalan normal",
        )

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    @bp.post("/auth/register")
    def auth_register() -> Any:
        payload = parse_json_body(
            request, required_fields=("email", "username", "full_name", "password")
        )
        services = current_app.config["TURNAMEN_SERVICES"]
        result = services["auth"].register(payload)
        return api_success(
            data=result,
            message="Registrasi akun berhasil",
            status_code=201,
        )

    @bp.post("/auth/login")
    def auth_login() -> Any:
        payload = parse_json_body(request, required_fields=("email", "password"))
        services = current_app.config["TURNAMEN_SERVICES"]
        result = services["auth"].login(payload["email"], payload["password"])
        return api_success(
            data=result,
            message="Login berhasil",
        )

    @bp.post("/auth/logout")
    def auth_logout() -> Any:
        token = _extract_bearer_token()
        services = current_app.config["TURNAMEN_SERVICES"]
        services["auth"].logout(token)
        return api_success(
            data={"logged_out": True},
            message="Sesi berhasil diakhiri",
        )

    @bp.get("/auth/me")
    def auth_me() -> Any:
        actor = _resolve_current_actor()
        if not actor:
            raise DomainUnauthorizedError("Sesi pengguna tidak ditemukan atau sudah berakhir.")
        return api_success(
            data={"user": actor},
            message="Profil pengguna aktif berhasil diperoleh",
        )

    # -------------------------------------------------------------------------
    # Games
    # -------------------------------------------------------------------------
    @bp.get("/games")
    def list_games() -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        games = services["tournaments"].list_games()
        return api_success(data=games, message="Daftar game berhasil diperoleh")

    @bp.get("/games/<game_id>")
    def get_game(game_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        game = services["tournaments"].get_game(game_id)
        return api_success(data=game, message="Detail game berhasil diperoleh")

    # -------------------------------------------------------------------------
    # Tournaments
    # -------------------------------------------------------------------------
    @bp.get("/tournaments")
    def list_tournaments() -> Any:
        status = request.args.get("status") or None
        game_id = request.args.get("game_id") or None
        services = current_app.config["TURNAMEN_SERVICES"]
        items = services["tournaments"].list_tournaments(status=status, game_id=game_id)
        return api_success(data=items, message="Daftar turnamen berhasil diperoleh")

    @bp.post("/tournaments")
    def create_tournament() -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(
            request, required_fields=("title", "game_id", "start_date")
        )
        services = current_app.config["TURNAMEN_SERVICES"]
        created = services["tournaments"].create_tournament(actor, payload)
        return api_success(
            data=created,
            message="Turnamen baru berhasil dibuat",
            status_code=201,
        )

    @bp.get("/tournaments/<tournament_id>")
    def get_tournament(tournament_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        tournament = services["tournaments"].get_tournament(tournament_id)
        return api_success(data=tournament, message="Detail turnamen berhasil diperoleh")

    @bp.patch("/tournaments/<tournament_id>")
    def update_tournament(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request)
        services = current_app.config["TURNAMEN_SERVICES"]
        updated = services["tournaments"].update_tournament(actor, tournament_id, payload)
        return api_success(data=updated, message="Data turnamen berhasil diperbarui")

    @bp.delete("/tournaments/<tournament_id>")
    def delete_tournament(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        deleted = services["tournaments"].delete_tournament(actor, tournament_id)
        return api_success(data=deleted, message="Turnamen berhasil dihapus")

    # -------------------------------------------------------------------------
    # Teams & Members
    # -------------------------------------------------------------------------
    @bp.get("/teams")
    def list_teams() -> Any:
        game_id = request.args.get("game_id") or None
        services = current_app.config["TURNAMEN_SERVICES"]
        teams = services["teams"].list_teams(game_id=game_id)
        return api_success(data=teams, message="Daftar tim berhasil diperoleh")

    @bp.post("/teams")
    def create_team() -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("name", "tag", "game_id"))
        services = current_app.config["TURNAMEN_SERVICES"]
        created = services["teams"].create_team(actor, payload)
        return api_success(
            data=created,
            message="Tim baru berhasil dibuat",
            status_code=201,
        )

    @bp.get("/teams/<team_id>")
    def get_team(team_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        team = services["teams"].get_team(team_id)
        return api_success(data=team, message="Detail tim berhasil diperoleh")

    @bp.patch("/teams/<team_id>")
    def update_team(team_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request)
        services = current_app.config["TURNAMEN_SERVICES"]
        updated = services["teams"].update_team(actor, team_id, payload)
        return api_success(data=updated, message="Data tim berhasil diperbarui")

    @bp.post("/teams/<team_id>/members")
    def add_team_member(team_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("nickname", "ingame_id"))
        services = current_app.config["TURNAMEN_SERVICES"]
        member = services["teams"].add_member(actor, team_id, payload)
        return api_success(
            data=member,
            message="Anggota tim berhasil ditambahkan",
            status_code=201,
        )

    # -------------------------------------------------------------------------
    # Registrations
    # -------------------------------------------------------------------------
    @bp.get("/tournaments/<tournament_id>/registrations")
    def list_registrations(tournament_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        regs = services["tournaments"].list_registrations(tournament_id)
        return api_success(data=regs, message="Daftar registrasi tim berhasil diperoleh")

    @bp.post("/tournaments/<tournament_id>/registrations")
    def register_team(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("team_id",))
        services = current_app.config["TURNAMEN_SERVICES"]
        created = services["tournaments"].register_team(actor, tournament_id, payload)
        return api_success(
            data=created,
            message="Pendaftaran tim berhasil dikirim",
            status_code=201,
        )

    @bp.patch("/registrations/<registration_id>/status")
    def update_registration_status(registration_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("status",))
        services = current_app.config["TURNAMEN_SERVICES"]
        updated = services["tournaments"].update_registration_status(
            actor, registration_id, payload
        )
        return api_success(
            data=updated,
            message="Status pendaftaran berhasil diperbarui",
        )

    # -------------------------------------------------------------------------
    # Matches & Bracket
    # -------------------------------------------------------------------------
    @bp.get("/tournaments/<tournament_id>/matches")
    def list_matches(tournament_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        bracket_data = services["matches"].get_tournament_bracket(tournament_id)
        return api_success(
            data=bracket_data,
            message="Data pertandingan dan bracket berhasil diperoleh",
        )

    @bp.post("/tournaments/<tournament_id>/bracket/generate")
    def generate_bracket(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request)
        services = current_app.config["TURNAMEN_SERVICES"]
        bracket_data = services["matches"].generate_bracket(actor, tournament_id, payload)
        return api_success(
            data=bracket_data,
            message="Bracket Single Elimination berhasil dibuat",
            status_code=201,
        )

    @bp.patch("/matches/<match_id>/result")
    def submit_match_result(match_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("score_a", "score_b"))
        services = current_app.config["TURNAMEN_SERVICES"]
        result = services["matches"].submit_match_result(actor, match_id, payload)
        return api_success(
            data=result,
            message="Hasil pertandingan berhasil disahkan",
        )

    # -------------------------------------------------------------------------
    # Announcements
    # -------------------------------------------------------------------------
    @bp.get("/tournaments/<tournament_id>/announcements")
    def list_announcements(tournament_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        items = services["announcements"].list_announcements(tournament_id)
        return api_success(data=items, message="Daftar pengumuman berhasil diperoleh")

    @bp.post("/tournaments/<tournament_id>/announcements")
    def create_announcement(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("title", "content"))
        services = current_app.config["TURNAMEN_SERVICES"]
        created = services["announcements"].create_announcement(
            actor, tournament_id, payload
        )
        return api_success(
            data=created,
            message="Pengumuman berhasil dipublikasikan",
            status_code=201,
        )

    # -------------------------------------------------------------------------
    # Reports & Standings
    # -------------------------------------------------------------------------
    @bp.get("/tournaments/<tournament_id>/reports")
    def get_tournament_reports(tournament_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        report = services["reports"].get_tournament_report(tournament_id)
        return api_success(data=report, message="Laporan turnamen berhasil diperoleh")

    @bp.get("/tournaments/<tournament_id>/standings")
    def get_tournament_standings(tournament_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        standings = services["reports"].get_tournament_standings(tournament_id)
        return api_success(data=standings, message="Klasemen turnamen berhasil diperoleh")

    return bp
