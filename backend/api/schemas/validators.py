"""Request body parsing and field validation utilities for Flask REST API."""

from __future__ import annotations

from typing import Any, Iterable
from flask import Request

from backend.core.exceptions import DomainValidationError


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def parse_json_body(req: Request, required_fields: Iterable[str] = ()) -> dict[str, Any]:
    """Parse JSON body from Flask request and verify required fields exist."""
    required = tuple(required_fields)
    raw_body = req.get_data(cache=True, as_text=True).strip()
    data = req.get_json(silent=True)

    if data is None:
        if raw_body or required:
            details = {"missing_fields": list(required)} if required else {}
            raise DomainValidationError(
                "Body request harus berupa JSON yang valid.",
                details,
            )
        return {}

    if not isinstance(data, dict):
        raise DomainValidationError("Payload JSON harus berupa objek (key-value).")

    missing = [f for f in required if f not in data or _is_missing(data[f])]
    if missing:
        raise DomainValidationError(
            f"Field wajib belum lengkap: {', '.join(missing)}.",
            {"missing_fields": missing},
        )
    return data
