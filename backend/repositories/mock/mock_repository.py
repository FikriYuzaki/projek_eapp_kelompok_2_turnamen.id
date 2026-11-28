"""In-memory mock repository implementing `DataStoreRepositoryProtocol`."""

from __future__ import annotations

import copy
import hashlib
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.contracts.dtos import (
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_CAPTAIN,
    TOURNAMENT_STATUSES,
)
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.matches.bracket_engine import (
    parse_best_of,
    validate_bracket_graph,
    validate_match_score,
)
from backend.modules.tournaments.artwork_validator import (
    build_mock_artwork_public_url,
    is_valid_artwork_storage_path,
)
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_data import build_initial_mock_store

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MockDataStoreRepository(DataStoreRepositoryProtocol):
    """Thread-safe in-memory repository for `APP_MODE=mock` and automated tests."""

    is_supabase_mode: bool = False

    def __init__(self) -> None:
        self._store: dict[str, Any] = build_initial_mock_store()
        self._store.setdefault("match_submission_requests", [])
        self._store.setdefault("game_artwork_overrides", {})
        self._store.setdefault("game_artwork_blobs", {})
        self._registration_lock = threading.RLock()
        self._tx_lock = self._registration_lock

    def reset_to_seed(self) -> None:
        """Reset all in-memory tables back to the initial demo seed state."""
        with self._registration_lock:
            self._store = build_initial_mock_store()
            self._store.setdefault("match_submission_requests", [])
            self._store["game_artwork_overrides"] = {}
            self._store["game_artwork_blobs"] = {}

    def list_profiles(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(p) for p in self._store["profiles"]]

    def get_profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        for p in self._store["profiles"]:
            if p["id"] == profile_id:
                return copy.deepcopy(p)
        return None

    def get_public_profile_summary(
        self,
        profile_id: str,
        team_id: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any] | None:
        actor = next(
            (p for p in self._store["profiles"] if p["id"] == actor_id and p.get("is_active", True)),
            None,
        )
        if not actor:
            raise DomainForbiddenError("Autentikasi diperlukan untuk melihat ringkasan profil.")

        if actor.get("role") == ROLE_SUPER_ADMIN:
            pass
        elif actor.get("role") == ROLE_TEAM_CAPTAIN:
            if not team_id:
                raise DomainForbiddenError(
                    "Team Captain wajib menyertakan team_id miliknya untuk lookup anggota."
                )
            team = next((t for t in self._store["teams"] if t["id"] == team_id), None)
            if not team or team.get("captain_id") != actor["id"]:
                raise DomainForbiddenError(
                    "Team Captain hanya dapat mencari profil anggota untuk tim miliknya sendiri."
                )
        else:
            raise DomainForbiddenError(
                "Hanya Super Admin atau Team Captain pemilik tim yang dapat melihat ringkasan profil anggota."
            )

        for p in self._store["profiles"]:
            if p["id"] == profile_id and p.get("is_active", True):
                return {
                    "id": p["id"],
                    "username": p["username"],
                    "full_name": p["full_name"],
                    "avatar_url": p.get("avatar_url"),
                }
        return None

    def get_profile_by_auth_user_id(self, auth_user_id: str) -> dict[str, Any] | None:
        for p in self._store["profiles"]:
            if p.get("auth_user_id") == auth_user_id:
                return copy.deepcopy(p)
        return None

    def get_profile_by_email(self, email: str) -> dict[str, Any] | None:
        normalized = email.strip().lower()
        for p in self._store["profiles"]:
            if p["email"].lower() == normalized:
                return copy.deepcopy(p)
        return None

    def get_profile_by_username(self, username: str) -> dict[str, Any] | None:
        normalized = username.strip().lower()
        for p in self._store["profiles"]:
            if p["username"].lower() == normalized:
                return copy.deepcopy(p)
        return None

    def create_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        now = _now_iso()
        profile_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": profile_id,
            "auth_user_id": data.get("auth_user_id", profile_id),
            "email": data["email"].strip().lower(),
            "username": data["username"].strip(),
            "full_name": data["full_name"].strip(),
            "role": data.get("role", "player"),
            "phone": data.get("phone"),
            "avatar_url": data.get("avatar_url"),
            "is_active": data.get("is_active", True),
            "password_hash": data.get("password_hash", ""),
            "created_at": now,
            "updated_at": now,
        }
        self._store["profiles"].append(record)
        return copy.deepcopy(record)

    def update_profile(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        for p in self._store["profiles"]:
            if p["id"] == profile_id:
                for key, value in data.items():
                    if key != "id":
                        p[key] = value
                p["updated_at"] = _now_iso()
                return copy.deepcopy(p)
        return None

    def assign_user_role(self, profile_id: str, new_role: str) -> dict[str, Any] | None:
        return self.update_profile(profile_id, {"role": new_role})

    def _enrich_game_with_artwork(self, game: dict[str, Any]) -> dict[str, Any]:
        enriched = copy.deepcopy(game)
        overrides: dict[str, dict[str, Any]] = self._store.get("game_artwork_overrides", {})
        override = overrides.get(str(enriched.get("id") or ""))
        if override and is_valid_artwork_storage_path(override.get("storage_path")):
            storage_path = str(override["storage_path"])
            enriched["custom_artwork_path"] = storage_path
            enriched["custom_artwork_url"] = build_mock_artwork_public_url(storage_path)
            enriched["custom_artwork_mime_type"] = override.get("mime_type")
            enriched["custom_artwork_width"] = override.get("width")
            enriched["custom_artwork_height"] = override.get("height")
            enriched["custom_artwork_updated_at"] = override.get("updated_at")
            enriched["artwork_source"] = "custom"
        else:
            enriched["custom_artwork_path"] = None
            enriched["custom_artwork_url"] = None
            enriched["custom_artwork_mime_type"] = None
            enriched["custom_artwork_width"] = None
            enriched["custom_artwork_height"] = None
            enriched["custom_artwork_updated_at"] = None
            enriched["artwork_source"] = "official"
        return enriched

    def list_games(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        with self._registration_lock:
            return [
                self._enrich_game_with_artwork(g)
                for g in self._store["games"]
                if include_inactive or g.get("is_active", True)
            ]

    def get_game_by_id(self, game_id: str) -> dict[str, Any] | None:
        with self._registration_lock:
            for g in self._store["games"]:
                if g["id"] == game_id or g["slug"] == game_id:
                    return self._enrich_game_with_artwork(g)
        return None

    def create_game(self, data: dict[str, Any]) -> dict[str, Any]:
        slug = str(data.get("slug") or "").strip().lower()
        for existing in self._store["games"]:
            if str(existing.get("slug") or "").strip().lower() == slug:
                raise DomainConflictError("Slug cabang game sudah digunakan.", {"slug": slug})
        now = _now_iso()
        game_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": game_id,
            "slug": slug,
            "name": str(data["name"]).strip(),
            "genre": str(data["genre"]).strip(),
            "platform": str(data.get("platform") or "PC / Mobile").strip(),
            "team_size": int(data.get("team_size", 5)),
            "max_substitutes": int(data.get("max_substitutes", 2)),
            "allow_draw": bool(data.get("allow_draw", False)),
            "default_best_of": int(data.get("default_best_of", 3)),
            "icon_url": data.get("icon_url"),
            "external_rawg_slug": data.get("external_rawg_slug"),
            "is_active": bool(data.get("is_active", True)),
            "created_at": now,
            "updated_at": now,
        }
        self._store["games"].append(record)
        return self._enrich_game_with_artwork(record)

    def update_game(self, game_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if "slug" in data and data["slug"]:
            candidate_slug = str(data["slug"]).strip().lower()
            for existing in self._store["games"]:
                if existing["id"] != game_id and str(existing.get("slug") or "").strip().lower() == candidate_slug:
                    raise DomainConflictError("Slug cabang game sudah digunakan.", {"slug": candidate_slug})
        for g in self._store["games"]:
            if g["id"] == game_id:
                for key, value in data.items():
                    if key not in ("id", "created_at"):
                        g[key] = value
                g["updated_at"] = _now_iso()
                return self._enrich_game_with_artwork(g)
        return None

    def get_game_artwork_override(self, game_id: str) -> dict[str, Any] | None:
        with self._registration_lock:
            row = self._store.get("game_artwork_overrides", {}).get(str(game_id))
            return copy.deepcopy(row) if row else None

    def upsert_game_artwork_override(
        self, game_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        with self._registration_lock:
            now = _now_iso()
            overrides = self._store.setdefault("game_artwork_overrides", {})
            existing = overrides.get(str(game_id))
            record = {
                "id": existing["id"] if existing else str(uuid.uuid4()),
                "game_id": str(game_id),
                "storage_path": str(data["storage_path"]),
                "mime_type": str(data["mime_type"]),
                "file_size_bytes": int(data["file_size_bytes"]),
                "width": data.get("width"),
                "height": data.get("height"),
                "uploaded_by": data.get("uploaded_by"),
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
            }
            overrides[str(game_id)] = record
            return copy.deepcopy(record)

    def delete_game_artwork_override(self, game_id: str) -> dict[str, Any] | None:
        with self._registration_lock:
            overrides = self._store.get("game_artwork_overrides", {})
            removed = overrides.pop(str(game_id), None)
            return copy.deepcopy(removed) if removed else None

    def upload_game_artwork_object(
        self, storage_path: str, file_bytes: bytes, mime_type: str
    ) -> str:
        if not is_valid_artwork_storage_path(storage_path):
            raise DomainValidationError("Path penyimpanan poster tidak valid.", {"storage_path": storage_path})
        with self._registration_lock:
            blobs = self._store.setdefault("game_artwork_blobs", {})
            blobs[storage_path] = (str(mime_type), bytes(file_bytes))
        return storage_path

    def delete_game_artwork_object(self, storage_path: str) -> bool:
        with self._registration_lock:
            blobs = self._store.get("game_artwork_blobs", {})
            return blobs.pop(storage_path, None) is not None

    def get_mock_artwork_blob(self, storage_path: str) -> tuple[str, bytes] | None:
        with self._registration_lock:
            item = self._store.get("game_artwork_blobs", {}).get(storage_path)
            if not item:
                return None
            return str(item[0]), bytes(item[1])

    def list_tournaments(
        self, status: str | None = None, game_id: str | None = None
    ) -> list[dict[str, Any]]:
        items = self._store["tournaments"]
        results: list[dict[str, Any]] = []
        for t in items:
            if status and t["status"] != status:
                continue
            if game_id and t["game_id"] != game_id:
                continue
            enriched = copy.deepcopy(t)
            game = self.get_game_by_id(t["game_id"])
            enriched["game_name"] = game["name"] if game else "Unknown Game"
            regs = self.list_registrations_by_tournament(t["id"])
            enriched["registered_teams_count"] = len(regs)
            enriched["approved_teams_count"] = sum(
                1 for r in regs if r["status"] == "approved"
            )
            results.append(enriched)
        return results

    def get_tournament_by_id(self, tournament_id: str) -> dict[str, Any] | None:
        for t in self._store["tournaments"]:
            if t["id"] == tournament_id or t["slug"] == tournament_id:
                enriched = copy.deepcopy(t)
                game = self.get_game_by_id(t["game_id"])
                enriched["game_name"] = game["name"] if game else "Unknown Game"
                regs = self.list_registrations_by_tournament(t["id"])
                enriched["registered_teams_count"] = len(regs)
                enriched["approved_teams_count"] = sum(
                    1 for r in regs if r["status"] == "approved"
                )
                return enriched
        return None

    def create_tournament(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.get_game_by_id(data["game_id"]):
            raise DomainNotFoundError("Game tidak ditemukan.", {"game_id": data["game_id"]})
        if not self.get_profile_by_id(data["organizer_id"]):
            raise DomainNotFoundError("Profil organizer tidak ditemukan.", {"organizer_id": data["organizer_id"]})

        now = _now_iso()
        tournament_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": tournament_id,
            "slug": data["slug"],
            "title": data["title"],
            "description": data.get("description", ""),
            "game_id": data["game_id"],
            "organizer_id": data["organizer_id"],
            "format": data.get("format", "single_elimination"),
            "status": data.get("status", "draft"),
            "max_teams": int(data.get("max_teams", 8)),
            "best_of": int(data.get("best_of", 3)),
            "allow_draw": bool(data.get("allow_draw", False)),
            "registration_fee": float(data.get("registration_fee", 0.0)),
            "prize_pool": float(data.get("prize_pool", 0.0)),
            "rules": data.get("rules", ""),
            "venue": data.get("venue", "Online"),
            "registration_start": data.get("registration_start"),
            "registration_end": data.get("registration_end"),
            "start_date": data["start_date"],
            "end_date": data.get("end_date"),
            "banner_url": data.get("banner_url"),
            "created_at": now,
            "updated_at": now,
        }
        self._store["tournaments"].append(record)
        return self.get_tournament_by_id(tournament_id) or copy.deepcopy(record)

    def update_tournament(
        self, tournament_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        if "game_id" in data and not self.get_game_by_id(data["game_id"]):
            raise DomainNotFoundError("Game tidak ditemukan.", {"game_id": data["game_id"]})
        for t in self._store["tournaments"]:
            if t["id"] == tournament_id:
                for key, value in data.items():
                    if key not in ("id", "created_at"):
                        t[key] = value
                t["updated_at"] = _now_iso()
                return self.get_tournament_by_id(tournament_id)
        return None

    def transition_tournament_status(
        self, tournament_id: str, new_status: str
    ) -> dict[str, Any] | None:
        if new_status not in TOURNAMENT_STATUSES:
            raise DomainValidationError(
                f"Status turnamen '{new_status}' tidak valid.", {"field": "status"}
            )
        allowed_transitions = {
            "draft": ("open_registration", "registration_closed", "cancelled"),
            "open_registration": ("draft", "registration_closed", "ongoing", "cancelled"),
            "registration_closed": ("open_registration", "ongoing", "cancelled"),
            "ongoing": ("completed", "cancelled"),
            "completed": (),
            "cancelled": (),
        }
        for t in self._store["tournaments"]:
            if t["id"] == tournament_id:
                current_status = t["status"]
                if current_status != new_status and new_status not in allowed_transitions.get(current_status, ()):
                    raise DomainConflictError(
                        "Transisi status turnamen tidak diizinkan.",
                        {
                            "field": "status",
                            "current_status": current_status,
                            "requested_status": new_status,
                        },
                    )
                if new_status == "completed":
                    matches = [m for m in self._store["matches"] if m["tournament_id"] == tournament_id]
                    validate_bracket_graph(tournament_id, matches)
                t["status"] = new_status
                t["updated_at"] = _now_iso()
                return self.get_tournament_by_id(tournament_id)
        return None

    def delete_tournament(self, tournament_id: str) -> bool:
        deleted = False
        for idx, t in enumerate(self._store["tournaments"]):
            if t["id"] == tournament_id:
                del self._store["tournaments"][idx]
                deleted = True
                break
        if not deleted:
            return False

        # Mirror PostgreSQL ON DELETE CASCADE across all tournament child records.
        deleted_reg_ids = {
            r["id"] for r in self._store["registrations"] if r["tournament_id"] == tournament_id
        }
        deleted_match_ids = {
            m["id"] for m in self._store["matches"] if m["tournament_id"] == tournament_id
        }
        self._store["tournament_staff"] = [
            s for s in self._store["tournament_staff"] if s["tournament_id"] != tournament_id
        ]
        self._store["registrations"] = [
            r for r in self._store["registrations"] if r["tournament_id"] != tournament_id
        ]
        self._store["payments"] = [
            p for p in self._store["payments"] if p["registration_id"] not in deleted_reg_ids
        ]
        self._store["matches"] = [
            m for m in self._store["matches"] if m["tournament_id"] != tournament_id
        ]
        self._store["match_results"] = [
            mr for mr in self._store["match_results"] if mr["match_id"] not in deleted_match_ids
        ]
        self._store["announcements"] = [
            a for a in self._store["announcements"] if a["tournament_id"] != tournament_id
        ]
        self._store["activity_logs"] = [
            log for log in self._store["activity_logs"] if log.get("tournament_id") != tournament_id
        ]
        return True

    def is_staff_assigned(self, tournament_id: str, user_id: str) -> bool:
        return any(
            s["tournament_id"] == tournament_id and s["user_id"] == user_id
            for s in self._store["tournament_staff"]
        )

    def list_assigned_tournament_ids(self, user_id: str) -> list[str]:
        return list(
            dict.fromkeys(
                s["tournament_id"]
                for s in self._store["tournament_staff"]
                if s["user_id"] == user_id
            )
        )

    def list_tournament_staff(self, tournament_id: str) -> list[dict[str, Any]]:
        profiles_by_id = {p["id"]: p for p in self._store["profiles"]}
        items: list[dict[str, Any]] = []
        for s in self._store["tournament_staff"]:
            if s["tournament_id"] != tournament_id:
                continue
            profile = profiles_by_id.get(s["user_id"])
            entry = copy.deepcopy(s)
            entry["username"] = profile["username"] if profile else ""
            entry["full_name"] = profile["full_name"] if profile else ""
            items.append(entry)
        return items

    def list_committee_candidates(self) -> list[dict[str, Any]]:
        candidates = [
            {
                "id": p["id"],
                "username": p["username"],
                "full_name": p["full_name"],
                "role": p["role"],
            }
            for p in self._store["profiles"]
            if p.get("role") == ROLE_COMMITTEE and p.get("is_active", True)
        ]
        candidates.sort(key=lambda c: (c["full_name"].lower(), c["username"].lower()))
        return candidates

    def add_tournament_staff(
        self, tournament_id: str, user_id: str, staff_role: str = "referee"
    ) -> dict[str, Any]:
        if not self.get_tournament_by_id(tournament_id):
            raise DomainNotFoundError("Turnamen tidak ditemukan.", {"tournament_id": tournament_id})
        profile = self.get_profile_by_id(user_id)
        if not profile:
            raise DomainNotFoundError("Profil panitia tidak ditemukan.", {"user_id": user_id})
        if profile.get("role") != ROLE_COMMITTEE or not profile.get("is_active", True):
            raise DomainValidationError(
                "Hanya akun aktif ber-role committee yang dapat ditugaskan sebagai panitia.",
                {"user_id": user_id, "role": profile.get("role")},
            )
        for existing in self._store["tournament_staff"]:
            if existing["tournament_id"] == tournament_id and existing["user_id"] == user_id:
                raise DomainConflictError(
                    "Panitia tersebut sudah ditugaskan pada turnamen ini.",
                    {"tournament_id": tournament_id, "user_id": user_id},
                )
        record = {
            "id": str(uuid.uuid4()),
            "tournament_id": tournament_id,
            "user_id": user_id,
            "staff_role": staff_role,
            "assigned_at": _now_iso(),
        }
        self._store["tournament_staff"].append(record)
        out = copy.deepcopy(record)
        out["username"] = profile["username"]
        out["full_name"] = profile["full_name"]
        return out

    def remove_tournament_staff(self, tournament_id: str, user_id: str) -> bool:
        for idx, s in enumerate(self._store["tournament_staff"]):
            if s["tournament_id"] == tournament_id and s["user_id"] == user_id:
                del self._store["tournament_staff"][idx]
                return True
        return False

    def list_teams(self, game_id: str | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for team in self._store["teams"]:
            if game_id and team["game_id"] != game_id:
                continue
            enriched = copy.deepcopy(team)
            members = self.list_team_members(team["id"])
            enriched["member_count"] = len(members)
            enriched["members"] = members
            game = self.get_game_by_id(team["game_id"])
            enriched["game_name"] = game["name"] if game else "Unknown Game"
            results.append(enriched)
        return results

    def get_team_by_id(self, team_id: str) -> dict[str, Any] | None:
        for team in self._store["teams"]:
            if team["id"] == team_id:
                enriched = copy.deepcopy(team)
                enriched["members"] = self.list_team_members(team_id)
                enriched["member_count"] = len(enriched["members"])
                game = self.get_game_by_id(team["game_id"])
                enriched["game_name"] = game["name"] if game else "Unknown Game"
                return enriched
        return None

    def create_team(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.get_game_by_id(data["game_id"]):
            raise DomainNotFoundError("Game tidak ditemukan.", {"game_id": data["game_id"]})
        if not self.get_profile_by_id(data["captain_id"]):
            raise DomainNotFoundError("Profil kapten tim tidak ditemukan.", {"captain_id": data["captain_id"]})

        now = _now_iso()
        team_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": team_id,
            "name": data["name"].strip(),
            "tag": data["tag"].strip().upper(),
            "game_id": data["game_id"],
            "captain_id": data["captain_id"],
            "logo_url": data.get("logo_url"),
            "region": data.get("region", "Indonesia"),
            "is_verified": bool(data.get("is_verified", False)),
            "created_at": now,
            "updated_at": now,
        }
        self._store["teams"].append(record)
        return self.get_team_by_id(team_id) or copy.deepcopy(record)

    def update_team(self, team_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        for team in self._store["teams"]:
            if team["id"] == team_id:
                for key, value in data.items():
                    if key not in ("id", "created_at"):
                        team[key] = value
                team["updated_at"] = _now_iso()
                return self.get_team_by_id(team_id)
        return None

    def list_team_members(self, team_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(m)
            for m in self._store["team_members"]
            if m["team_id"] == team_id and m.get("is_active", True)
        ]

    def add_team_member(self, team_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if not self.get_team_by_id(team_id):
            raise DomainNotFoundError("Tim tidak ditemukan.", {"team_id": team_id})

        member_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": member_id,
            "team_id": team_id,
            "user_id": data.get("user_id"),
            "nickname": data["nickname"].strip(),
            "ingame_id": data["ingame_id"].strip(),
            "member_role": data.get("member_role", "starter"),
            "is_active": True,
        }
        self._store["team_members"].append(record)
        return copy.deepcopy(record)

    def list_registrations_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        teams_by_id = {t["id"]: t for t in self._store["teams"]}
        for reg in self._store["registrations"]:
            if reg["tournament_id"] == tournament_id:
                enriched = copy.deepcopy(reg)
                team = teams_by_id.get(reg["team_id"])
                enriched["team_name"] = team["name"] if team else "Unknown Team"
                enriched["team_tag"] = team["tag"] if team else "---"
                results.append(enriched)
        results.sort(key=lambda r: (r.get("seed_number") or 999, r.get("registered_at") or ""))
        return results

    def get_registration_by_id(self, registration_id: str) -> dict[str, Any] | None:
        for reg in self._store["registrations"]:
            if reg["id"] == registration_id:
                return copy.deepcopy(reg)
        return None

    def create_registration(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.get_tournament_by_id(data["tournament_id"]):
            raise DomainNotFoundError("Turnamen tidak ditemukan.", {"tournament_id": data["tournament_id"]})
        if not self.get_team_by_id(data["team_id"]):
            raise DomainNotFoundError("Tim tidak ditemukan.", {"team_id": data["team_id"]})

        now = _now_iso()
        reg_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": reg_id,
            "tournament_id": data["tournament_id"],
            "team_id": data["team_id"],
            "registered_by": data["registered_by"],
            "status": data.get("status", "pending"),
            "seed_number": data.get("seed_number"),
            "verified_by": data.get("verified_by"),
            "verified_at": data.get("verified_at"),
            "notes": data.get("notes", ""),
            "registered_at": now,
            "updated_at": now,
        }
        self._store["registrations"].append(record)
        return copy.deepcopy(record)

    def register_team_atomic(
        self, tournament_id: str, team_id: str, registered_by: str, notes: str = ""
    ) -> dict[str, Any]:
        with self._registration_lock:
            tournament = next(
                (t for t in self._store["tournaments"] if t["id"] == tournament_id), None
            )
            if not tournament:
                raise DomainNotFoundError("Turnamen tidak ditemukan.", {"tournament_id": tournament_id})
            team = next((tm for tm in self._store["teams"] if tm["id"] == team_id), None)
            if not team:
                raise DomainNotFoundError("Tim tidak ditemukan.", {"team_id": team_id})
            if tournament["status"] != "open_registration":
                raise DomainConflictError(
                    f"Pendaftaran ditutup untuk turnamen berstatus '{tournament['status']}'.",
                    {"tournament_id": tournament_id, "status": tournament["status"]},
                )
            if team["game_id"] != tournament["game_id"]:
                raise DomainValidationError(
                    "Game yang dimainkan tim tidak sesuai dengan game turnamen."
                )

            tournament_regs = [
                r for r in self._store["registrations"] if r["tournament_id"] == tournament_id
            ]
            existing_for_team = next(
                (r for r in tournament_regs if r["team_id"] == team_id), None
            )
            if existing_for_team and existing_for_team.get("status") != "withdrawn":
                raise DomainConflictError(
                    "Tim ini sudah terdaftar pada turnamen tersebut.",
                    {"tournament_id": tournament_id, "team_id": team_id},
                )

            active_count = sum(
                1 for r in tournament_regs if r.get("status") in ("pending", "approved")
            )
            if active_count >= int(tournament["max_teams"]):
                raise DomainConflictError(
                    f"Kuota turnamen sudah penuh ({tournament['max_teams']} tim).",
                    {"tournament_id": tournament_id, "max_teams": tournament["max_teams"]},
                )

            next_seed = max((int(r.get("seed_number") or 0) for r in tournament_regs), default=0) + 1
            now = _now_iso()
            if existing_for_team:
                existing_for_team["registered_by"] = registered_by
                existing_for_team["status"] = "pending"
                existing_for_team["seed_number"] = next_seed
                existing_for_team["verified_by"] = None
                existing_for_team["verified_at"] = None
                existing_for_team["notes"] = notes
                existing_for_team["registered_at"] = now
                existing_for_team["updated_at"] = now
                return copy.deepcopy(existing_for_team)

            record: dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "tournament_id": tournament_id,
                "team_id": team_id,
                "registered_by": registered_by,
                "status": "pending",
                "seed_number": next_seed,
                "verified_by": None,
                "verified_at": None,
                "notes": notes,
                "registered_at": now,
                "updated_at": now,
            }
            self._store["registrations"].append(record)
            return copy.deepcopy(record)

    def update_registration_status(
        self, registration_id: str, status: str, verified_by: str, notes: str = ""
    ) -> dict[str, Any] | None:
        now = _now_iso()
        for reg in self._store["registrations"]:
            if reg["id"] == registration_id:
                reg["status"] = status
                reg["verified_by"] = verified_by
                reg["verified_at"] = now
                if notes:
                    reg["notes"] = notes
                reg["updated_at"] = now
                return copy.deepcopy(reg)
        return None

    def _enrich_match(self, match: dict[str, Any]) -> dict[str, Any]:
        enriched = copy.deepcopy(match)
        teams_by_id = {t["id"]: t for t in self._store["teams"]}
        team_a = teams_by_id.get(match.get("team_a_id") or "")
        team_b = teams_by_id.get(match.get("team_b_id") or "")
        winner = teams_by_id.get(match.get("winner_team_id") or "")
        enriched["team_a_name"] = team_a["name"] if team_a else ("BYE" if match.get("status") == "bye" and not team_a else "TBD")
        enriched["team_a_tag"] = team_a["tag"] if team_a else "---"
        enriched["team_b_name"] = team_b["name"] if team_b else ("BYE" if match.get("status") == "bye" and not team_b else "TBD")
        enriched["team_b_tag"] = team_b["tag"] if team_b else "---"
        enriched["winner_team_name"] = winner["name"] if winner else None
        return enriched

    def list_matches_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        matches = [
            self._enrich_match(m)
            for m in self._store["matches"]
            if m["tournament_id"] == tournament_id
        ]
        matches.sort(key=lambda m: (m["round_number"], m["match_number"]))
        return matches

    def get_match_by_id(self, match_id: str) -> dict[str, Any] | None:
        for m in self._store["matches"]:
            if m["id"] == match_id:
                return self._enrich_match(m)
        return None

    def replace_tournament_matches(
        self, tournament_id: str, matches: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not tournament_id or not isinstance(tournament_id, str):
            raise DomainValidationError("Parameter 'tournament_id' wajib diisi.", {"field": "tournament_id"})
        if matches is None or not isinstance(matches, list):
            raise DomainValidationError(
                "Parameter 'matches' wajib berupa JSON array / list.",
                {"field": "matches"},
            )
        if not self.get_tournament_by_id(tournament_id):
            raise DomainNotFoundError("Turnamen tidak ditemukan.", {"tournament_id": tournament_id})

        prepared: list[dict[str, Any]] = []
        for idx, match in enumerate(matches):
            if not isinstance(match, dict):
                raise DomainValidationError(
                    "Item pertandingan tidak valid.",
                    {"index": idx},
                )
            if "round_number" not in match or "match_number" not in match:
                raise DomainValidationError(
                    "Field 'round_number' dan 'match_number' wajib ada pada setiap match.",
                    {"index": idx},
                )
            if (
                isinstance(match["round_number"], bool)
                or not isinstance(match["round_number"], int)
                or match["round_number"] < 1
                or isinstance(match["match_number"], bool)
                or not isinstance(match["match_number"], int)
                or match["match_number"] < 1
            ):
                raise DomainValidationError(
                    "Field 'round_number' dan 'match_number' wajib berupa integer positif.",
                    {"index": idx},
                )
            record = copy.deepcopy(match)
            record.setdefault("id", str(uuid.uuid4()))
            record["tournament_id"] = tournament_id
            prepared.append(record)

        retained = [
            m for m in self._store["matches"] if m["tournament_id"] != tournament_id
        ]
        self._store["matches"] = retained + prepared
        return self.list_matches_by_tournament(tournament_id)

    def update_match(self, match_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        for m in self._store["matches"]:
            if m["id"] == match_id:
                for key, value in data.items():
                    if key != "id":
                        m[key] = value
                m["updated_at"] = _now_iso()
                return self._enrich_match(m)
        return None

    def record_match_result(self, data: dict[str, Any]) -> dict[str, Any]:
        match_id = str(data["match_id"])
        if not self.get_match_by_id(match_id):
            raise DomainNotFoundError("Pertandingan tidak ditemukan.", {"match_id": match_id})

        game_number = int(data.get("game_number", 1))
        now = _now_iso()
        for existing in self._store["match_results"]:
            if existing["match_id"] == match_id and int(existing.get("game_number", 1)) == game_number:
                existing["score_a"] = int(data["score_a"])
                existing["score_b"] = int(data["score_b"])
                existing["winner_team_id"] = data["winner_team_id"]
                existing["proof_url"] = data.get("proof_url")
                existing["notes"] = data.get("notes", "")
                existing["verified_by"] = data["verified_by"]
                existing["verified_at"] = now
                return copy.deepcopy(existing)

        result_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": result_id,
            "match_id": match_id,
            "game_number": game_number,
            "score_a": int(data["score_a"]),
            "score_b": int(data["score_b"]),
            "winner_team_id": data["winner_team_id"],
            "proof_url": data.get("proof_url"),
            "notes": data.get("notes", ""),
            "verified_by": data["verified_by"],
            "verified_at": now,
        }
        self._store["match_results"].append(record)
        return copy.deepcopy(record)

    def list_match_results(self, match_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(r)
            for r in self._store["match_results"]
            if r["match_id"] == match_id
        ]

    # Internal transactional hooks for atomic submission & isolated rollback verification
    def _atomic_update_match_row(self, match_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        return self.update_match(match_id, data)

    def _atomic_propagate_winner(
        self, next_match_id: str, slot_field: str, winner_team_id: str | None
    ) -> dict[str, Any] | None:
        return self.update_match(next_match_id, {slot_field: winner_team_id})

    def _atomic_transition_tournament(self, tournament_id: str, new_status: str) -> dict[str, Any] | None:
        return self.transition_tournament_status(tournament_id, new_status)

    def _atomic_upsert_match_result(self, result_data: dict[str, Any]) -> dict[str, Any]:
        return self.record_match_result(result_data)

    def _atomic_insert_activity_log(
        self,
        actor_id: str | None,
        tournament_id: str | None,
        entity_type: str,
        entity_id: str | None,
        action: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        return self.log_activity(
            actor_id=actor_id,
            tournament_id=tournament_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
        )

    def _rollback_match_row(self, match_id: str, snapshot: dict[str, Any]) -> None:
        for idx, m in enumerate(self._store["matches"]):
            if m["id"] == match_id:
                self._store["matches"][idx] = copy.deepcopy(snapshot)
                return

    def _rollback_tournament_row(self, tournament_id: str, snapshot: dict[str, Any]) -> None:
        for idx, t in enumerate(self._store["tournaments"]):
            if t["id"] == tournament_id:
                self._store["tournaments"][idx] = copy.deepcopy(snapshot)
                return

    def _rollback_match_results(
        self,
        match_id: str,
        game_number: int,
        previous_result: dict[str, Any] | None,
    ) -> None:
        if previous_result is None:
            self._store["match_results"] = [
                r
                for r in self._store["match_results"]
                if not (r["match_id"] == match_id and int(r.get("game_number", 1)) == game_number)
            ]
            return
        for idx, r in enumerate(self._store["match_results"]):
            if r["match_id"] == match_id and int(r.get("game_number", 1)) == game_number:
                self._store["match_results"][idx] = copy.deepcopy(previous_result)
                return
        self._store["match_results"].append(copy.deepcopy(previous_result))

    def _rollback_activity_log(self, log_id: str) -> None:
        self._store["activity_logs"] = [
            item for item in self._store["activity_logs"] if item.get("id") != log_id
        ]

    def _rollback_idempotency_record(self, request_id: str) -> None:
        reqs = self._store.setdefault("match_submission_requests", [])
        self._store["match_submission_requests"] = [
            item for item in reqs if item.get("id") != request_id
        ]

    def submit_match_result_atomic(
        self,
        *,
        match_id: str,
        score_a: int,
        score_b: int,
        winner_team_id: str,
        notes: str = "",
        force_override: bool = False,
        actor_id: str | None = None,
        game_number: int = 1,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        with self._tx_lock:
            actor = next(
                (p for p in self._store["profiles"] if p["id"] == actor_id and p.get("is_active", True)),
                None,
            )
            if not actor:
                raise DomainForbiddenError("Autentikasi diperlukan untuk mengesahkan hasil pertandingan.")
            if actor.get("role") not in (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE):
                raise DomainForbiddenError(
                    "Role pengguna tidak memiliki izin untuk mengesahkan hasil pertandingan."
                )

            match_row = next((m for m in self._store["matches"] if m["id"] == match_id), None)
            if not match_row:
                raise DomainNotFoundError("Pertandingan tidak ditemukan.", {"match_id": match_id})

            tournament_row = next(
                (t for t in self._store["tournaments"] if t["id"] == match_row["tournament_id"]),
                None,
            )
            if not tournament_row:
                raise DomainNotFoundError("Turnamen pertandingan tidak ditemukan.")

            if actor["role"] == ROLE_ORGANIZER and tournament_row["organizer_id"] != actor["id"]:
                raise DomainForbiddenError(
                    "Organizer hanya dapat mengelola pertandingan pada turnamen miliknya.",
                    {"tournament_id": tournament_row["id"], "user_id": actor["id"]},
                )
            if actor["role"] == ROLE_COMMITTEE and not self.is_staff_assigned(
                tournament_row["id"], actor["id"]
            ):
                raise DomainForbiddenError(
                    "Panitia hanya dapat mengelola pertandingan pada turnamen yang ditugaskan.",
                    {"tournament_id": tournament_row["id"], "user_id": actor["id"]},
                )

            clean_notes = (notes or "").strip()
            clean_idem = idempotency_key.strip() if isinstance(idempotency_key, str) and idempotency_key.strip() else None
            if clean_idem is not None and len(clean_idem) > 128:
                raise DomainValidationError(
                    "Field idempotency_key maksimal 128 karakter.", {"field": "idempotency_key"}
                )

            request_hash = hashlib.sha256(
                "|".join(
                    [
                        str(match_id),
                        str(score_a),
                        str(score_b),
                        str(bool(force_override)).lower(),
                        clean_notes,
                        str(int(game_number)),
                    ]
                ).encode("utf-8")
            ).hexdigest()

            idem_store = self._store.setdefault("match_submission_requests", [])
            if clean_idem is not None:
                existing_idem = next(
                    (
                        r
                        for r in idem_store
                        if r["match_id"] == match_id
                        and r["actor_id"] == actor["id"]
                        and r["idempotency_key"] == clean_idem
                    ),
                    None,
                )
                if existing_idem is not None:
                    if existing_idem["request_hash"] != request_hash:
                        raise DomainConflictError(
                            "Idempotency key sudah digunakan dengan payload skor yang berbeda.",
                            {"match_id": match_id, "idempotency_key": clean_idem},
                        )
                    replay = copy.deepcopy(existing_idem["response_payload"])
                    replay["idempotent_replay"] = True
                    return replay

            if tournament_row["status"] == "cancelled":
                raise DomainConflictError(
                    "Hasil pertandingan tidak dapat disahkan karena turnamen telah dibatalkan.",
                    {"tournament_id": tournament_row["id"], "status": tournament_row["status"]},
                )
            if match_row["status"] == "bye":
                raise DomainConflictError(
                    "Pertandingan BYE otomatis dimenangkan dan tidak dapat diisi skor secara manual.",
                    {"match_id": match_id, "status": match_row["status"]},
                )
            if match_row["status"] == "completed" and not force_override:
                raise DomainConflictError(
                    "Hasil pertandingan ini sudah disahkan dan dikunci. "
                    "Gunakan otorisasi force_override beserta catatan audit untuk mengubahnya.",
                    {"match_id": match_id, "status": match_row["status"]},
                )
            if force_override and len(clean_notes) < 4:
                raise DomainValidationError(
                    "Koreksi hasil (force_override) wajib menyertakan alasan audit minimal 4 karakter.",
                    {"field": "notes"},
                )
            if not match_row.get("team_a_id") or not match_row.get("team_b_id"):
                raise DomainValidationError(
                    "Pertandingan belum memiliki kedua tim peserta (Team A dan Team B wajib terisi).",
                    {"team_a_id": match_row.get("team_a_id"), "team_b_id": match_row.get("team_b_id")},
                )

            best_of = parse_best_of(match_row.get("best_of") or tournament_row.get("best_of") or 3)
            winning_side = validate_match_score(
                score_a=score_a,
                score_b=score_b,
                best_of=best_of,
                allow_draw=bool(tournament_row.get("allow_draw", False)),
            )
            computed_winner_id = (
                match_row["team_a_id"] if winning_side == "A" else match_row["team_b_id"]
            )
            if winner_team_id != computed_winner_id:
                raise DomainValidationError(
                    "winner_team_id tidak sesuai dengan pemenang skor pertandingan.",
                    {"winner_team_id": winner_team_id},
                )

            next_match_id = match_row.get("next_match_id")
            next_slot = match_row.get("next_slot")
            slot_field = "team_a_id" if next_slot == "A" else "team_b_id"
            next_match_row: dict[str, Any] | None = None
            if next_match_id and next_slot in ("A", "B"):
                next_match_row = next(
                    (
                        m
                        for m in self._store["matches"]
                        if m["id"] == next_match_id and m["tournament_id"] == tournament_row["id"]
                    ),
                    None,
                )
                if not next_match_row:
                    raise DomainConflictError(
                        "Pertandingan babak berikutnya tidak ditemukan pada turnamen ini.",
                        {"next_match_id": next_match_id},
                    )
                if next_match_row.get(slot_field) != computed_winner_id and (
                    next_match_row.get("status") in ("ongoing", "completed")
                    or next_match_row.get("winner_team_id")
                ):
                    raise DomainConflictError(
                        "Pemenang tidak dapat diubah karena pertandingan babak berikutnya sudah berjalan atau selesai.",
                        {"match_id": match_id, "next_match_id": next_match_id},
                    )
            else:
                if tournament_row["status"] not in ("ongoing", "completed"):
                    raise DomainConflictError(
                        "Grand Final hanya dapat disahkan ketika turnamen berstatus 'ongoing' atau 'completed'.",
                        {"tournament_id": tournament_row["id"], "status": tournament_row["status"]},
                    )
                tournament_matches = [
                    m for m in self._store["matches"] if m["tournament_id"] == tournament_row["id"]
                ]
                validate_bracket_graph(
                    tournament_row["id"],
                    tournament_matches,
                    pending_final_id=match_id,
                )

            # Deep snapshots before any mutation for full compensating transaction safety
            match_snapshot = copy.deepcopy(match_row)
            tournament_snapshot = copy.deepcopy(tournament_row)
            next_match_snapshot = copy.deepcopy(next_match_row) if next_match_row is not None else None
            existing_result_snapshot = copy.deepcopy(
                next(
                    (
                        r
                        for r in self._store["match_results"]
                        if r["match_id"] == match_id and int(r.get("game_number", 1)) == int(game_number)
                    ),
                    None,
                )
            )
            now = _now_iso()

            match_mutated = False
            next_match_mutated = False
            tournament_mutated = False
            result_mutated = False
            inserted_log_id: str | None = None
            inserted_idem_id: str | None = None

            try:
                updated_match = self._atomic_update_match_row(
                    match_id,
                    {
                        "score_a": score_a,
                        "score_b": score_b,
                        "winner_team_id": computed_winner_id,
                        "status": "completed",
                        "completed_at": now,
                    },
                )
                match_mutated = True

                updated_next_match: dict[str, Any] | None = None
                if next_match_id and next_slot in ("A", "B"):
                    updated_next_match = self._atomic_propagate_winner(
                        next_match_id, slot_field, computed_winner_id
                    )
                    next_match_mutated = True
                else:
                    self._atomic_transition_tournament(tournament_row["id"], "completed")
                    tournament_mutated = True

                self._atomic_upsert_match_result(
                    {
                        "match_id": match_id,
                        "game_number": int(game_number),
                        "score_a": score_a,
                        "score_b": score_b,
                        "winner_team_id": computed_winner_id,
                        "notes": clean_notes,
                        "verified_by": actor["id"],
                        "verified_at": now,
                    }
                )
                result_mutated = True

                action_name = (
                    "MATCH_RESULT_OVERRIDDEN" if force_override else "MATCH_RESULT_VERIFIED"
                )
                created_log = self._atomic_insert_activity_log(
                    actor_id=actor["id"],
                    tournament_id=tournament_row["id"],
                    entity_type="match",
                    entity_id=match_id,
                    action=action_name,
                    details={
                        "score_a": score_a,
                        "score_b": score_b,
                        "winner_team_id": computed_winner_id,
                        "next_match_id": next_match_id,
                        "next_slot": next_slot,
                        "notes": clean_notes,
                    },
                )
                inserted_log_id = created_log["id"]

                response_payload: dict[str, Any] = {
                    "match": updated_match,
                    "next_match": updated_next_match,
                    "tournament_status": "completed" if not next_match_id else tournament_row["status"],
                    "idempotent_replay": False,
                }

                if clean_idem is not None:
                    req_id = str(uuid.uuid4())
                    idem_store.append(
                        {
                            "id": req_id,
                            "match_id": match_id,
                            "actor_id": actor["id"],
                            "idempotency_key": clean_idem,
                            "request_hash": request_hash,
                            "response_payload": copy.deepcopy(response_payload),
                            "created_at": now,
                        }
                    )
                    inserted_idem_id = req_id

                return response_payload
            except Exception as primary_exc:
                rollback_steps: list[tuple[str, Any]] = []
                if inserted_idem_id is not None:
                    rollback_steps.append(
                        ("match_submission_requests", lambda: self._rollback_idempotency_record(inserted_idem_id))
                    )
                if inserted_log_id is not None:
                    rollback_steps.append(
                        ("activity_logs", lambda: self._rollback_activity_log(inserted_log_id))
                    )
                if result_mutated:
                    rollback_steps.append(
                        (
                            "match_results",
                            lambda: self._rollback_match_results(
                                match_id, int(game_number), existing_result_snapshot
                            ),
                        )
                    )
                if tournament_mutated:
                    rollback_steps.append(
                        (
                            "tournament",
                            lambda: self._rollback_tournament_row(tournament_row["id"], tournament_snapshot),
                        )
                    )
                if next_match_mutated and next_match_snapshot is not None:
                    rollback_steps.append(
                        (
                            "downstream_match",
                            lambda: self._rollback_match_row(next_match_snapshot["id"], next_match_snapshot),
                        )
                    )
                if match_mutated:
                    rollback_steps.append(
                        ("match", lambda: self._rollback_match_row(match_id, match_snapshot))
                    )

                restored_targets: list[str] = []
                failed_rollbacks: list[tuple[str, Exception]] = []
                for target_name, rb_fn in rollback_steps:
                    try:
                        rb_fn()
                        restored_targets.append(target_name)
                    except Exception as rb_exc:
                        failed_rollbacks.append((target_name, rb_exc))

                if failed_rollbacks:
                    unrecovered_names = [name for name, _ in failed_rollbacks]
                    logger.critical(
                        "Atomic mock rollback incomplete for match=%s tournament=%s; "
                        "primary_error=%r; restored=%s; unrecovered=%s; secondary_errors=%r",
                        match_id,
                        tournament_row["id"],
                        primary_exc,
                        restored_targets,
                        unrecovered_names,
                        [(name, repr(err)) for name, err in failed_rollbacks],
                    )
                    details = getattr(primary_exc, "details", None)
                    if isinstance(details, dict):
                        details["rollback_incomplete"] = True
                        details["unrecovered_targets"] = unrecovered_names
                    raise primary_exc from failed_rollbacks[-1][1]
                raise

    def list_announcements_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        profiles_by_id = {p["id"]: p for p in self._store["profiles"]}
        items: list[dict[str, Any]] = []
        for ann in self._store["announcements"]:
            if ann["tournament_id"] == tournament_id:
                enriched = copy.deepcopy(ann)
                author = profiles_by_id.get(ann.get("author_id"))
                raw_name = (
                    str(author.get("full_name") or "").strip()
                    if author and author.get("is_active", True)
                    else ""
                )
                enriched["author_name"] = raw_name or "Panitia"
                items.append(enriched)
        items.sort(key=lambda a: (not a.get("is_pinned", False), a.get("published_at", "")), reverse=False)
        return items

    def create_announcement(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.get_tournament_by_id(data["tournament_id"]):
            raise DomainNotFoundError("Turnamen tidak ditemukan.", {"tournament_id": data["tournament_id"]})

        now = _now_iso()
        ann_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": ann_id,
            "tournament_id": data["tournament_id"],
            "author_id": data["author_id"],
            "title": data["title"].strip(),
            "content": data["content"].strip(),
            "priority": data.get("priority", "normal"),
            "is_pinned": bool(data.get("is_pinned", False)),
            "published_at": now,
            "created_at": now,
        }
        self._store["announcements"].append(record)
        return copy.deepcopy(record)

    def log_activity(
        self,
        actor_id: str | None,
        tournament_id: str | None,
        entity_type: str,
        entity_id: str | None,
        action: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        log_record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "actor_id": actor_id,
            "tournament_id": tournament_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "details": copy.deepcopy(details),
            "created_at": _now_iso(),
        }
        self._store["activity_logs"].append(log_record)
        return copy.deepcopy(log_record)

    def list_activity_logs(self, tournament_id: str | None = None) -> list[dict[str, Any]]:
        logs = [
            copy.deepcopy(log)
            for log in self._store["activity_logs"]
            if tournament_id is None or log.get("tournament_id") == tournament_id
        ]
        logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return logs
