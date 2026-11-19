"""Unit tests for AnnouncementService RBAC, validation, and activity logging."""

from __future__ import annotations

import pytest

from backend.contracts.dtos import ROLE_COMMITTEE, ROLE_ORGANIZER
from backend.core.exceptions import (
    DomainForbiddenError,
    DomainNotFoundError,
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.modules.announcements.service import AnnouncementService
from backend.repositories.mock.mock_repository import MockDataStoreRepository

MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"


def test_list_announcements_and_not_found(mock_repo: MockDataStoreRepository) -> None:
    svc = AnnouncementService(mock_repo)
    items = svc.list_announcements(MLBB_TOURNAMENT_ID)
    assert len(items) >= 1

    with pytest.raises(DomainNotFoundError):
        svc.list_announcements("00000000-0000-4000-8000-000000000000")


def test_create_announcement_enforces_rbac_and_ownership(
    mock_repo: MockDataStoreRepository,
) -> None:
    svc = AnnouncementService(mock_repo)
    payload = {"title": "Jadwal Technical Meeting", "content": "Dimulai pukul 19.00 WIB."}

    with pytest.raises(DomainUnauthorizedError):
        svc.create_announcement(None, MLBB_TOURNAMENT_ID, payload)

    player = mock_repo.get_profile_by_email("player@turnamen.in")
    captain = mock_repo.get_profile_by_email("captain@turnamen.in")
    with pytest.raises(DomainForbiddenError):
        svc.create_announcement(player, MLBB_TOURNAMENT_ID, payload)
    with pytest.raises(DomainForbiddenError):
        svc.create_announcement(captain, MLBB_TOURNAMENT_ID, payload)

    other_organizer = {
        "id": "99999999-9999-4999-8999-999999999901",
        "role": ROLE_ORGANIZER,
        "is_active": True,
    }
    with pytest.raises(DomainForbiddenError, match="miliknya"):
        svc.create_announcement(other_organizer, MLBB_TOURNAMENT_ID, payload)

    unassigned_committee = {
        "id": "99999999-9999-4999-8999-999999999902",
        "role": ROLE_COMMITTEE,
        "is_active": True,
    }
    with pytest.raises(DomainForbiddenError, match="ditugaskan"):
        svc.create_announcement(unassigned_committee, MLBB_TOURNAMENT_ID, payload)


def test_create_announcement_succeeds_for_authorized_roles_and_logs_activity(
    mock_repo: MockDataStoreRepository,
) -> None:
    svc = AnnouncementService(mock_repo)
    committee = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert committee is not None

    created = svc.create_announcement(
        committee,
        MLBB_TOURNAMENT_ID,
        {
            "title": "Jadwal Semifinal",
            "content": "Seluruh tim wajib check-in 30 menit sebelum tanding.",
            "priority": "important",
            "is_pinned": True,
        },
    )
    assert created["title"] == "Jadwal Semifinal"
    assert created["priority"] == "important"
    assert created["is_pinned"] is True
    assert created["author_id"] == committee["id"]

    logs = mock_repo.list_activity_logs(MLBB_TOURNAMENT_ID)
    assert any(
        log["action"] == "ANNOUNCEMENT_PUBLISHED" and log["entity_id"] == created["id"]
        for log in logs
    )


def test_create_announcement_validates_fields_and_is_pinned_type(
    mock_repo: MockDataStoreRepository,
) -> None:
    svc = AnnouncementService(mock_repo)
    organizer = mock_repo.get_profile_by_email("organizer@turnamen.in")
    assert organizer is not None

    with pytest.raises(DomainValidationError, match="Judul pengumuman"):
        svc.create_announcement(
            organizer, MLBB_TOURNAMENT_ID, {"title": "Hai", "content": "Isi valid sekali."}
        )

    with pytest.raises(DomainValidationError, match="Isi pengumuman"):
        svc.create_announcement(
            organizer, MLBB_TOURNAMENT_ID, {"title": "Judul Valid", "content": "Hi"}
        )

    with pytest.raises(DomainValidationError, match="Prioritas"):
        svc.create_announcement(
            organizer,
            MLBB_TOURNAMENT_ID,
            {"title": "Judul Valid", "content": "Isi pengumuman valid.", "priority": "critical"},
        )

    with pytest.raises(DomainValidationError, match="is_pinned"):
        svc.create_announcement(
            organizer,
            MLBB_TOURNAMENT_ID,
            {
                "title": "Judul Valid",
                "content": "Isi pengumuman valid.",
                "is_pinned": "false",
            },
        )
