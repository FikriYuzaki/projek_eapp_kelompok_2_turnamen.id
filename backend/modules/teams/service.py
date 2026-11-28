"""Service untuk pengelolaan tim esports dan roster pemain."""

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
NAME_LENGTH = (3, 120)
TAG_LENGTH = (2, 6)
REGION_LENGTH = (2, 100)
NICKNAME_LENGTH = (2, 80)
INGAME_ID_LENGTH = (3, 100)


def _validate_length(value: str, field: str, label: str, bounds: tuple[int, int]) -> str:
    low, high = bounds
    if len(value) < low or len(value) > high:
        raise DomainValidationError(
            f"{label} harus terdiri dari {low} hingga {high} karakter.", {"field": field}
        )
    return value


def _require_text_field(raw: Any, field: str, label: str) -> str:
    if not isinstance(raw, str):
        raise DomainValidationError(f"{label} harus berupa teks.", {"field": field})
    return raw.strip()


def _clean_update_text(payload: dict[str, Any], field: str) -> str | None:
    """Return the trimmed value, or None when the field is absent; blank strings are rejected."""
    if field not in payload or payload[field] is None:
        return None
    if not isinstance(payload[field], str):
        raise DomainValidationError(f"Field {field} harus berupa teks.", {"field": field})
    value = payload[field].strip()
    if not value:
        raise DomainValidationError(f"Field {field} tidak boleh kosong.", {"field": field})
    return value


class TeamService:
    """Pengelolaan tim esports dan anggota tim."""

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
        name = _require_text_field(payload.get("name") or "", "name", "Nama tim")
        tag = _require_text_field(payload.get("tag") or "", "tag", "Tag tim").upper()
        game_id = _require_text_field(payload.get("game_id") or "", "game_id", "Game tim")
        raw_region = payload.get("region")
        if raw_region is None:
            region = "Indonesia"
        else:
            region = _require_text_field(raw_region, "region", "Region tim")

        _validate_length(name, "name", "Nama tim", NAME_LENGTH)
        _validate_length(tag, "tag", "Tag tim", TAG_LENGTH)
        _validate_length(region, "region", "Region tim", REGION_LENGTH)
        if not game_id or not self._repo.get_game_by_id(game_id):
            raise DomainValidationError("Game tim tidak valid atau tidak ditemukan.", {"field": "game_id"})

        self._ensure_unique_identity(name=name, tag=tag, exclude_team_id=None)

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
        name = _clean_update_text(payload, "name")
        if name is not None:
            updates["name"] = _validate_length(name, "name", "Nama tim", NAME_LENGTH)
        tag = _clean_update_text(payload, "tag")
        if tag is not None:
            updates["tag"] = _validate_length(tag.upper(), "tag", "Tag tim", TAG_LENGTH)
        region = _clean_update_text(payload, "region")
        if region is not None:
            updates["region"] = _validate_length(region, "region", "Region tim", REGION_LENGTH)

        self._ensure_unique_identity(
            name=updates.get("name"), tag=updates.get("tag"), exclude_team_id=team["id"]
        )

        if not updates:
            return team

        updated = self._repo.update_team(team["id"], updates)
        if not updated:
            raise DomainNotFoundError("Data tim tidak ditemukan.")
        return updated

    def _ensure_unique_identity(
        self, name: str | None, tag: str | None, exclude_team_id: str | None
    ) -> None:
        for existing in self._repo.list_teams():
            if exclude_team_id and existing["id"] == exclude_team_id:
                continue
            if name is not None and existing["name"].lower() == name.lower():
                raise DomainConflictError("Nama tim sudah digunakan.", {"name": name})
            if tag is not None and existing["tag"].upper() == tag.upper():
                raise DomainConflictError("Tag tim sudah digunakan.", {"tag": tag})

    def add_member(
        self, actor: dict[str, Any] | None, team_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "team:add_member")
        team = self.get_team(team_id)
        if user["role"] == ROLE_TEAM_CAPTAIN and team["captain_id"] != user["id"]:
            raise DomainForbiddenError("Kapten hanya dapat menambah anggota ke tim miliknya sendiri.")

        nickname = _require_text_field(payload.get("nickname") or "", "nickname", "Nickname pemain")
        ingame_id = _require_text_field(payload.get("ingame_id") or "", "ingame_id", "ID Game (ingame_id)")
        raw_member_role = payload.get("member_role")
        if raw_member_role is None:
            member_role = "starter"
        else:
            member_role = _require_text_field(raw_member_role, "member_role", "Peran anggota").lower() or "starter"

        _validate_length(nickname, "nickname", "Nickname pemain", NICKNAME_LENGTH)
        _validate_length(ingame_id, "ingame_id", "ID Game (ingame_id)", INGAME_ID_LENGTH)
        if member_role not in VALID_MEMBER_ROLES:
            raise DomainValidationError(
                f"Peran anggota '{member_role}' tidak valid.",
                {"field": "member_role", "valid_roles": list(VALID_MEMBER_ROLES)},
            )

        raw_user_id = payload.get("user_id")
        clean_user_id: str | None = None
        if raw_user_id is not None:
            clean_user_id = _require_text_field(raw_user_id, "user_id", "User ID") or None
            if clean_user_id and not self._repo.get_public_profile_summary(
                clean_user_id, team_id=team["id"], actor_id=user["id"]
            ):
                raise DomainNotFoundError(
                    "Profil pengguna anggota tidak ditemukan.",
                    {"field": "user_id", "user_id": clean_user_id},
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
                "user_id": clean_user_id,
            },
        )
        return member
