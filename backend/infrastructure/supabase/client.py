"""Supabase client factory and request-scoped JWT context management for `APP_MODE=supabase`.

SECURITY RULE:
Never configure or distribute `service_role` or `sb_secret_*` keys inside the desktop client.
Always use a publishable key (`sb_publishable_*`) or legacy public `anon` JWT key together with user
authentication and Row Level Security (RLS).
Never store user access tokens on a shared global client instance.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from backend.core.config import (
    AppConfig,
    decode_jwt_payload_unverified,
    validate_supabase_config_values,
)

_CURRENT_ACCESS_TOKEN: ContextVar[str | None] = ContextVar(
    "turnamen_supabase_access_token",
    default=None,
)


def _normalize_jwt_token(token: str | None) -> str | None:
    if not token or not isinstance(token, str):
        return None
    cleaned = token.strip()
    if not cleaned or cleaned.startswith("tok_"):
        return None
    return cleaned


@contextmanager
def use_access_token(access_token: str | None) -> Iterator[None]:
    """Bind a user's Supabase JWT to the current execution context (thread & coroutine safe)."""
    normalized = _normalize_jwt_token(access_token)
    reset_token = _CURRENT_ACCESS_TOKEN.set(normalized)
    try:
        yield
    finally:
        _CURRENT_ACCESS_TOKEN.reset(reset_token)


def bind_request_access_token(access_token: str | None) -> None:
    """Attach a verified Supabase JWT to the current Flask request context (`flask.g`), if active."""
    normalized = _normalize_jwt_token(access_token)
    try:
        from flask import g, has_request_context

        if has_request_context():
            g.supabase_access_token = normalized
    except ImportError:
        pass


def get_current_access_token() -> str | None:
    """Resolve the active caller's Supabase JWT from ContextVar or active Flask HTTP request."""
    ctx_token = _CURRENT_ACCESS_TOKEN.get()
    if ctx_token:
        return ctx_token

    try:
        from flask import g, has_request_context, request

        if has_request_context():
            bound = getattr(g, "supabase_access_token", None)
            if bound:
                return _normalize_jwt_token(bound)
            auth_header = request.headers.get("Authorization", "").strip()
            if auth_header.lower().startswith("bearer "):
                return _normalize_jwt_token(auth_header[7:])
    except ImportError:
        pass

    return None


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Backward-compatible helper for decoding unverified JWT claims."""
    return decode_jwt_payload_unverified(token)


def validate_supabase_credentials(
    supabase_url: str,
    supabase_key: str = "",
    *,
    publishable_key: str = "",
    anon_key: str = "",
) -> str:
    """Validate Supabase URL and client API key without logging or exposing secret values."""
    try:
        return validate_supabase_config_values(
            supabase_url,
            supabase_key,
            publishable_key=publishable_key,
            anon_key=anon_key,
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc


def create_supabase_client(
    config: AppConfig,
    access_token: str | None = None,
) -> Any:
    """Create a stateless Supabase Python SDK client when `APP_MODE=supabase` is configured."""
    resolved_key = validate_supabase_credentials(
        config.supabase_url,
        publishable_key=getattr(config, "supabase_publishable_key", ""),
        anon_key=getattr(config, "supabase_anon_key", ""),
    )

    try:
        from supabase import ClientOptions, create_client
    except ImportError as exc:
        raise RuntimeError(
            "Paket 'supabase' belum terpasang. Jalankan 'pip install -r requirements.txt'."
        ) from exc

    headers: dict[str, str] = {}
    clean_token = _normalize_jwt_token(access_token)
    if clean_token:
        headers["Authorization"] = f"Bearer {clean_token}"

    options = ClientOptions(
        persist_session=False,
        auto_refresh_token=False,
        headers=headers,
    )
    return create_client(config.supabase_url.strip(), resolved_key, options=options)
