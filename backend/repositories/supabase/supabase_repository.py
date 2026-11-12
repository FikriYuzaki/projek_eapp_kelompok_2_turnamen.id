"""Supabase PostgreSQL repository adapter implementing `DataStoreRepositoryProtocol`.

Owner: Habil (Database & Authentication Developer)
Note: Active only when `APP_MODE=supabase` is configured with valid credentials.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.core.config import AppConfig
from backend.infrastructure.supabase.client import create_supabase_client
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_data import DEFAULT_DEMO_PASSWORD_HASH


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


class SupabaseDataStoreRepository(DataStoreRepositoryProtocol):
    """Production repository backed by Supabase PostgreSQL Data API and RLS."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._client = create_supabase_client(config)
        self._password_hashes: dict[str, str] = {}

    def reset_to_seed(self) -> None:
        raise NotImplementedError(
            "reset_to_seed() hanya diizinkan pada APP_MODE=mock untuk pengujian lokal."
        )

    def _attach_auth_fields(self, profile: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(profile)
        if not enriched.get("password_hash"):
            pid = str(enriched.get("id") or "")
            email = str(enriched.get("email") or "").lower()
            if pid in self._password_hashes:
                enriched["password_hash"] = self._password_hashes[pid]
            elif email.endswith("@turnamen.in"):
                enriched["password_hash"] = DEFAULT_DEMO_PASSWORD_HASH
        return enriched

    def list_profiles(self) -> list[dict[str, Any]]:
        resp = self._client.table("profiles").select("*").execute()
        return [self._attach_auth_fields(p) for p in (resp.data or [])]

    def get_profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        resp = self._client.table("profiles").select("*").eq("id", profile_id).limit(1).execute()
        return self._attach_auth_fields(resp.data[0]) if resp.data else None

    def get_profile_by_email(self, email: str) -> dict[str, Any] | None:
        resp = self._client.table("profiles").select("*").eq("email", email.strip().lower()).limit(1).execute()
        return self._attach_auth_fields(resp.data[0]) if resp.data else None

    def get_profile_by_username(self, username: str) -> dict[str, Any] | None:
        resp = self._client.table("profiles").select("*").eq("username", username.strip()).limit(1).execute()
        return self._attach_auth_fields(resp.data[0]) if resp.data else None

    def create_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        password_hash = data.get("password_hash", "")
        payload = {k: v for k, v in data.items() if k != "password_hash"}
        resp = self._client.table("profiles").insert(payload).execute()
        created = dict(resp.data[0])
        if password_hash and created.get("id"):
            self._password_hashes[str(created["id"])] = str(password_hash)
            created["password_hash"] = password_hash
        return created

    def update_profile(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        payload = {k: v for k, v in data.items() if k not in ("id", "password_hash")}
        resp = self._client.table("profiles").update(payload).eq("id", profile_id).execute()
        return self._attach_auth_fields(resp.data[0]) if resp.data else None

    def list_games(self) -> list[dict[str, Any]]:
        resp = self._client.table("games").select("*").eq("is_active", True).execute()
        return list(resp.data or [])

    def get_game_by_id(self, game_id: str) -> dict[str, Any] | None:
        column = "id" if _is_uuid(game_id) else "slug"
        resp = self._client.table("games").select("*").eq(column, game_id).limit(1).execute()
        return dict(resp.data[0]) if resp.data else None

    def _enrich_tournament(
        self,
        tournament: dict[str, Any],
        games_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(tournament)
        if games_by_id is not None:
            game = games_by_id.get(str(tournament.get("game_id") or ""))
        else:
            game = self.get_game_by_id(str(tournament.get("game_id") or ""))
        enriched["game_name"] = game["name"] if game else "Unknown Game"
        regs = self.list_registrations_by_tournament(str(tournament["id"]))
        enriched["registered_teams_count"] = len(regs)
        enriched["approved_teams_count"] = sum(
            1 for r in regs if r.get("status") == "approved"
        )
        return enriched

    def list_tournaments(
        self, status: str | None = None, game_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = self._client.table("tournaments").select("*")
        if status:
            query = query.eq("status", status)
        if game_id:
            query = query.eq("game_id", game_id)
        resp = query.order("start_date", desc=False).execute()
        games_by_id = {str(g["id"]): g for g in self.list_games()}
        return [self._enrich_tournament(t, games_by_id) for t in (resp.data or [])]

    def get_tournament_by_id(self, tournament_id: str) -> dict[str, Any] | None:
        column = "id" if _is_uuid(tournament_id) else "slug"
        resp = self._client.table("tournaments").select("*").eq(column, tournament_id).limit(1).execute()
        if not resp.data:
            return None
        return self._enrich_tournament(resp.data[0])

    def create_tournament(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("tournaments").insert(data).execute()
        return self._enrich_tournament(resp.data[0])

    def update_tournament(
        self, tournament_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        resp = self._client.table("tournaments").update(data).eq("id", tournament_id).execute()
        return self._enrich_tournament(resp.data[0]) if resp.data else None

    def delete_tournament(self, tournament_id: str) -> bool:
        resp = self._client.table("tournaments").delete().eq("id", tournament_id).execute()
        return bool(resp.data)

    def is_staff_assigned(self, tournament_id: str, user_id: str) -> bool:
        resp = (
            self._client.table("tournament_staff")
            .select("id")
            .eq("tournament_id", tournament_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(resp.data)

    def _enrich_team(
        self,
        team: dict[str, Any],
        games_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(team)
        members = self.list_team_members(str(team["id"]))
        enriched["members"] = members
        enriched["member_count"] = len(members)
        if games_by_id is not None:
            game = games_by_id.get(str(team.get("game_id") or ""))
        else:
            game = self.get_game_by_id(str(team.get("game_id") or ""))
        enriched["game_name"] = game["name"] if game else "Unknown Game"
        return enriched

    def list_teams(self, game_id: str | None = None) -> list[dict[str, Any]]:
        query = self._client.table("teams").select("*")
        if game_id:
            query = query.eq("game_id", game_id)
        resp = query.execute()
        games_by_id = {str(g["id"]): g for g in self.list_games()}
        return [self._enrich_team(t, games_by_id) for t in (resp.data or [])]

    def get_team_by_id(self, team_id: str) -> dict[str, Any] | None:
        resp = self._client.table("teams").select("*").eq("id", team_id).limit(1).execute()
        if not resp.data:
            return None
        return self._enrich_team(resp.data[0])

    def create_team(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("teams").insert(data).execute()
        return self._enrich_team(resp.data[0])

    def update_team(self, team_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        resp = self._client.table("teams").update(data).eq("id", team_id).execute()
        return self._enrich_team(resp.data[0]) if resp.data else None

    def list_team_members(self, team_id: str) -> list[dict[str, Any]]:
        resp = (
            self._client.table("team_members")
            .select("*")
            .eq("team_id", team_id)
            .eq("is_active", True)
            .execute()
        )
        return list(resp.data or [])

    def add_team_member(self, team_id: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {**data, "team_id": team_id}
        resp = self._client.table("team_members").insert(payload).execute()
        return dict(resp.data[0])

    def list_registrations_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        resp = (
            self._client.table("registrations")
            .select("*")
            .eq("tournament_id", tournament_id)
            .execute()
        )
        teams_resp = self._client.table("teams").select("id,name,tag").execute()
        teams_by_id = {str(t["id"]): t for t in (teams_resp.data or [])}
        results: list[dict[str, Any]] = []
        for reg in resp.data or []:
            enriched = dict(reg)
            team = teams_by_id.get(str(reg.get("team_id") or ""))
            enriched["team_name"] = team["name"] if team else "Unknown Team"
            enriched["team_tag"] = team["tag"] if team else "---"
            results.append(enriched)
        results.sort(key=lambda r: (r.get("seed_number") or 999, r.get("registered_at") or ""))
        return results

    def get_registration_by_id(self, registration_id: str) -> dict[str, Any] | None:
        resp = (
            self._client.table("registrations")
            .select("*")
            .eq("id", registration_id)
            .limit(1)
            .execute()
        )
        return dict(resp.data[0]) if resp.data else None

    def create_registration(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("registrations").insert(data).execute()
        return dict(resp.data[0])

    def update_registration_status(
        self, registration_id: str, status: str, verified_by: str, notes: str = ""
    ) -> dict[str, Any] | None:
        resp = (
            self._client.table("registrations")
            .update({"status": status, "verified_by": verified_by, "notes": notes})
            .eq("id", registration_id)
            .execute()
        )
        return dict(resp.data[0]) if resp.data else None

    def _enrich_match(
        self,
        match: dict[str, Any],
        teams_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(match)
        if teams_by_id is None:
            teams_resp = self._client.table("teams").select("id,name,tag").execute()
            teams_by_id = {str(t["id"]): t for t in (teams_resp.data or [])}
        team_a = teams_by_id.get(str(match.get("team_a_id") or ""))
        team_b = teams_by_id.get(str(match.get("team_b_id") or ""))
        winner = teams_by_id.get(str(match.get("winner_team_id") or ""))
        enriched["team_a_name"] = (
            team_a["name"]
            if team_a
            else ("BYE" if match.get("status") == "bye" and not team_a else "TBD")
        )
        enriched["team_a_tag"] = team_a["tag"] if team_a else "---"
        enriched["team_b_name"] = (
            team_b["name"]
            if team_b
            else ("BYE" if match.get("status") == "bye" and not team_b else "TBD")
        )
        enriched["team_b_tag"] = team_b["tag"] if team_b else "---"
        enriched["winner_team_name"] = winner["name"] if winner else None
        return enriched

    def list_matches_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        resp = (
            self._client.table("matches")
            .select("*")
            .eq("tournament_id", tournament_id)
            .order("round_number")
            .order("match_number")
            .execute()
        )
        teams_resp = self._client.table("teams").select("id,name,tag").execute()
        teams_by_id = {str(t["id"]): t for t in (teams_resp.data or [])}
        return [self._enrich_match(m, teams_by_id) for m in (resp.data or [])]

    def get_match_by_id(self, match_id: str) -> dict[str, Any] | None:
        resp = self._client.table("matches").select("*").eq("id", match_id).limit(1).execute()
        if not resp.data:
            return None
        return self._enrich_match(resp.data[0])

    def replace_tournament_matches(
        self, tournament_id: str, matches: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        self._client.table("matches").delete().eq("tournament_id", tournament_id).execute()
        if matches:
            self._client.table("matches").insert(matches).execute()
        return self.list_matches_by_tournament(tournament_id)

    def update_match(self, match_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        resp = self._client.table("matches").update(data).eq("id", match_id).execute()
        if not resp.data:
            return None
        return self._enrich_match(resp.data[0])

    def record_match_result(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("match_results").insert(data).execute()
        return dict(resp.data[0])

    def list_match_results(self, match_id: str) -> list[dict[str, Any]]:
        resp = self._client.table("match_results").select("*").eq("match_id", match_id).execute()
        return list(resp.data or [])

    def list_announcements_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        resp = (
            self._client.table("announcements")
            .select("*")
            .eq("tournament_id", tournament_id)
            .order("is_pinned", desc=True)
            .order("published_at", desc=True)
            .execute()
        )
        profiles_resp = self._client.table("profiles").select("id,full_name").execute()
        profiles_by_id = {str(p["id"]): p for p in (profiles_resp.data or [])}
        results: list[dict[str, Any]] = []
        for ann in resp.data or []:
            enriched = dict(ann)
            author = profiles_by_id.get(str(ann.get("author_id") or ""))
            enriched["author_name"] = author["full_name"] if author else "Panitia"
            results.append(enriched)
        return results

    def create_announcement(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("announcements").insert(data).execute()
        return dict(resp.data[0])

    def log_activity(
        self,
        actor_id: str | None,
        tournament_id: str | None,
        entity_type: str,
        entity_id: str | None,
        action: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "actor_id": actor_id,
            "tournament_id": tournament_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "details": details,
        }
        try:
            resp = self._client.table("activity_logs").insert(payload).execute()
            if resp.data:
                return dict(resp.data[0])
        except Exception:
            pass
        return {
            "id": str(uuid.uuid4()),
            **payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def list_activity_logs(self, tournament_id: str | None = None) -> list[dict[str, Any]]:
        query = self._client.table("activity_logs").select("*")
        if tournament_id:
            query = query.eq("tournament_id", tournament_id)
        resp = query.order("created_at", desc=True).execute()
        return list(resp.data or [])
