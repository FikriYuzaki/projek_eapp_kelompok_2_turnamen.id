"""Tournament and registration management service.

Owner: Adriel (Tournament & Match System Developer)
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from backend.contracts.dtos import (
    REGISTRATION_STATUSES,
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
    ROLE_SUPER_ADMIN,
    TOURNAMENT_STATUSES,
    VALID_BEST_OF,
)
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.auth.permissions import require_permission
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or f"tournament-{uuid.uuid4().hex[:8]}"


class TournamentService:
    """Application service for tournaments and team registrations."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def list_games(self) -> list[dict[str, Any]]:
        return self._repo.list_games()

    def get_game(self, game_id: str) -> dict[str, Any]:
        game = self._repo.get_game_by_id(game_id)
        if not game:
            raise DomainNotFoundError("Data game tidak ditemukan.", {"game_id": game_id})
        return game

    def list_tournaments(
        self, status: str | None = None, game_id: str | None = None
    ) -> list[dict[str, Any]]:
        if status and status not in TOURNAMENT_STATUSES:
            raise DomainValidationError(
                f"Status filter '{status}' tidak valid.",
                {"valid_statuses": list(TOURNAMENT_STATUSES)},
            )
        return self._repo.list_tournaments(status=status, game_id=game_id)

    def get_tournament(self, tournament_id: str) -> dict[str, Any]:
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )
        return tournament

    def create_tournament(
        self, actor: dict[str, Any] | None, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "tournament:create")
        title = str(payload.get("title") or "").strip()
        game_id = str(payload.get("game_id") or "").strip()
        start_date = str(payload.get("start_date") or "").strip()

        if len(title) < 4:
            raise DomainValidationError(
                "Judul turnamen minimal terdiri dari 4 karakter.", {"field": "title"}
            )
        if not game_id:
            raise DomainValidationError("Game wajib dipilih.", {"field": "game_id"})
        game = self._repo.get_game_by_id(game_id)
        if not game:
            raise DomainNotFoundError("Game tidak ditemukan.", {"game_id": game_id})
        if not start_date:
            raise DomainValidationError(
                "Tanggal mulai turnamen (start_date) wajib diisi.", {"field": "start_date"}
            )

        max_teams = int(payload.get("max_teams", 8))
        if max_teams < 2 or max_teams > 128:
            raise DomainValidationError(
                "Kuota tim (max_teams) harus berada di antara 2 hingga 128.",
                {"max_teams": max_teams},
            )

        best_of = int(payload.get("best_of", game.get("default_best_of", 3)))
        if best_of not in VALID_BEST_OF:
            raise DomainValidationError(
                f"Format best_of harus salah satu dari {VALID_BEST_OF}.", {"best_of": best_of}
            )

        registration_fee = float(payload.get("registration_fee", 0.0))
        prize_pool = float(payload.get("prize_pool", 0.0))
        if registration_fee < 0 or prize_pool < 0:
            raise DomainValidationError(
                "Biaya pendaftaran dan total hadiah tidak boleh bernilai negatif."
            )

        status = str(payload.get("status") or "open_registration").strip()
        if status not in TOURNAMENT_STATUSES:
            raise DomainValidationError(f"Status turnamen '{status}' tidak valid.")

        base_slug = _slugify(str(payload.get("slug") or title))
        slug = base_slug
        if self._repo.get_tournament_by_id(slug):
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        created = self._repo.create_tournament(
            {
                "slug": slug,
                "title": title,
                "description": str(payload.get("description") or "").strip(),
                "game_id": game["id"],
                "organizer_id": user["id"],
                "format": "single_elimination",
                "status": status,
                "max_teams": max_teams,
                "best_of": best_of,
                "allow_draw": bool(payload.get("allow_draw", False)),
                "registration_fee": registration_fee,
                "prize_pool": prize_pool,
                "rules": str(payload.get("rules") or "").strip(),
                "venue": str(payload.get("venue") or "Online").strip(),
                "start_date": start_date,
                "end_date": payload.get("end_date"),
            }
        )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=created["id"],
            entity_type="tournament",
            entity_id=created["id"],
            action="TOURNAMENT_CREATED",
            details={"title": title, "max_teams": max_teams, "best_of": best_of},
        )
        return created

    def update_tournament(
        self, actor: dict[str, Any] | None, tournament_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "tournament:update")
        tournament = self.get_tournament(tournament_id)

        if (
            user["role"] == ROLE_ORGANIZER
            and tournament["organizer_id"] != user["id"]
        ):
            raise DomainForbiddenError(
                "Organizer hanya dapat mengubah turnamen yang dikelolanya sendiri."
            )

        updates: dict[str, Any] = {}
        for field in ("title", "description", "rules", "venue", "start_date", "end_date"):
            if field in payload and payload[field] is not None:
                updates[field] = str(payload[field]).strip()

        if "status" in payload and payload["status"] is not None:
            new_status = str(payload["status"]).strip()
            if new_status not in TOURNAMENT_STATUSES:
                raise DomainValidationError(f"Status turnamen '{new_status}' tidak valid.")
            updates["status"] = new_status

        if "max_teams" in payload and payload["max_teams"] is not None:
            max_teams = int(payload["max_teams"])
            if max_teams < 2 or max_teams > 128:
                raise DomainValidationError("max_teams harus di antara 2 hingga 128.")
            updates["max_teams"] = max_teams

        if "best_of" in payload and payload["best_of"] is not None:
            best_of = int(payload["best_of"])
            if best_of not in VALID_BEST_OF:
                raise DomainValidationError(f"best_of harus salah satu dari {VALID_BEST_OF}.")
            updates["best_of"] = best_of

        if "prize_pool" in payload and payload["prize_pool"] is not None:
            prize_pool = float(payload["prize_pool"])
            if prize_pool < 0:
                raise DomainValidationError("prize_pool tidak boleh negatif.")
            updates["prize_pool"] = prize_pool

        updated = self._repo.update_tournament(tournament["id"], updates)
        if not updated:
            raise DomainNotFoundError("Turnamen tidak ditemukan.")
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="tournament",
            entity_id=tournament["id"],
            action="TOURNAMENT_UPDATED",
            details=updates,
        )
        return updated

    def delete_tournament(self, actor: dict[str, Any] | None, tournament_id: str) -> dict[str, Any]:
        user = require_permission(actor, "tournament:delete")
        tournament = self.get_tournament(tournament_id)
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat menghapus turnamen miliknya sendiri."
            )
        if tournament["status"] in ("ongoing", "completed"):
            raise DomainConflictError(
                "Turnamen yang sedang berlangsung atau sudah selesai tidak dapat dihapus."
            )
        self._repo.delete_tournament(tournament["id"])
        return {"deleted_id": tournament["id"], "title": tournament["title"]}

    # -------------------------------------------------------------------------
    # Registrations
    # -------------------------------------------------------------------------
    def list_registrations(self, tournament_id: str) -> list[dict[str, Any]]:
        tournament = self.get_tournament(tournament_id)
        return self._repo.list_registrations_by_tournament(tournament["id"])

    def register_team(
        self, actor: dict[str, Any] | None, tournament_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "registration:create")
        tournament = self.get_tournament(tournament_id)

        if tournament["status"] not in ("open_registration", "draft"):
            raise DomainConflictError(
                f"Pendaftaran ditutup untuk turnamen berstatus '{tournament['status']}'."
            )

        team_id = str(payload.get("team_id") or "").strip()
        if not team_id:
            raise DomainValidationError("team_id wajib diisi.", {"field": "team_id"})

        team = self._repo.get_team_by_id(team_id)
        if not team:
            raise DomainNotFoundError("Tim tidak ditemukan.", {"team_id": team_id})

        if team["game_id"] != tournament["game_id"]:
            raise DomainValidationError(
                "Game yang dimainkan tim tidak sesuai dengan game turnamen."
            )

        existing_regs = self._repo.list_registrations_by_tournament(tournament["id"])
        for reg in existing_regs:
            if reg["team_id"] == team_id and reg["status"] != "withdrawn":
                raise DomainConflictError(
                    "Tim ini sudah terdaftar pada turnamen tersebut.",
                    {"tournament_id": tournament["id"], "team_id": team_id},
                )

        active_count = sum(
            1 for r in existing_regs if r["status"] in ("pending", "approved")
        )
        if active_count >= int(tournament["max_teams"]):
            raise DomainConflictError(
                f"Kuota turnamen sudah penuh ({tournament['max_teams']} tim)."
            )

        created = self._repo.create_registration(
            {
                "tournament_id": tournament["id"],
                "team_id": team["id"],
                "registered_by": user["id"],
                "status": "pending",
                "seed_number": len(existing_regs) + 1,
                "notes": str(payload.get("notes") or "").strip(),
            }
        )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="registration",
            entity_id=created["id"],
            action="TEAM_REGISTERED",
            details={"team_id": team["id"], "team_name": team["name"]},
        )
        return created

    def update_registration_status(
        self,
        actor: dict[str, Any] | None,
        registration_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        user = require_permission(actor, "registration:verify")
        reg = self._repo.get_registration_by_id(registration_id)
        if not reg:
            raise DomainNotFoundError(
                "Data registrasi tidak ditemukan.", {"registration_id": registration_id}
            )

        tournament = self.get_tournament(reg["tournament_id"])
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat memverifikasi registrasi pada turnamen miliknya."
            )
        if user["role"] == ROLE_COMMITTEE and not self._repo.is_staff_assigned(
            tournament["id"], user["id"]
        ):
            raise DomainForbiddenError(
                "Panitia hanya dapat memverifikasi registrasi pada turnamen yang ditugaskan."
            )

        new_status = str(payload.get("status") or "").strip().lower()
        if new_status not in REGISTRATION_STATUSES:
            raise DomainValidationError(
                f"Status registrasi '{new_status}' tidak valid.",
                {"valid_statuses": list(REGISTRATION_STATUSES)},
            )

        notes = str(payload.get("notes") or "").strip()
        updated = self._repo.update_registration_status(
            registration_id=reg["id"],
            status=new_status,
            verified_by=user["id"],
            notes=notes,
        )
        if not updated:
            raise DomainNotFoundError("Data registrasi tidak ditemukan.")

        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="registration",
            entity_id=reg["id"],
            action="REGISTRATION_STATUS_UPDATED",
            details={"status": new_status, "notes": notes},
        )
        return updated
