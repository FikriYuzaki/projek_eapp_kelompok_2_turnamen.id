"""Centralized configuration loader for Turnamen.in.

Defaults to `APP_MODE=mock` and binds local servers to `127.0.0.1` so the
starter application can run safely offline without cloud credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=False)


VALID_APP_MODES = ("mock", "supabase")
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOCALHOST_HOST = "127.0.0.1"
DEFAULT_DEV_SECRET_KEY = "dev-local-only-secret-key-do-not-use-in-prod"
MIN_PORT = 1
MAX_PORT = 65535
MIN_WINDOW_WIDTH = 320
MAX_WINDOW_WIDTH = 7680
MIN_WINDOW_HEIGHT = 240
MAX_WINDOW_HEIGHT = 4320


def _parse_int(field_name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Konfigurasi {field_name} harus berupa bilangan bulat, bukan boolean.")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Konfigurasi {field_name} harus berupa bilangan bulat yang valid.") from exc


@dataclass(frozen=True)
class AppConfig:
    """Immutable runtime configuration for Desktop + Flask Backend."""

    app_name: str = "Turnamen.in"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_mode: str = "mock"
    api_host: str = LOCALHOST_HOST
    api_port: int = 5000
    flask_debug: bool = False
    secret_key: str = field(default=DEFAULT_DEV_SECRET_KEY, repr=False)
    eel_host: str = LOCALHOST_HOST
    eel_port: int = 8080
    eel_browser_mode: str = "chrome"
    eel_start_page: str = "index.html"
    eel_window_width: int = 1366
    eel_window_height: int = 820
    supabase_url: str = ""
    supabase_anon_key: str = field(default="", repr=False)
    supabase_storage_bucket: str = "tournament-assets"
    rawg_api_key: str = field(default="", repr=False)
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
        """Validate configuration settings and fail fast without exposing credentials."""
        if self.app_mode not in VALID_APP_MODES:
            raise ValueError(
                f"APP_MODE tidak valid: '{self.app_mode}'. Gunakan salah satu dari {VALID_APP_MODES}."
            )

        if self.api_host != LOCALHOST_HOST:
            raise ValueError(
                f"API_HOST tidak valid: '{self.api_host}'. Server API hanya diizinkan bind ke '{LOCALHOST_HOST}'."
            )
        if self.eel_host != LOCALHOST_HOST:
            raise ValueError(
                f"EEL_HOST tidak valid: '{self.eel_host}'. Server Eel hanya diizinkan bind ke '{LOCALHOST_HOST}'."
            )

        if isinstance(self.api_port, bool) or not isinstance(self.api_port, int) or not (MIN_PORT <= self.api_port <= MAX_PORT):
            raise ValueError(
                f"API_PORT tidak valid: {self.api_port}. Gunakan port dalam rentang {MIN_PORT}-{MAX_PORT}."
            )
        if isinstance(self.eel_port, bool) or not isinstance(self.eel_port, int) or not (MIN_PORT <= self.eel_port <= MAX_PORT):
            raise ValueError(
                f"EEL_PORT tidak valid: {self.eel_port}. Gunakan port dalam rentang {MIN_PORT}-{MAX_PORT}."
            )
        if self.api_port == self.eel_port:
            raise ValueError(
                f"API_PORT dan EEL_PORT tidak boleh menggunakan port yang sama ({self.api_port})."
            )

        if (
            isinstance(self.eel_window_width, bool)
            or not isinstance(self.eel_window_width, int)
            or not (MIN_WINDOW_WIDTH <= self.eel_window_width <= MAX_WINDOW_WIDTH)
        ):
            raise ValueError(
                f"EEL_WINDOW_WIDTH tidak valid: {self.eel_window_width}. Rentang valid: {MIN_WINDOW_WIDTH}-{MAX_WINDOW_WIDTH}."
            )
        if (
            isinstance(self.eel_window_height, bool)
            or not isinstance(self.eel_window_height, int)
            or not (MIN_WINDOW_HEIGHT <= self.eel_window_height <= MAX_WINDOW_HEIGHT)
        ):
            raise ValueError(
                f"EEL_WINDOW_HEIGHT tidak valid: {self.eel_window_height}. Rentang valid: {MIN_WINDOW_HEIGHT}-{MAX_WINDOW_HEIGHT}."
            )

        if not self.secret_key or not str(self.secret_key).strip():
            raise ValueError("SECRET_KEY tidak boleh kosong.")
        if self.app_env.strip().lower() in ("production", "prod"):
            if self.secret_key.strip() == DEFAULT_DEV_SECRET_KEY or len(self.secret_key.strip()) < 16:
                raise ValueError(
                    "Konfigurasi production membutuhkan SECRET_KEY khusus (minimal 16 karakter) dan tidak boleh menggunakan nilai default development."
                )

        if self.is_supabase_mode:
            if not self.supabase_url or not self.supabase_anon_key:
                raise ValueError(
                    "APP_MODE=supabase membutuhkan SUPABASE_URL dan SUPABASE_ANON_KEY pada file .env."
                )
            if not self.supabase_url.startswith(("https://", "http://")):
                raise ValueError("SUPABASE_URL harus diawali dengan 'https://' atau 'http://'.")

        if self.log_level.upper() not in VALID_LOG_LEVELS:
            raise ValueError(
                f"LOG_LEVEL tidak valid: '{self.log_level}'. Gunakan salah satu dari {VALID_LOG_LEVELS}."
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
            "rawg_api_key": "***REDACTED***" if self.rawg_api_key else "",
        }


def load_config(overrides: dict[str, Any] | None = None) -> AppConfig:
    """Load application configuration from environment variables and optional overrides."""
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=False)

    raw_mode = os.getenv("APP_MODE", "mock").strip().lower()
    raw_debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in ("1", "true", "yes")

    values: dict[str, Any] = {
        "app_name": os.getenv("APP_NAME", "Turnamen.in").strip() or "Turnamen.in",
        "app_version": os.getenv("APP_VERSION", "0.1.0").strip() or "0.1.0",
        "app_env": os.getenv("APP_ENV", "development").strip() or "development",
        "app_mode": raw_mode or "mock",
        "api_host": os.getenv("API_HOST", LOCALHOST_HOST).strip() or LOCALHOST_HOST,
        "api_port": _parse_int("API_PORT", os.getenv("API_PORT", "5000")),
        "flask_debug": raw_debug,
        "secret_key": os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET_KEY),
        "eel_host": os.getenv("EEL_HOST", LOCALHOST_HOST).strip() or LOCALHOST_HOST,
        "eel_port": _parse_int("EEL_PORT", os.getenv("EEL_PORT", "8080")),
        "eel_browser_mode": os.getenv("EEL_BROWSER_MODE", "chrome").strip() or "chrome",
        "eel_start_page": os.getenv("EEL_START_PAGE", "index.html").strip() or "index.html",
        "eel_window_width": _parse_int("EEL_WINDOW_WIDTH", os.getenv("EEL_WINDOW_WIDTH", "1366")),
        "eel_window_height": _parse_int("EEL_WINDOW_HEIGHT", os.getenv("EEL_WINDOW_HEIGHT", "820")),
        "supabase_url": os.getenv("SUPABASE_URL", "").strip(),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", "").strip(),
        "supabase_storage_bucket": os.getenv("SUPABASE_STORAGE_BUCKET", "tournament-assets").strip(),
        "rawg_api_key": os.getenv("RAWG_API_KEY", "").strip(),
        "rawg_api_base_url": os.getenv("RAWG_API_BASE_URL", "https://api.rawg.io/api").strip(),
        "log_level": os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        "log_file": os.getenv("LOG_FILE", "logs/turnamen_in.log").strip(),
    }

    if overrides:
        merged = dict(overrides)
        for int_key in ("api_port", "eel_port", "eel_window_width", "eel_window_height"):
            if int_key in merged and merged[int_key] is not None:
                merged[int_key] = _parse_int(int_key.upper(), merged[int_key])
        if "app_mode" in merged and isinstance(merged["app_mode"], str):
            merged["app_mode"] = merged["app_mode"].strip().lower()
        if "log_level" in merged and isinstance(merged["log_level"], str):
            merged["log_level"] = merged["log_level"].strip().upper()
        values.update(merged)

    cfg = AppConfig(**values)
    cfg.validate()
    return cfg
