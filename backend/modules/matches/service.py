"""Match management and bracket progression application service.

Owner: Adriel (Tournament & Match System Developer)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.contracts.dtos import ROLE_COMMITTEE, ROLE_ORGANIZER
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.auth.permissions import require_permission
from backend.modules.matches.bracket_engine import (
    SingleEliminationBracketEngine,
    validate_match_score,
)
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol


class MatchService:
    """Application service managing tournament brackets, match scores, and round advancement."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def _verify_tournament_staff_access(
        self, user: dict[str, Any], tournament: dict[str, Any]
    ) -> None:
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat mengelola pertandingan pada turnamen miliknya."
            )
        if user["role"] == ROLE_COMMITTEE and not self._repo.is_staff_assigned(
            tournament["id"], user["id"]
        ):
            raise DomainForbiddenError(
                "Panitia hanya dapat mengelola pertandingan pada turnamen yang ditugaskan."
            )

    def get_tournament_bracket(self, tournament_id: str) -> dict[str, Any]:
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )
        matches = self._repo.list_matches_by_tournament(tournament["id"])
        rounds_map: dict[int, dict[str, Any]] = {}
        for m in matches:
            r_num = m["round_number"]
            if r_num not in rounds_map:
                rounds_map[r_num] = {
                    "round_number": r_num,
                    "round_name": m["round_name"],
                    "matches": [],
                }
            rounds_map[r_num]["matches"].append(m)

        rounds_list = [rounds_map[k] for k in sorted(rounds_map.keys())]
        return {
            "tournament_id": tournament["id"],
            "tournament_title": tournament["title"],
            "format": tournament["format"],
            "best_of": tournament["best_of"],
            "total_matches": len(matches),
            "rounds": rounds_list,
            "matches": matches,
        }

    def generate_bracket(
        self,
        actor: dict[str, Any] | None,
        tournament_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        user = require_permission(actor, "bracket:generate")
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )
        self._verify_tournament_staff_access(user, tournament)

        payload = payload or {}
        explicit_team_ids = payload.get("team_ids")
        if explicit_team_ids and isinstance(explicit_team_ids, list):
            team_ids = [str(tid) for tid in explicit_team_ids]
        else:
            regs = self._repo.list_registrations_by_tournament(tournament["id"])
            approved_regs = [r for r in regs if r["status"] == "approved"]
            approved_regs.sort(key=lambda r: (r.get("seed_number") or 999))
            team_ids = [r["team_id"] for r in approved_regs]

        best_of = int(payload.get("best_of") or tournament.get("best_of") or 3)
        generated_matches = SingleEliminationBracketEngine.generate_bracket(
            tournament_id=tournament["id"],
            team_ids=team_ids,
            best_of=best_of,
        )
        stored_matches = self._repo.replace_tournament_matches(
            tournament["id"], generated_matches
        )
        if tournament["status"] in ("draft", "open_registration", "registration_closed"):
            self._repo.update_tournament(tournament["id"], {"status": "ongoing"})

        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="bracket",
            entity_id=tournament["id"],
            action="BRACKET_GENERATED",
            details={"team_count": len(team_ids), "total_matches": len(stored_matches)},
        )
        return self.get_tournament_bracket(tournament["id"])

    def submit_match_result(
        self,
        actor: dict[str, Any] | None,
        match_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        user = require_permission(actor, "match:submit_result")
        match = self._repo.get_match_by_id(match_id)
        if not match:
            raise DomainNotFoundError(
                "Pertandingan tidak ditemukan.", {"match_id": match_id}
            )

        tournament = self._repo.get_tournament_by_id(match["tournament_id"])
        if not tournament:
            raise DomainNotFoundError("Turnamen pertandingan tidak ditemukan.")
        self._verify_tournament_staff_access(user, tournament)

        force_override = bool(payload.get("force_override", False))
        if match["status"] == "completed" and not force_override:
            raise DomainConflictError(
                "Hasil pertandingan ini sudah disahkan dan dikunci. "
                "Gunakan otorisasi force_override beserta catatan audit untuk mengubahnya.",
                {"match_id": match_id, "status": match["status"]},
            )

        if not match.get("team_a_id") or not match.get("team_b_id"):
            raise DomainValidationError(
                "Pertandingan belum memiliki kedua tim peserta (Team A dan Team B wajib terisi).",
                {"team_a_id": match.get("team_a_id"), "team_b_id": match.get("team_b_id")},
            )

        if "score_a" not in payload or "score_b" not in payload:
            raise DomainValidationError("Field score_a dan score_b wajib diisi.")

        try:
            score_a = int(payload["score_a"])
            score_b = int(payload["score_b"])
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("score_a dan score_b harus berupa angka bulat.") from exc

        best_of = int(match.get("best_of") or tournament.get("best_of") or 3)
        winning_side = validate_match_score(
            score_a=score_a,
            score_b=score_b,
            best_of=best_of,
            allow_draw=bool(tournament.get("allow_draw", False)),
        )
        winner_team_id = (
            match["team_a_id"] if winning_side == "A" else match["team_b_id"]
        )
        now = datetime.now(timezone.utc).isoformat()
        notes = str(payload.get("notes") or "").strip()

        updated_match = self._repo.update_match(
            match["id"],
            {
                "score_a": score_a,
                "score_b": score_b,
                "winner_team_id": winner_team_id,
                "status": "completed",
                "completed_at": now,
            },
        )

        self._repo.record_match_result(
            {
                "match_id": match["id"],
                "game_number": 1,
                "score_a": score_a,
                "score_b": score_b,
                "winner_team_id": winner_team_id,
                "notes": notes,
                "verified_by": user["id"],
            }
        )

        # Advance winner automatically to next match slot if applicable
        updated_next_match: dict[str, Any] | None = None
        next_match_id = match.get("next_match_id")
        next_slot = match.get("next_slot")
        if next_match_id and next_slot in ("A", "B"):
            slot_field = "team_a_id" if next_slot == "A" else "team_b_id"
            updated_next_match = self._repo.update_match(
                next_match_id, {slot_field: winner_team_id}
            )
        elif not next_match_id:
            # Grand Final completed -> mark tournament completed
            self._repo.update_tournament(tournament["id"], {"status": "completed"})

        action_name = (
            "MATCH_RESULT_OVERRIDDEN" if force_override else "MATCH_RESULT_VERIFIED"
        )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="match",
            entity_id=match["id"],
            action=action_name,
            details={
                "score_a": score_a,
                "score_b": score_b,
                "winner_team_id": winner_team_id,
                "next_match_id": next_match_id,
                "next_slot": next_slot,
                "notes": notes,
            },
        )

        return {
            "match": updated_match,
            "next_match": updated_next_match,
        }
