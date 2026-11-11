"""Single Elimination Bracket Engine and score validation rules.

Owner: Adriel (Tournament & Match System Developer)

Rules enforced (Master Prompt Section 10):
1. For 8 teams: Quarter Final (4 matches) -> Semi Final (2 matches) -> Grand Final (1 match).
2. Non-power-of-two team counts (e.g. 5, 6, 7 teams) are padded to the next power of two
   (e.g. 8 slots). Top-seeded teams receive a Round 1 BYE (`status="bye"`) and advance
   automatically to their Round 2 slot (`next_match_id`, `next_slot`).
3. Scores are validated against `best_of` (1, 3, 5, 7) and `allow_draw`.
4. Ties/draws are never resolved randomly; if a single-elimination match is tied, validation fails.
5. Unplayed matches (`scheduled` / `ongoing`) never have a `winner_team_id`.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.contracts.dtos import VALID_BEST_OF
from backend.core.exceptions import DomainValidationError


def next_power_of_two(n: int) -> int:
    """Return the smallest power of two greater than or equal to `n` (minimum 2)."""
    if n < 2:
        raise DomainValidationError(
            "Pembuatan bracket membutuhkan minimal 2 tim peserta.",
            {"team_count": n},
        )
    power = 1
    while power < n:
        power *= 2
    return power


def get_round_name(round_number: int, total_rounds: int) -> str:
    """Return human-readable round name for Single Elimination brackets."""
    remaining = total_rounds - round_number
    if remaining == 0:
        return "Grand Final"
    if remaining == 1:
        return "Semi Final"
    if remaining == 2:
        return "Quarter Final"
    teams_in_round = 2 ** (remaining + 1)
    return f"Round of {teams_in_round}"


def validate_match_score(
    score_a: int,
    score_b: int,
    best_of: int = 3,
    allow_draw: bool = False,
) -> str:
    """Validate match scores according to `best_of` series rules and return winning side ('A' or 'B').

    Raises `DomainValidationError` if scores are negative, tied, or impossible for the `best_of` format.
    """
    if not isinstance(score_a, int) or not isinstance(score_b, int):
        raise DomainValidationError("Skor pertandingan harus berupa bilangan bulat (integer).")

    if score_a < 0 or score_b < 0:
        raise DomainValidationError(
            "Skor pertandingan tidak boleh bernilai negatif.",
            {"score_a": score_a, "score_b": score_b},
        )

    if best_of not in VALID_BEST_OF:
        raise DomainValidationError(
            f"Format best_of '{best_of}' tidak valid. Gunakan {VALID_BEST_OF}.",
            {"best_of": best_of},
        )

    if score_a == score_b:
        if allow_draw:
            raise DomainValidationError(
                "Pada sistem gugur (Single Elimination), pertandingan wajib memiliki pemenang untuk maju ke babak berikutnya.",
                {"score_a": score_a, "score_b": score_b},
            )
        raise DomainValidationError(
            "Hasil seri tidak diizinkan. Pertandingan harus memiliki pemenang yang sah.",
            {"score_a": score_a, "score_b": score_b},
        )

    wins_required = (best_of // 2) + 1
    winner_score = max(score_a, score_b)
    loser_score = min(score_a, score_b)

    if winner_score != wins_required:
        raise DomainValidationError(
            f"Pada format Best of {best_of}, pemenang wajib mencapai tepat {wins_required} kemenangan.",
            {
                "best_of": best_of,
                "wins_required": wins_required,
                "score_a": score_a,
                "score_b": score_b,
            },
        )

    if loser_score >= wins_required or (score_a + score_b) > best_of:
        raise DomainValidationError(
            f"Kombinasi skor {score_a}-{score_b} melebihi batas jumlah game Best of {best_of}.",
            {"best_of": best_of, "score_a": score_a, "score_b": score_b},
        )

    return "A" if score_a > score_b else "B"


class SingleEliminationBracketEngine:
    """Pure domain engine for generating and progressing Single Elimination brackets."""

    @staticmethod
    def generate_bracket(
        tournament_id: str,
        team_ids: list[str],
        best_of: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate a complete Single Elimination bracket tree for `team_ids`.

        Supports power-of-two counts (e.g., 4, 8, 16) as well as non-power-of-two counts
        (e.g., 3, 5, 6, 7) by assigning automatic Round 1 BYEs to top seeds.
        """
        num_teams = len(team_ids)
        if num_teams < 2:
            raise DomainValidationError(
                "Minimal 2 tim terverifikasi diperlukan untuk membuat bracket.",
                {"team_count": num_teams},
            )
        if len(set(team_ids)) != num_teams:
            raise DomainValidationError("Terdapat duplikasi tim dalam daftar peserta bracket.")

        bracket_size = next_power_of_two(num_teams)
        total_rounds = int(math.log2(bracket_size))
        num_byes = bracket_size - num_teams
        now = datetime.now(timezone.utc).isoformat()

        rounds_matches: dict[int, list[dict[str, Any]]] = {}
        for r in range(1, total_rounds + 1):
            matches_in_round = bracket_size // (2**r)
            round_name = get_round_name(r, total_rounds)
            rounds_matches[r] = []
            for m_idx in range(1, matches_in_round + 1):
                rounds_matches[r].append(
                    {
                        "id": str(uuid.uuid4()),
                        "tournament_id": tournament_id,
                        "round_number": r,
                        "round_name": round_name,
                        "match_number": m_idx,
                        "team_a_id": None,
                        "team_b_id": None,
                        "score_a": 0,
                        "score_b": 0,
                        "winner_team_id": None,
                        "status": "scheduled",
                        "best_of": best_of,
                        "scheduled_at": now,
                        "completed_at": None,
                        "next_match_id": None,
                        "next_slot": None,
                    }
                )

        # Link each round's matches to the next round's match and slot ('A' or 'B')
        for r in range(1, total_rounds):
            for idx, match in enumerate(rounds_matches[r]):
                next_match = rounds_matches[r + 1][idx // 2]
                next_slot = "A" if (idx % 2 == 0) else "B"
                match["next_match_id"] = next_match["id"]
                match["next_slot"] = next_slot

        # Populate Round 1 pairings (with BYE handling for non-power-of-two counts)
        round_1 = rounds_matches[1]
        first_round_matches_count = len(round_1)

        # Top `num_byes` seeds get a BYE in the first `num_byes` matches of Round 1;
        # remaining teams are paired sequentially in the remaining matches.
        team_cursor = 0
        for m_idx in range(first_round_matches_count):
            match = round_1[m_idx]
            if m_idx < num_byes:
                team_a = team_ids[team_cursor]
                team_cursor += 1
                match["team_a_id"] = team_a
                match["team_b_id"] = None
                match["status"] = "bye"
                match["winner_team_id"] = team_a
                match["completed_at"] = now
            else:
                match["team_a_id"] = team_ids[team_cursor]
                match["team_b_id"] = team_ids[team_cursor + 1]
                team_cursor += 2
                match["status"] = "scheduled"
                match["winner_team_id"] = None

        # Advance any Round 1 BYE winners immediately into Round 2 slots
        if total_rounds >= 2:
            round_2_by_id = {m["id"]: m for m in rounds_matches[2]}
            for match in round_1:
                if match["status"] == "bye" and match["winner_team_id"] and match["next_match_id"]:
                    target = round_2_by_id[match["next_match_id"]]
                    if match["next_slot"] == "A":
                        target["team_a_id"] = match["winner_team_id"]
                    else:
                        target["team_b_id"] = match["winner_team_id"]

        all_matches: list[dict[str, Any]] = []
        for r in range(1, total_rounds + 1):
            all_matches.extend(rounds_matches[r])
        return all_matches
