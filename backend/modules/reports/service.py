"""Tournament statistics, summary report, and standings service.

Owner: Anisa (REST API, Reporting & Testing Developer)
"""

from __future__ import annotations

from typing import Any

from backend.contracts.dtos import ROLE_COMMITTEE
from backend.core.exceptions import DomainNotFoundError
from backend.modules.auth.permissions import is_tournament_manager
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol


class ReportService:
    """Application service calculating tournament reports and team standings."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def _compute_standings(
        self,
        regs: list[dict[str, Any]],
        matches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        approved_regs = [r for r in regs if r.get("status") == "approved"]
        needs_team_lookup = any(
            not r.get("team_name") or not r.get("team_tag") for r in approved_regs
        )
        teams_by_id = (
            {t["id"]: t for t in self._repo.list_teams()} if needs_team_lookup else {}
        )

        stats: dict[str, dict[str, Any]] = {}
        for reg in approved_regs:
            tid = reg["team_id"]
            team = teams_by_id.get(tid, {})
            stats[tid] = {
                "team_id": tid,
                "team_name": team.get("name") or reg.get("team_name") or "Unknown Team",
                "team_tag": team.get("tag") or reg.get("team_tag") or "---",
                "seed_number": reg.get("seed_number"),
                "matches_played": 0,
                "matches_won": 0,
                "matches_lost": 0,
                "games_won": 0,
                "games_lost": 0,
                "highest_round_reached": 1,
                "highest_round_name": "Participant",
                "placement_label": "Peserta Aktif",
            }

        max_round = max((m["round_number"] for m in matches), default=1)
        for m in matches:
            r_num = m["round_number"]
            r_name = m["round_name"]
            for slot_tid in (m.get("team_a_id"), m.get("team_b_id")):
                if slot_tid and slot_tid in stats:
                    if r_num >= stats[slot_tid]["highest_round_reached"]:
                        stats[slot_tid]["highest_round_reached"] = r_num
                        stats[slot_tid]["highest_round_name"] = r_name

            if m["status"] == "completed":
                tid_a = m.get("team_a_id")
                tid_b = m.get("team_b_id")
                winner_id = m.get("winner_team_id")
                score_a = int(m.get("score_a", 0))
                score_b = int(m.get("score_b", 0))

                if tid_a in stats:
                    stats[tid_a]["matches_played"] += 1
                    stats[tid_a]["games_won"] += score_a
                    stats[tid_a]["games_lost"] += score_b
                    if winner_id == tid_a:
                        stats[tid_a]["matches_won"] += 1
                    else:
                        stats[tid_a]["matches_lost"] += 1
                        stats[tid_a]["placement_label"] = f"Gugur di {r_name}"

                if tid_b in stats:
                    stats[tid_b]["matches_played"] += 1
                    stats[tid_b]["games_won"] += score_b
                    stats[tid_b]["games_lost"] += score_a
                    if winner_id == tid_b:
                        stats[tid_b]["matches_won"] += 1
                    else:
                        stats[tid_b]["matches_lost"] += 1
                        stats[tid_b]["placement_label"] = f"Gugur di {r_name}"

                if r_num == max_round and winner_id in stats:
                    stats[winner_id]["placement_label"] = "Juara 1 (Champion)"
                    loser_id = tid_b if winner_id == tid_a else tid_a
                    if loser_id and loser_id in stats:
                        stats[loser_id]["placement_label"] = "Juara 2 (Runner-Up)"

        def _placement_tier(row: dict[str, Any]) -> int:
            label = row.get("placement_label", "")
            if label == "Juara 1 (Champion)":
                return 0
            if label == "Juara 2 (Runner-Up)":
                return 1
            return 2

        standings = list(stats.values())
        standings.sort(
            key=lambda s: (
                _placement_tier(s),
                -s["highest_round_reached"],
                -s["matches_won"],
                -(s["games_won"] - s["games_lost"]),
                s["seed_number"] or 999,
            )
        )
        for idx, row in enumerate(standings, start=1):
            row["rank"] = idx
        return standings

    def get_tournament_standings(self, tournament_id: str) -> list[dict[str, Any]]:
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )

        regs = self._repo.list_registrations_by_tournament(tournament["id"])
        matches = self._repo.list_matches_by_tournament(tournament["id"])
        return self._compute_standings(regs, matches)

    def get_tournament_report(
        self, tournament_id: str, actor: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )

        is_manager = is_tournament_manager(self._repo, actor, tournament)
        if (
            actor
            and actor.get("is_active", True)
            and str(actor.get("role") or "").strip().lower() == ROLE_COMMITTEE
        ):
            tournament["is_assigned_committee"] = is_manager

        regs = self._repo.list_registrations_by_tournament(tournament["id"])
        matches = self._repo.list_matches_by_tournament(tournament["id"])
        announcements = self._repo.list_announcements_by_tournament(tournament["id"])
        standings = self._compute_standings(regs, matches)

        total_matches = len(matches)
        completed_matches = sum(1 for m in matches if m["status"] in ("completed", "bye"))
        scheduled_matches = sum(1 for m in matches if m["status"] == "scheduled")
        completion_rate = (
            round((completed_matches / total_matches) * 100, 1) if total_matches > 0 else 0.0
        )

        champion = next(
            (s for s in standings if "Juara 1" in s.get("placement_label", "")),
            None,
        )

        summary: dict[str, Any] = {
            "max_teams": tournament["max_teams"],
            "approved_teams": sum(1 for r in regs if r["status"] == "approved"),
            "total_matches": total_matches,
            "completed_matches": completed_matches,
            "scheduled_matches": scheduled_matches,
            "completion_percentage": completion_rate,
            "announcements_count": len(announcements),
            "prize_pool": tournament["prize_pool"],
            "champion_team": champion["team_name"] if champion else None,
        }
        if is_manager:
            try:
                recent_activity = self._repo.list_activity_logs(tournament["id"], limit=10)[:10]
            except TypeError:
                recent_activity = self._repo.list_activity_logs(tournament["id"])[:10]
            summary["total_registrations"] = len(regs)
            summary["pending_registrations"] = sum(
                1 for r in regs if r["status"] == "pending"
            )
        else:
            recent_activity = []

        return {
            "tournament": tournament,
            "summary": summary,
            "standings": standings,
            "recent_activity": recent_activity,
        }
