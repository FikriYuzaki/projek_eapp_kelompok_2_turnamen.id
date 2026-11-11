"""Shared Pytest fixtures for Turnamen.in unit and integration tests."""

from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient

from backend.app import create_app
from backend.core.config import AppConfig, load_config
from backend.repositories.mock.mock_repository import MockDataStoreRepository


@pytest.fixture()
def mock_config() -> AppConfig:
    """Return a clean `AppConfig` forced to `APP_MODE=mock`."""
    return load_config(overrides={"app_mode": "mock", "api_host": "127.0.0.1", "api_port": 5000})


@pytest.fixture()
def mock_repo() -> MockDataStoreRepository:
    """Return a freshly seeded `MockDataStoreRepository` instance for each test."""
    return MockDataStoreRepository()


@pytest.fixture()
def app(mock_config: AppConfig, mock_repo: MockDataStoreRepository) -> Flask:
    """Create a Flask application wired to an isolated `MockDataStoreRepository`."""
    flask_app = create_app(config=mock_config, repository=mock_repo)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return a Flask test client for `/api/v1/*` endpoint testing."""
    return app.test_client()
