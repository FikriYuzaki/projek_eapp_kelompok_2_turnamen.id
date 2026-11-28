"""Unit tests for Wave 6.1 Supabase publishable key compatibility and legacy anon fallback."""

from __future__ import annotations

import base64
import json
import logging
from types import SimpleNamespace
from typing import Any

import pytest

from backend.core import config as config_mod
from backend.core.config import (
    AppConfig,
    load_config,
    resolve_supabase_api_key,
    validate_supabase_config_values,
)
from backend.core.logging_config import SecretRedactingFilter, redact_sensitive_text
from backend.infrastructure.supabase import client as supabase_client_mod
from backend.infrastructure.supabase.client import (
    create_supabase_client,
    validate_supabase_credentials,
)
from desktop.launcher.app_launcher import run_smoke_check


def _build_test_jwt(payload: dict[str, Any]) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode("ascii").rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    return f"{header}.{body}.test_signature_segment_12345"


VALID_URL = "https://example.supabase.co"
VALID_PUBLISHABLE_KEY = "sb_publishable_Wave61TestKey_0123456789"
VALID_ANON_JWT = _build_test_jwt({"role": "anon", "iss": "supabase"})
VALID_USER_JWT_A = _build_test_jwt({"role": "authenticated", "sub": "user-a"})
VALID_USER_JWT_B = _build_test_jwt({"role": "authenticated", "sub": "user-b"})
SERVICE_ROLE_JWT = _build_test_jwt({"role": "service_role", "iss": "supabase"})


def _clear_supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)


def test_valid_publishable_key_supported_in_config_and_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("APP_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", VALID_URL)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", VALID_PUBLISHABLE_KEY)

    cfg = load_config()
    assert cfg.is_supabase_mode is True
    assert cfg.supabase_api_key == VALID_PUBLISHABLE_KEY
    assert validate_supabase_credentials(VALID_URL, VALID_PUBLISHABLE_KEY) == VALID_PUBLISHABLE_KEY


def test_valid_legacy_anon_jwt_fallback_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("APP_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", VALID_URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", VALID_ANON_JWT)

    cfg = load_config()
    assert cfg.supabase_api_key == VALID_ANON_JWT
    assert validate_supabase_credentials(VALID_URL, VALID_ANON_JWT) == VALID_ANON_JWT


def test_empty_publishable_key_falls_back_to_valid_anon_or_fails_when_both_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("APP_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", VALID_URL)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "   ")
    monkeypatch.setenv("SUPABASE_ANON_KEY", VALID_ANON_JWT)

    cfg = load_config()
    assert cfg.supabase_api_key == VALID_ANON_JWT

    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    with pytest.raises(ValueError, match="SUPABASE_PUBLISHABLE_KEY"):
        load_config()

    with pytest.raises(RuntimeError, match="SUPABASE_PUBLISHABLE_KEY"):
        validate_supabase_credentials(VALID_URL, "")


def test_consistent_dual_keys_succeed_and_conflicting_keys_fail_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("APP_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", VALID_URL)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", VALID_PUBLISHABLE_KEY)
    monkeypatch.setenv("SUPABASE_ANON_KEY", VALID_PUBLISHABLE_KEY)

    cfg = load_config()
    assert cfg.supabase_api_key == VALID_PUBLISHABLE_KEY
    assert (
        resolve_supabase_api_key(VALID_PUBLISHABLE_KEY, VALID_PUBLISHABLE_KEY)
        == VALID_PUBLISHABLE_KEY
    )

    # Conflicting values must fail explicitly instead of silently picking one.
    monkeypatch.setenv("SUPABASE_ANON_KEY", VALID_ANON_JWT)
    with pytest.raises(ValueError, match="ambigu|berbeda"):
        load_config()

    with pytest.raises(ValueError, match="ambigu|berbeda"):
        resolve_supabase_api_key(VALID_PUBLISHABLE_KEY, VALID_ANON_JWT)

    with pytest.raises(RuntimeError, match="ambigu|berbeda"):
        validate_supabase_credentials(
            VALID_URL,
            publishable_key=VALID_PUBLISHABLE_KEY,
            anon_key=VALID_ANON_JWT,
        )


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "   ",
        "not-a-url",
        "ftp://example.supabase.co",
        "https://",
        "https://localhost-invalid-nodot",
        "https://your-project-ref.supabase.co",
    ],
)
def test_empty_and_invalid_supabase_urls_rejected(bad_url: str) -> None:
    with pytest.raises(ValueError):
        validate_supabase_config_values(bad_url, VALID_PUBLISHABLE_KEY)

    with pytest.raises(RuntimeError):
        validate_supabase_credentials(bad_url, VALID_PUBLISHABLE_KEY)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "sb_secret_test_key_should_never_be_allowed",
        SERVICE_ROLE_JWT,
        "prefix_service_role_literal",
    ],
)
def test_secret_and_service_role_keys_rejected_everywhere(
    forbidden_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_supabase_env(monkeypatch)

    with pytest.raises(RuntimeError, match="service_role"):
        validate_supabase_credentials(VALID_URL, forbidden_key)

    with pytest.raises(ValueError, match="service_role"):
        load_config(
            overrides={
                "app_mode": "supabase",
                "supabase_url": VALID_URL,
                "supabase_publishable_key": forbidden_key,
            }
        )

    with pytest.raises(ValueError, match="service_role"):
        load_config(
            overrides={
                "app_mode": "mock",
                "supabase_anon_key": forbidden_key,
            }
        )


def test_mock_mode_runs_without_cloud_credentials_and_remains_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_supabase_env(monkeypatch)
    cfg = load_config()
    assert cfg.app_mode == "mock"
    assert cfg.is_mock_mode is True
    assert cfg.supabase_api_key == ""

    summary = run_smoke_check(cfg)
    assert summary["health_ok"] is True
    assert summary["repository_ok"] is True


def test_supabase_mode_fails_with_clear_message_when_credentials_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_supabase_env(monkeypatch)
    monkeypatch.setenv("APP_MODE", "supabase")

    with pytest.raises(ValueError, match="APP_MODE=supabase membutuhkan SUPABASE_URL"):
        load_config()

    incomplete_cfg = AppConfig(app_mode="supabase", supabase_url="", supabase_publishable_key="")
    summary = run_smoke_check(incomplete_cfg)
    assert summary["health_ok"] is False
    assert "SUPABASE_URL" in summary["error"]


def test_sdk_client_accepts_publishable_key_without_jwt_decode_and_preserves_apikey_across_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _forbid_jwt_decode(_token: str) -> dict[str, Any]:
        raise AssertionError("Publishable key must not be decoded as a JWT")

    monkeypatch.setattr(config_mod, "decode_jwt_payload_unverified", _forbid_jwt_decode)
    monkeypatch.setattr(supabase_client_mod, "decode_jwt_payload_unverified", _forbid_jwt_decode)

    cfg = AppConfig(
        app_mode="supabase",
        supabase_url=VALID_URL,
        supabase_publishable_key=VALID_PUBLISHABLE_KEY,
    )

    anon_client = create_supabase_client(cfg)
    assert anon_client.supabase_key == VALID_PUBLISHABLE_KEY
    assert anon_client.options.headers.get("apiKey") == VALID_PUBLISHABLE_KEY
    assert anon_client.postgrest.session.headers.get("apikey") == VALID_PUBLISHABLE_KEY

    client_a = create_supabase_client(cfg, access_token=VALID_USER_JWT_A)
    assert client_a.options.headers.get("apiKey") == VALID_PUBLISHABLE_KEY
    assert client_a.options.headers.get("Authorization") == f"Bearer {VALID_USER_JWT_A}"
    assert client_a.postgrest.session.headers.get("apikey") == VALID_PUBLISHABLE_KEY
    assert client_a.postgrest.session.headers.get("authorization") == f"Bearer {VALID_USER_JWT_A}"
    assert client_a.auth._headers.get("apiKey") == VALID_PUBLISHABLE_KEY
    assert client_a.auth._headers.get("Authorization") == f"Bearer {VALID_USER_JWT_A}"

    # Simulate auth session transition via official SDK callback and verify apiKey stays intact.
    client_a._listen_to_auth_events("SIGNED_IN", SimpleNamespace(access_token=VALID_USER_JWT_B))
    assert client_a.supabase_key == VALID_PUBLISHABLE_KEY
    assert client_a.options.headers.get("apiKey") == VALID_PUBLISHABLE_KEY
    assert client_a.options.headers.get("Authorization") == f"Bearer {VALID_USER_JWT_B}"

    client_a._listen_to_auth_events("SIGNED_OUT", None)
    assert client_a.supabase_key == VALID_PUBLISHABLE_KEY
    assert client_a.options.headers.get("apiKey") == VALID_PUBLISHABLE_KEY

    # Verify create_supabase_client passes resolved publishable key to official create_client().
    captured_calls: list[tuple[str, str, Any]] = []
    import supabase as official_supabase

    def _spy_create_client(url: str, key: str, options: Any = None) -> str:
        captured_calls.append((url, key, options))
        return "spied-client"

    monkeypatch.setattr(official_supabase, "create_client", _spy_create_client)
    res = create_supabase_client(cfg, access_token=VALID_USER_JWT_A)
    assert res == "spied-client"
    assert captured_calls[0][0] == VALID_URL
    assert captured_calls[0][1] == VALID_PUBLISHABLE_KEY
    assert captured_calls[0][2].headers == {"Authorization": f"Bearer {VALID_USER_JWT_A}"}


def test_keys_and_tokens_are_redacted_from_safe_dict_and_logs() -> None:
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url=VALID_URL,
        supabase_publishable_key=VALID_PUBLISHABLE_KEY,
    )
    safe = cfg.to_safe_dict()
    assert safe["supabase_configured"] is True
    assert safe["supabase_publishable_key"] == "***REDACTED***"
    assert VALID_PUBLISHABLE_KEY not in str(safe)

    sample_log = (
        f"apikey={VALID_PUBLISHABLE_KEY} Authorization=Bearer {VALID_USER_JWT_A} "
        f"sb_secret_raw_leak"
    )
    redacted = redact_sensitive_text(sample_log, extra_secrets=(VALID_PUBLISHABLE_KEY,))
    assert VALID_PUBLISHABLE_KEY not in redacted
    assert VALID_USER_JWT_A not in redacted
    assert "sb_secret_raw_leak" not in redacted

    filt = SecretRedactingFilter(extra_secrets=(VALID_PUBLISHABLE_KEY,))
    record = logging.LogRecord(
        name="turnamen_in",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Connected with %s and Bearer %s",
        args=(VALID_PUBLISHABLE_KEY, VALID_USER_JWT_A),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert VALID_PUBLISHABLE_KEY not in record.getMessage()
    assert VALID_USER_JWT_A not in record.getMessage()
