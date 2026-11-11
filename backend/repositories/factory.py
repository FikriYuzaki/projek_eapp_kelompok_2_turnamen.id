"""Repository factory selecting Mock or Supabase repository based on `APP_MODE`."""

from __future__ import annotations

from backend.core.config import AppConfig
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository

_SHARED_MOCK_REPO: MockDataStoreRepository | None = None


def get_repository(config: AppConfig, fresh_mock: bool = False) -> DataStoreRepositoryProtocol:
    """Return the active repository implementation for the given `AppConfig`."""
    global _SHARED_MOCK_REPO
    if config.is_mock_mode:
        if fresh_mock or _SHARED_MOCK_REPO is None:
            _SHARED_MOCK_REPO = MockDataStoreRepository()
        return _SHARED_MOCK_REPO
    return SupabaseDataStoreRepository(config)
