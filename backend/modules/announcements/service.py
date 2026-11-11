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
from backend.modules.auth.permissions import require_permission
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol


class AnnouncementService:
    """Application service for reading and publishing tournament announcements."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def list_announcements(self, tournament_id: str) -> list[dict[str, Any]]:
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )
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

        title = str(payload.get("title") or "").strip()
        content = str(payload.get("content") or "").strip()
        priority = str(payload.get("priority") or "normal").strip().lower()
        is_pinned = bool(payload.get("is_pinned", False))

        if len(title) < 4:
            raise DomainValidationError(
                "Judul pengumuman minimal terdiri dari 4 karakter.", {"field": "title"}
            )
        if len(content) < 5:
            raise DomainValidationError(
                "Isi pengumuman minimal terdiri dari 5 karakter.", {"field": "content"}
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
