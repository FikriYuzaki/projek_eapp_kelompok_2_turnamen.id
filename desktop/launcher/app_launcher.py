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


def _extract_config_secrets(config: AppConfig | None) -> tuple[str, ...]:
    if not isinstance(config, AppConfig):
        return ()
    candidates = (
        getattr(config, "secret_key", ""),
        getattr(config, "supabase_anon_key", ""),
        getattr(config, "rawg_api_key", ""),
    )
    return tuple(s.strip() for s in candidates if isinstance(s, str) and s.strip())


def _format_endpoint_failure(
    label: str,
    status_code: int,
    payload: Any,
    captured_exceptions: list[str],
) -> str:
    if isinstance(payload, dict):
        msg = payload.get("message")
        if isinstance(msg, str) and msg.strip():
            base = f"{label} gagal: {msg.strip()}"
        else:
            base = f"{label} gagal (HTTP {status_code})."
    else:
        base = f"{label} gagal (HTTP {status_code})."

    if captured_exceptions:
        detail = "; ".join(s.strip() for s in captured_exceptions if s and s.strip())
        if detail and detail not in base:
            return f"{base} ({detail})"
    return base


def run_smoke_check(config: AppConfig | None = None) -> dict[str, Any]:
    """Verify configuration, repository queries, and `/api/v1/health` in-process."""
    try:
        cfg = config or load_config()
        cfg.validate()
    except Exception as exc:
        extra_secrets = _extract_config_secrets(config)
        return {
            "config": config.to_safe_dict() if isinstance(config, AppConfig) else None,
            "health_ok": False,
            "repository_ok": False,
            "games_count": 0,
            "tournaments_count": 0,
            "error": redact_sensitive_text(str(exc), extra_secrets=extra_secrets),
        }

    extra_secrets = _extract_config_secrets(cfg)
    try:
        app = create_app(cfg)
        repo = app.config.get("TURNAMEN_REPO")
        repo_available = (
            repo is not None
            and callable(getattr(repo, "list_games", None))
            and callable(getattr(repo, "list_tournaments", None))
        )

        captured_exceptions: list[str] = []
        if hasattr(app, "handle_user_exception"):
            orig_handle_user_exception = app.handle_user_exception

            def _capture_user_exception(exc: Exception) -> Any:
                captured_exceptions.append(str(exc))
                return orig_handle_user_exception(exc)

            app.handle_user_exception = _capture_user_exception  # type: ignore[method-assign]

        errors: list[str] = []
        if not repo_available:
            errors.append(
                "Repository tidak tersedia atau tidak memiliki method list_games dan list_tournaments."
            )

        health_ok = False
        games_ok = False
        games_count = 0
        tournaments_ok = False
        tournaments_count = 0

        with app.test_client() as client:
            captured_exceptions.clear()
            try:
                health_resp = client.get("/api/v1/health")
                health_res = health_resp.get_json(silent=True)
                health_ok = bool(
                    health_resp.status_code == 200
                    and isinstance(health_res, dict)
                    and health_res.get("success") is True
                    and isinstance(health_res.get("data"), dict)
                    and health_res["data"].get("status") == "healthy"
                )
                if not health_ok:
                    errors.append(
                        _format_endpoint_failure(
                            "Health check",
                            health_resp.status_code,
                            health_res,
                            captured_exceptions,
                        )
                    )
            except Exception as exc:
                errors.append(f"Health check gagal: {exc}")

            if repo_available:
                captured_exceptions.clear()
                try:
                    games_resp = client.get("/api/v1/games")
                    games_res = games_resp.get_json(silent=True)
                    if (
                        games_resp.status_code == 200
                        and isinstance(games_res, dict)
                        and games_res.get("success") is True
                    ):
                        games_data = games_res.get("data")
                        if isinstance(games_data, list):
                            games_ok = True
                            games_count = len(games_data)
                        else:
                            errors.append(
                                "Query games gagal: Data games bukan berupa list yang valid."
                            )
                    else:
                        errors.append(
                            _format_endpoint_failure(
                                "Query games",
                                games_resp.status_code,
                                games_res,
                                captured_exceptions,
                            )
                        )
                except Exception as exc:
                    errors.append(f"Query games gagal: {exc}")

                captured_exceptions.clear()
                try:
                    tournaments_resp = client.get("/api/v1/tournaments")
                    tournaments_res = tournaments_resp.get_json(silent=True)
                    if (
                        tournaments_resp.status_code == 200
                        and isinstance(tournaments_res, dict)
                        and tournaments_res.get("success") is True
                    ):
                        tournaments_data = tournaments_res.get("data")
                        if isinstance(tournaments_data, list):
                            tournaments_ok = True
                            tournaments_count = len(tournaments_data)
                        else:
                            errors.append(
                                "Query tournaments gagal: Data tournaments bukan berupa list yang valid."
                            )
                    else:
                        errors.append(
                            _format_endpoint_failure(
                                "Query tournaments",
                                tournaments_resp.status_code,
                                tournaments_res,
                                captured_exceptions,
                            )
                        )
                except Exception as exc:
                    errors.append(f"Query tournaments gagal: {exc}")

        repository_ok = bool(repo_available and games_ok and tournaments_ok)
        summary: dict[str, Any] = {
            "config": cfg.to_safe_dict(),
            "health_ok": health_ok,
            "repository_ok": repository_ok,
            "games_count": games_count,
            "tournaments_count": tournaments_count,
        }
        if errors:
            summary["error"] = redact_sensitive_text(
                "; ".join(errors),
                extra_secrets=extra_secrets,
            )
        return summary
    except Exception as exc:
        return {
            "config": cfg.to_safe_dict(),
            "health_ok": False,
            "repository_ok": False,
            "games_count": 0,
            "tournaments_count": 0,
            "error": redact_sensitive_text(str(exc), extra_secrets=extra_secrets),
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
