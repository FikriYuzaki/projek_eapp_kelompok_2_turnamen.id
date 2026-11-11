"""Team and roster management service.

Owner: Adriel (Tournament & Match System Developer)
"""

from __future__ import annotations

from typing import Any

from backend.contracts.dtos import ROLE_TEAM_CAPTAIN
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.auth.permissions import require_permission
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol

VALID_MEMBER_ROLES = ("captain", "starter", "substitute", "coach")


class TeamService:
    """Application service for managing esports teams and player rosters."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def list_teams(self, game_id: str | None = None) -> list[dict[str, Any]]:
        return self._repo.list_teams(game_id=game_id)

    def get_team(self, team_id: str) -> dict[str, Any]:
        team = self._repo.get_team_by_id(team_id)
        if not team:
            raise DomainNotFoundError("Data tim tidak ditemukan.", {"team_id": team_id})
        return team

    def create_team(self, actor: dict[str, Any] | None, payload: dict[str, Any]) -> dict[str, Any]:
        user = require_permission(actor, "team:create")
        name = str(payload.get("name") or "").strip()
        tag = str(payload.get("tag") or "").strip().upper()
        game_id = str(payload.get("game_id") or "").strip()
        region = str(payload.get("region") or "Indonesia").strip()

        if len(name) < 3:
            raise DomainValidationError("Nama tim minimal terdiri dari 3 karakter.", {"field": "name"})
        if len(tag) < 2 or len(tag) > 6:
            raise DomainValidationError("Tag tim harus terdiri dari 2 hingga 6 karakter.", {"field": "tag"})
        if not game_id or not self._repo.get_game_by_id(game_id):
            raise DomainValidationError("Game tim tidak valid atau tidak ditemukan.", {"field": "game_id"})

        for existing in self._repo.list_teams():
            if existing["name"].lower() == name.lower():
                raise DomainConflictError("Nama tim sudah digunakan.", {"name": name})
            if existing["tag"].upper() == tag:
                raise DomainConflictError("Tag tim sudah digunakan.", {"tag": tag})

        created = self._repo.create_team(
            {
                "name": name,
                "tag": tag,
                "game_id": game_id,
                "captain_id": user["id"],
                "region": region,
                "is_verified": True,
            }
        )
        return created

    def update_team(
        self, actor: dict[str, Any] | None, team_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "team:update")
        team = self.get_team(team_id)
        if user["role"] == ROLE_TEAM_CAPTAIN and team["captain_id"] != user["id"]:
            raise DomainForbiddenError("Kapten hanya dapat mengubah tim miliknya sendiri.")

        updates: dict[str, Any] = {}
        if "name" in payload and payload["name"]:
            updates["name"] = str(payload["name"]).strip()
        if "tag" in payload and payload["tag"]:
            updates["tag"] = str(payload["tag"]).strip().upper()
        if "region" in payload and payload["region"]:
            updates["region"] = str(payload["region"]).strip()

        updated = self._repo.update_team(team["id"], updates)
        if not updated:
            raise DomainNotFoundError("Data tim tidak ditemukan.")
        return updated

    def add_member(
        self, actor: dict[str, Any] | None, team_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "team:add_member")
        team = self.get_team(team_id)
        if user["role"] == ROLE_TEAM_CAPTAIN and team["captain_id"] != user["id"]:
            raise DomainForbiddenError("Kapten hanya dapat menambah anggota ke tim miliknya sendiri.")

        nickname = str(payload.get("nickname") or "").strip()
        ingame_id = str(payload.get("ingame_id") or "").strip()
        member_role = str(payload.get("member_role") or "starter").strip().lower()

        if len(nickname) < 2:
            raise DomainValidationError("Nickname pemain wajib diisi.", {"field": "nickname"})
        if len(ingame_id) < 3:
            raise DomainValidationError("ID Game (ingame_id) wajib diisi.", {"field": "ingame_id"})
        if member_role not in VALID_MEMBER_ROLES:
            raise DomainValidationError(
                f"Peran anggota '{member_role}' tidak valid.",
                {"valid_roles": list(VALID_MEMBER_ROLES)},
            )

        existing_members = self._repo.list_team_members(team["id"])
        for m in existing_members:
            if m["ingame_id"].lower() == ingame_id.lower():
                raise DomainConflictError(
                    "ID Game tersebut sudah terdaftar di dalam tim ini.",
                    {"ingame_id": ingame_id},
                )

        member = self._repo.add_team_member(
            team["id"],
            {
                "nickname": nickname,
                "ingame_id": ingame_id,
                "member_role": member_role,
                "user_id": payload.get("user_id"),
            },
        )
        return member
