"""Python Eel Bridge exposing safe runtime and HTTP proxy functions to the Desktop UI.

Owner: Fikri (System Integration & Python Eel Developer)
Architecture Rule:
Do NOT duplicate domain/business logic here. All business requests are forwarded
to the local Flask REST API (`/api/v1/*`).
"""

from __future__ import annotations

import posixpath
import re
import threading
from typing import Any
from urllib.parse import unquote, urlsplit
import requests

from backend.core.config import AppConfig, LOCALHOST_HOST, load_config

_ACTIVE_CONFIG: AppConfig | None = None
_EEL_REGISTERED: bool = False
_SESSION_LOCAL = threading.local()
_ACTIVE_SESSIONS: set[requests.Session] = set()
_ACTIVE_SESSIONS_LOCK = threading.Lock()

ALLOWED_HTTP_METHODS = ("GET", "POST", "PATCH", "PUT", "DELETE")
ALLOWED_BASE_HEADERS = {
    "authorization": "Authorization",
    "content-type": "Content-Type",
    "accept": "Accept",
}
ALLOWED_MOCK_HEADERS = {
    "x-mock-user-id": "X-Mock-User-Id",
    "x-mock-role": "X-Mock-Role",
}
DEFAULT_BRIDGE_TIMEOUT_SECONDS = 8.0
_MAX_PERCENT_DECODE_ROUNDS = 5
_ENCODED_TRAVERSAL_RE = re.compile(r"%(?:2e|2f|5c)", re.IGNORECASE)
_MALFORMED_PERCENT_RE = re.compile(r"%(?![0-9a-fA-F]{2})")


def _get_local_http_session() -> requests.Session:
    """Return a reusable per-thread loopback Session isolated from env proxies."""
    session = getattr(_SESSION_LOCAL, "session", None)
    with _ACTIVE_SESSIONS_LOCK:
        if session is None or session not in _ACTIVE_SESSIONS:
            session = requests.Session()
            session.trust_env = False
            session.proxies = {}
            _ACTIVE_SESSIONS.add(session)
            _SESSION_LOCAL.session = session
    return session


def close_bridge_sessions() -> None:
    """Close all active bridge HTTP sessions during shutdown or test cleanup."""
    with _ACTIVE_SESSIONS_LOCK:
        sessions = list(_ACTIVE_SESSIONS)
        _ACTIVE_SESSIONS.clear()
    if hasattr(_SESSION_LOCAL, "session"):
        delattr(_SESSION_LOCAL, "session")
    for session in sessions:
        try:
            session.close()
        except Exception:
            pass


def _bridge_error(
    message: str,
    code: str = "BRIDGE_CONNECTION_ERROR",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": None,
        "error": {
            "code": code,
            "details": details or {},
        },
    }


def _normalize_bridge_response(raw_payload: Any, status_code: int = 200) -> dict[str, Any]:
    if not isinstance(raw_payload, dict):
        return _bridge_error(
            message="Format respons dari server API lokal tidak sesuai kontrak.",
            code="BRIDGE_INVALID_RESPONSE",
            details={"status_code": status_code},
        )

    success = bool(raw_payload.get("success", 200 <= status_code < 300))
    message = str(
        raw_payload.get("message")
        or ("Operasi berhasil" if success else f"Permintaan gagal (HTTP {status_code}).")
    )
    if success:
        return {
            "success": True,
            "message": message,
            "data": raw_payload.get("data", {}),
            "error": None,
        }

    raw_error = raw_payload.get("error")
    if isinstance(raw_error, dict):
        error_obj = {
            "code": str(raw_error.get("code") or "HTTP_ERROR"),
            "details": raw_error.get("details") if isinstance(raw_error.get("details"), dict) else {},
        }
    else:
        error_obj = {
            "code": "HTTP_ERROR",
            "details": {"status_code": status_code},
        }

    return {
        "success": False,
        "message": message,
        "data": None,
        "error": error_obj,
    }


def _has_control_chars(value: str) -> bool:
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def _has_unsafe_path_state(value: str) -> bool:
    if (
        _ENCODED_TRAVERSAL_RE.search(value)
        or _has_control_chars(value)
        or any(ch in value for ch in ("\\", "@", "#"))
        or "//" in value
    ):
        return True
    segments = value.split("/")
    return "." in segments or ".." in segments


def _normalize_and_validate_endpoint(endpoint: str) -> str | None:
    if not isinstance(endpoint, str):
        return None
    raw = endpoint.strip()
    if not raw:
        return None
    if (
        _has_control_chars(raw)
        or any(ch in raw for ch in ("\\", "@", "#"))
        or "://" in raw
        or raw.startswith("//")
    ):
        return None

    clean = raw if raw.startswith("/") else f"/{raw}"
    if clean == "/api/v1" or clean.startswith(("/api/v1?", "/api/v1#")):
        return None
    if not clean.startswith("/api/v1/"):
        if clean.startswith("/api/v1"):
            return None
        clean = f"/api/v1{clean}"

    parsed = urlsplit(clean)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        return None

    raw_path = parsed.path
    if (
        not raw_path
        or any(ch.isspace() for ch in raw_path)
        or "//" in raw_path
        or _MALFORMED_PERCENT_RE.search(raw_path)
    ):
        return None

    current = raw_path
    for _ in range(_MAX_PERCENT_DECODE_ROUNDS):
        if _has_unsafe_path_state(current):
            return None
        decoded = unquote(current)
        if decoded == current:
            break
        current = decoded
    else:
        if unquote(current) != current:
            return None

    if _has_unsafe_path_state(current):
        return None

    if not current.startswith("/api/v1/") or len(current) <= len("/api/v1/"):
        return None

    norm_path = posixpath.normpath(current)
    if (
        not norm_path.startswith("/api/v1/")
        or len(norm_path) <= len("/api/v1/")
        or norm_path != current.rstrip("/")
    ):
        return None

    if parsed.query:
        if _has_control_chars(parsed.query) or _has_control_chars(unquote(parsed.query)):
            return None

    return clean


def _sanitize_headers(
    headers: dict[str, str] | None,
    is_mock_mode: bool,
) -> dict[str, str]:
    sanitized: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if not isinstance(headers, dict):
        return sanitized

    for raw_key, raw_val in headers.items():
        if not isinstance(raw_key, str) or raw_val is None:
            continue
        key_lower = raw_key.strip().lower()
        val_str = str(raw_val).strip()
        if not val_str or "\r" in val_str or "\n" in val_str:
            continue

        if key_lower in ALLOWED_BASE_HEADERS:
            sanitized[ALLOWED_BASE_HEADERS[key_lower]] = val_str
        elif is_mock_mode and key_lower in ALLOWED_MOCK_HEADERS:
            sanitized[ALLOWED_MOCK_HEADERS[key_lower]] = val_str

    return sanitized


def get_runtime_info_payload(config: AppConfig) -> dict[str, Any]:
    """Return safe runtime metadata for the desktop UI header and profile diagnostics."""
    return {
        "success": True,
        "message": "Informasi runtime aplikasi berhasil diperoleh",
        "data": config.to_safe_dict(),
        "error": None,
    }


def forward_api_request(
    config: AppConfig,
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Forward a validated request from the Eel bridge to the local Flask REST API (`127.0.0.1`)."""
    if config.api_host != LOCALHOST_HOST:
        return _bridge_error(
            message="Konfigurasi host API lokal tidak diizinkan.",
            code="BRIDGE_SECURITY_ERROR",
        )

    if not isinstance(method, str) or not method.strip():
        return _bridge_error(
            message="Metode HTTP tidak valid.",
            code="BRIDGE_INVALID_METHOD",
        )
    normalized_method = method.strip().upper()
    if normalized_method not in ALLOWED_HTTP_METHODS:
        return _bridge_error(
            message=f"Metode HTTP '{normalized_method}' tidak diizinkan melalui bridge.",
            code="BRIDGE_INVALID_METHOD",
            details={"method": normalized_method},
        )

    clean_endpoint = _normalize_and_validate_endpoint(endpoint)
    if not clean_endpoint:
        return _bridge_error(
            message="Endpoint API tidak valid. Hanya path lokal '/api/v1/*' yang diizinkan.",
            code="BRIDGE_INVALID_ENDPOINT",
        )

    url = f"http://{config.api_host}:{config.api_port}{clean_endpoint}"
    req_headers = _sanitize_headers(headers, is_mock_mode=config.is_mock_mode)
    req_json = payload if (payload is not None and normalized_method != "GET") else None
    session = _get_local_http_session()

    try:
        resp = session.request(
            method=normalized_method,
            url=url,
            json=req_json,
            headers=req_headers,
            timeout=DEFAULT_BRIDGE_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.Timeout:
        return _bridge_error(
            message="Permintaan ke server Flask lokal melebihi batas waktu tunggu.",
            code="BRIDGE_TIMEOUT",
            details={"endpoint": clean_endpoint},
        )
    except requests.RequestException:
        return _bridge_error(
            message="Gagal menghubungi server Flask lokal.",
            code="BRIDGE_CONNECTION_ERROR",
            details={"endpoint": clean_endpoint},
        )
    except Exception:
        return _bridge_error(
            message="Terjadi kesalahan internal saat meneruskan permintaan melalui bridge.",
            code="BRIDGE_INTERNAL_ERROR",
            details={"endpoint": clean_endpoint},
        )

    if 300 <= resp.status_code < 400:
        return _bridge_error(
            message="Server API lokal mengembalikan redirect yang tidak diizinkan melalui bridge.",
            code="BRIDGE_REDIRECT_BLOCKED",
            details={"status_code": resp.status_code, "endpoint": clean_endpoint},
        )

    try:
        parsed_json = resp.json()
    except ValueError:
        if resp.status_code >= 400:
            return _bridge_error(
                message=f"Server API lokal mengembalikan status HTTP {resp.status_code}.",
                code="HTTP_ERROR",
                details={"status_code": resp.status_code, "endpoint": clean_endpoint},
            )
        return _bridge_error(
            message="Respons dari server API lokal bukan format JSON yang valid.",
            code="BRIDGE_INVALID_RESPONSE",
            details={"status_code": resp.status_code, "endpoint": clean_endpoint},
        )

    return _normalize_bridge_response(parsed_json, status_code=resp.status_code)


def _get_active_config() -> AppConfig:
    global _ACTIVE_CONFIG
    if _ACTIVE_CONFIG is None:
        _ACTIVE_CONFIG = load_config()
    return _ACTIVE_CONFIG


def eel_get_runtime_info() -> dict[str, Any]:
    """Exposed Eel function returning safe runtime configuration."""
    return get_runtime_info_payload(_get_active_config())


def eel_check_api_health() -> dict[str, Any]:
    """Exposed Eel function checking `/api/v1/health` on the local Flask API."""
    return forward_api_request(_get_active_config(), "GET", "/api/v1/health")


def eel_api_request(
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Exposed Eel function proxying `/api/v1/*` requests to the local Flask API."""
    return forward_api_request(_get_active_config(), method, endpoint, payload, headers)


def register_eel_bridge(config: AppConfig) -> None:
    """Register `@eel.expose` functions once and bind the active runtime config."""
    global _ACTIVE_CONFIG, _EEL_REGISTERED
    _ACTIVE_CONFIG = config
    if _EEL_REGISTERED:
        return

    try:
        import eel
    except ImportError:
        return

    eel.expose(eel_get_runtime_info)
    eel.expose(eel_check_api_health)
    eel.expose(eel_api_request)

    _EEL_REGISTERED = True
