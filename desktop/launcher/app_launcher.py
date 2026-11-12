"""Unified Desktop + Flask REST API Launcher for Turnamen.in.

Owner: Fikri (System Integration & Python Eel Developer)
Handles coordinated startup, health readiness checks, and graceful shutdown
of both the local Flask API server and the Python Eel desktop window.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import threading
import time
from typing import Any
import requests
from werkzeug.serving import make_server

from backend.app import create_app
from backend.core.config import AppConfig, ROOT_DIR, load_config
from backend.core.logging_config import configure_logging, redact_sensitive_text
from desktop.bridge.eel_bridge import register_eel_bridge

WEB_DIR = ROOT_DIR / "desktop" / "web"
DEFAULT_API_READY_TIMEOUT = 10.0
DEFAULT_SHUTDOWN_TIMEOUT = 5.0

CHROME_CANDIDATES = (
    "chrome",
    "google-chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)

EDGE_CANDIDATES = (
    "msedge",
    "microsoft-edge",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


class BackgroundFlaskServer(threading.Thread):
    """Run the local Flask REST API inside a controllable background daemon thread."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__(daemon=True, name="TurnamenFlaskServer")
        self.config = config
        self.app = create_app(config)
        self._server = make_server(config.api_host, config.api_port, self.app, threaded=True)
        self._lock = threading.Lock()
        self._is_serving = False
        self._is_closed = False
        self.startup_error: Exception | None = None

    def run(self) -> None:
        with self._lock:
            if self._is_closed:
                return
            self._is_serving = True
        try:
            self._server.serve_forever()
        except Exception as exc:  # pragma: no cover
            self.startup_error = exc
        finally:
            with self._lock:
                self._is_serving = False
                if not self._is_closed:
                    try:
                        self._server.server_close()
                    except Exception:
                        pass
                    self._is_closed = True

    def shutdown(self, timeout: float = DEFAULT_SHUTDOWN_TIMEOUT) -> None:
        with self._lock:
            should_shutdown = self._is_serving
            already_closed = self._is_closed

        if should_shutdown:
            try:
                self._server.shutdown()
            except Exception:
                pass

        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout=timeout)

        with self._lock:
            if not already_closed and not self._is_closed:
                try:
                    self._server.server_close()
                except Exception:
                    pass
                self._is_closed = True


def wait_for_api_ready(
    config: AppConfig,
    server_thread: BackgroundFlaskServer | None = None,
    timeout: float = DEFAULT_API_READY_TIMEOUT,
    poll_interval: float = 0.1,
) -> bool:
    """Poll `/api/v1/health` until the local Flask API responds healthy or timeout expires."""
    health_url = f"http://{config.api_host}:{config.api_port}/api/v1/health"
    deadline = time.monotonic() + max(timeout, 0.1)

    while time.monotonic() < deadline:
        if server_thread is not None and not server_thread.is_alive():
            return False
        try:
            resp = requests.get(health_url, timeout=1.0)
            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, dict) and payload.get("success") is True:
                    return True
        except (requests.RequestException, ValueError):
            pass
        time.sleep(poll_interval)

    return False


def run_smoke_check(config: AppConfig | None = None) -> dict[str, Any]:
    """Verify configuration, repository initialization, and `/api/v1/health` in-process."""
    try:
        cfg = config or load_config()
        cfg.validate()
    except Exception as exc:
        return {
            "config": config.to_safe_dict() if isinstance(config, AppConfig) else None,
            "health_ok": False,
            "repository_ok": False,
            "games_count": 0,
            "tournaments_count": 0,
            "error": redact_sensitive_text(str(exc)),
        }

    try:
        app = create_app(cfg)
        repo = app.config.get("TURNAMEN_REPO")
        repo_ok = repo is not None and hasattr(repo, "list_games") and hasattr(repo, "list_tournaments")

        with app.test_client() as client:
            health_resp = client.get("/api/v1/health")
            health_res = health_resp.get_json(silent=True) or {}
            tournaments_res = client.get("/api/v1/tournaments").get_json(silent=True) or {}
            games_res = client.get("/api/v1/games").get_json(silent=True) or {}

        health_ok = bool(
            repo_ok
            and health_resp.status_code == 200
            and health_res.get("success") is True
            and isinstance(health_res.get("data"), dict)
            and health_res["data"].get("status") == "healthy"
        )
        return {
            "config": cfg.to_safe_dict(),
            "health_ok": health_ok,
            "repository_ok": repo_ok,
            "games_count": len(games_res.get("data", [])) if isinstance(games_res.get("data"), list) else 0,
            "tournaments_count": (
                len(tournaments_res.get("data", [])) if isinstance(tournaments_res.get("data"), list) else 0
            ),
        }
    except Exception as exc:
        return {
            "config": cfg.to_safe_dict(),
            "health_ok": False,
            "repository_ok": False,
            "games_count": 0,
            "tournaments_count": 0,
            "error": redact_sensitive_text(str(exc)),
        }


def _find_executable(candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        expanded = os.path.expandvars(candidate)
        if os.path.isfile(expanded):
            return expanded
    return None


def _get_browser_candidates(mode: str) -> tuple[str, ...]:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if mode == "chrome":
        extra = (
            (str(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe"),)
            if local_app_data
            else ()
        )
        return CHROME_CANDIDATES + extra
    if mode == "edge":
        extra = (
            (str(Path(local_app_data) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),)
            if local_app_data
            else ()
        )
        return EDGE_CANDIDATES + extra
    return ()


def detect_chromium_browser(preferred: str = "chrome") -> str | None:
    """Detect whether Chrome or Edge is genuinely installed on Windows for Python Eel.

    Returns `'chrome'` or `'edge'` (matching modes supported by `eel.browsers`),
    or `None` if neither browser executable is found.
    """
    norm = (preferred or "chrome").strip().lower()
    if norm in ("msedge", "edge"):
        search_order = ("edge", "chrome")
    elif norm in ("default", "system"):
        return "default"
    else:
        search_order = ("chrome", "edge")

    for mode in search_order:
        if _find_executable(_get_browser_candidates(mode)):
            return mode

    return None


def launch_application(api_only: bool = False, config: AppConfig | None = None) -> int:
    """Start the local Flask REST API and (unless `api_only=True`) open the Python Eel window."""
    try:
        cfg = config or load_config()
        cfg.validate()
    except Exception as exc:
        print(f"Konfigurasi aplikasi tidak valid: {redact_sensitive_text(str(exc))}")
        return 1

    logger = configure_logging(cfg)

    mode_banner = (
        "MOCK MODE (SIMULASI LOKAL - TANPA CLOUD)"
        if cfg.is_mock_mode
        else "SUPABASE ONLINE MODE"
    )
    logger.info("Starting %s v%s [%s]", cfg.app_name, cfg.app_version, mode_banner)
    logger.info("Flask REST API : http://%s:%s/api/v1", cfg.api_host, cfg.api_port)
    logger.info("Web UI         : http://%s:%s/", cfg.api_host, cfg.api_port)

    if api_only:
        try:
            app = create_app(cfg)
            app.run(
                host=cfg.api_host,
                port=cfg.api_port,
                debug=False,
                use_reloader=False,
            )
        except KeyboardInterrupt:
            logger.info("Flask API server stopped by user.")
        except OSError as exc:
            logger.error("Gagal menjalankan server Flask API pada %s:%s (%s).", cfg.api_host, cfg.api_port, exc)
            return 1
        return 0

    try:
        flask_thread = BackgroundFlaskServer(cfg)
    except OSError as exc:
        logger.error("Gagal mengikat port Flask API %s:%s (%s).", cfg.api_host, cfg.api_port, exc)
        return 1

    flask_thread.start()
    if not wait_for_api_ready(cfg, server_thread=flask_thread, timeout=DEFAULT_API_READY_TIMEOUT):
        logger.error(
            "Server Flask REST API gagal siap dalam %.1f detik pada http://%s:%s/api/v1/health.",
            DEFAULT_API_READY_TIMEOUT,
            cfg.api_host,
            cfg.api_port,
        )
        flask_thread.shutdown()
        return 1

    exit_code = 0
    try:
        import eel
        import eel.browsers

        register_eel_bridge(cfg)
        if not WEB_DIR.exists():
            logger.error("Direktori Web UI tidak ditemukan: %s", WEB_DIR)
            return 1

        eel.init(str(WEB_DIR))
        detected_mode = detect_chromium_browser(cfg.eel_browser_mode)
        if detected_mode == "chrome":
            chrome_exe = _find_executable(_get_browser_candidates("chrome"))
            if chrome_exe:
                eel.browsers.set_path("chrome", chrome_exe)
            browser_mode = "chrome"
        elif detected_mode == "edge":
            browser_mode = "edge"
        else:
            browser_mode = "default"
            logger.warning(
                "Chrome atau Microsoft Edge tidak terdeteksi. Menggunakan fallback browser default pada http://%s:%s/%s",
                cfg.eel_host,
                cfg.eel_port,
                cfg.eel_start_page,
            )

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
    except (SystemExit, KeyboardInterrupt):
        logger.info("Jendela desktop ditutup. Menghentikan layanan lokal...")
    except (ImportError, OSError, RuntimeError) as exc:
        logger.error("Kegagalan pada jendela Python Eel (%s). Menghentikan layanan lokal...", exc)
        exit_code = 1
    finally:
        logger.info("Stopping background Flask REST API server...")
        flask_thread.shutdown()
        logger.info("Shutdown complete.")

    return exit_code
