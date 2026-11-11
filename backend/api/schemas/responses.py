"""Standardized JSON response helpers for `/api/v1`.

Owner: Anisa (REST API, Reporting & Testing Developer)
Enforces the exact JSON contract specified in Master Prompt Section 8.
"""

from __future__ import annotations

from typing import Any
from flask import Response, jsonify


def api_success(
    data: Any = None,
    message: str = "Data berhasil diperoleh",
    status_code: int = 200,
) -> tuple[Response, int]:
    """Return a consistent JSON success response."""
    payload = {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
    }
    return jsonify(payload), status_code


def api_error(
    message: str = "Terjadi kesalahan",
    code: str = "VALIDATION_ERROR",
    details: dict[str, Any] | None = None,
    status_code: int = 400,
) -> tuple[Response, int]:
    """Return a consistent JSON error response."""
    payload = {
        "success": False,
        "message": message,
        "error": {
            "code": code,
            "details": details or {},
        },
    }
    return jsonify(payload), status_code
