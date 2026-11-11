"""Supabase PostgreSQL repository adapter implementing `DataStoreRepositoryProtocol`.

Owner: Habil (Database & Authentication Developer)
Note: Active only when `APP_MODE=supabase` is configured with valid credentials.
"""

from __future__ import annotations

from typing import Any

from backend.core.config import AppConfig
from backend.infrastructure.supabase.client import create_supabase_client
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol


class SupabaseDataStoreRepository(DataStoreRepositoryProtocol):
    """Production repository backed by Supabase PostgreSQL Data API and RLS."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._client = create_supabase_client(config)

    def reset_to_seed(self) -> None:
        raise NotImplementedError(
            "reset_to_seed() hanya diizinkan pada APP_MODE=mock untuk pengujian lokal."
        )

    def list_profiles(self) -> list[dict[str, Any]]:
        resp = self._client.table("profiles").select("*").execute()
        return list(resp.data or [])

    def get_profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        resp = self._client.table("profiles").select("*").eq("id", profile_id).limit(1).execute()
        return resp.data[0] if resp.data else None

    def get_profile_by_email(self, email: str) -> dict[str, Any] | None:
        resp = self._client.table("profiles").select("*").eq("email", email.lower()).limit(1).execute()
        return resp.data[0] if resp.data else None

    def get_profile_by_username(self, username: str) -> dict[str, Any] | None:
        resp = self._client.table("profiles").select("*").eq("username", username).limit(1).execute()
        return resp.data[0] if resp.data else None

    def create_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = {k: v for k, v in data.items() if k != "password_hash"}
        resp = self._client.table("profiles").insert(payload).execute()
        return resp.data[0]

    def update_profile(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        resp = self._client.table("profiles").update(data).eq("id", profile_id).execute()
        return resp.data[0] if resp.data else None

    def list_games(self) -> list[dict[str, Any]]:
        resp = self._client.table("games").select("*").eq("is_active", True).execute()
        return list(resp.data or [])

    def get_game_by_id(self, game_id: str) -> dict[str, Any] | None:
        resp = self._client.table("games").select("*").eq("id", game_id).limit(1).execute()
        return resp.data[0] if resp.data else None

    def list_tournaments(
        self, status: str | None = None, game_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = self._client.table("tournaments").select("*")
        if status:
            query = query.eq("status", status)
        if game_id:
            query = query.eq("game_id", game_id)
        resp = query.order("start_date", desc=False).execute()
        return list(resp.data or [])

    def get_tournament_by_id(self, tournament_id: str) -> dict[str, Any] | None:
        resp = self._client.table("tournaments").select("*").eq("id", tournament_id).limit(1).execute()
        return resp.data[0] if resp.data else None

    def create_tournament(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("tournaments").insert(data).execute()
        return resp.data[0]

    def update_tournament(
        self, tournament_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        resp = self._client.table("tournaments").update(data).eq("id", tournament_id).execute()
        return resp.data[0] if resp.data else None

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

    def list_teams(self, game_id: str | None = None) -> list[dict[str, Any]]:
        query = self._client.table("teams").select("*")
        if game_id:
            query = query.eq("game_id", game_id)
        resp = query.execute()
        return list(resp.data or [])

    def get_team_by_id(self, team_id: str) -> dict[str, Any] | None:
        resp = self._client.table("teams").select("*").eq("id", team_id).limit(1).execute()
        if not resp.data:
            return None
        team = dict(resp.data[0])
        team["members"] = self.list_team_members(team_id)
        return team

    def create_team(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("teams").insert(data).execute()
        return resp.data[0]

    def update_team(self, team_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        resp = self._client.table("teams").update(data).eq("id", team_id).execute()
        return resp.data[0] if resp.data else None

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
        return resp.data[0]

    def list_registrations_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        resp = (
            self._client.table("registrations")
            .select("*")
            .eq("tournament_id", tournament_id)
            .execute()
        )
        return list(resp.data or [])

    def get_registration_by_id(self, registration_id: str) -> dict[str, Any] | None:
        resp = (
            self._client.table("registrations")
            .select("*")
            .eq("id", registration_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None

    def create_registration(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("registrations").insert(data).execute()
        return resp.data[0]

    def update_registration_status(
        self, registration_id: str, status: str, verified_by: str, notes: str = ""
    ) -> dict[str, Any] | None:
        resp = (
            self._client.table("registrations")
            .update({"status": status, "verified_by": verified_by, "notes": notes})
            .eq("id", registration_id)
            .execute()
        )
        return resp.data[0] if resp.data else None

    def list_matches_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        resp = (
            self._client.table("matches")
            .select("*")
            .eq("tournament_id", tournament_id)
            .order("round_number")
            .order("match_number")
            .execute()
        )
        return list(resp.data or [])

    def get_match_by_id(self, match_id: str) -> dict[str, Any] | None:
        resp = self._client.table("matches").select("*").eq("id", match_id).limit(1).execute()
        return resp.data[0] if resp.data else None

    def replace_tournament_matches(
        self, tournament_id: str, matches: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        self._client.table("matches").delete().eq("tournament_id", tournament_id).execute()
        if matches:
            self._client.table("matches").insert(matches).execute()
        return self.list_matches_by_tournament(tournament_id)

    def update_match(self, match_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        resp = self._client.table("matches").update(data).eq("id", match_id).execute()
        return resp.data[0] if resp.data else None

    def record_match_result(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("match_results").insert(data).execute()
        return resp.data[0]

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
        return list(resp.data or [])

    def create_announcement(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.table("announcements").insert(data).execute()
        return resp.data[0]

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
        resp = self._client.table("activity_logs").insert(payload).execute()
        return resp.data[0]

    def list_activity_logs(self, tournament_id: str | None = None) -> list[dict[str, Any]]:
        query = self._client.table("activity_logs").select("*")
        if tournament_id:
            query = query.eq("tournament_id", tournament_id)
        resp = query.order("created_at", desc=True).execute()
        return list(resp.data or [])
