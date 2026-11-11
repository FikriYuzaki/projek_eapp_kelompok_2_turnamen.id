"""Flask application factory for Turnamen.in.

Owner: Anisa (REST API, Reporting & Testing Developer) & Fikri (System Integration)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from flask import Flask, send_from_directory
from werkzeug.exceptions import HTTPException

from backend.api.routes.v1_routes import create_v1_blueprint
from backend.api.schemas.responses import api_error
from backend.core.config import AppConfig, ROOT_DIR, load_config
from backend.core.exceptions import DomainError
from backend.core.logging_config import configure_logging
from backend.modules.announcements.service import AnnouncementService
from backend.modules.auth.service import AuthService
from backend.modules.matches.service import MatchService
from backend.modules.reports.service import ReportService
from backend.modules.teams.service import TeamService
from backend.modules.tournaments.service import TournamentService
from backend.repositories.factory import get_repository
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol

WEB_DIR = ROOT_DIR / "desktop" / "web"


def build_services(repository: DataStoreRepositoryProtocol) -> dict[str, Any]:
    """Instantiate all domain application services sharing the given repository."""
    return {
        "auth": AuthService(repository),
        "tournaments": TournamentService(repository),
        "teams": TeamService(repository),
        "matches": MatchService(repository),
        "announcements": AnnouncementService(repository),
        "reports": ReportService(repository),
    }


def create_app(
    config: AppConfig | None = None,
    repository: DataStoreRepositoryProtocol | None = None,
    fresh_mock: bool = False,
) -> Flask:
    """Create and configure the Turnamen.in Flask REST API application."""
    cfg = config or load_config()
    logger = configure_logging(cfg)
    repo = repository or get_repository(cfg, fresh_mock=fresh_mock)
    services = build_services(repo)

    app = Flask(
        __name__,
        static_folder=str(WEB_DIR),
        static_url_path="",
    )
    app.config["SECRET_KEY"] = cfg.secret_key
    app.config["TURNAMEN_CONFIG"] = cfg
    app.config["TURNAMEN_REPO"] = repo
    app.config["TURNAMEN_SERVICES"] = services

    # Register CORS headers for local Eel window (127.0.0.1:8080 -> 127.0.0.1:5000)
    @app.after_request
    def add_local_cors_headers(response: Any) -> Any:
        origin = f"http://{cfg.eel_host}:{cfg.eel_port}"
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Mock-User-Id, X-Mock-Role"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PATCH, PUT, DELETE, OPTIONS"
        )
        return response

    app.register_blueprint(create_v1_blueprint())

    # Serve Desktop Web UI at root when browsing http://127.0.0.1:5000/
    @app.get("/")
    def serve_index() -> Any:
        if (WEB_DIR / "index.html").exists():
            return send_from_directory(str(WEB_DIR), "index.html")
        return {"status": "Turnamen.in API Server Running"}, 200

    # Global Error Handlers ensuring consistent JSON contract
    @app.errorhandler(DomainError)
    def handle_domain_error(err: DomainError) -> Any:
        return api_error(
            message=err.message,
            code=err.error_code,
            details=err.details,
            status_code=err.http_status,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException) -> Any:
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
        }
        status_code = err.code or 500
        return api_error(
            message=err.description or "Permintaan HTTP tidak valid.",
            code=code_map.get(status_code, "HTTP_ERROR"),
            details={"status_code": status_code},
            status_code=status_code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(err: Exception) -> Any:  # pragma: no cover
        logger.exception("Unexpected internal error: %s", err)
        return api_error(
            message="Terjadi kesalahan internal pada server.",
            code="INTERNAL_ERROR",
            details={},
            status_code=500,
        )

    return app
