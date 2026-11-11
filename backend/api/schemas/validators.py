"""Request body parsing and field validation utilities for Flask REST API."""

from __future__ import annotations

from typing import Any, Iterable
from flask import Request

from backend.core.exceptions import DomainValidationError


def parse_json_body(req: Request, required_fields: Iterable[str] = ()) -> dict[str, Any]:
    """Parse JSON body from Flask request and verify required fields exist."""
    data = req.get_json(silent=True)
    if data is None:
        if list(required_fields):
            raise DomainValidationError(
                "Body request harus berupa JSON yang valid.",
                {"missing_fields": list(required_fields)},
            )
        return {}

    if not isinstance(data, dict):
        raise DomainValidationError("Payload JSON harus berupa objek (key-value).")

    missing = [
        f for f in required_fields if f not in data or data[f] is None or data[f] == ""
    ]
    if missing:
        raise DomainValidationError(
            f"Field wajib belum lengkap: {', '.join(missing)}.",
            {"missing_fields": missing},
        )
    return data
