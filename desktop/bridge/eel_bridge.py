"""Python Eel Bridge exposing safe runtime and HTTP proxy functions to the Desktop UI.

Owner: Fikri (System Integration & Python Eel Developer)
Architecture Rule:
Do NOT duplicate domain/business logic here. All business requests are forwarded
to the local Flask REST API (`/api/v1/*`).
"""

from __future__ import annotations

from typing import Any
import requests

from backend.core.config import AppConfig

_ACTIVE_CONFIG: AppConfig | None = None
_EEL_REGISTERED: bool = False


def get_runtime_info_payload(config: AppConfig) -> dict[str, Any]:
    """Return safe runtime metadata for the desktop UI header and profile diagnostics."""
    return {
        "success": True,
        "message": "Informasi runtime aplikasi berhasil diperoleh",
        "data": config.to_safe_dict(),
    }


def forward_api_request(
    config: AppConfig,
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Forward a request from the Eel bridge to the local Flask REST API (`127.0.0.1`)."""
    clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    if not clean_endpoint.startswith("/api/v1"):
        clean_endpoint = f"/api/v1{clean_endpoint}"
    url = f"http://{config.api_host}:{config.api_port}{clean_endpoint}"

    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            json=payload,
            headers=req_headers,
            timeout=5.0,
        )
        return resp.json()
    except Exception as exc:
        return {
            "success": False,
            "message": f"Gagal menghubungi server Flask lokal: {exc}",
            "error": {"code": "BRIDGE_CONNECTION_ERROR", "details": {"url": url}},
        }


def register_eel_bridge(config: AppConfig) -> None:
    """Register `@eel.expose` functions once when launching the desktop window."""
    global _ACTIVE_CONFIG, _EEL_REGISTERED
    _ACTIVE_CONFIG = config
    if _EEL_REGISTERED:
        return

    try:
        import eel
    except ImportError:
        return

    @eel.expose
    def eel_get_runtime_info() -> dict[str, Any]:
        cfg = _ACTIVE_CONFIG or config
        return get_runtime_info_payload(cfg)

    @eel.expose
    def eel_check_api_health() -> dict[str, Any]:
        cfg = _ACTIVE_CONFIG or config
        return forward_api_request(cfg, "GET", "/api/v1/health")

    @eel.expose
    def eel_api_request(
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        cfg = _ACTIVE_CONFIG or config
        return forward_api_request(cfg, method, endpoint, payload, headers)

    _EEL_REGISTERED = True
