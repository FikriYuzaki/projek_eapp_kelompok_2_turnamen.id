"""Algoritma Single Elimination bracket engine dan validasi skor pertandingan."""

from __future__ import annotations

import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.contracts.dtos import VALID_BEST_OF
from backend.core.exceptions import DomainConflictError, DomainValidationError

_INTEGER_STRING = re.compile(r"^[+-]?\d+$")


def parse_strict_int(value: Any, field: str) -> int:
    """Parse an integer field without silently truncating floats or accepting booleans.

    Python treats `True` as `1`, so booleans are rejected explicitly. Digit-only strings are
    accepted for compatibility with form inputs; decimal strings such as "2.5" are rejected.
    """
    if isinstance(value, bool):
        raise DomainValidationError(
            f"Field {field} harus berupa angka bulat, bukan boolean.", {"field": field}
        )
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _INTEGER_STRING.match(value.strip()):
        return int(value.strip())
    raise DomainValidationError(
        f"Field {field} harus berupa angka bulat.", {"field": field, "value": str(value)}
    )


def parse_best_of(value: Any) -> int:
    best_of = parse_strict_int(value, "best_of")
    if best_of not in VALID_BEST_OF:
        raise DomainValidationError(
            f"Format best_of '{best_of}' tidak valid.",
            {"field": "best_of", "best_of": best_of, "valid_options": list(VALID_BEST_OF)},
        )
    return best_of


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
    if (
        isinstance(score_a, bool)
        or isinstance(score_b, bool)
        or not isinstance(score_a, int)
        or not isinstance(score_b, int)
    ):
        raise DomainValidationError(
            "Skor pertandingan harus berupa angka bulat.",
            {"score_a": score_a, "score_b": score_b},
        )

    if score_a < 0 or score_b < 0:
        raise DomainValidationError(
            "Skor pertandingan tidak boleh negatif.",
            {"score_a": score_a, "score_b": score_b},
        )

    if isinstance(best_of, bool) or best_of not in VALID_BEST_OF:
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
        best_of = parse_best_of(best_of)
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


def validate_bracket_graph(
    tournament_id: str,
    matches: list[dict[str, Any]],
    *,
    pending_final_id: str | None = None,
) -> dict[str, Any]:
    """Prove all matches form one acyclic tree converging on a single Grand Final.

    When `pending_final_id` is supplied, validates the pre-completion state where every
    feeder match is already `completed` or `bye` and only `pending_final_id` awaits
    final result confirmation. Otherwise requires the unique Grand Final to already be
    `completed` with a valid participant winner.
    """
    if not matches:
        raise DomainConflictError(
            "Turnamen belum memiliki struktur bracket pertandingan.",
            {"tournament_id": tournament_id},
        )

    match_by_id: dict[str, dict[str, Any]] = {}
    for item in matches:
        mid = item.get("id")
        if not mid or item.get("tournament_id") != tournament_id or mid in match_by_id:
            raise DomainConflictError(
                "Struktur bracket tidak valid: ditemukan ID pertandingan tidak konsisten.",
                {"tournament_id": tournament_id, "match_id": mid},
            )
        match_by_id[mid] = item

    seen_feeder_slots: set[tuple[str, str]] = set()
    for mid, item in match_by_id.items():
        next_id = item.get("next_match_id")
        next_slot = item.get("next_slot")
        if next_id is not None:
            if next_id == mid:
                raise DomainConflictError(
                    "Struktur bracket tidak valid: ditemukan self-loop pada pertandingan.",
                    {"tournament_id": tournament_id, "match_id": mid},
                )
            target = match_by_id.get(next_id)
            if target is None:
                raise DomainConflictError(
                    "Struktur bracket tidak valid: next_match_id menunjuk ke luar turnamen atau tidak ditemukan.",
                    {
                        "tournament_id": tournament_id,
                        "match_id": mid,
                        "next_match_id": next_id,
                    },
                )
            if next_slot not in ("A", "B"):
                raise DomainConflictError(
                    "Struktur bracket tidak valid: next_slot wajib 'A' atau 'B' saat next_match_id terisi.",
                    {
                        "tournament_id": tournament_id,
                        "match_id": mid,
                        "next_slot": next_slot,
                    },
                )
            slot_key = (next_id, next_slot)
            if slot_key in seen_feeder_slots:
                raise DomainConflictError(
                    "Struktur bracket tidak valid: duplikasi feeder slot menuju pertandingan lanjutan.",
                    {
                        "tournament_id": tournament_id,
                        "next_match_id": next_id,
                        "next_slot": next_slot,
                    },
                )
            seen_feeder_slots.add(slot_key)

            cur_round = item.get("round_number")
            nxt_round = target.get("round_number")
            if cur_round is not None and nxt_round is not None and int(cur_round) >= int(nxt_round):
                raise DomainConflictError(
                    "Struktur bracket tidak valid: round_number feeder tidak boleh melebihi babak lanjutan.",
                    {
                        "tournament_id": tournament_id,
                        "match_id": mid,
                        "next_match_id": next_id,
                    },
                )

    finals = [m for m in matches if m.get("next_match_id") is None]
    if len(finals) != 1:
        raise DomainConflictError(
            "Struktur bracket tidak valid: harus terdapat tepat satu pertandingan Grand Final.",
            {
                "tournament_id": tournament_id,
                "final_match_ids": [m.get("id") for m in finals],
            },
        )

    grand_final = finals[0]
    gf_id = grand_final["id"]
    if grand_final.get("next_slot") not in (None, ""):
        raise DomainConflictError(
            "Struktur bracket tidak valid: Grand Final tidak boleh memiliki next_slot.",
            {
                "tournament_id": tournament_id,
                "match_id": gf_id,
                "next_slot": grand_final.get("next_slot"),
            },
        )

    if pending_final_id is not None and gf_id != pending_final_id:
        raise DomainConflictError(
            "Struktur bracket tidak valid: pertandingan bukan Grand Final yang sah.",
            {
                "tournament_id": tournament_id,
                "match_id": pending_final_id,
                "final_match_id": gf_id,
            },
        )

    # Walk directed paths from every node with cycle detection + memoized reachability.
    verified_to_gf: set[str] = {gf_id}
    for mid in match_by_id:
        if mid in verified_to_gf:
            continue
        curr: str | None = mid
        visiting: set[str] = set()
        trail: list[str] = []
        while curr is not None and curr not in verified_to_gf:
            if curr in visiting:
                raise DomainConflictError(
                    "Struktur bracket tidak valid: ditemukan siklus antar pertandingan.",
                    {"tournament_id": tournament_id, "cycle_match_ids": trail},
                )
            visiting.add(curr)
            trail.append(curr)
            curr = match_by_id[curr].get("next_match_id")
        if curr not in verified_to_gf:
            raise DomainConflictError(
                "Struktur bracket tidak valid: terdapat pertandingan yang tidak terhubung ke Grand Final.",
                {"tournament_id": tournament_id, "match_id": mid},
            )
        verified_to_gf.update(trail)

    if len(verified_to_gf) != len(match_by_id):
        raise DomainConflictError(
            "Struktur bracket tidak valid: tidak seluruh pertandingan terhubung ke Grand Final.",
            {"tournament_id": tournament_id},
        )

    target_final_id = pending_final_id or gf_id
    unfinished = [
        m["id"]
        for m in matches
        if m["id"] != target_final_id and m.get("status") not in ("completed", "bye")
    ]
    if unfinished:
        raise DomainConflictError(
            "Grand Final tidak dapat diselesaikan karena masih terdapat pertandingan sebelumnya yang belum berstatus completed atau bye.",
            {
                "tournament_id": tournament_id,
                "unfinished_match_ids": unfinished,
            },
        )

    if pending_final_id is None:
        winner = grand_final.get("winner_team_id")
        if grand_final.get("status") != "completed" or not winner or winner not in (
            grand_final.get("team_a_id"),
            grand_final.get("team_b_id"),
        ):
            raise DomainConflictError(
                "Grand Final belum selesai dengan pemenang yang sah.",
                {"tournament_id": tournament_id, "match_id": gf_id},
            )

    return grand_final
