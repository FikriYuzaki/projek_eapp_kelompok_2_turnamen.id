"""Centralized configuration loader for Turnamen.in.

Defaults to `APP_MODE=mock` and binds local servers to `127.0.0.1` so the
starter application can run safely offline without cloud credentials.
"""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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

_JWT_PATTERN = re.compile(r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+$")
_PUBLISHABLE_KEY_PATTERN = re.compile(r"^sb_publishable_[A-Za-z0-9_-]{4,}$")
_PLACEHOLDER_URLS = {
    "https://your-project-ref.supabase.co",
    "http://your-project-ref.supabase.co",
}
_PLACEHOLDER_KEYS = {
    "your-supabase-publishable-key",
    "your-supabase-publishable-or-anon-key",
    "your-supabase-anon-key",
    "sb_publishable_your-key-here",
}


def decode_jwt_payload_unverified(token: str) -> dict[str, Any]:
    """Decode JWT payload claims locally without verifying signature (for role-claim guards only)."""
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)
    try:
        decoded_bytes = base64.urlsafe_b64decode(payload_segment + padding)
        parsed = json.loads(decoded_bytes.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _ensure_not_secret_supabase_key(key: str, label: str = "API key Supabase") -> None:
    """Reject secret or service_role keys before any client initialization."""
    cleaned = (key or "").strip()
    if not cleaned:
        return
    if cleaned.startswith("sb_secret_") or "service_role" in cleaned.lower():
        raise ValueError(
            "Keamanan ditolak: Dilarang menggunakan secret key ('sb_secret_*') atau 'service_role' key pada aplikasi desktop Turnamen.in."
        )
    if not cleaned.startswith("sb_publishable_") and _JWT_PATTERN.match(cleaned):
        claims = decode_jwt_payload_unverified(cleaned)
        role_claim = str(claims.get("role") or "").strip().lower()
        if role_claim == "service_role":
            raise ValueError(
                f"Keamanan ditolak: {label} terdeteksi memiliki klaim role 'service_role'. Gunakan publishable key atau legacy key dengan role 'anon'."
            )
        if role_claim and role_claim != "anon":
            raise ValueError(
                f"Keamanan ditolak: {label} memiliki klaim role '{role_claim}' yang tidak diizinkan untuk klien desktop."
            )


def resolve_supabase_api_key(
    publishable_key: str = "",
    anon_key: str = "",
) -> str:
    """Resolve active Supabase API key (publishable key preferred, legacy anon key fallback)."""
    pub = (publishable_key or "").strip()
    anon = (anon_key or "").strip()

    _ensure_not_secret_supabase_key(pub, "SUPABASE_PUBLISHABLE_KEY")
    _ensure_not_secret_supabase_key(anon, "SUPABASE_ANON_KEY")

    if pub and anon and pub != anon:
        raise ValueError(
            "Konfigurasi Supabase ambigu: SUPABASE_PUBLISHABLE_KEY dan SUPABASE_ANON_KEY keduanya diisi dengan nilai berbeda. "
            "Gunakan salah satu saja (prioritaskan SUPABASE_PUBLISHABLE_KEY)."
        )
    return pub or anon


def validate_supabase_config_values(
    supabase_url: str,
    supabase_key: str = "",
    *,
    publishable_key: str = "",
    anon_key: str = "",
) -> str:
    """Validate Supabase URL and client API key (publishable or legacy anon) without network calls."""
    url = (supabase_url or "").strip()
    explicit_key = (supabase_key or "").strip()

    if explicit_key:
        _ensure_not_secret_supabase_key(explicit_key)
        if publishable_key or anon_key:
            pair_key = resolve_supabase_api_key(publishable_key, anon_key)
            if pair_key and pair_key != explicit_key:
                raise ValueError(
                    "Konfigurasi Supabase ambigu: nilai API key yang diberikan tidak konsisten."
                )
        key = explicit_key
    else:
        key = resolve_supabase_api_key(publishable_key, anon_key)

    if not url or not key:
        raise ValueError(
            "APP_MODE=supabase membutuhkan SUPABASE_URL serta SUPABASE_PUBLISHABLE_KEY "
            "(atau legacy SUPABASE_ANON_KEY) pada file .env."
        )

    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""
    if (
        parsed_url.scheme not in ("http", "https")
        or not parsed_url.netloc
        or not hostname
        or ("." not in hostname and hostname not in ("localhost", "127.0.0.1"))
        or url.lower().rstrip("/") in _PLACEHOLDER_URLS
    ):
        raise ValueError(
            "Konfigurasi SUPABASE_URL tidak valid. Gunakan URL proyek Supabase yang benar "
            "(https://<project-ref>.supabase.co)."
        )

    if key.lower() in _PLACEHOLDER_KEYS or key.lower().startswith("your-supabase-"):
        raise ValueError(
            "Konfigurasi key Supabase masih berisi nilai placeholder. "
            "Isi dengan SUPABASE_PUBLISHABLE_KEY ('sb_publishable_...') atau legacy SUPABASE_ANON_KEY."
        )

    _ensure_not_secret_supabase_key(key)

    if key.startswith("sb_publishable_"):
        # Publishable keys are opaque strings, so never force JWT decoding on them.
        if not _PUBLISHABLE_KEY_PATTERN.match(key):
            raise ValueError(
                "Format SUPABASE_PUBLISHABLE_KEY tidak valid. "
                "Gunakan publishable key berformat 'sb_publishable_...' tanpa spasi atau placeholder."
            )
        return key

    if not _JWT_PATTERN.match(key):
        raise ValueError(
            "Format key Supabase tidak valid. Gunakan SUPABASE_PUBLISHABLE_KEY ('sb_publishable_...') "
            "atau legacy 'anon' public JWT ('eyJ...') dari proyek Supabase."
        )

    return key


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
    supabase_publishable_key: str = field(default="", repr=False)
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

    @property
    def supabase_api_key(self) -> str:
        """Consistent active Supabase client API key across the repository."""
        return resolve_supabase_api_key(
            publishable_key=self.supabase_publishable_key,
            anon_key=self.supabase_anon_key,
        )

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

        _ensure_not_secret_supabase_key(self.supabase_publishable_key, "SUPABASE_PUBLISHABLE_KEY")
        _ensure_not_secret_supabase_key(self.supabase_anon_key, "SUPABASE_ANON_KEY")

        if self.is_supabase_mode:
            validate_supabase_config_values(
                self.supabase_url,
                publishable_key=self.supabase_publishable_key,
                anon_key=self.supabase_anon_key,
            )

        if self.log_level.upper() not in VALID_LOG_LEVELS:
            raise ValueError(
                f"LOG_LEVEL tidak valid: '{self.log_level}'. Gunakan salah satu dari {VALID_LOG_LEVELS}."
            )

    def to_safe_dict(self) -> dict[str, Any]:
        """Return configuration dictionary with secrets redacted for logging/UI inspection."""
        pub = (self.supabase_publishable_key or "").strip()
        anon = (self.supabase_anon_key or "").strip()
        keys_conflict = bool(pub and anon and pub != anon)
        supabase_host = (
            (urlparse(self.supabase_url).hostname or "").strip().lower()
            if self.supabase_url
            else ""
        )
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
            "supabase_configured": bool(self.supabase_url and (pub or anon) and not keys_conflict),
            "supabase_host": supabase_host if self.is_supabase_mode else "",
            "secret_key": "***REDACTED***",
            "supabase_publishable_key": "***REDACTED***" if pub else "",
            "supabase_anon_key": "***REDACTED***" if anon else "",
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
        "supabase_publishable_key": os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip(),
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
