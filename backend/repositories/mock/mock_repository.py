"""In-memory mock repository implementing `DataStoreRepositoryProtocol`."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.core.exceptions import DomainNotFoundError, DomainValidationError
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_data import build_initial_mock_store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MockDataStoreRepository(DataStoreRepositoryProtocol):
    """Thread-safe in-memory repository for `APP_MODE=mock` and automated tests."""

    is_supabase_mode: bool = False

    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = build_initial_mock_store()

    def reset_to_seed(self) -> None:
        """Reset all in-memory tables back to the initial demo seed state."""
        self._store = build_initial_mock_store()

    def list_profiles(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(p) for p in self._store["profiles"]]

    def get_profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        for p in self._store["profiles"]:
            if p["id"] == profile_id:
                return copy.deepcopy(p)
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

    def list_games(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(g) for g in self._store["games"] if g.get("is_active", True)]

    def get_game_by_id(self, game_id: str) -> dict[str, Any] | None:
        for g in self._store["games"]:
            if g["id"] == game_id or g["slug"] == game_id:
                return copy.deepcopy(g)
        return None

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

    def delete_tournament(self, tournament_id: str) -> bool:
        for idx, t in enumerate(self._store["tournaments"]):
            if t["id"] == tournament_id:
                del self._store["tournaments"][idx]
                return True
        return False

    def is_staff_assigned(self, tournament_id: str, user_id: str) -> bool:
        return any(
            s["tournament_id"] == tournament_id and s["user_id"] == user_id
            for s in self._store["tournament_staff"]
        )

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
        if not self.get_match_by_id(data["match_id"]):
            raise DomainNotFoundError("Pertandingan tidak ditemukan.", {"match_id": data["match_id"]})

        result_id = data.get("id") or str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": result_id,
            "match_id": data["match_id"],
            "game_number": int(data.get("game_number", 1)),
            "score_a": int(data["score_a"]),
            "score_b": int(data["score_b"]),
            "winner_team_id": data["winner_team_id"],
            "proof_url": data.get("proof_url"),
            "notes": data.get("notes", ""),
            "verified_by": data["verified_by"],
            "verified_at": _now_iso(),
        }
        self._store["match_results"].append(record)
        return copy.deepcopy(record)

    def list_match_results(self, match_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(r)
            for r in self._store["match_results"]
            if r["match_id"] == match_id
        ]

    def list_announcements_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        profiles_by_id = {p["id"]: p for p in self._store["profiles"]}
        items: list[dict[str, Any]] = []
        for ann in self._store["announcements"]:
            if ann["tournament_id"] == tournament_id:
                enriched = copy.deepcopy(ann)
                author = profiles_by_id.get(ann["author_id"])
                enriched["author_name"] = author["full_name"] if author else "Panitia"
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
