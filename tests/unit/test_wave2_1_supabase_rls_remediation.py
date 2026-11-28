"""Regression tests for Wave 2.1: Supabase RLS compatibility (FAIL-1, FAIL-2, FAIL-3)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
from pathlib import Path
import re
import threading
from typing import Any
import uuid

import pytest

from backend.app import create_app
from backend.contracts.dtos import (
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
    ROLE_PLAYER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_CAPTAIN,
)
from backend.core.config import AppConfig
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
)
from backend.infrastructure.supabase.client import use_access_token
from backend.modules.matches.bracket_engine import (
    parse_best_of,
    validate_bracket_graph,
    validate_match_score,
)
from backend.modules.matches.service import MatchService
from backend.modules.teams.service import TeamService
from backend.modules.tournaments.service import TournamentService
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
from tests.unit.test_auth_and_permissions import (
    _FakeResponse,
    _PostgrestError,
    _RLSEnforcingSupabaseEngine,
    _RLSTableQuery,
    _build_test_jwt,
)

MLBB_GAME_ID = "22222222-2222-4222-8222-222222222201"
MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
VAL_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333302"
TEAM_GRD = "44444444-4444-4444-8444-444444444401"
TEAM_SRW = "44444444-4444-4444-8444-444444444402"
PLAYER_ID = "11111111-1111-4111-8111-111111111105"
COMMITTEE_ID = "11111111-1111-4111-8111-111111111103"


class _Wave2RLSTableQuery(_RLSTableQuery):
    def upsert(self, payload: Any, on_conflict: str = "") -> _Wave2RLSTableQuery:
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def execute(self) -> _FakeResponse:
        if self._op == "upsert":
            return self._engine.execute_upsert(  # type: ignore[attr-defined]
                table=self._table,
                payload=self._payload,
                on_conflict=getattr(self, "_on_conflict", ""),
                access_token=self._token,
            )
        return super().execute()


class _Wave2RLSClient:
    def __init__(self, engine: _Wave2RLSEnforcingSupabaseEngine, access_token: str | None) -> None:
        self._engine = engine
        self.access_token = access_token
        from tests.unit.test_auth_and_permissions import _RLSAuthEndpoint

        self.auth = _RLSAuthEndpoint(engine, access_token)

    def table(self, table_name: str) -> _Wave2RLSTableQuery:
        return _Wave2RLSTableQuery(self._engine, table_name, self.access_token)

    def rpc(self, fn_name: str, params: dict[str, Any]) -> Any:
        from tests.unit.test_auth_and_permissions import _RLSRpcQuery

        return _RLSRpcQuery(self._engine, fn_name, params, self.access_token)


class _Wave2RLSEnforcingSupabaseEngine(_RLSEnforcingSupabaseEngine):
    """Extended RLS + RPC simulator matching 0002_security_hardening.sql and 0003_wave2_rls_compatibility.sql."""

    def __init__(self) -> None:
        super().__init__()
        self._tx_lock = threading.RLock()

    def create_client(self, _config: AppConfig, access_token: str | None = None) -> Any:
        return _Wave2RLSClient(self, access_token)

    def _is_assigned_committee(self, tournament_id: str, profile_id: str | None) -> bool:
        return any(
            s["tournament_id"] == tournament_id and s["user_id"] == profile_id
            for s in self.store["tournament_staff"]
        )

    def _is_team_captain(self, team_id: str, profile_id: str | None) -> bool:
        return any(
            t["id"] == team_id and t.get("captain_id") == profile_id
            for t in self.store["teams"]
        )

    def execute_table_op(
        self,
        table: str,
        op: str,
        payload: Any,
        filters: list[tuple[str, Any]],
        limit: int | None,
        access_token: str | None,
    ) -> _FakeResponse:
        with self._tx_lock:
            auth_uid, caller = self._resolve_caller(access_token)
            caller_role = caller.get("role") if caller else None
            caller_id = caller.get("id") if caller else None

            if table == "tournaments" and op == "insert":
                if not payload.get("id"):
                    payload = {**payload, "id": str(uuid.uuid4())}

            if table == "teams" and op == "insert":
                if not payload.get("id"):
                    payload = {**payload, "id": str(uuid.uuid4())}

            if table == "registrations":
                self.recorded_operations.append(
                    {
                        "table": table,
                        "op": op,
                        "access_token": access_token,
                        "caller_id": caller_id,
                        "caller_role": caller_role,
                    }
                )
                rows = self.store["registrations"]
                if op == "select":
                    visible = []
                    for r in rows:
                        if not self._matches_filters(r, filters):
                            continue
                        is_approved = r.get("status") == "approved"
                        is_owner = bool(
                            caller
                            and (
                                caller_role == ROLE_SUPER_ADMIN
                                or r.get("registered_by") == caller_id
                                or self._is_team_captain(r["team_id"], caller_id)
                                or any(
                                    t["id"] == r["tournament_id"] and t.get("organizer_id") == caller_id
                                    for t in self.store["tournaments"]
                                )
                                or (
                                    caller_role == ROLE_COMMITTEE
                                    and self._is_assigned_committee(r["tournament_id"], caller_id)
                                )
                            )
                        )
                        if is_approved or is_owner:
                            visible.append(copy.deepcopy(r))
                    return _FakeResponse(visible[:limit] if limit else visible)
                if op == "insert":
                    if not caller or not (
                        caller_role == ROLE_SUPER_ADMIN
                        or (
                            caller_role == ROLE_TEAM_CAPTAIN
                            and payload.get("registered_by") == caller_id
                            and self._is_team_captain(payload.get("team_id", ""), caller_id)
                            and payload.get("status", "pending") == "pending"
                        )
                    ):
                        raise _PostgrestError(
                            'new row violates row-level security policy for table "registrations"', "42501"
                        )
                    for r in rows:
                        if (
                            r["tournament_id"] == payload["tournament_id"]
                            and r["team_id"] == payload["team_id"]
                        ):
                            raise _PostgrestError("uq_tournament_team_registration", "23505")
                        if (
                            payload.get("seed_number") is not None
                            and r["tournament_id"] == payload["tournament_id"]
                            and r.get("seed_number") == payload.get("seed_number")
                        ):
                            raise _PostgrestError("uq_tournament_seed", "23505")
                    rec = {"id": payload.get("id") or f"reg-{len(rows) + 1}", **payload}
                    rows.append(rec)
                    return _FakeResponse([copy.deepcopy(rec)])
                if op == "update":
                    updated = []
                    for r in rows:
                        if not self._matches_filters(r, filters):
                            continue
                        allowed = bool(
                            caller
                            and (
                                caller_role == ROLE_SUPER_ADMIN
                                or (
                                    caller_role == ROLE_ORGANIZER
                                    and any(
                                        t["id"] == r["tournament_id"]
                                        and t.get("organizer_id") == caller_id
                                        for t in self.store["tournaments"]
                                    )
                                )
                                or (
                                    caller_role == ROLE_COMMITTEE
                                    and self._is_assigned_committee(r["tournament_id"], caller_id)
                                )
                            )
                        )
                        if not allowed:
                            raise _PostgrestError(
                                'row-level security policy violation for table "registrations"', "42501"
                            )
                        r.update(payload)
                        updated.append(copy.deepcopy(r))
                    return _FakeResponse(updated)

            if table == "tournament_staff" and op == "select":
                if not caller:
                    return _FakeResponse([])
                visible = [
                    copy.deepcopy(s)
                    for s in self.store["tournament_staff"]
                    if self._matches_filters(s, filters)
                    and (
                        caller_role == ROLE_SUPER_ADMIN
                        or s.get("user_id") == caller_id
                        or any(
                            t["id"] == s["tournament_id"] and t.get("organizer_id") == caller_id
                            for t in self.store["tournaments"]
                        )
                        or self._is_assigned_committee(s["tournament_id"], caller_id)
                    )
                ]
                return _FakeResponse(visible[:limit] if limit else visible)

            if table == "team_members" and op == "insert":
                if not caller or not (
                    caller_role == ROLE_SUPER_ADMIN
                    or (
                        caller_role == ROLE_TEAM_CAPTAIN
                        and self._is_team_captain(payload.get("team_id", ""), caller_id)
                    )
                ):
                    raise _PostgrestError(
                        'new row violates row-level security policy for table "team_members"', "42501"
                    )
                rec = {"id": payload.get("id") or f"tm-{len(self.store['team_members']) + 1}", **payload}
                self.store["team_members"].append(rec)
                return _FakeResponse([copy.deepcopy(rec)])

            if table == "matches" and op == "update":
                updated = []
                for m in self.store["matches"]:
                    if not self._matches_filters(m, filters):
                        continue
                    allowed = bool(
                        caller
                        and (
                            caller_role == ROLE_SUPER_ADMIN
                            or (
                                caller_role == ROLE_ORGANIZER
                                and any(
                                    t["id"] == m["tournament_id"] and t.get("organizer_id") == caller_id
                                    for t in self.store["tournaments"]
                                )
                            )
                            or (
                                caller_role == ROLE_COMMITTEE
                                and self._is_assigned_committee(m["tournament_id"], caller_id)
                            )
                        )
                    )
                    if not allowed:
                        raise _PostgrestError(
                            'row-level security policy violation for table "matches"', "42501"
                        )
                    m.update(payload)
                    updated.append(copy.deepcopy(m))
                return _FakeResponse(updated)

            return super().execute_table_op(table, op, payload, filters, limit, access_token)

    def execute_upsert(
        self, table: str, payload: dict[str, Any], on_conflict: str, access_token: str | None
    ) -> _FakeResponse:
        with self._tx_lock:
            _, caller = self._resolve_caller(access_token)
            caller_role = caller.get("role") if caller else None
            caller_id = caller.get("id") if caller else None
            if table != "match_results":
                raise _PostgrestError(f"Unsupported upsert table {table}", "42501")

            match = next((m for m in self.store["matches"] if m["id"] == payload.get("match_id")), None)
            if not match:
                raise _PostgrestError("insert or update on table \"match_results\" violates foreign key", "23503")

            allowed = bool(
                caller
                and (
                    caller_role == ROLE_SUPER_ADMIN
                    or (
                        caller_role == ROLE_ORGANIZER
                        and any(
                            t["id"] == match["tournament_id"] and t.get("organizer_id") == caller_id
                            for t in self.store["tournaments"]
                        )
                    )
                    or (
                        caller_role == ROLE_COMMITTEE
                        and self._is_assigned_committee(match["tournament_id"], caller_id)
                    )
                )
            )
            if not allowed:
                raise _PostgrestError(
                    'row-level security policy violation for table "match_results"', "42501"
                )
            assert on_conflict == "match_id,game_number"
            for existing in self.store["match_results"]:
                if (
                    existing["match_id"] == payload["match_id"]
                    and int(existing.get("game_number", 1)) == int(payload.get("game_number", 1))
                ):
                    existing.update(payload)
                    return _FakeResponse([copy.deepcopy(existing)])
            rec = {"id": f"mr-{len(self.store['match_results']) + 1}", **payload}
            self.store["match_results"].append(rec)
            return _FakeResponse([copy.deepcopy(rec)])

    def execute_rpc(self, fn_name: str, params: dict[str, Any], access_token: str | None) -> _FakeResponse:
        with self._tx_lock:
            auth_uid, caller = self._resolve_caller(access_token)
            caller_role = caller.get("role") if caller else None
            caller_id = caller.get("id") if caller else None

            if fn_name == "transition_tournament_status":
                p_tournament_id = params.get("p_tournament_id")
                p_new_status = params.get("p_new_status")
                if not auth_uid or not caller:
                    raise _PostgrestError("Autentikasi diperlukan.", "42501")
                tournament = next(
                    (t for t in self.store["tournaments"] if t["id"] == p_tournament_id), None
                )
                if not tournament:
                    raise _PostgrestError("Turnamen tidak ditemukan.", "P0002")

                matches = [m for m in self.store["matches"] if m["tournament_id"] == p_tournament_id]
                if caller_role == ROLE_SUPER_ADMIN:
                    pass
                elif caller_role == ROLE_ORGANIZER:
                    if tournament.get("organizer_id") != caller_id:
                        raise _PostgrestError("Organizer hanya dapat mengubah turnamen miliknya.", "42501")
                elif caller_role == ROLE_COMMITTEE:
                    if not self._is_assigned_committee(p_tournament_id, caller_id):
                        raise _PostgrestError("Panitia tidak ditugaskan.", "42501")
                    if (
                        p_new_status == "ongoing"
                        and tournament["status"] in ("draft", "open_registration", "registration_closed")
                        and len(matches) > 0
                    ):
                        pass
                    elif (
                        p_new_status == "completed"
                        and tournament["status"] in ("ongoing", "completed")
                    ):
                        pass
                    else:
                        raise _PostgrestError(
                            "Panitia tidak diizinkan melakukan transisi status turnamen tersebut.", "42501"
                        )
                else:
                    raise _PostgrestError("Role tidak diizinkan.", "42501")

                allowed_transitions = {
                    "draft": ("open_registration", "registration_closed", "cancelled"),
                    "open_registration": ("draft", "registration_closed", "ongoing", "cancelled"),
                    "registration_closed": ("open_registration", "ongoing", "cancelled"),
                    "ongoing": ("completed", "cancelled"),
                    "completed": (),
                    "cancelled": (),
                }
                if (
                    tournament["status"] != p_new_status
                    and p_new_status not in allowed_transitions.get(tournament["status"], ())
                ):
                    raise _PostgrestError("Transisi status turnamen tidak diizinkan.", "P0009")

                if p_new_status == "completed":
                    try:
                        validate_bracket_graph(p_tournament_id, matches)
                    except DomainConflictError as exc:
                        raise _PostgrestError(str(exc), "P0009") from exc

                tournament["status"] = p_new_status
                return _FakeResponse([copy.deepcopy(tournament)])

            if fn_name == "submit_match_result_atomic":
                if not auth_uid or not caller or not caller.get("is_active", True):
                    raise _PostgrestError("Autentikasi diperlukan.", "42501")
                if caller_role not in (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE):
                    raise _PostgrestError("Role tidak diizinkan.", "42501")

                p_match_id = params.get("p_match_id")
                p_score_a = params.get("p_score_a")
                p_score_b = params.get("p_score_b")
                p_force_override = bool(params.get("p_force_override", False))
                p_notes = str(params.get("p_notes") or "").strip()
                p_game_number = int(params.get("p_game_number") or 1)
                raw_idem = params.get("p_idempotency_key")
                p_idem = str(raw_idem).strip() if isinstance(raw_idem, str) and raw_idem.strip() else None

                match = next((m for m in self.store["matches"] if m["id"] == p_match_id), None)
                if not match:
                    raise _PostgrestError("Pertandingan tidak ditemukan.", "P0002")
                tournament = next(
                    (t for t in self.store["tournaments"] if t["id"] == match["tournament_id"]),
                    None,
                )
                if not tournament:
                    raise _PostgrestError("Turnamen tidak ditemukan.", "P0002")

                if caller_role == ROLE_ORGANIZER and tournament.get("organizer_id") != caller_id:
                    raise _PostgrestError("Organizer hanya dapat mengelola turnamen miliknya.", "42501")
                if caller_role == ROLE_COMMITTEE and not self._is_assigned_committee(
                    tournament["id"], caller_id
                ):
                    raise _PostgrestError("Panitia tidak ditugaskan.", "42501")

                req_hash = hashlib.sha256(
                    "|".join(
                        [
                            str(p_match_id),
                            str(p_score_a),
                            str(p_score_b),
                            str(p_force_override).lower(),
                            p_notes,
                            str(p_game_number),
                        ]
                    ).encode("utf-8")
                ).hexdigest()
                idem_rows = self.store.setdefault("match_submission_requests", [])
                if p_idem is not None:
                    existing_idem = next(
                        (
                            r
                            for r in idem_rows
                            if r["match_id"] == p_match_id
                            and r["actor_id"] == caller_id
                            and r["idempotency_key"] == p_idem
                        ),
                        None,
                    )
                    if existing_idem is not None:
                        if existing_idem["request_hash"] != req_hash:
                            raise _PostgrestError(
                                "Idempotency key sudah digunakan dengan payload skor yang berbeda.",
                                "P0009",
                            )
                        replay = copy.deepcopy(existing_idem["response_payload"])
                        replay["idempotent_replay"] = True
                        return _FakeResponse(replay)

                if tournament["status"] == "cancelled":
                    raise _PostgrestError("Turnamen telah dibatalkan.", "P0009")
                if match["status"] == "bye":
                    raise _PostgrestError("Pertandingan BYE tidak dapat diisi skor.", "P0009")
                if match["status"] == "completed" and not p_force_override:
                    raise _PostgrestError("Pertandingan sudah dikunci.", "P0009")
                if p_force_override and len(p_notes) < 4:
                    raise _PostgrestError("force_override wajib menyertakan notes >= 4 karakter.", "22023")
                if not match.get("team_a_id") or not match.get("team_b_id"):
                    raise _PostgrestError("Kedua tim wajib terisi.", "22023")

                best_of = parse_best_of(match.get("best_of") or tournament.get("best_of") or 3)
                side = validate_match_score(int(p_score_a), int(p_score_b), best_of=best_of)
                winner_team_id = match["team_a_id"] if side == "A" else match["team_b_id"]

                # Snapshot full store before write steps so any exception performs PostgreSQL ACID rollback
                tx_snapshot = copy.deepcopy(self.store)
                fail_hook = getattr(self, "_fail_atomic_hook", None)
                try:
                    next_match_id = match.get("next_match_id")
                    next_slot = match.get("next_slot")
                    slot_field = "team_a_id" if next_slot == "A" else "team_b_id"
                    next_match = None
                    if next_match_id and next_slot in ("A", "B"):
                        next_match = next(
                            (
                                m
                                for m in self.store["matches"]
                                if m["id"] == next_match_id and m["tournament_id"] == tournament["id"]
                            ),
                            None,
                        )
                        if not next_match:
                            raise _PostgrestError("Downstream match tidak ditemukan.", "P0009")
                        if next_match.get(slot_field) != winner_team_id and (
                            next_match.get("status") in ("ongoing", "completed")
                            or next_match.get("winner_team_id")
                        ):
                            raise _PostgrestError("Pertandingan berikutnya sudah berjalan/selesai.", "P0009")
                    else:
                        if tournament["status"] not in ("ongoing", "completed"):
                            raise _PostgrestError("Turnamen bukan ongoing/completed.", "P0009")
                        t_matches = [
                            m for m in self.store["matches"] if m["tournament_id"] == tournament["id"]
                        ]
                        try:
                            validate_bracket_graph(tournament["id"], t_matches, pending_final_id=p_match_id)
                        except DomainConflictError as exc:
                            raise _PostgrestError(str(exc), "P0009") from exc

                    match["score_a"] = int(p_score_a)
                    match["score_b"] = int(p_score_b)
                    match["winner_team_id"] = winner_team_id
                    match["status"] = "completed"
                    match["completed_at"] = "2026-11-25T20:00:00+07:00"
                    if callable(fail_hook):
                        fail_hook("update_match")

                    if next_match is not None:
                        next_match[slot_field] = winner_team_id
                    else:
                        if callable(fail_hook):
                            fail_hook("transition_tournament")
                        t_matches_after = [
                            m for m in self.store["matches"] if m["tournament_id"] == tournament["id"]
                        ]
                        try:
                            validate_bracket_graph(tournament["id"], t_matches_after)
                        except DomainConflictError as exc:
                            raise _PostgrestError(str(exc), "P0009") from exc
                        tournament["status"] = "completed"

                    if callable(fail_hook):
                        fail_hook("upsert_match_result")
                    existing_res = next(
                        (
                            r
                            for r in self.store["match_results"]
                            if r["match_id"] == p_match_id and int(r.get("game_number", 1)) == p_game_number
                        ),
                        None,
                    )
                    if existing_res is not None:
                        existing_res.update(
                            {
                                "score_a": int(p_score_a),
                                "score_b": int(p_score_b),
                                "winner_team_id": winner_team_id,
                                "notes": p_notes,
                                "verified_by": caller_id,
                                "verified_at": "2026-11-25T20:00:00+07:00",
                            }
                        )
                    else:
                        self.store["match_results"].append(
                            {
                                "id": str(uuid.uuid4()),
                                "match_id": p_match_id,
                                "game_number": p_game_number,
                                "score_a": int(p_score_a),
                                "score_b": int(p_score_b),
                                "winner_team_id": winner_team_id,
                                "proof_url": None,
                                "notes": p_notes,
                                "verified_by": caller_id,
                                "verified_at": "2026-11-25T20:00:00+07:00",
                            }
                        )

                    if callable(fail_hook):
                        fail_hook("insert_activity_log")
                    self.store.setdefault("activity_logs", []).append(
                        {
                            "id": str(uuid.uuid4()),
                            "actor_id": caller_id,
                            "tournament_id": tournament["id"],
                            "entity_type": "match",
                            "entity_id": p_match_id,
                            "action": "MATCH_RESULT_OVERRIDDEN" if p_force_override else "MATCH_RESULT_VERIFIED",
                            "details": {"score_a": int(p_score_a), "score_b": int(p_score_b)},
                        }
                    )

                    response_obj = {
                        "match": copy.deepcopy(match),
                        "next_match": copy.deepcopy(next_match) if next_match is not None else None,
                        "tournament_status": tournament["status"],
                        "idempotent_replay": False,
                    }
                    if p_idem is not None:
                        self.store.setdefault("match_submission_requests", []).append(
                            {
                                "id": str(uuid.uuid4()),
                                "match_id": p_match_id,
                                "actor_id": caller_id,
                                "idempotency_key": p_idem,
                                "request_hash": req_hash,
                                "response_payload": copy.deepcopy(response_obj),
                            }
                        )
                except Exception:
                    # Atomic PostgreSQL rollback on any error inside transaction
                    self.store.clear()
                    self.store.update(tx_snapshot)
                    raise

                # Optional post-commit response timeout simulation (DB committed, HTTP response timed out)
                if getattr(self, "_post_commit_timeout_once", False):
                    self._post_commit_timeout_once = False
                    raise TimeoutError("Simulated PostgREST read timeout after PostgreSQL commit")

                return _FakeResponse(response_obj)

            if fn_name == "get_public_profile_summary":
                if not auth_uid or not caller or not caller.get("is_active", True):
                    raise _PostgrestError("Autentikasi diperlukan.", "42501")
                p_team_id = params.get("p_team_id")
                if caller_role == ROLE_SUPER_ADMIN:
                    pass
                elif caller_role == ROLE_TEAM_CAPTAIN:
                    if not p_team_id:
                        raise _PostgrestError(
                            "Team Captain wajib menyertakan team_id miliknya.", "42501"
                        )
                    team = next((t for t in self.store["teams"] if t["id"] == p_team_id), None)
                    if not team or team.get("captain_id") != caller_id:
                        raise _PostgrestError(
                            "Team Captain hanya dapat mencari profil untuk tim miliknya sendiri.",
                            "42501",
                        )
                else:
                    raise _PostgrestError(
                        "Role pengguna tidak diizinkan melihat ringkasan profil.", "42501"
                    )

                target_id = params.get("p_profile_id")
                if not target_id:
                    raise _PostgrestError("profile_id wajib diisi.", "22023")
                profile = next(
                    (p for p in self.store["profiles"] if p["id"] == target_id and p.get("is_active", True)),
                    None,
                )
                if not profile:
                    return _FakeResponse([])
                return _FakeResponse(
                    [
                        {
                            "id": profile["id"],
                            "username": profile["username"],
                            "full_name": profile["full_name"],
                            "avatar_url": profile.get("avatar_url"),
                        }
                    ]
                )

            if fn_name == "register_team_atomic":
                if not auth_uid or not caller:
                    raise _PostgrestError("Autentikasi diperlukan.", "42501")
                if caller_role not in (ROLE_SUPER_ADMIN, ROLE_TEAM_CAPTAIN):
                    raise _PostgrestError("Role tidak diizinkan.", "42501")
                p_tournament_id = params.get("p_tournament_id")
                p_team_id = params.get("p_team_id")
                p_notes = str(params.get("p_notes") or "").strip()

                tournament = next(
                    (t for t in self.store["tournaments"] if t["id"] == p_tournament_id), None
                )
                if not tournament:
                    raise _PostgrestError("Turnamen tidak ditemukan.", "P0002")
                if tournament["status"] != "open_registration":
                    raise _PostgrestError("Pendaftaran ditutup untuk turnamen ini.", "P0009")
                team = next((tm for tm in self.store["teams"] if tm["id"] == p_team_id), None)
                if not team:
                    raise _PostgrestError("Tim tidak ditemukan.", "P0002")
                if caller_role == ROLE_TEAM_CAPTAIN and team.get("captain_id") != caller_id:
                    raise _PostgrestError("Kapten hanya dapat mendaftarkan tim miliknya sendiri.", "42501")
                if team["game_id"] != tournament["game_id"]:
                    raise _PostgrestError("Game tim tidak sesuai.", "22023")

                t_regs = [
                    r for r in self.store["registrations"] if r["tournament_id"] == p_tournament_id
                ]
                existing = next((r for r in t_regs if r["team_id"] == p_team_id), None)
                if existing and existing["status"] != "withdrawn":
                    raise _PostgrestError("Tim ini sudah terdaftar pada turnamen tersebut.", "P0009")

                active_count = sum(1 for r in t_regs if r["status"] in ("pending", "approved"))
                if active_count >= int(tournament["max_teams"]):
                    raise _PostgrestError("Kuota turnamen sudah penuh.", "P0009")

                next_seed = max((int(r.get("seed_number") or 0) for r in t_regs), default=0) + 1
                if existing:
                    existing["registered_by"] = caller_id
                    existing["status"] = "pending"
                    existing["seed_number"] = next_seed
                    existing["verified_by"] = None
                    existing["verified_at"] = None
                    existing["notes"] = p_notes
                    return _FakeResponse([copy.deepcopy(existing)])

                new_reg = {
                    "id": str(uuid.uuid4()),
                    "tournament_id": p_tournament_id,
                    "team_id": p_team_id,
                    "registered_by": caller_id,
                    "status": "pending",
                    "seed_number": next_seed,
                    "verified_by": None,
                    "verified_at": None,
                    "notes": p_notes,
                }
                self.store["registrations"].append(new_reg)
                return _FakeResponse([copy.deepcopy(new_reg)])

            return super().execute_rpc(fn_name, params, access_token)


def _supabase_setup() -> tuple[_Wave2RLSEnforcingSupabaseEngine, SupabaseDataStoreRepository, AppConfig]:
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=_build_test_jwt({"role": "anon", "iss": "supabase"}),
    )
    engine = _Wave2RLSEnforcingSupabaseEngine()
    repo = SupabaseDataStoreRepository(cfg, client_factory=engine.create_client)
    return engine, repo, cfg


def _create_second_captain_and_team(
    repo: MockDataStoreRepository | SupabaseDataStoreRepository,
    engine: _Wave2RLSEnforcingSupabaseEngine | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if engine is not None:
        cap2 = {
            "id": "11111111-1111-4111-8111-111111111199",
            "auth_user_id": "11111111-1111-4111-8111-111111111199",
            "email": "captain2@turnamen.in",
            "username": "captain_dua",
            "full_name": "Kapten Dua",
            "role": ROLE_TEAM_CAPTAIN,
            "is_active": True,
        }
        engine.store["profiles"].append(cap2)
        engine.passwords["captain2@turnamen.in"] = "turnamen123"
    else:
        cap2 = repo.create_profile(
            {
                "email": "captain2@turnamen.in",
                "username": "captain_dua",
                "full_name": "Kapten Dua",
                "role": ROLE_TEAM_CAPTAIN,
            }
        )
    team2 = TeamService(repo).create_team(
        cap2,
        {"name": "Siliwangi Force", "tag": "SLW", "game_id": MLBB_GAME_ID, "region": "Bandung"},
    )
    return cap2, team2


def test_fail1_assigned_committee_transitions_status_without_direct_table_update() -> None:
    engine, repo, cfg = _supabase_setup()
    app = create_app(config=cfg, repository=repo)
    client = app.test_client()

    unassigned_comm = {
        "id": "11111111-1111-4111-8111-111111111188",
        "auth_user_id": "11111111-1111-4111-8111-111111111188",
        "email": "unassigned.comm@turnamen.in",
        "username": "unassigned_comm",
        "full_name": "Panitia Lepas",
        "role": ROLE_COMMITTEE,
        "is_active": True,
    }
    engine.store["profiles"].append(unassigned_comm)
    engine.passwords["unassigned.comm@turnamen.in"] = "turnamen123"

    comm_jwt = engine.token_for_profile("committee@turnamen.in")
    unassigned_jwt = engine.token_for_profile("unassigned.comm@turnamen.in")
    org_jwt = engine.token_for_profile("organizer@turnamen.in")

    # Direct update on tournaments table by committee must remain blocked by RLS
    with use_access_token(comm_jwt):
        with pytest.raises(DomainForbiddenError):
            repo.update_tournament(VAL_TOURNAMENT_ID, {"status": "ongoing"})
        with pytest.raises(DomainForbiddenError):
            repo.transition_tournament_status(VAL_TOURNAMENT_ID, "cancelled")

    # Create a clean 2-team MLBB tournament as organizer, approve 2 teams, then let assigned committee run bracket & final
    create_resp = client.post(
        "/api/v1/tournaments",
        headers={"Authorization": f"Bearer {org_jwt}"},
        json={
            "title": "Cup Committee RLS",
            "game_id": MLBB_GAME_ID,
            "start_date": "2026-12-20T10:00:00+07:00",
            "max_teams": 4,
            "status": "open_registration",
        },
    )
    assert create_resp.status_code == 201
    tour_id = create_resp.get_json()["data"]["id"]
    engine.store["tournament_staff"].append(
        {
            "id": "66666666-6666-4666-8666-666666666699",
            "tournament_id": tour_id,
            "user_id": COMMITTEE_ID,
            "staff_role": "head_committee",
        }
    )

    cap_jwt = engine.token_for_profile("captain@turnamen.in")
    for tid in (TEAM_GRD, TEAM_SRW):
        reg = client.post(
            f"/api/v1/tournaments/{tour_id}/registrations",
            headers={"Authorization": f"Bearer {cap_jwt}"},
            json={"team_id": tid},
        )
        assert reg.status_code == 201
        reg_id = reg.get_json()["data"]["id"]
        assert (
            client.patch(
                f"/api/v1/registrations/{reg_id}/status",
                headers={"Authorization": f"Bearer {comm_jwt}"},
                json={"status": "approved"},
            ).status_code
            == 200
        )

    # Unassigned committee cannot generate bracket
    assert (
        client.post(
            f"/api/v1/tournaments/{tour_id}/bracket/generate",
            headers={"Authorization": f"Bearer {unassigned_jwt}"},
        ).status_code
        == 403
    )

    # Assigned committee generates bracket -> tournament transitions to ongoing
    gen_resp = client.post(
        f"/api/v1/tournaments/{tour_id}/bracket/generate",
        headers={"Authorization": f"Bearer {comm_jwt}"},
    )
    assert gen_resp.status_code == 201
    assert repo.get_tournament_by_id(tour_id)["status"] == "ongoing"

    final_match_id = gen_resp.get_json()["data"]["matches"][0]["id"]
    # Unassigned committee cannot submit match result
    assert (
        client.patch(
            f"/api/v1/matches/{final_match_id}/result",
            headers={"Authorization": f"Bearer {unassigned_jwt}"},
            json={"score_a": 2, "score_b": 0},
        ).status_code
        == 403
    )

    # Assigned committee submits Grand Final -> tournament transitions to completed
    res_resp = client.patch(
        f"/api/v1/matches/{final_match_id}/result",
        headers={"Authorization": f"Bearer {comm_jwt}"},
        json={"score_a": 2, "score_b": 1, "notes": "Final selesai"},
    )
    assert res_resp.status_code == 200
    assert repo.get_tournament_by_id(tour_id)["status"] == "completed"


def test_fail2_team_captain_adds_member_via_safe_profile_lookup_without_pii() -> None:
    engine, supa_repo, cfg = _supabase_setup()
    app = create_app(config=cfg, repository=supa_repo)
    client = app.test_client()
    cap_jwt = engine.token_for_profile("captain@turnamen.in")

    # Direct profiles SELECT for another user remains blocked by RLS for team_captain
    with use_access_token(cap_jwt):
        assert supa_repo.get_profile_by_id(PLAYER_ID) is None
        summary = supa_repo.get_public_profile_summary(PLAYER_ID, team_id=TEAM_GRD)
        assert summary is not None
        assert set(summary.keys()) == {"id", "username", "full_name", "avatar_url"}
        assert "email" not in summary
        assert "phone" not in summary

    # Add member with valid player user_id succeeds through HTTP API under Supabase RLS
    ok_resp = client.post(
        f"/api/v1/teams/{TEAM_GRD}/members",
        headers={"Authorization": f"Bearer {cap_jwt}"},
        json={
            "nickname": "GRD.Linked",
            "ingame_id": "ML-LINKED-01",
            "member_role": "starter",
            "user_id": PLAYER_ID,
        },
    )
    assert ok_resp.status_code == 201
    assert ok_resp.get_json()["data"]["user_id"] == PLAYER_ID

    # Invalid / non-UUID / unknown user_id returns controlled 404, never 500
    for bad_uid in ("not-a-uuid", "00000000-0000-4000-8000-000000000999"):
        err_resp = client.post(
            f"/api/v1/teams/{TEAM_GRD}/members",
            headers={"Authorization": f"Bearer {cap_jwt}"},
            json={
                "nickname": "GRD.Bad",
                "ingame_id": f"ML-BAD-{bad_uid[-3:]}",
                "user_id": bad_uid,
            },
        )
        assert err_resp.status_code == 404
        assert err_resp.get_json()["error"]["code"] == "NOT_FOUND"

    # Mock repository returns identical minimal summary without PII
    mock_repo = MockDataStoreRepository()
    mock_cap = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert mock_cap is not None
    mock_summary = mock_repo.get_public_profile_summary(
        PLAYER_ID, team_id=TEAM_GRD, actor_id=mock_cap["id"]
    )
    assert mock_summary == summary


def test_fail3_two_captains_and_concurrent_registrations_enforce_seed_and_capacity() -> None:
    # 1. RLS-enforcing Supabase mode: Captain A and Captain B register sequentially & concurrently
    engine, supa_repo, cfg = _supabase_setup()
    app = create_app(config=cfg, repository=supa_repo)
    client = app.test_client()
    org_jwt = engine.token_for_profile("organizer@turnamen.in")
    cap1_jwt = engine.token_for_profile("captain@turnamen.in")
    with use_access_token(engine.token_for_profile("admin@turnamen.in")):
        cap2, team2 = _create_second_captain_and_team(supa_repo, engine)
    cap2_jwt = engine.token_for_profile(cap2["email"])

    tour_resp = client.post(
        "/api/v1/tournaments",
        headers={"Authorization": f"Bearer {org_jwt}"},
        json={
            "title": "Atomic Registration Cup",
            "game_id": MLBB_GAME_ID,
            "start_date": "2026-12-21T10:00:00+07:00",
            "max_teams": 2,
            "status": "open_registration",
        },
    )
    assert tour_resp.status_code == 201
    tour_id = tour_resp.get_json()["data"]["id"]

    # Captain 1 registers TEAM_GRD (seed 1)
    r1 = client.post(
        f"/api/v1/tournaments/{tour_id}/registrations",
        headers={"Authorization": f"Bearer {cap1_jwt}"},
        json={"team_id": TEAM_GRD},
    )
    assert r1.status_code == 201
    assert r1.get_json()["data"]["seed_number"] == 1

    # Under RLS, Captain 2 cannot see Captain 1's pending registration
    cap2_visible = client.get(
        f"/api/v1/tournaments/{tour_id}/registrations",
        headers={"Authorization": f"Bearer {cap2_jwt}"},
    ).get_json()["data"]
    assert cap2_visible == []

    # Yet Captain 2 registering team2 gets seed 2 without colliding on uq_tournament_seed!
    r2 = client.post(
        f"/api/v1/tournaments/{tour_id}/registrations",
        headers={"Authorization": f"Bearer {cap2_jwt}"},
        json={"team_id": team2["id"]},
    )
    assert r2.status_code == 201
    assert r2.get_json()["data"]["seed_number"] == 2

    # 3rd registration exceeds max_teams=2 even though registrations are pending
    r3 = client.post(
        f"/api/v1/tournaments/{tour_id}/registrations",
        headers={"Authorization": f"Bearer {cap1_jwt}"},
        json={"team_id": TEAM_SRW},
    )
    assert r3.status_code == 409

    # Withdraw team2 and re-register -> updates withdrawn row cleanly with next seed 3
    comm_jwt = engine.token_for_profile("committee@turnamen.in")
    engine.store["tournament_staff"].append(
        {
            "id": "66666666-6666-4666-8666-666666666698",
            "tournament_id": tour_id,
            "user_id": COMMITTEE_ID,
            "staff_role": "head_committee",
        }
    )
    assert (
        client.patch(
            f"/api/v1/registrations/{r2.get_json()['data']['id']}/status",
            headers={"Authorization": f"Bearer {comm_jwt}"},
            json={"status": "withdrawn"},
        ).status_code
        == 200
    )
    r2_again = client.post(
        f"/api/v1/tournaments/{tour_id}/registrations",
        headers={"Authorization": f"Bearer {cap2_jwt}"},
        json={"team_id": team2["id"]},
    )
    assert r2_again.status_code == 201
    assert r2_again.get_json()["data"]["seed_number"] == 3

    # 2. Concurrency test on max_teams=1 in BOTH RLS-enforcing Supabase engine and Mock repository
    race_tour = client.post(
        "/api/v1/tournaments",
        headers={"Authorization": f"Bearer {org_jwt}"},
        json={
            "title": "Concurrency Race Cup",
            "game_id": MLBB_GAME_ID,
            "start_date": "2026-12-22T10:00:00+07:00",
            "max_teams": 2,
            "status": "open_registration",
        },
    ).get_json()["data"]["id"]
    # Fill slot 1 so only 1 slot remains for two concurrent captains
    assert (
        client.post(
            f"/api/v1/tournaments/{race_tour}/registrations",
            headers={"Authorization": f"Bearer {cap1_jwt}"},
            json={"team_id": TEAM_SRW},
        ).status_code
        == 201
    )

    cap1_profile = next(p for p in engine.store["profiles"] if p["email"] == "captain@turnamen.in")
    svc_supa = TournamentService(supa_repo)

    def _supa_race(jwt_tok: str, actor: dict[str, Any], tid: str) -> str:
        with use_access_token(jwt_tok):
            try:
                svc_supa.register_team(actor, race_tour, {"team_id": tid})
                return "ok"
            except DomainConflictError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_supa_race, cap1_jwt, cap1_profile, TEAM_GRD)
        f2 = pool.submit(_supa_race, cap2_jwt, cap2, team2["id"])
        supa_outcomes = sorted([f1.result(), f2.result()])
    assert supa_outcomes == ["conflict", "ok"]
    assert sum(1 for r in engine.store["registrations"] if r["tournament_id"] == race_tour) == 2

    # Same concurrency check on MockDataStoreRepository
    mock_repo = MockDataStoreRepository()
    mock_org = mock_repo.get_profile_by_email("organizer@turnamen.in")
    mock_cap1 = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert mock_org and mock_cap1
    mock_cap2, mock_team2 = _create_second_captain_and_team(mock_repo)
    mock_svc = TournamentService(mock_repo)
    mock_tour = mock_svc.create_tournament(
        mock_org,
        {
            "title": "Mock Concurrency Cup",
            "game_id": MLBB_GAME_ID,
            "start_date": "2026-12-23T10:00:00+07:00",
            "max_teams": 2,
            "status": "open_registration",
        },
    )
    mock_svc.register_team(mock_cap1, mock_tour["id"], {"team_id": TEAM_SRW})

    def _mock_race(actor: dict[str, Any], tid: str) -> str:
        try:
            mock_svc.register_team(actor, mock_tour["id"], {"team_id": tid})
            return "ok"
        except DomainConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        mf1 = pool.submit(_mock_race, mock_cap1, TEAM_GRD)
        mf2 = pool.submit(_mock_race, mock_cap2, mock_team2["id"])
        mock_outcomes = sorted([mf1.result(), mf2.result()])
    assert mock_outcomes == ["conflict", "ok"]
    mock_regs = mock_repo.list_registrations_by_tournament(mock_tour["id"])
    assert len(mock_regs) == 2
    assert len({r["seed_number"] for r in mock_regs}) == 2


def test_wave2_1_migration_security_invariants() -> None:
    sql_path = (
        Path(__file__).resolve().parents[2]
        / "supabase"
        / "migrations"
        / "0003_wave2_rls_compatibility.sql"
    )
    assert sql_path.exists()
    sql = sql_path.read_text(encoding="utf-8")

    assert "CREATE SCHEMA IF NOT EXISTS private;" in sql
    assert "REVOKE ALL ON SCHEMA private FROM PUBLIC, anon;" in sql
    assert "CREATE OR REPLACE FUNCTION private.transition_tournament_status(" in sql
    assert "CREATE OR REPLACE FUNCTION private.get_public_profile_summary(" in sql
    assert "CREATE OR REPLACE FUNCTION private.register_team_atomic(" in sql
    assert "SECURITY DEFINER" in sql
    assert "SET search_path = ''" in sql
    assert "SELECT auth.uid()" in sql
    assert "FOR UPDATE" in sql
    assert "REVOKE ALL ON FUNCTION public.transition_tournament_status(UUID, VARCHAR) FROM PUBLIC, anon;" in sql
    assert "REVOKE ALL ON FUNCTION public.get_public_profile_summary(UUID, UUID) FROM PUBLIC, anon;" in sql
    assert "REVOKE ALL ON FUNCTION public.register_team_atomic(UUID, UUID, TEXT) FROM PUBLIC, anon;" in sql
    # Every public wrapper must remain SECURITY INVOKER (never SECURITY DEFINER in public)
    public_blocks = re.findall(
        r"CREATE OR REPLACE FUNCTION public\.[^\n]+.*?AS \$\$.*?\$\$;",
        sql,
        flags=re.DOTALL,
    )
    assert len(public_blocks) == 3
    for block in public_blocks:
        assert "SECURITY INVOKER" in block
        assert "SECURITY DEFINER" not in block
