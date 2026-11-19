"""Unit tests for Flask REST API request validators."""

from __future__ import annotations

import pytest
from flask import Flask, request

from backend.api.schemas.validators import parse_json_body
from backend.core.exceptions import DomainValidationError


def test_parse_json_body_rejects_whitespace_only_required_field(app: Flask) -> None:
    with app.test_request_context(
        "/api/v1/tournaments",
        method="POST",
        json={"title": "   ", "game_id": "g1", "start_date": "2026-12-01T10:00:00+07:00"},
    ):
        with pytest.raises(DomainValidationError) as exc_info:
            parse_json_body(request, required_fields=("title", "game_id", "start_date"))

    assert exc_info.value.details["missing_fields"] == ["title"]


def test_parse_json_body_rejects_malformed_json_even_without_required_fields(app: Flask) -> None:
    with app.test_request_context(
        "/api/v1/tournaments/tour-1",
        method="PATCH",
        data="{invalid-json",
        content_type="application/json",
    ):
        with pytest.raises(DomainValidationError, match="JSON yang valid"):
            parse_json_body(request)


def test_parse_json_body_allows_empty_body_and_zero_values(app: Flask) -> None:
    with app.test_request_context("/api/v1/tournaments/tour-1/bracket/generate", method="POST"):
        assert parse_json_body(request) == {}

    with app.test_request_context(
        "/api/v1/matches/m1/result",
        method="PATCH",
        json={"score_a": 2, "score_b": 0},
    ):
        parsed = parse_json_body(request, required_fields=("score_a", "score_b"))
        assert parsed == {"score_a": 2, "score_b": 0}
