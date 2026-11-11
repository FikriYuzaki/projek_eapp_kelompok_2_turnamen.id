"""Unit tests for configuration, secret redaction, and mock repository consistency."""

from __future__ import annotations

import pytest

from backend.core.config import load_config
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_repository import MockDataStoreRepository


def test_default_config_is_mock_mode_and_localhost() -> None:
    cfg = load_config(overrides={"app_mode": "mock"})
    assert cfg.app_mode == "mock"
    assert cfg.is_mock_mode is True
    assert cfg.is_supabase_mode is False
    assert cfg.api_host == "127.0.0.1"
    assert cfg.eel_host == "127.0.0.1"


def test_safe_dict_redacts_secrets() -> None:
    cfg = load_config(
        overrides={
            "app_mode": "mock",
            "secret_key": "super-secret-value",
            "supabase_anon_key": "anon-key-value",
        }
    )
    safe = cfg.to_safe_dict()
    assert safe["secret_key"] == "***REDACTED***"
    assert safe["supabase_anon_key"] == "***REDACTED***"
    assert "super-secret-value" not in str(safe)


def test_supabase_mode_requires_credentials() -> None:
    with pytest.raises(ValueError, match="APP_MODE=supabase membutuhkan"):
        load_config(
            overrides={
                "app_mode": "supabase",
                "supabase_url": "",
                "supabase_anon_key": "",
            }
        )


def test_mock_repository_implements_protocol_and_has_consistent_seed(
    mock_repo: MockDataStoreRepository,
) -> None:
    assert isinstance(mock_repo, DataStoreRepositoryProtocol)

    games = mock_repo.list_games()
    tournaments = mock_repo.list_tournaments()
    teams = mock_repo.list_teams()
    matches = mock_repo.list_matches_by_tournament("33333333-3333-4333-8333-333333333301")
    announcements = mock_repo.list_announcements_by_tournament(
        "33333333-3333-4333-8333-333333333301"
    )

    assert len(games) >= 3
    assert len(tournaments) >= 2
    assert len(teams) >= 8
    assert len(matches) == 7  # 4 QF + 2 SF + 1 Final
    assert len(announcements) >= 1
