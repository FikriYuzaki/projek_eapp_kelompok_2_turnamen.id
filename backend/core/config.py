"""Centralized configuration loader for Turnamen.in.

Defaults to `APP_MODE=mock` and binds local servers to `127.0.0.1` so the
starter application can run safely offline without cloud credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback if python-dotenv is not loaded
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=False)


VALID_APP_MODES = ("mock", "supabase")


@dataclass(frozen=True)
class AppConfig:
    """Immutable runtime configuration for Desktop + Flask Backend."""

    app_name: str = "Turnamen.in"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_mode: str = "mock"
    api_host: str = "127.0.0.1"
    api_port: int = 5000
    flask_debug: bool = False
    secret_key: str = "dev-local-only-secret-key-do-not-use-in-prod"
    eel_host: str = "127.0.0.1"
    eel_port: int = 8080
    eel_browser_mode: str = "chrome"
    eel_start_page: str = "index.html"
    eel_window_width: int = 1366
    eel_window_height: int = 820
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_storage_bucket: str = "tournament-assets"
    rawg_api_key: str = ""
    rawg_api_base_url: str = "https://api.rawg.io/api"
    log_level: str = "INFO"
    log_file: str = "logs/turnamen_in.log"

    @property
    def is_mock_mode(self) -> bool:
        return self.app_mode == "mock"

    @property
    def is_supabase_mode(self) -> bool:
        return self.app_mode == "supabase"

    @property
    def api_base_url(self) -> str:
        return f"http://{self.api_host}:{self.api_port}/api/v1"

    def validate(self) -> None:
        """Validate configuration settings and fail fast on invalid modes."""
        if self.app_mode not in VALID_APP_MODES:
            raise ValueError(
                f"APP_MODE tidak valid: '{self.app_mode}'. Gunakan salah satu dari {VALID_APP_MODES}."
            )
        if self.is_supabase_mode and (not self.supabase_url or not self.supabase_anon_key):
            raise ValueError(
                "APP_MODE=supabase membutuhkan SUPABASE_URL dan SUPABASE_ANON_KEY pada file .env."
            )

    def to_safe_dict(self) -> dict[str, Any]:
        """Return configuration dictionary with secrets redacted for logging/UI inspection."""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "app_env": self.app_env,
            "app_mode": self.app_mode,
            "is_simulation": self.is_mock_mode,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "api_base_url": self.api_base_url,
            "eel_host": self.eel_host,
            "eel_port": self.eel_port,
            "eel_window_width": self.eel_window_width,
            "eel_window_height": self.eel_window_height,
            "supabase_configured": bool(self.supabase_url and self.supabase_anon_key),
            "secret_key": "***REDACTED***",
            "supabase_anon_key": "***REDACTED***" if self.supabase_anon_key else "",
        }


def load_config(overrides: dict[str, Any] | None = None) -> AppConfig:
    """Load application configuration from environment variables and optional overrides."""
    raw_mode = os.getenv("APP_MODE", "mock").strip().lower()
    raw_debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in ("1", "true", "yes")

    values: dict[str, Any] = {
        "app_name": os.getenv("APP_NAME", "Turnamen.in").strip(),
        "app_version": os.getenv("APP_VERSION", "0.1.0").strip(),
        "app_env": os.getenv("APP_ENV", "development").strip(),
        "app_mode": raw_mode or "mock",
        "api_host": os.getenv("API_HOST", "127.0.0.1").strip() or "127.0.0.1",
        "api_port": int(os.getenv("API_PORT", "5000")),
        "flask_debug": raw_debug,
        "secret_key": os.getenv("SECRET_KEY", "dev-local-only-secret-key-do-not-use-in-prod"),
        "eel_host": os.getenv("EEL_HOST", "127.0.0.1").strip() or "127.0.0.1",
        "eel_port": int(os.getenv("EEL_PORT", "8080")),
        "eel_browser_mode": os.getenv("EEL_BROWSER_MODE", "chrome").strip(),
        "eel_start_page": os.getenv("EEL_START_PAGE", "index.html").strip(),
        "eel_window_width": int(os.getenv("EEL_WINDOW_WIDTH", "1366")),
        "eel_window_height": int(os.getenv("EEL_WINDOW_HEIGHT", "820")),
        "supabase_url": os.getenv("SUPABASE_URL", "").strip(),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", "").strip(),
        "supabase_storage_bucket": os.getenv("SUPABASE_STORAGE_BUCKET", "tournament-assets").strip(),
        "rawg_api_key": os.getenv("RAWG_API_KEY", "").strip(),
        "rawg_api_base_url": os.getenv("RAWG_API_BASE_URL", "https://api.rawg.io/api").strip(),
        "log_level": os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        "log_file": os.getenv("LOG_FILE", "logs/turnamen_in.log").strip(),
    }

    if overrides:
        values.update(overrides)

    cfg = AppConfig(**values)
    cfg.validate()
    return cfg
