"""REST API v1 Blueprint (`/api/v1`) implementing all contract endpoints.

Owner: Anisa (REST API, Reporting & Testing Developer)
"""

from __future__ import annotations

import base64
import binascii
from typing import Any
from urllib.parse import urlparse
from flask import Blueprint, Response, current_app, g, has_request_context, request

from backend.api.schemas.responses import api_success
from backend.api.schemas.validators import parse_json_body
from backend.core.exceptions import DomainNotFoundError, DomainUnauthorizedError, DomainValidationError
from backend.modules.tournaments.artwork_validator import (
    MAX_GAME_ARTWORK_BYTES,
    is_valid_artwork_storage_path,
)


def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def _resolve_current_actor() -> dict[str, Any] | None:
    """Resolve authenticated user from Bearer token or mock testing headers."""
    if has_request_context() and getattr(g, "_turnamen_actor_resolved", False):
        return getattr(g, "_turnamen_actor_cache", None)

    services = current_app.config["TURNAMEN_SERVICES"]
    app_config = current_app.config["TURNAMEN_CONFIG"]
    auth_service = services["auth"]

    resolved: dict[str, Any] | None = None
    token = _extract_bearer_token()
    if token:
        user = auth_service.get_user_by_token(token)
        if user:
            resolved = user

    if resolved is None and app_config.is_mock_mode:
        mock_user_id = request.headers.get("X-Mock-User-Id", "").strip() or None
        mock_role = request.headers.get("X-Mock-Role", "").strip() or None
        if mock_user_id or mock_role:
            resolved = auth_service.get_user_by_mock_header(
                mock_user_id=mock_user_id, mock_role=mock_role
            )

    if has_request_context():
        g._turnamen_actor_resolved = True
        g._turnamen_actor_cache = resolved
    return resolved


def create_v1_blueprint() -> Blueprint:
    bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

    # Health
    @bp.get("/health")
    def get_health() -> Any:
        cfg = current_app.config["TURNAMEN_CONFIG"]
        supabase_host = (
            (urlparse(cfg.supabase_url).hostname or "").strip().lower()
            if cfg.is_supabase_mode and cfg.supabase_url
            else ""
        )
        return api_success(
            data={
                "app_name": cfg.app_name,
                "version": cfg.app_version,
                "app_mode": cfg.app_mode,
                "is_simulation": cfg.is_mock_mode,
                "supabase_host": supabase_host,
                "status": "healthy",
            },
            message="Layanan API Turnamen.in berjalan normal",
        )

    # Authentication
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
        actor = _resolve_current_actor()
        if not actor:
            raise DomainUnauthorizedError("Sesi pengguna tidak ditemukan atau sudah berakhir.")
        token = _extract_bearer_token()
        services = current_app.config["TURNAMEN_SERVICES"]
        services["auth"].logout(token)
        return api_success(
            data={"logged_out": True},
            message="Sesi berhasil diakhiri",
        )

    @bp.post("/auth/password-recovery")
    def auth_request_password_recovery() -> Any:
        payload = parse_json_body(request, required_fields=("email",))
        cfg = current_app.config["TURNAMEN_CONFIG"]
        default_redirect = f"http://{cfg.eel_host}:{cfg.eel_port}/{cfg.eel_start_page}"
        redirect_to = payload.get("redirect_to") or default_redirect
        services = current_app.config["TURNAMEN_SERVICES"]
        result = services["auth"].request_password_recovery(
            payload["email"], redirect_to=redirect_to
        )
        return api_success(
            data=result,
            message="Jika email terdaftar, instruksi pemulihan password telah dikirimkan.",
        )

    @bp.post("/auth/password-recovery/update")
    def auth_update_password_recovery() -> Any:
        payload = parse_json_body(request, required_fields=("new_password",))
        token = _extract_bearer_token() or payload.get("access_token")
        services = current_app.config["TURNAMEN_SERVICES"]
        result = services["auth"].complete_password_recovery(
            new_password=payload["new_password"],
            access_token=token,
            refresh_token=payload.get("refresh_token"),
            token_hash=payload.get("token_hash"),
        )
        return api_success(
            data=result,
            message="Password berhasil diperbarui. Silakan masuk menggunakan password baru Anda.",
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

    @bp.patch("/auth/me")
    def auth_update_me() -> Any:
        actor = _resolve_current_actor()
        if not actor:
            raise DomainUnauthorizedError("Sesi pengguna tidak ditemukan atau sudah berakhir.")
        payload = parse_json_body(request)
        services = current_app.config["TURNAMEN_SERVICES"]
        updated = services["auth"].update_profile(actor, actor["id"], payload)
        return api_success(
            data={"user": updated},
            message="Profil pengguna berhasil diperbarui",
        )

    @bp.get("/users")
    def list_users() -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        users = services["auth"].list_users(actor)
        return api_success(data=users, message="Daftar pengguna sistem berhasil diperoleh")

    @bp.patch("/users/<user_id>/role")
    def assign_user_role(user_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("role",))
        services = current_app.config["TURNAMEN_SERVICES"]
        updated = services["auth"].assign_role(actor, user_id, payload["role"])
        return api_success(
            data={"user": updated},
            message="Role pengguna berhasil diperbarui",
        )

    # Games
    @bp.get("/games")
    def list_games() -> Any:
        actor = _resolve_current_actor()
        include_inactive = request.args.get("include_inactive", "").strip().lower() in ("1", "true", "yes")
        services = current_app.config["TURNAMEN_SERVICES"]
        games = services["tournaments"].list_games(include_inactive=include_inactive, actor=actor)
        return api_success(data=games, message="Daftar game berhasil diperoleh")

    @bp.get("/games/<game_id>")
    def get_game(game_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        game = services["tournaments"].get_game(game_id)
        return api_success(data=game, message="Detail game berhasil diperoleh")

    @bp.post("/games")
    def create_game() -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("name", "genre"))
        services = current_app.config["TURNAMEN_SERVICES"]
        created = services["tournaments"].create_game(actor, payload)
        return api_success(
            data=created,
            message="Cabang game baru berhasil ditambahkan",
            status_code=201,
        )

    @bp.patch("/games/<game_id>")
    def update_game(game_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request)
        services = current_app.config["TURNAMEN_SERVICES"]
        updated = services["tournaments"].update_game(actor, game_id, payload)
        return api_success(data=updated, message="Data cabang game berhasil diperbarui")

    @bp.post("/games/<game_id>/artwork")
    def upload_game_artwork(game_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        if request.files and "file" in request.files:
            uploaded_file = request.files["file"]
            raw_bytes = uploaded_file.read(MAX_GAME_ARTWORK_BYTES + 1)
            filename = uploaded_file.filename or ""
            declared_type = uploaded_file.mimetype or ""
        else:
            payload = parse_json_body(request, required_fields=("image_base64",))
            raw_b64 = str(payload.get("image_base64") or "").strip()
            if raw_b64.startswith("data:") and "," in raw_b64:
                header_part, raw_b64 = raw_b64.split(",", 1)
                if not payload.get("content_type") and ";" in header_part:
                    payload["content_type"] = header_part[5:].split(";", 1)[0].strip()
            max_b64_chars = ((MAX_GAME_ARTWORK_BYTES + 2) // 3) * 4 + 64
            if len(raw_b64) > max_b64_chars:
                raise DomainValidationError(
                    "Ukuran gambar poster melebihi batas maksimal 5 MB.",
                    {"max_bytes": MAX_GAME_ARTWORK_BYTES},
                )
            try:
                raw_bytes = base64.b64decode(raw_b64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise DomainValidationError(
                    "Data gambar base64 tidak valid.",
                    {"field": "image_base64"},
                ) from exc
            filename = str(payload.get("filename") or "")
            declared_type = str(payload.get("content_type") or "")

        updated = services["tournaments"].upload_game_artwork(
            actor,
            game_id,
            raw_bytes=raw_bytes,
            filename=filename,
            declared_content_type=declared_type,
        )
        return api_success(data=updated, message="Poster game berhasil diperbarui")

    @bp.delete("/games/<game_id>/artwork")
    def restore_game_artwork(game_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        restored = services["tournaments"].restore_game_artwork(actor, game_id)
        return api_success(
            data=restored,
            message="Poster game berhasil dikembalikan ke artwork resmi",
        )

    @bp.get("/games/artwork-assets/<path:storage_path>")
    def get_mock_game_artwork_asset(storage_path: str) -> Any:
        cfg = current_app.config["TURNAMEN_CONFIG"]
        if not cfg.is_mock_mode or not is_valid_artwork_storage_path(storage_path):
            raise DomainNotFoundError("Aset poster game tidak ditemukan.", {"storage_path": storage_path})
        services = current_app.config["TURNAMEN_SERVICES"]
        asset = services["tournaments"].get_mock_artwork_asset(storage_path)
        if not asset:
            raise DomainNotFoundError("Aset poster game tidak ditemukan.", {"storage_path": storage_path})
        mime_type, blob_bytes = asset
        return Response(
            blob_bytes,
            status=200,
            mimetype=mime_type,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    # Tournaments
    @bp.get("/tournaments")
    def list_tournaments() -> Any:
        actor = _resolve_current_actor()
        status = request.args.get("status") or None
        game_id = request.args.get("game_id") or None
        services = current_app.config["TURNAMEN_SERVICES"]
        items = services["tournaments"].list_tournaments(
            status=status, game_id=game_id, actor=actor
        )
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
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        tournament = services["tournaments"].get_tournament(tournament_id, actor=actor)
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

    # Tournament Staff
    @bp.get("/staff/candidates")
    def list_committee_candidates() -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        candidates = services["tournaments"].list_committee_candidates(actor)
        return api_success(data=candidates, message="Daftar kandidat panitia berhasil diperoleh")

    @bp.get("/tournaments/<tournament_id>/staff")
    def list_tournament_staff(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        staff = services["tournaments"].list_tournament_staff(actor, tournament_id)
        return api_success(data=staff, message="Daftar panitia turnamen berhasil diperoleh")

    @bp.post("/tournaments/<tournament_id>/staff")
    def add_tournament_staff(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        payload = parse_json_body(request, required_fields=("user_id",))
        services = current_app.config["TURNAMEN_SERVICES"]
        created = services["tournaments"].add_tournament_staff(actor, tournament_id, payload)
        return api_success(
            data=created,
            message="Panitia berhasil ditugaskan ke turnamen",
            status_code=201,
        )

    @bp.delete("/tournaments/<tournament_id>/staff/<user_id>")
    def remove_tournament_staff(tournament_id: str, user_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        removed = services["tournaments"].remove_tournament_staff(actor, tournament_id, user_id)
        return api_success(data=removed, message="Penugasan panitia berhasil dicabut")

    # Teams & Members
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

    # Registrations
    @bp.get("/tournaments/<tournament_id>/registrations")
    def list_registrations(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        regs = services["tournaments"].list_registrations(tournament_id, actor=actor)
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

    # Matches & Bracket
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
        raw_header_idem = request.headers.get("Idempotency-Key")
        if raw_header_idem is not None:
            header_idem = raw_header_idem.strip()
            body_idem = payload.get("idempotency_key")
            if body_idem is not None and str(body_idem).strip() != header_idem:
                raise DomainValidationError(
                    "Header Idempotency-Key tidak cocok dengan field idempotency_key di payload.",
                    {"field": "idempotency_key"},
                )
            payload["idempotency_key"] = header_idem
        services = current_app.config["TURNAMEN_SERVICES"]
        result = services["matches"].submit_match_result(actor, match_id, payload)
        return api_success(
            data=result,
            message="Hasil pertandingan berhasil disahkan",
        )

    # Announcements
    @bp.get("/tournaments/<tournament_id>/announcements")
    def list_announcements(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        items = services["announcements"].list_announcements(tournament_id, actor=actor)
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

    # Reports & Standings
    @bp.get("/tournaments/<tournament_id>/reports")
    def get_tournament_reports(tournament_id: str) -> Any:
        actor = _resolve_current_actor()
        services = current_app.config["TURNAMEN_SERVICES"]
        report = services["reports"].get_tournament_report(tournament_id, actor=actor)
        return api_success(data=report, message="Laporan turnamen berhasil diperoleh")

    @bp.get("/tournaments/<tournament_id>/standings")
    def get_tournament_standings(tournament_id: str) -> Any:
        services = current_app.config["TURNAMEN_SERVICES"]
        standings = services["reports"].get_tournament_standings(tournament_id)
        return api_success(data=standings, message="Klasemen turnamen berhasil diperoleh")

    return bp
