"""Service untuk manajemen pertandingan, skor, dan pergerakan bracket."""

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
    parse_best_of,
    parse_strict_int,
    validate_bracket_graph,
    validate_match_score,
)
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol

MIN_OVERRIDE_NOTES_LENGTH = 4
LOCKED_TOURNAMENT_STATUSES = ("completed", "cancelled")
STARTED_MATCH_STATUSES = ("ongoing", "completed")


class MatchService:
    """Mengelola alur bracket, input skor pertandingan, dan validasi."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def _verify_tournament_staff_access(
        self, user: dict[str, Any], tournament: dict[str, Any]
    ) -> None:
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat mengelola pertandingan pada turnamen miliknya.",
                {"tournament_id": tournament["id"], "user_id": user["id"]},
            )
        if user["role"] == ROLE_COMMITTEE and not self._repo.is_staff_assigned(
            tournament["id"], user["id"]
        ):
            raise DomainForbiddenError(
                "Panitia hanya dapat mengelola pertandingan pada turnamen yang ditugaskan.",
                {"tournament_id": tournament["id"], "user_id": user["id"]},
            )

    def get_match(self, match_id: str) -> dict[str, Any]:
        match = self._repo.get_match_by_id(match_id)
        if not match:
            raise DomainNotFoundError(
                "Pertandingan tidak ditemukan.", {"match_id": match_id}
            )
        return match

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
        if tournament["status"] in LOCKED_TOURNAMENT_STATUSES:
            raise DomainConflictError(
                f"Bracket tidak dapat dibuat ulang untuk turnamen berstatus '{tournament['status']}'.",
                {"tournament_id": tournament["id"], "status": tournament["status"]},
            )

        payload = payload or {}
        raw_best_of = payload.get("best_of")
        if raw_best_of is None:
            raw_best_of = tournament.get("best_of") or 3
        best_of = parse_best_of(raw_best_of)

        existing_matches = self._repo.list_matches_by_tournament(tournament["id"])
        if any(m.get("status") in STARTED_MATCH_STATUSES for m in existing_matches):
            raise DomainConflictError(
                "Bracket tidak dapat dibuat ulang karena sudah ada pertandingan yang berjalan atau selesai.",
                {"tournament_id": tournament["id"]},
            )

        if "team_ids" in payload and payload["team_ids"] is not None:
            raw_team_ids = payload["team_ids"]
            if not isinstance(raw_team_ids, list):
                raise DomainValidationError(
                    "Field team_ids harus berupa daftar ID tim (array).", {"field": "team_ids"}
                )
            team_ids: list[str] = []
            for idx, tid in enumerate(raw_team_ids):
                if not isinstance(tid, str) or not tid.strip():
                    raise DomainValidationError(
                        "Setiap item team_ids harus berupa ID tim yang valid.",
                        {"field": "team_ids", "index": idx},
                    )
                clean_tid = tid.strip()
                if not self._repo.get_team_by_id(clean_tid):
                    raise DomainNotFoundError(
                        "Tim peserta bracket tidak ditemukan.",
                        {"field": "team_ids", "team_id": clean_tid},
                    )
                team_ids.append(clean_tid)
        else:
            regs = self._repo.list_registrations_by_tournament(tournament["id"])
            approved_regs = [r for r in regs if r["status"] == "approved"]
            approved_regs.sort(key=lambda r: (r.get("seed_number") or 999))
            team_ids = [r["team_id"] for r in approved_regs]
        generated_matches = SingleEliminationBracketEngine.generate_bracket(
            tournament_id=tournament["id"],
            team_ids=team_ids,
            best_of=best_of,
        )
        stored_matches = self._repo.replace_tournament_matches(
            tournament["id"], generated_matches
        )
        if tournament["status"] in ("draft", "open_registration", "registration_closed"):
            self._repo.transition_tournament_status(tournament["id"], "ongoing")

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
        if tournament["status"] == "cancelled":
            raise DomainConflictError(
                "Hasil pertandingan tidak dapat disahkan karena turnamen telah dibatalkan.",
                {"tournament_id": tournament["id"], "status": tournament["status"]},
            )
        if match["status"] == "bye":
            raise DomainConflictError(
                "Pertandingan BYE otomatis dimenangkan dan tidak dapat diisi skor secara manual.",
                {"match_id": match_id, "status": match["status"]},
            )

        raw_force_override = payload.get("force_override", False)
        if not isinstance(raw_force_override, bool):
            raise DomainValidationError(
                "Field force_override harus berupa boolean (true/false).",
                {"field": "force_override"},
            )
        force_override = raw_force_override

        raw_idem_key = payload.get("idempotency_key")
        idempotency_key: str | None = None
        if raw_idem_key is not None:
            if not isinstance(raw_idem_key, str) or not raw_idem_key.strip():
                raise DomainValidationError(
                    "Field idempotency_key harus berupa string tidak kosong.",
                    {"field": "idempotency_key"},
                )
            idempotency_key = raw_idem_key.strip()
            if len(idempotency_key) > 128:
                raise DomainValidationError(
                    "Field idempotency_key maksimal 128 karakter.",
                    {"field": "idempotency_key"},
                )

        if match["status"] == "completed" and not force_override and idempotency_key is None:
            raise DomainConflictError(
                "Hasil pertandingan ini sudah disahkan dan dikunci. "
                "Gunakan otorisasi force_override beserta catatan audit untuk mengubahnya.",
                {"match_id": match_id, "status": match["status"]},
            )

        raw_notes = payload.get("notes")
        if raw_notes is not None and not isinstance(raw_notes, str):
            raise DomainValidationError("Field notes harus berupa teks.", {"field": "notes"})
        notes = (raw_notes or "").strip()
        if force_override and len(notes) < MIN_OVERRIDE_NOTES_LENGTH:
            raise DomainValidationError(
                "Koreksi hasil (force_override) wajib menyertakan alasan audit "
                f"minimal {MIN_OVERRIDE_NOTES_LENGTH} karakter.",
                {"field": "notes"},
            )

        if not match.get("team_a_id") or not match.get("team_b_id"):
            raise DomainValidationError(
                "Pertandingan belum memiliki kedua tim peserta (Team A dan Team B wajib terisi).",
                {"team_a_id": match.get("team_a_id"), "team_b_id": match.get("team_b_id")},
            )

        if "score_a" not in payload or "score_b" not in payload:
            raise DomainValidationError("Field score_a dan score_b wajib diisi.")

        score_a = parse_strict_int(payload["score_a"], "score_a")
        score_b = parse_strict_int(payload["score_b"], "score_b")

        best_of = parse_best_of(match.get("best_of") or tournament.get("best_of") or 3)
        winning_side = validate_match_score(
            score_a=score_a,
            score_b=score_b,
            best_of=best_of,
            allow_draw=bool(tournament.get("allow_draw", False)),
        )
        winner_team_id = (
            match["team_a_id"] if winning_side == "A" else match["team_b_id"]
        )

        next_match_id = match.get("next_match_id")
        next_slot = match.get("next_slot")
        slot_field = "team_a_id" if next_slot == "A" else "team_b_id"
        if idempotency_key is None:
            if next_match_id and next_slot in ("A", "B"):
                self._guard_downstream_match(match, next_match_id, slot_field, winner_team_id)
            else:
                self._validate_grand_final_completion(tournament, match)

        return self._repo.submit_match_result_atomic(
            match_id=match["id"],
            score_a=score_a,
            score_b=score_b,
            winner_team_id=winner_team_id,
            notes=notes,
            force_override=force_override,
            actor_id=user["id"],
            game_number=1,
            idempotency_key=idempotency_key,
        )

    def _guard_downstream_match(
        self,
        match: dict[str, Any],
        next_match_id: str,
        slot_field: str,
        winner_team_id: str,
    ) -> None:
        """Reject a winner change once the next-round match has started or finished.

        Rewriting the slot at that point would leave the next match's result pointing at a team
        that no longer plays in it, which corrupts the bracket and standings.
        """
        next_match = self._repo.get_match_by_id(next_match_id)
        if not next_match or next_match.get(slot_field) == winner_team_id:
            return
        if next_match.get("status") in STARTED_MATCH_STATUSES or next_match.get("winner_team_id"):
            raise DomainConflictError(
                "Pemenang tidak dapat diubah karena pertandingan babak berikutnya sudah "
                "berjalan atau selesai. Koreksi pertandingan lanjutan terlebih dahulu.",
                {
                    "match_id": match["id"],
                    "next_match_id": next_match_id,
                    "next_match_status": next_match.get("status"),
                },
            )

    def _validate_grand_final_completion(
        self, tournament: dict[str, Any], match: dict[str, Any]
    ) -> None:
        """Verify full bracket graph structure and prerequisite completion before closing tournament."""
        if tournament["status"] not in ("ongoing", "completed"):
            raise DomainConflictError(
                "Grand Final hanya dapat disahkan ketika turnamen berstatus 'ongoing' atau 'completed'.",
                {"tournament_id": tournament["id"], "status": tournament["status"]},
            )

        tournament_matches = self._repo.list_matches_by_tournament(tournament["id"])
        validate_bracket_graph(
            tournament["id"],
            tournament_matches,
            pending_final_id=match["id"],
        )
