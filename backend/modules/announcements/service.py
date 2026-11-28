"""Tournament announcements service.

Owner: Anisa (REST API, Reporting & Testing Developer)
"""

from __future__ import annotations

from typing import Any

from backend.contracts.dtos import (
    ANNOUNCEMENT_PRIORITIES,
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
)
from backend.core.exceptions import (
    DomainForbiddenError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.auth.permissions import is_tournament_manager, require_permission
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol


TITLE_MIN_LENGTH = 4
TITLE_MAX_LENGTH = 180
CONTENT_MIN_LENGTH = 5


def _require_str_field(payload: dict[str, Any], field: str, label: str, default: str | None = None) -> str:
    raw = payload.get(field)
    if raw is None:
        if default is not None:
            return default
        return ""
    if not isinstance(raw, str):
        raise DomainValidationError(f"{label} harus berupa teks.", {"field": field})
    return raw.strip()


class AnnouncementService:
    """Application service for reading and publishing tournament announcements."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def list_announcements(
        self, tournament_id: str, actor: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )
        if tournament.get("status") == "draft" and not is_tournament_manager(
            self._repo, actor, tournament
        ):
            return []
        return self._repo.list_announcements_by_tournament(tournament["id"])

    def create_announcement(
        self, actor: dict[str, Any] | None, tournament_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "announcement:create")
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )

        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat membuat pengumuman pada turnamen miliknya."
            )
        if user["role"] == ROLE_COMMITTEE and not self._repo.is_staff_assigned(
            tournament["id"], user["id"]
        ):
            raise DomainForbiddenError(
                "Panitia hanya dapat membuat pengumuman pada turnamen yang ditugaskan."
            )

        title = _require_str_field(payload, "title", "Judul pengumuman")
        content = _require_str_field(payload, "content", "Isi pengumuman")
        priority = _require_str_field(payload, "priority", "Prioritas pengumuman", default="normal").lower()
        raw_pinned = payload.get("is_pinned", False)
        if not isinstance(raw_pinned, bool):
            raise DomainValidationError(
                "Field is_pinned harus berupa boolean (true/false).",
                {"field": "is_pinned"},
            )
        is_pinned = raw_pinned

        if len(title) < TITLE_MIN_LENGTH or len(title) > TITLE_MAX_LENGTH:
            raise DomainValidationError(
                f"Judul pengumuman harus terdiri dari {TITLE_MIN_LENGTH} hingga {TITLE_MAX_LENGTH} karakter.",
                {"field": "title"},
            )
        if len(content) < CONTENT_MIN_LENGTH:
            raise DomainValidationError(
                f"Isi pengumuman minimal terdiri dari {CONTENT_MIN_LENGTH} karakter.",
                {"field": "content"},
            )
        if priority not in ANNOUNCEMENT_PRIORITIES:
            raise DomainValidationError(
                f"Prioritas pengumuman '{priority}' tidak valid.",
                {"valid_priorities": list(ANNOUNCEMENT_PRIORITIES)},
            )

        created = self._repo.create_announcement(
            {
                "tournament_id": tournament["id"],
                "author_id": user["id"],
                "title": title,
                "content": content,
                "priority": priority,
                "is_pinned": is_pinned,
            }
        )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="announcement",
            entity_id=created["id"],
            action="ANNOUNCEMENT_PUBLISHED",
            details={"title": title, "priority": priority},
        )
        return created
