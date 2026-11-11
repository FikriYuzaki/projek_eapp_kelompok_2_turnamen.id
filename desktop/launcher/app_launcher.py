"""Unified Desktop + Flask REST API Launcher for Turnamen.in.

Owner: Fikri (System Integration & Python Eel Developer)
Handles coordinated startup, health readiness checks, and graceful shutdown
of both the local Flask API server and the Python Eel desktop window.
"""

from __future__ import annotations

import shutil
import threading
import time
from typing import Any
from werkzeug.serving import make_server

from backend.app import create_app
from backend.core.config import AppConfig, ROOT_DIR, load_config
from backend.core.logging_config import configure_logging
from desktop.bridge.eel_bridge import register_eel_bridge

WEB_DIR = ROOT_DIR / "desktop" / "web"


class BackgroundFlaskServer(threading.Thread):
    """Run the local Flask REST API inside a controllable background daemon thread."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__(daemon=True, name="TurnamenFlaskServer")
        self.config = config
        self.app = create_app(config)
        self._server = make_server(config.api_host, config.api_port, self.app, threaded=True)
        self._ctx = self.app.app_context()
        self._ctx.push()

    def run(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()


def run_smoke_check(config: AppConfig | None = None) -> dict[str, Any]:
    """Verify configuration, repository initialization, and `/api/v1/health` in-process."""
    cfg = config or load_config()
    app = create_app(cfg)
    with app.test_client() as client:
        health_res = client.get("/api/v1/health").get_json()
        tournaments_res = client.get("/api/v1/tournaments").get_json()
        games_res = client.get("/api/v1/games").get_json()

    return {
        "config": cfg.to_safe_dict(),
        "health_ok": bool(health_res and health_res.get("success")),
        "games_count": len(games_res.get("data", [])) if games_res else 0,
        "tournaments_count": len(tournaments_res.get("data", [])) if tournaments_res else 0,
    }


def detect_chromium_browser(preferred: str = "chrome") -> str | None:
    """Detect whether Chrome or Edge is available on Windows for Python Eel."""
    candidates = [
        preferred,
        "chrome",
        "msedge",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if shutil.which(candidate):
            return preferred if candidate in ("chrome", "msedge", "edge") else "chrome"
    return None


def launch_application(api_only: bool = False, config: AppConfig | None = None) -> int:
    """Start the local Flask REST API and (unless `api_only=True`) open the Python Eel window."""
    cfg = config or load_config()
    logger = configure_logging(cfg)

    mode_banner = (
        "MOCK MODE (SIMULASI LOKAL - TANPA CLOUD)"
        if cfg.is_mock_mode
        else "SUPABASE ONLINE MODE"
    )
    logger.info("============================================================")
    logger.info("Starting %s v%s [%s]", cfg.app_name, cfg.app_version, mode_banner)
    logger.info("Flask REST API : http://%s:%s/api/v1", cfg.api_host, cfg.api_port)
    logger.info("Web UI         : http://%s:%s/", cfg.api_host, cfg.api_port)
    logger.info("============================================================")

    if api_only:
        app = create_app(cfg)
        try:
            app.run(host=cfg.api_host, port=cfg.api_port, debug=cfg.flask_debug, use_reloader=False)
        except KeyboardInterrupt:
            logger.info("Flask API server stopped by user.")
        return 0

    flask_thread = BackgroundFlaskServer(cfg)
    flask_thread.start()
    time.sleep(0.3)

    try:
        import eel

        register_eel_bridge(cfg)
        eel.init(str(WEB_DIR))
        browser_mode = detect_chromium_browser(cfg.eel_browser_mode) or "default"
        logger.info(
            "Opening Python Eel desktop window on http://%s:%s/%s (mode=%s)",
            cfg.eel_host,
            cfg.eel_port,
            cfg.eel_start_page,
            browser_mode,
        )
        eel.start(
            cfg.eel_start_page,
            mode=browser_mode,
            host=cfg.eel_host,
            port=cfg.eel_port,
            size=(cfg.eel_window_width, cfg.eel_window_height),
            block=True,
        )
    except (ImportError, EnvironmentError, SystemExit, KeyboardInterrupt) as exc:
        logger.info("Desktop window closed or interrupted (%s). Shutting down...", exc)
    finally:
        logger.info("Stopping background Flask REST API server...")
        flask_thread.shutdown()
        logger.info("Shutdown complete.")

    return 0
