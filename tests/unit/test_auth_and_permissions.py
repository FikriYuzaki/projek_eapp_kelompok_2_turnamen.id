"""Unit and integration tests for authentication, 5-role RBAC, request-scoped JWT propagation, RLS enforcement, and atomic RPC."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
from typing import Any

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
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.infrastructure.supabase.client import (
    create_supabase_client,
    get_current_access_token,
    use_access_token,
    validate_supabase_credentials,
)
from backend.modules.auth.permissions import (
    RolePermissionGuard,
    has_permission,
    require_any_role,
    require_authenticated,
    require_permission,
)
from backend.modules.auth.service import AuthService
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol
from backend.repositories.mock.mock_data import build_initial_mock_store
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository


def _build_test_jwt(payload: dict[str, Any]) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode("ascii").rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    signature = "test_signature_segment_12345"
    return f"{header}.{body}.{signature}"


def _decode_test_jwt(token: str | None) -> dict[str, Any]:
    if not token or "." not in token:
        return {}
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    padding = "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(parts[1] + padding).decode("utf-8"))


class _PostgrestError(Exception):
    def __init__(self, message: str, code: str = "42501") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class _FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class _RLSTableQuery:
    """Simulated PostgREST query builder enforcing RLS and triggers from 0002_security_hardening.sql."""

    def __init__(self, engine: _RLSEnforcingSupabaseEngine, table_name: str, access_token: str | None) -> None:
        self._engine = engine
        self._table = table_name
        self._token = access_token
        self._op = "select"
        self._payload: Any = None
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None

    def select(self, _columns: str = "*") -> _RLSTableQuery:
        self._op = "select"
        return self

    def insert(self, payload: Any) -> _RLSTableQuery:
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> _RLSTableQuery:
        self._op = "update"
        self._payload = payload
        return self

    def delete(self) -> _RLSTableQuery:
        self._op = "delete"
        return self

    def eq(self, column: str, value: Any) -> _RLSTableQuery:
        self._filters.append((column, value))
        return self

    def order(self, _column: str, desc: bool = False) -> _RLSTableQuery:
        return self

    def limit(self, count: int) -> _RLSTableQuery:
        self._limit = count
        return self

    def execute(self) -> _FakeResponse:
        return self._engine.execute_table_op(
            table=self._table,
            op=self._op,
            payload=self._payload,
            filters=self._filters,
            limit=self._limit,
            access_token=self._token,
        )


class _RLSRpcQuery:
    """Simulated PostgreSQL RPC execution for `public.replace_tournament_matches`."""

    def __init__(
        self,
        engine: _RLSEnforcingSupabaseEngine,
        fn_name: str,
        params: dict[str, Any],
        access_token: str | None,
    ) -> None:
        self._engine = engine
        self._fn_name = fn_name
        self._params = params
        self._token = access_token

    def execute(self) -> _FakeResponse:
        return self._engine.execute_rpc(self._fn_name, self._params, self._token)


class _RLSAuthEndpoint:
    """Simulated Supabase GoTrue Auth endpoint."""

    def __init__(self, engine: _RLSEnforcingSupabaseEngine, access_token: str | None) -> None:
        self._engine = engine
        self._token = access_token

    def sign_up(self, credentials: dict[str, Any]) -> Any:
        return self._engine.handle_auth_sign_up(credentials)

    def sign_in_with_password(self, credentials: dict[str, Any]) -> Any:
        return self._engine.handle_auth_sign_in(credentials)

    def get_user(self, jwt: str) -> Any:
        return self._engine.handle_auth_get_user(jwt)

    def sign_out(self) -> None:
        self._engine.handle_auth_sign_out(self._token)


class _RLSClient:
    def __init__(self, engine: _RLSEnforcingSupabaseEngine, access_token: str | None) -> None:
        self._engine = engine
        self.access_token = access_token
        self.auth = _RLSAuthEndpoint(engine, access_token)

    def table(self, table_name: str) -> _RLSTableQuery:
        return _RLSTableQuery(self._engine, table_name, self.access_token)

    def rpc(self, fn_name: str, params: dict[str, Any]) -> _RLSRpcQuery:
        return _RLSRpcQuery(self._engine, fn_name, params, self.access_token)


class _RLSEnforcingSupabaseEngine:
    """In-memory PostgreSQL + PostgREST + GoTrue simulator enforcing 0002_security_hardening.sql rules."""

    def __init__(self, email_confirmation_required: bool = False) -> None:
        self.store = build_initial_mock_store()
        self.email_confirmation_required = email_confirmation_required
        self.recorded_operations: list[dict[str, Any]] = []
        self.signed_out_tokens: list[str] = []
        self.revoked_tokens: set[str] = set()
        self.passwords: dict[str, str] = {
            p["email"].lower(): "turnamen123" for p in self.store["profiles"]
        }
        for p in self.store["profiles"]:
            p.pop("password_hash", None)

    def create_client(self, _config: AppConfig, access_token: str | None = None) -> _RLSClient:
        return _RLSClient(self, access_token)

    def token_for_profile(self, email: str) -> str:
        for p in self.store["profiles"]:
            if p["email"].lower() == email.lower():
                return _build_test_jwt(
                    {
                        "sub": p["auth_user_id"],
                        "email": p["email"],
                        "role": "authenticated",
                    }
                )
        raise KeyError(email)

    def _resolve_caller(self, access_token: str | None) -> tuple[str | None, dict[str, Any] | None]:
        if not access_token or access_token in self.revoked_tokens:
            return None, None
        claims = _decode_test_jwt(access_token)
        auth_uid = claims.get("sub")
        if not auth_uid:
            return None, None
        for p in self.store["profiles"]:
            if p.get("auth_user_id") == auth_uid and p.get("is_active", True):
                return str(auth_uid), p
        return str(auth_uid), None

    def handle_auth_sign_up(self, credentials: dict[str, Any]) -> Any:
        email = str(credentials.get("email") or "").strip().lower()
        password = str(credentials.get("password") or "")
        meta = (credentials.get("options") or {}).get("data") or {}

        for p in self.store["profiles"]:
            if p["email"].lower() == email:
                raise _PostgrestError("User already registered", code="23505")
            if meta.get("username") and p["username"].lower() == str(meta["username"]).lower():
                raise _PostgrestError("duplicate key value violates unique constraint profiles_username_key", code="23505")

        new_uid = f"11111111-2222-4333-8444-{len(self.store['profiles']) + 10:012d}"
        req_role = str(meta.get("role") or "player").lower()
        safe_role = req_role if req_role in ("player", "team_captain") else "player"

        # Simulate PostgreSQL trigger `on_auth_user_created` -> `handle_new_auth_user()`
        self.store["profiles"].append(
            {
                "id": new_uid,
                "auth_user_id": new_uid,
                "email": email,
                "username": meta.get("username") or email.split("@")[0],
                "full_name": meta.get("full_name") or email.split("@")[0],
                "role": safe_role,
                "phone": meta.get("phone"),
                "avatar_url": None,
                "is_active": True,
                "created_at": "2026-11-12T10:00:00+00:00",
                "updated_at": "2026-11-12T10:00:00+00:00",
            }
        )
        self.passwords[email] = password

        user_obj = type("UserObj", (), {"id": new_uid, "email": email})()
        if self.email_confirmation_required:
            session_obj = None
        else:
            jwt_token = _build_test_jwt({"sub": new_uid, "email": email, "role": "authenticated"})
            session_obj = type("SessionObj", (), {"access_token": jwt_token})()
        return type("AuthResp", (), {"user": user_obj, "session": session_obj})()

    def handle_auth_sign_in(self, credentials: dict[str, Any]) -> Any:
        email = str(credentials.get("email") or "").strip().lower()
        password = str(credentials.get("password") or "")
        if self.passwords.get(email) != password:
            raise _PostgrestError("Invalid login credentials", code="400")

        target_profile = None
        for p in self.store["profiles"]:
            if p["email"].lower() == email:
                target_profile = p
                break
        if not target_profile:
            raise _PostgrestError("Invalid login credentials", code="400")

        auth_uid = target_profile.get("auth_user_id") or target_profile["id"]
        jwt_token = _build_test_jwt({"sub": auth_uid, "email": email, "role": "authenticated"})
        user_obj = type("UserObj", (), {"id": auth_uid, "email": email})()
        session_obj = type("SessionObj", (), {"access_token": jwt_token})()
        return type("AuthResp", (), {"user": user_obj, "session": session_obj})()

    def handle_auth_get_user(self, jwt: str) -> Any:
        if not jwt or jwt in self.revoked_tokens:
            raise _PostgrestError("Invalid token", code="401")
        claims = _decode_test_jwt(jwt)
        if not claims.get("sub"):
            raise _PostgrestError("Invalid token", code="401")
        user_obj = type("UserObj", (), {"id": claims["sub"], "email": claims.get("email", "")})()
        return type("UserResp", (), {"user": user_obj})()

    def handle_auth_sign_out(self, token: str | None) -> None:
        if token:
            self.revoked_tokens.add(token)
            self.signed_out_tokens.append(token)

    def _matches_filters(self, row: dict[str, Any], filters: list[tuple[str, Any]]) -> bool:
        return all(str(row.get(col)) == str(val) for col, val in filters)

    def execute_table_op(
        self,
        table: str,
        op: str,
        payload: Any,
        filters: list[tuple[str, Any]],
        limit: int | None,
        access_token: str | None,
    ) -> _FakeResponse:
        auth_uid, caller = self._resolve_caller(access_token)
        caller_role = caller.get("role") if caller else None
        caller_id = caller.get("id") if caller else None

        self.recorded_operations.append(
            {
                "table": table,
                "op": op,
                "access_token": access_token,
                "caller_id": caller_id,
                "caller_role": caller_role,
            }
        )

        rows = self.store.get(table, [])

        if table == "profiles":
            if op == "select":
                if not auth_uid:
                    return _FakeResponse([])
                visible = [
                    copy.deepcopy(r)
                    for r in rows
                    if self._matches_filters(r, filters)
                    and (
                        r.get("auth_user_id") == auth_uid
                        or caller_role in (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE)
                    )
                ]
                return _FakeResponse(visible[:limit] if limit else visible)

            if op == "insert":
                if not auth_uid:
                    raise _PostgrestError("new row violates row-level security policy for table \"profiles\"", "42501")
                item = dict(payload)
                if caller_role != ROLE_SUPER_ADMIN:
                    if item.get("auth_user_id") != auth_uid or item.get("role") not in ("player", "team_captain"):
                        raise _PostgrestError("new row violates row-level security policy for table \"profiles\"", "42501")
                rows.append(item)
                return _FakeResponse([copy.deepcopy(item)])

            if op == "update":
                if not auth_uid:
                    raise _PostgrestError("row-level security policy violation on profiles", "42501")
                updated_rows: list[dict[str, Any]] = []
                for r in rows:
                    if not self._matches_filters(r, filters):
                        continue
                    # RLS USING check: own profile (or unlinked own email during first login) or super_admin
                    is_own = r.get("auth_user_id") == auth_uid or (
                        r.get("auth_user_id") is None
                        and _decode_test_jwt(access_token).get("email") == r.get("email")
                    )
                    if not is_own and caller_role != ROLE_SUPER_ADMIN:
                        raise _PostgrestError("row-level security policy violation on profiles", "42501")

                    # Trigger `prevent_profile_privilege_escalation`
                    if "id" in payload and payload["id"] != r["id"]:
                        raise _PostgrestError("Immutable field: profile id cannot be modified", "42501")
                    if "created_at" in payload and payload["created_at"] != r.get("created_at"):
                        raise _PostgrestError("Immutable field: created_at cannot be modified", "42501")

                    if caller_role != ROLE_SUPER_ADMIN:
                        if "role" in payload and payload["role"] != r["role"]:
                            raise _PostgrestError(
                                "Privilege escalation denied: role cannot be modified by non-admin user",
                                "42501",
                            )
                        if "is_active" in payload and payload["is_active"] != r.get("is_active", True):
                            raise _PostgrestError(
                                "Privilege escalation denied: account active status cannot be modified by non-admin user",
                                "42501",
                            )
                        if "email" in payload and payload["email"] != r["email"]:
                            raise _PostgrestError("Email address cannot be modified directly on profile", "42501")
                        if "username" in payload and payload["username"] != r["username"]:
                            raise _PostgrestError("Username cannot be modified directly by non-admin user", "42501")
                        if (
                            "auth_user_id" in payload
                            and r.get("auth_user_id") is not None
                            and payload["auth_user_id"] != r.get("auth_user_id")
                        ):
                            raise _PostgrestError("Privilege escalation denied: auth_user_id cannot be reassigned", "42501")

                    for k, v in payload.items():
                        r[k] = v
                    updated_rows.append(copy.deepcopy(r))
                return _FakeResponse(updated_rows)

        if table == "tournaments":
            if op == "select":
                matched = [copy.deepcopy(r) for r in rows if self._matches_filters(r, filters)]
                return _FakeResponse(matched[:limit] if limit else matched)
            if op == "insert":
                if not caller or not (
                    caller_role == ROLE_SUPER_ADMIN
                    or (caller_role == ROLE_ORGANIZER and payload.get("organizer_id") == caller_id)
                ):
                    raise _PostgrestError("new row violates row-level security policy for table \"tournaments\"", "42501")
                record = {"id": payload.get("id") or "tour-new-id", **payload}
                rows.append(record)
                return _FakeResponse([copy.deepcopy(record)])
            if op == "update":
                updated = []
                for r in rows:
                    if self._matches_filters(r, filters):
                        if not caller or not (
                            caller_role == ROLE_SUPER_ADMIN
                            or (caller_role == ROLE_ORGANIZER and r.get("organizer_id") == caller_id)
                        ):
                            raise _PostgrestError("row-level security policy violation for table \"tournaments\"", "42501")
                        r.update(payload)
                        updated.append(copy.deepcopy(r))
                return _FakeResponse(updated)
            if op == "delete":
                deleted = []
                remaining = []
                for r in rows:
                    if self._matches_filters(r, filters):
                        if not caller or not (
                            caller_role == ROLE_SUPER_ADMIN
                            or (caller_role == ROLE_ORGANIZER and r.get("organizer_id") == caller_id)
                        ):
                            raise _PostgrestError("row-level security policy violation for table \"tournaments\"", "42501")
                        deleted.append(copy.deepcopy(r))
                    else:
                        remaining.append(r)
                self.store[table] = remaining
                return _FakeResponse(deleted)

        if table == "teams":
            if op == "select":
                matched = [copy.deepcopy(r) for r in rows if self._matches_filters(r, filters)]
                return _FakeResponse(matched[:limit] if limit else matched)
            if op == "insert":
                if not caller or not (
                    caller_role == ROLE_SUPER_ADMIN
                    or (caller_role == ROLE_TEAM_CAPTAIN and payload.get("captain_id") == caller_id)
                ):
                    raise _PostgrestError("new row violates row-level security policy for table \"teams\"", "42501")
                record = {"id": payload.get("id") or "team-new-id", **payload}
                rows.append(record)
                return _FakeResponse([copy.deepcopy(record)])

        if table == "activity_logs":
            if op == "select":
                if not caller:
                    raise _PostgrestError("row-level security policy violation for table \"activity_logs\"", "42501")
                visible = [
                    copy.deepcopy(r)
                    for r in rows
                    if self._matches_filters(r, filters)
                    and (caller_role == ROLE_SUPER_ADMIN or r.get("actor_id") == caller_id)
                ]
                return _FakeResponse(visible)
            if op == "insert":
                if not caller or (caller_role != ROLE_SUPER_ADMIN and payload.get("actor_id") != caller_id):
                    raise _PostgrestError("row-level security policy violation for table \"activity_logs\"", "42501")
                rec = {"id": "log-new", **payload}
                rows.append(rec)
                return _FakeResponse([copy.deepcopy(rec)])

        # Default select/insert for auxiliary tables (`games`, `registrations`, `matches`, `team_members`)
        if op == "select":
            matched = [copy.deepcopy(r) for r in rows if self._matches_filters(r, filters)]
            return _FakeResponse(matched[:limit] if limit else matched)
        if op == "insert":
            item = dict(payload)
            rows.append(item)
            return _FakeResponse([copy.deepcopy(item)])
        return _FakeResponse([])

    def execute_rpc(self, fn_name: str, params: dict[str, Any], access_token: str | None) -> _FakeResponse:
        if fn_name != "replace_tournament_matches":
            raise _PostgrestError(f"Unknown RPC {fn_name}", "42883")

        _, caller = self._resolve_caller(access_token)
        caller_role = caller.get("role") if caller else None
        caller_id = caller.get("id") if caller else None

        p_tournament_id = params.get("p_tournament_id")
        p_matches = params.get("p_matches")

        self.recorded_operations.append(
            {
                "table": "rpc:replace_tournament_matches",
                "op": "rpc",
                "access_token": access_token,
                "caller_id": caller_id,
                "caller_role": caller_role,
            }
        )

        # Mirror SQL validation order in `0002_security_hardening.sql` BEFORE DELETE:
        if not p_tournament_id:
            raise _PostgrestError("tournament_id wajib diisi", "22023")
        if p_matches is None:
            raise _PostgrestError("p_matches tidak boleh bernilai NULL", "22023")
        if not isinstance(p_matches, list):
            raise _PostgrestError("p_matches harus berupa JSON array", "22023")

        tournament = next((t for t in self.store["tournaments"] if t["id"] == p_tournament_id), None)
        if not tournament:
            raise _PostgrestError("Turnamen tidak ditemukan", "P0002")

        # SECURITY INVOKER RLS check on `matches`
        is_assigned_committee = any(
            s["tournament_id"] == p_tournament_id and s["user_id"] == caller_id
            for s in self.store["tournament_staff"]
        )
        if not caller or not (
            caller_role == ROLE_SUPER_ADMIN
            or (caller_role == ROLE_ORGANIZER and tournament.get("organizer_id") == caller_id)
            or (caller_role == ROLE_COMMITTEE and is_assigned_committee)
        ):
            raise _PostgrestError("row-level security policy violation for table \"matches\"", "42501")

        # Pre-DELETE element validation + transactional snapshot
        for elem in p_matches:
            if (
                not isinstance(elem, dict)
                or elem.get("round_number") is None
                or elem.get("match_number") is None
                or isinstance(elem.get("round_number"), bool)
                or not isinstance(elem.get("round_number"), int)
                or elem["round_number"] < 1
                or isinstance(elem.get("match_number"), bool)
                or not isinstance(elem.get("match_number"), int)
                or elem["match_number"] < 1
            ):
                raise _PostgrestError(
                    "Setiap elemen p_matches wajib berupa JSON object dengan round_number dan match_number bertipe integer positif",
                    "22023",
                )

        snapshot = copy.deepcopy(self.store["matches"])
        try:
            retained = [m for m in self.store["matches"] if m["tournament_id"] != p_tournament_id]
            inserted: list[dict[str, Any]] = []
            valid_team_ids = {t["id"] for t in self.store["teams"]}
            for elem in p_matches:
                team_a = elem.get("team_a_id")
                team_b = elem.get("team_b_id")
                if team_a and team_a not in valid_team_ids:
                    raise _PostgrestError("insert or update on table \"matches\" violates foreign key constraint", "23503")
                if team_b and team_b not in valid_team_ids:
                    raise _PostgrestError("insert or update on table \"matches\" violates foreign key constraint", "23503")
                if team_a and team_b and team_a == team_b:
                    raise _PostgrestError("new row for relation \"matches\" violates check constraint \"chk_different_teams\"", "23514")
                inserted.append(copy.deepcopy(elem))
            self.store["matches"] = retained + inserted
            return _FakeResponse(inserted)
        except Exception:
            self.store["matches"] = snapshot
            raise


def test_mock_login_and_session_resolution(mock_repo: MockDataStoreRepository) -> None:
    auth = AuthService(mock_repo)
    demo_accounts = [
        ("admin@turnamen.in", ROLE_SUPER_ADMIN),
        ("organizer@turnamen.in", ROLE_ORGANIZER),
        ("committee@turnamen.in", ROLE_COMMITTEE),
        ("captain@turnamen.in", ROLE_TEAM_CAPTAIN),
        ("player@turnamen.in", ROLE_PLAYER),
    ]
    for email, expected_role in demo_accounts:
        res = auth.login(email, "turnamen123")
        assert "token" in res
        assert res["token"].startswith("tok_")
        assert res["user"]["role"] == expected_role
        assert "password_hash" not in res["user"]

        me = auth.get_user_by_token(res["token"])
        assert me is not None
        assert me["email"] == email
        assert me["role"] == expected_role

        assert auth.logout(res["token"]) is True
        assert auth.get_user_by_token(res["token"]) is None


def test_login_rejects_wrong_password(mock_repo: MockDataStoreRepository) -> None:
    auth = AuthService(mock_repo)
    with pytest.raises(DomainUnauthorizedError):
        auth.login("organizer@turnamen.in", "wrong-password")


def test_self_registration_prevents_privilege_escalation(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    for privileged_role in (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE):
        with pytest.raises(DomainForbiddenError, match="Pendaftaran mandiri tidak diizinkan"):
            auth.register(
                {
                    "email": f"hacker_{privileged_role}@turnamen.in",
                    "username": f"elevated_{privileged_role}",
                    "full_name": "Unauthorized Escalation",
                    "password": "password123",
                    "role": privileged_role,
                }
            )


def test_self_registration_allows_player_and_captain_and_checks_conflicts(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    captain_res = auth.register(
        {
            "email": "newcaptain@turnamen.in",
            "username": "new_capt",
            "full_name": "Kapten Baru",
            "password": "password123",
            "role": ROLE_TEAM_CAPTAIN,
        }
    )
    assert captain_res["user"]["role"] == ROLE_TEAM_CAPTAIN
    assert "password_hash" not in captain_res["user"]

    with pytest.raises(DomainConflictError, match="Email sudah terdaftar"):
        auth.register(
            {
                "email": "newcaptain@turnamen.in",
                "username": "other_user",
                "full_name": "Duplikat Email",
                "password": "password123",
            }
        )

    with pytest.raises(DomainConflictError, match="Username sudah digunakan"):
        auth.register(
            {
                "email": "unique@turnamen.in",
                "username": "new_capt",
                "full_name": "Duplikat Username",
                "password": "password123",
            }
        )


def test_update_profile_and_role_assignment_security(
    mock_repo: MockDataStoreRepository,
) -> None:
    auth = AuthService(mock_repo)
    player_login = auth.login("player@turnamen.in", "turnamen123")
    player_user = player_login["user"]
    admin_login = auth.login("admin@turnamen.in", "turnamen123")
    admin_user = admin_login["user"]

    updated = auth.update_profile(
        actor=player_user,
        target_user_id=player_user["id"],
        payload={"full_name": "Rizky Maulana Pro", "phone": "081299998888"},
    )
    assert updated["full_name"] == "Rizky Maulana Pro"
    assert updated["phone"] == "081299998888"
    assert "password_hash" not in updated

    with pytest.raises(DomainForbiddenError, match="tidak diizinkan mengubah role"):
        auth.update_profile(
            actor=player_user,
            target_user_id=player_user["id"],
            payload={"role": ROLE_SUPER_ADMIN},
        )

    with pytest.raises(DomainForbiddenError, match="milik sendiri"):
        auth.update_profile(
            actor=player_user,
            target_user_id=admin_user["id"],
            payload={"full_name": "Bajak Admin"},
        )

    with pytest.raises(DomainForbiddenError):
        auth.assign_role(actor=player_user, target_user_id=player_user["id"], new_role=ROLE_COMMITTEE)

    promoted = auth.assign_role(
        actor=admin_user,
        target_user_id=player_user["id"],
        new_role=ROLE_COMMITTEE,
    )
    assert promoted["role"] == ROLE_COMMITTEE


def test_role_permission_matrix() -> None:
    assert has_permission(ROLE_SUPER_ADMIN, "tournament:create") is True
    assert has_permission(ROLE_ORGANIZER, "tournament:create") is True
    assert has_permission(ROLE_COMMITTEE, "tournament:create") is False
    assert has_permission(ROLE_TEAM_CAPTAIN, "tournament:create") is False
    assert has_permission(ROLE_PLAYER, "tournament:create") is False

    assert has_permission(ROLE_COMMITTEE, "match:submit_result") is True
    assert has_permission(ROLE_COMMITTEE, "registration:verify") is True
    assert has_permission(ROLE_COMMITTEE, "announcement:create") is True
    assert has_permission(ROLE_TEAM_CAPTAIN, "team:create") is True
    assert has_permission(ROLE_TEAM_CAPTAIN, "registration:create") is True
    assert has_permission(ROLE_PLAYER, "match:submit_result") is False
    assert has_permission(ROLE_SUPER_ADMIN, "user:assign_role") is True
    assert has_permission(ROLE_ORGANIZER, "user:assign_role") is False

    player_user = {"id": "u1", "role": ROLE_PLAYER, "is_active": True}
    with pytest.raises(DomainForbiddenError):
        require_permission(player_user, "match:submit_result")

    with pytest.raises(DomainForbiddenError):
        require_any_role(player_user, (ROLE_SUPER_ADMIN, ROLE_ORGANIZER))

    inactive_user = {"id": "u2", "role": ROLE_SUPER_ADMIN, "is_active": False}
    with pytest.raises(DomainForbiddenError, match="dinonaktifkan"):
        require_authenticated(inactive_user)

    assert RolePermissionGuard.has_permission(ROLE_SUPER_ADMIN, "game:manage") is True


def test_repository_foreign_key_integrity(mock_repo: MockDataStoreRepository) -> None:
    organizer = mock_repo.get_profile_by_email("organizer@turnamen.in")
    captain = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert organizer is not None and captain is not None

    with pytest.raises(DomainNotFoundError, match="Game tidak ditemukan"):
        mock_repo.create_tournament(
            {
                "slug": "invalid-game-tour",
                "title": "Invalid Game Tournament",
                "game_id": "non-existent-game",
                "organizer_id": organizer["id"],
                "start_date": "2026-12-01T10:00:00+07:00",
            }
        )

    with pytest.raises(DomainNotFoundError, match="Game tidak ditemukan"):
        mock_repo.create_team(
            {
                "name": "Ghost Team",
                "tag": "GHT",
                "game_id": "non-existent-game",
                "captain_id": captain["id"],
            }
        )

    with pytest.raises(DomainNotFoundError, match="Turnamen tidak ditemukan"):
        mock_repo.create_registration(
            {
                "tournament_id": "non-existent-tournament",
                "team_id": "44444444-4444-4444-8444-444444444401",
                "registered_by": captain["id"],
            }
        )

    with pytest.raises(DomainNotFoundError, match="Tim tidak ditemukan"):
        mock_repo.create_registration(
            {
                "tournament_id": "33333333-3333-4333-8333-333333333301",
                "team_id": "non-existent-team",
                "registered_by": captain["id"],
            }
        )

    with pytest.raises(DomainNotFoundError, match="Pertandingan tidak ditemukan"):
        mock_repo.record_match_result(
            {
                "match_id": "non-existent-match",
                "score_a": 2,
                "score_b": 0,
                "winner_team_id": "44444444-4444-4444-8444-444444444401",
                "verified_by": organizer["id"],
            }
        )


def test_supabase_client_credential_validation_and_no_monkey_patch() -> None:
    import re as stdlib_re
    from supabase._sync import client as sync_client_mod

    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    service_role_jwt = _build_test_jwt({"role": "service_role", "iss": "supabase"})

    with pytest.raises(RuntimeError, match="SUPABASE_URL dan SUPABASE_ANON_KEY belum tersedia"):
        validate_supabase_credentials("", "")

    with pytest.raises(RuntimeError, match="SUPABASE_URL tidak valid"):
        validate_supabase_credentials("https://your-project-ref.supabase.co", valid_anon_jwt)

    with pytest.raises(RuntimeError, match="service_role"):
        validate_supabase_credentials("https://example.supabase.co", "sb_secret_12345")

    with pytest.raises(RuntimeError, match="service_role"):
        validate_supabase_credentials("https://example.supabase.co", service_role_jwt)

    with pytest.raises(RuntimeError, match="sb_publishable_"):
        validate_supabase_credentials(
            "https://example.supabase.co",
            "sb_publishable_test_key_format",
        )

    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )
    client = create_supabase_client(cfg, access_token=valid_anon_jwt)
    assert client is not None
    assert sync_client_mod.re.match is stdlib_re.match


def test_online_supabase_auth_session_registration_and_email_confirmation() -> None:
    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )

    # 1. Registration when session IS immediately available (auto-confirm):
    # Trigger `on_auth_user_created` already inserts the profile; AuthService must NOT insert a second profile!
    engine_session = _RLSEnforcingSupabaseEngine(email_confirmation_required=False)
    repo_session = SupabaseDataStoreRepository(cfg, client_factory=engine_session.create_client)
    auth_session = AuthService(repo_session)

    reg_res = auth_session.register(
        {
            "email": "active_new@turnamen.in",
            "username": "active_new",
            "full_name": "Active New Player",
            "password": "password123",
            "role": ROLE_PLAYER,
            "phone": "081122334455",
        }
    )
    assert reg_res["token"] is not None
    assert reg_res["requires_email_confirmation"] is False
    assert reg_res["user"]["email"] == "active_new@turnamen.in"
    assert reg_res["user"]["phone"] == "081122334455"

    profile_inserts = [
        op for op in engine_session.recorded_operations if op["table"] == "profiles" and op["op"] == "insert"
    ]
    assert len(profile_inserts) == 0, "AuthService must not execute a second INSERT when trigger created profile"
    profile_selects = [
        op for op in engine_session.recorded_operations if op["table"] == "profiles" and op["op"] == "select"
    ]
    assert len(profile_selects) == 1
    assert profile_selects[0]["access_token"] == reg_res["token"]

    # 2. Registration when email confirmation IS enabled (no session available yet):
    # Must NOT query or write private `profiles` or `activity_logs` with `anon` client, and must return token=None!
    engine_confirm = _RLSEnforcingSupabaseEngine(email_confirmation_required=True)
    repo_confirm = SupabaseDataStoreRepository(cfg, client_factory=engine_confirm.create_client)
    auth_confirm = AuthService(repo_confirm)

    pending_res = auth_confirm.register(
        {
            "email": "pending_confirm@turnamen.in",
            "username": "pending_user",
            "full_name": "Pending Confirmation User",
            "password": "password123",
            "role": ROLE_TEAM_CAPTAIN,
        }
    )
    assert pending_res["token"] is None
    assert pending_res["requires_email_confirmation"] is True
    assert pending_res["user"]["role"] == ROLE_TEAM_CAPTAIN
    assert engine_confirm.recorded_operations == [], (
        "No anon queries to private profiles/activity_logs should occur when session is pending email confirmation"
    )


def test_online_login_inactive_user_and_jwt_propagation() -> None:
    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )
    engine = _RLSEnforcingSupabaseEngine()
    repo = SupabaseDataStoreRepository(cfg, client_factory=engine.create_client)
    auth = AuthService(repo)

    # Login propagates user JWT to profile lookup (would return [] if anon were used!)
    login_res = auth.login("player@turnamen.in", "turnamen123")
    player_jwt = login_res["token"]
    assert login_res["user"]["role"] == ROLE_PLAYER
    assert engine.recorded_operations[-1]["access_token"] == player_jwt

    resolved = auth.get_user_by_token(player_jwt)
    assert resolved is not None
    assert resolved["email"] == "player@turnamen.in"

    # Deactivate player account and verify login and token resolution both reject access
    for p in engine.store["profiles"]:
        if p["email"] == "player@turnamen.in":
            p["is_active"] = False

    with pytest.raises(DomainForbiddenError, match="tidak aktif"):
        auth.login("player@turnamen.in", "turnamen123")

    assert auth.get_user_by_token(player_jwt) is None


def test_two_users_concurrent_and_flask_requests_do_not_leak_jwt() -> None:
    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )
    engine = _RLSEnforcingSupabaseEngine()
    repo = SupabaseDataStoreRepository(cfg, client_factory=engine.create_client)
    app = create_app(config=cfg, repository=repo)
    client = app.test_client()

    org_login = client.post(
        "/api/v1/auth/login",
        json={"email": "organizer@turnamen.in", "password": "turnamen123"},
    ).get_json()["data"]
    capt_login = client.post(
        "/api/v1/auth/login",
        json={"email": "captain@turnamen.in", "password": "turnamen123"},
    ).get_json()["data"]
    player_login = client.post(
        "/api/v1/auth/login",
        json={"email": "player@turnamen.in", "password": "turnamen123"},
    ).get_json()["data"]

    org_jwt = org_login["token"]
    capt_jwt = capt_login["token"]
    player_jwt = player_login["token"]
    assert org_jwt != capt_jwt != player_jwt

    # Organizer creates tournament via Flask API -> JWT is propagated to SupabaseDataStoreRepository.create_tournament
    create_tour_resp = client.post(
        "/api/v1/tournaments",
        headers={"Authorization": f"Bearer {org_jwt}"},
        json={
            "title": "Garuda Online Cup",
            "game_id": "22222222-2222-4222-8222-222222222201",
            "start_date": "2026-12-15T10:00:00+07:00",
        },
    )
    assert create_tour_resp.status_code == 201
    insert_tour_ops = [
        op for op in engine.recorded_operations if op["table"] == "tournaments" and op["op"] == "insert"
    ]
    assert len(insert_tour_ops) == 1
    assert insert_tour_ops[0]["access_token"] == org_jwt
    assert insert_tour_ops[0]["caller_role"] == ROLE_ORGANIZER

    # Immediately after Organizer's request, Captain creates a team -> uses Captain's JWT, NOT Organizer's JWT!
    create_team_resp = client.post(
        "/api/v1/teams",
        headers={"Authorization": f"Bearer {capt_jwt}"},
        json={
            "name": "Phoenix Esports",
            "tag": "PHX",
            "game_id": "22222222-2222-4222-8222-222222222201",
        },
    )
    assert create_team_resp.status_code == 201
    insert_team_ops = [
        op for op in engine.recorded_operations if op["table"] == "teams" and op["op"] == "insert"
    ]
    assert len(insert_team_ops) == 1
    assert insert_team_ops[0]["access_token"] == capt_jwt
    assert insert_team_ops[0]["caller_role"] == ROLE_TEAM_CAPTAIN

    # Unauthenticated request after authenticated requests does NOT inherit previous user's JWT
    assert get_current_access_token() is None
    me_unauth = client.get("/api/v1/auth/me")
    assert me_unauth.status_code == 401

    # Concurrent multi-threaded repository operations with two different JWTs never cross-contaminate
    def _worker_fetch_own_profile(jwt_token: str, expected_email: str) -> str:
        with use_access_token(jwt_token):
            profiles = repo.list_profiles()
            assert len(profiles) >= 1
            own = [p for p in profiles if p["email"] == expected_email]
            assert len(own) == 1
            return own[0]["email"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_player = pool.submit(_worker_fetch_own_profile, player_jwt, "player@turnamen.in")
        f_capt = pool.submit(_worker_fetch_own_profile, capt_jwt, "captain@turnamen.in")
        assert f_player.result() == "player@turnamen.in"
        assert f_capt.result() == "captain@turnamen.in"


def test_rls_profiles_update_behavior_and_anti_privilege_escalation() -> None:
    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )
    engine = _RLSEnforcingSupabaseEngine()
    repo = SupabaseDataStoreRepository(cfg, client_factory=engine.create_client)

    player_jwt = engine.token_for_profile("player@turnamen.in")
    admin_jwt = engine.token_for_profile("admin@turnamen.in")
    player_id = "11111111-1111-4111-8111-111111111105"
    admin_id = "11111111-1111-4111-8111-111111111101"

    # 1. Player can update their own mutable fields (`full_name`, `phone`) via Data API without recursion
    with use_access_token(player_jwt):
        updated = repo.update_profile(player_id, {"full_name": "Rizky Updated", "phone": "0899112233"})
        assert updated is not None
        assert updated["full_name"] == "Rizky Updated"
        assert updated["phone"] == "0899112233"

        # 2. Player cannot update another user's profile via direct Data API call
        with pytest.raises(DomainForbiddenError):
            repo.update_profile(admin_id, {"full_name": "Hacked Admin"})

        # 3. Player cannot escalate their own role, active status, email, username, or auth_user_id via direct Data API call
        for forbidden_patch in (
            {"role": ROLE_SUPER_ADMIN},
            {"is_active": False},
            {"email": "spoofed@turnamen.in"},
            {"username": "spoofed_username"},
            {"auth_user_id": "99999999-9999-4999-8999-999999999999"},
        ):
            with pytest.raises(DomainForbiddenError):
                repo.update_profile(player_id, forbidden_patch)

    # 4. Super Admin can assign/promote role on target profile
    with use_access_token(admin_jwt):
        promoted = repo.update_profile(player_id, {"role": ROLE_COMMITTEE})
        assert promoted is not None
        assert promoted["role"] == ROLE_COMMITTEE


def test_rpc_replace_tournament_matches_validation_and_rollback() -> None:
    valid_anon_jwt = _build_test_jwt({"role": "anon", "iss": "supabase"})
    cfg = AppConfig(
        app_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_anon_key=valid_anon_jwt,
    )
    engine = _RLSEnforcingSupabaseEngine()
    repo = SupabaseDataStoreRepository(cfg, client_factory=engine.create_client)

    tournament_id = "33333333-3333-4333-8333-333333333301"
    organizer_jwt = engine.token_for_profile("organizer@turnamen.in")
    player_jwt = engine.token_for_profile("player@turnamen.in")

    initial_matches = repo.list_matches_by_tournament(tournament_id)
    assert len(initial_matches) == 7

    # 1. Unauthorized role (`player`) calling RPC is rejected by SECURITY INVOKER RLS; old bracket stays intact
    with use_access_token(player_jwt):
        with pytest.raises(DomainForbiddenError):
            repo.replace_tournament_matches(
                tournament_id,
                [{"id": "55555555-5555-4555-8555-555555555599", "round_number": 1, "match_number": 1}],
            )
    assert len(repo.list_matches_by_tournament(tournament_id)) == 7

    with use_access_token(organizer_jwt):
        # 2. NULL payload is rejected BEFORE DELETE ( both at repository layer and SQL RPC layer )
        with pytest.raises(DomainValidationError):
            repo.replace_tournament_matches(tournament_id, None)  # type: ignore[arg-type]
        with pytest.raises(_PostgrestError, match="NULL"):
            engine.execute_rpc(
                "replace_tournament_matches",
                {"p_tournament_id": tournament_id, "p_matches": None},
                organizer_jwt,
            )
        assert len(repo.list_matches_by_tournament(tournament_id)) == 7

        # 3. JSON object payload (`{}`) is rejected BEFORE DELETE
        with pytest.raises(DomainValidationError):
            repo.replace_tournament_matches(tournament_id, {"not": "an_array"})  # type: ignore[arg-type]
        with pytest.raises(_PostgrestError, match="JSON array"):
            engine.execute_rpc(
                "replace_tournament_matches",
                {"p_tournament_id": tournament_id, "p_matches": {"not": "an_array"}},
                organizer_jwt,
            )
        assert len(repo.list_matches_by_tournament(tournament_id)) == 7

        # 4. Invalid data in the middle of insert (e.g. non-existent FK team_a_id on match 2) rolls back transaction
        with pytest.raises(DomainNotFoundError):
            repo.replace_tournament_matches(
                tournament_id,
                [
                    {
                        "id": "55555555-5555-4555-8555-555555555591",
                        "round_number": 1,
                        "round_name": "Final",
                        "match_number": 1,
                        "team_a_id": "44444444-4444-4444-8444-444444444401",
                        "team_b_id": "44444444-4444-4444-8444-444444444402",
                    },
                    {
                        "id": "55555555-5555-4555-8555-555555555592",
                        "round_number": 1,
                        "round_name": "Invalid FK Match",
                        "match_number": 2,
                        "team_a_id": "99999999-9999-4999-8999-999999999999",
                    },
                ],
            )
        assert len(repo.list_matches_by_tournament(tournament_id)) == 7

        # 5. Valid array replaces the bracket atomically
        new_bracket = repo.replace_tournament_matches(
            tournament_id,
            [
                {
                    "id": "55555555-5555-4555-8555-555555555591",
                    "round_number": 1,
                    "round_name": "Grand Final",
                    "match_number": 1,
                    "team_a_id": "44444444-4444-4444-8444-444444444401",
                    "team_b_id": "44444444-4444-4444-8444-444444444402",
                    "status": "scheduled",
                    "best_of": 3,
                }
            ],
        )
        assert len(new_bracket) == 1
        assert new_bracket[0]["round_name"] == "Grand Final"

        # 6. Explicit empty array `[]` clears the bracket as documented
        cleared = repo.replace_tournament_matches(tournament_id, [])
        assert cleared == []


def test_rls_security_hardening_migration_policies() -> None:
    assert isinstance(MockDataStoreRepository(), DataStoreRepositoryProtocol)

    migration_path = (
        Path(__file__).resolve().parents[2]
        / "supabase"
        / "migrations"
        / "0002_security_hardening.sql"
    )
    assert migration_path.exists()
    sql = migration_path.read_text(encoding="utf-8")

    expected_tables = (
        "profiles",
        "games",
        "tournaments",
        "teams",
        "team_members",
        "tournament_staff",
        "registrations",
        "matches",
        "match_results",
        "payments",
        "announcements",
        "activity_logs",
    )
    for table in expected_tables:
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;" in sql

    assert "FOR ALL USING (true)" not in sql
    assert "WITH CHECK (true)" not in sql
    assert "FROM public.profiles p WHERE p.id = profiles.id" not in sql
    assert "IF p_matches IS NULL THEN" in sql
    assert "IF jsonb_typeof(p_matches) <> 'array' THEN" in sql
    assert sql.index("IF jsonb_typeof(p_matches) <> 'array' THEN") < sql.index(
        "DELETE FROM public.matches WHERE tournament_id = p_tournament_id;"
    )
    assert "CREATE OR REPLACE FUNCTION public.prevent_profile_privilege_escalation()" in sql
    assert "CREATE OR REPLACE FUNCTION public.replace_tournament_matches(" in sql
