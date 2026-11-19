"""Algoritma Single Elimination bracket engine dan validasi skor pertandingan."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.contracts.dtos import VALID_BEST_OF
from backend.core.exceptions import DomainValidationError


def next_power_of_two(n: int) -> int:
    """Menghitung bilangan pangkat dua terkecil yang lebih besar atau sama dengan n.

    Digunakan untuk menentukan ukuran bracket dan alokasi slot bye.
    """
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
    """Mengembalikan nama babak turnamen berdasarkan posisi relatif terhadap final."""
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
    score_a: int, score_b: int, best_of: int = 3, allow_draw: bool = False
) -> str:
    """Validasi skor pertandingan sistem gugur berdasarkan format Best of N.

    Mengembalikan 'A' jika Tim A menang, atau 'B' jika Tim B menang.
    Menolak skor negatif, hasil seri, atau skor yang tidak memenuhi syarat kemenangan.
    """
    if not isinstance(score_a, int) or not isinstance(score_b, int):
        raise DomainValidationError(
            "Skor pertandingan harus berupa angka bulat.",
            {"score_a": score_a, "score_b": score_b},
        )

    if score_a < 0 or score_b < 0:
        raise DomainValidationError(
            "Skor pertandingan tidak boleh negatif.",
            {"score_a": score_a, "score_b": score_b},
        )

    if best_of not in VALID_BEST_OF:
        raise DomainValidationError(
            f"Format best_of '{best_of}' tidak valid.",
            {"best_of": best_of, "valid_options": list(VALID_BEST_OF)},
        )

    if score_a == score_b:
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
                "score_a": score_a,
                "score_b": score_b,
                "best_of": best_of,
                "wins_required": wins_required,
            },
        )

    if loser_score >= wins_required or (score_a + score_b) > best_of:
        raise DomainValidationError(
            f"Kombinasi skor {score_a}-{score_b} melebihi batas jumlah game Best of {best_of}.",
            {
                "score_a": score_a,
                "score_b": score_b,
                "best_of": best_of,
            },
        )

    return "A" if score_a > score_b else "B"


class SingleEliminationBracketEngine:
    """Engine pembangkit bagan Single Elimination turnamen esports."""

    @staticmethod
    def generate_bracket(
        tournament_id: str, team_ids: list[str], best_of: int = 3
    ) -> list[dict[str, Any]]:
        """Membangkitkan seluruh pertandingan dari ronde pertama hingga Grand Final.

        Mendukung jumlah tim pangkat dua maupun bukan pangkat dua dengan penanganan BYE otomatis
        dan pemindahan langsung tim penerima BYE ke babak Semi Final / babak selanjutnya.
        """
        num_teams = len(team_ids)
        if num_teams < 2:
            raise DomainValidationError(
                "Minimal 2 tim terverifikasi diperlukan untuk membuat bracket.",
                {"team_count": num_teams},
            )
        if len(set(team_ids)) != num_teams:
            raise DomainValidationError(
                "Terdapat duplikasi tim dalam daftar peserta bracket.",
                {"team_count": num_teams, "unique_teams": len(set(team_ids))},
            )

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

        # Sambungkan setiap pertandingan ke babak berikutnya
        for r in range(1, total_rounds):
            for idx, match in enumerate(rounds_matches[r]):
                next_match = rounds_matches[r + 1][idx // 2]
                next_slot = "A" if (idx % 2 == 0) else "B"
                match["next_match_id"] = next_match["id"]
                match["next_slot"] = next_slot

        # Tempatkan peserta pada babak pertama dengan alokasi BYE di slot teratas
        round_1 = rounds_matches[1]
        team_cursor = 0
        for m_idx in range(len(round_1)):
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

        # Otomatis majukan penerima BYE ke babak berikutnya
        if total_rounds >= 2:
            round_2_by_id = {m["id"]: m for m in rounds_matches[2]}
            for match in round_1:
                if (
                    match["status"] == "bye"
                    and match["winner_team_id"]
                    and match["next_match_id"]
                ):
                    target = round_2_by_id[match["next_match_id"]]
                    if match["next_slot"] == "A":
                        target["team_a_id"] = match["winner_team_id"]
                    else:
                        target["team_b_id"] = match["winner_team_id"]

        all_matches: list[dict[str, Any]] = []
        for r in range(1, total_rounds + 1):
            all_matches.extend(rounds_matches[r])
        return all_matches
