"""Wave 5 Regression Tests: Functional Gap Closure, State Integrity, Author Projection & Session Persistence."""

from __future__ import annotations

import base64
import copy
import json
import time
from typing import Any

import pytest

from backend.app import create_app
from backend.contracts.dtos import ROLE_COMMITTEE, ROLE_ORGANIZER, ROLE_PLAYER, ROLE_SUPER_ADMIN
from backend.core.config import load_config
from backend.core.exceptions import DomainConflictError, DomainForbiddenError
from backend.infrastructure.supabase.client import use_access_token
from backend.modules.tournaments.service import TournamentService
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
from tests.unit.test_wave3_6_interaction_hotfixes import _run_hotfix_harness

MLBB_GAME_ID = "22222222-2222-4222-8222-222222222201"
MLBB_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301"
VAL_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333302"


def _login_headers(client: Any, email: str, password: str = "turnamen123") -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    token = resp.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_update_tournament_routes_status_through_transition_and_prevents_partial_writes() -> None:
    repo = MockDataStoreRepository()
    svc = TournamentService(repo)
    organizer = repo.get_profile_by_email("organizer@turnamen.in")
    assert organizer is not None

    tour = svc.create_tournament(
        organizer,
        {
            "title": "Wave 5 Cup",
            "game_id": MLBB_GAME_ID,
            "start_date": "2026-12-20T10:00:00+07:00",
            "status": "draft",
        },
    )
    calls: list[tuple[str, str]] = []
    real_transition = repo.transition_tournament_status

    def _spy_transition(tid: str, new_status: str) -> dict[str, Any] | None:
        calls.append((tid, new_status))
        return real_transition(tid, new_status)

    repo.transition_tournament_status = _spy_transition  # type: ignore[method-assign]

    # Updating ordinary field must not trigger status transition or mutate status.
    updated_title = svc.update_tournament(organizer, tour["id"], {"title": "Wave 5 Updated"})
    assert updated_title["title"] == "Wave 5 Updated"
    assert updated_title["status"] == "draft"
    assert calls == []

    # Legal forward move uses transition_tournament_status.
    opened = svc.update_tournament(
        organizer, tour["id"], {"status": "open_registration", "venue": "Jakarta Hall"}
    )
    assert opened["status"] == "open_registration"
    assert opened["venue"] == "Jakarta Hall"
    assert calls == [(tour["id"], "open_registration")]

    # Move to ongoing, then try illegal completion without completed bracket + simultaneous title change:
    svc.update_tournament(organizer, tour["id"], {"status": "ongoing"})
    with pytest.raises(DomainConflictError):
        svc.update_tournament(
            organizer,
            tour["id"],
            {"title": "Should Not Be Saved", "status": "completed"},
        )
    persisted = svc.get_tournament(tour["id"])
    assert persisted["status"] == "ongoing"
    assert persisted["title"] == "Wave 5 Updated"

    # Terminal transition cancelled works via transition_tournament_status, after which all edits are rejected.
    assert svc.update_tournament(organizer, tour["id"], {"status": "cancelled"})["status"] == "cancelled"
    with pytest.raises(DomainConflictError):
        svc.update_tournament(organizer, tour["id"], {"status": "open_registration"})


def test_supabase_announcements_use_safe_projection_rpc_without_direct_profiles_select() -> None:
    cfg = load_config(
        overrides={
            "app_mode": "supabase",
            "supabase_url": "https://example.supabase.co",
            "supabase_anon_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.sig123456",
        }
    )
    direct_tables_queried: list[str] = []

    class _FakeResp:
        def __init__(self, data: Any) -> None:
            self.data = data

    class _RpcExec:
        def __init__(self, name: str, params: dict[str, Any]) -> None:
            self._name = name
            self._params = params

        def execute(self) -> _FakeResp:
            assert self._name == "list_tournament_announcements"
            return _FakeResp(
                [
                    {
                        "id": "ann-1",
                        "tournament_id": MLBB_TOURNAMENT_ID,
                        "author_id": "auth-1",
                        "title": "Jadwal",
                        "content": "Check in segera.",
                        "priority": "important",
                        "is_pinned": True,
                        "author_name": "Nadia Kusuma",
                    },
                    {
                        "id": "ann-2",
                        "tournament_id": MLBB_TOURNAMENT_ID,
                        "author_id": "auth-missing",
                        "title": "Info Sistem",
                        "content": "Pembuat profil tidak ditemukan.",
                        "priority": "normal",
                        "is_pinned": False,
                        "author_name": "",
                    },
                ]
            )

    class _FakeClient:
        def table(self, name: str) -> Any:
            direct_tables_queried.append(name)
            raise AssertionError(f"Unexpected direct table query on {name}")

        def rpc(self, name: str, params: dict[str, Any]) -> _RpcExec:
            return _RpcExec(name, params)

    repo = SupabaseDataStoreRepository(cfg, client_factory=lambda *a, **kw: _FakeClient())
    items = repo.list_announcements_by_tournament(MLBB_TOURNAMENT_ID)
    assert direct_tables_queried == []
    assert [i["author_name"] for i in items] == ["Nadia Kusuma", "Panitia"]


def test_announcements_endpoint_cross_role_and_draft_isolation() -> None:
    repo = MockDataStoreRepository()
    app = create_app(load_config({"app_mode": "mock"}), repository=repo)
    client = app.test_client()

    # Add missing-author announcement and draft tournament announcement.
    draft_tour = TournamentService(repo).create_tournament(
        repo.get_profile_by_email("organizer@turnamen.in"),
        {
            "title": "Draft Private Ann Cup",
            "game_id": MLBB_GAME_ID,
            "start_date": "2026-12-25T10:00:00+07:00",
            "status": "draft",
        },
    )
    repo.create_announcement(
        {
            "tournament_id": MLBB_TOURNAMENT_ID,
            "author_id": "00000000-0000-4000-8000-000000000999",
            "title": "Sistem Fallback",
            "content": "Author eksternal sudah dihapus.",
            "priority": "normal",
        }
    )
    repo.create_announcement(
        {
            "tournament_id": draft_tour["id"],
            "author_id": "11111111-1111-4111-8111-111111111102",
            "title": "Draft Secret Notice",
            "content": "Khusus organizer.",
        }
    )

    for headers in (
        {},
        _login_headers(client, "player@turnamen.in"),
        _login_headers(client, "organizer@turnamen.in"),
        _login_headers(client, "committee@turnamen.in"),
    ):
        resp = client.get(f"/api/v1/tournaments/{MLBB_TOURNAMENT_ID}/announcements", headers=headers)
        assert resp.status_code == 200
        rows = resp.get_json()["data"]
        names = {r["author_name"] for r in rows}
        assert "Nadia Kusuma (Tournament Organizer)" in names
        assert "Bima Saputra (Head Committee)" in names
        assert "Panitia" in names

    # Draft announcements stay hidden from Guest and Player, visible to owning Organizer.
    assert client.get(f"/api/v1/tournaments/{draft_tour['id']}/announcements").get_json()["data"] == []
    player_headers = _login_headers(client, "player@turnamen.in")
    assert client.get(f"/api/v1/tournaments/{draft_tour['id']}/announcements", headers=player_headers).get_json()["data"] == []
    org_headers = _login_headers(client, "organizer@turnamen.in")
    assert len(client.get(f"/api/v1/tournaments/{draft_tour['id']}/announcements", headers=org_headers).get_json()["data"]) == 1


def test_partial_features_api_end_to_end_profile_games_staff_and_assign_role() -> None:
    repo = MockDataStoreRepository()
    app = create_app(load_config({"app_mode": "mock"}), repository=repo)
    client = app.test_client()

    admin_h = _login_headers(client, "admin@turnamen.in")
    org_h = _login_headers(client, "organizer@turnamen.in")
    player_h = _login_headers(client, "player@turnamen.in")

    # 1. PATCH /api/v1/auth/me
    assert client.patch("/api/v1/auth/me", json={"full_name": "Guest Fail"}).status_code == 401
    upd_me = client.patch(
        "/api/v1/auth/me",
        headers=player_h,
        json={"full_name": "Rizky Updated", "phone": "081234567890", "avatar_url": "https://img.local/a.png"},
    )
    assert upd_me.status_code == 200
    assert upd_me.get_json()["data"]["user"]["full_name"] == "Rizky Updated"
    # Self role escalation rejected
    assert client.patch("/api/v1/auth/me", headers=player_h, json={"role": "super_admin"}).status_code == 403

    # 2. Users list & assign_role (super_admin only)
    assert client.get("/api/v1/users", headers=org_h).status_code == 403
    users_res = client.get("/api/v1/users", headers=admin_h)
    assert users_res.status_code == 200
    player_id = "11111111-1111-4111-8111-111111111105"
    assert client.patch(f"/api/v1/users/{player_id}/role", headers=org_h, json={"role": "committee"}).status_code == 403
    role_res = client.patch(
        f"/api/v1/users/{player_id}/role",
        headers=admin_h,
        json={"role": ROLE_COMMITTEE},
    )
    assert role_res.status_code == 200
    assert role_res.get_json()["data"]["user"]["role"] == ROLE_COMMITTEE

    # 3. Games CRUD (super_admin only)
    assert client.post("/api/v1/games", headers=org_h, json={"name": "CS2", "genre": "FPS"}).status_code == 403
    g_create = client.post(
        "/api/v1/games",
        headers=admin_h,
        json={"name": "Counter-Strike 2", "genre": "FPS", "team_size": 5, "default_best_of": 3},
    )
    assert g_create.status_code == 201
    new_gid = g_create.get_json()["data"]["id"]
    assert client.patch(f"/api/v1/games/{new_gid}", headers=org_h, json={"name": "Hacked"}).status_code == 403
    g_upd = client.patch(f"/api/v1/games/{new_gid}", headers=admin_h, json={"is_active": False})
    assert g_upd.status_code == 200 and g_upd.get_json()["data"]["is_active"] is False
    public_ids = {g["id"] for g in client.get("/api/v1/games").get_json()["data"]}
    assert new_gid not in public_ids
    admin_ids = {g["id"] for g in client.get("/api/v1/games?include_inactive=true", headers=admin_h).get_json()["data"]}
    assert new_gid in admin_ids

    # 4. Tournament staff management (organizer owner & super_admin)
    assert client.get("/api/v1/staff/candidates", headers=player_h).status_code == 403
    cands = client.get("/api/v1/staff/candidates", headers=org_h).get_json()["data"]
    assert any(c["id"] == player_id for c in cands)
    assert all("email" not in c and "phone" not in c for c in cands)

    add_staff = client.post(
        f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}/staff",
        headers=org_h,
        json={"user_id": player_id, "staff_role": "referee"},
    )
    assert add_staff.status_code == 201
    # Newly assigned committee (player promoted earlier) sees is_assigned_committee=True
    promoted_comm_h = _login_headers(client, "player@turnamen.in")
    val_detail = client.get(f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}", headers=promoted_comm_h).get_json()["data"]
    assert val_detail["is_assigned_committee"] is True

    # Removing committee revokes assignment cleanly
    rem_staff = client.delete(
        f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}/staff/{player_id}",
        headers=org_h,
    )
    assert rem_staff.status_code == 200
    val_after = client.get(f"/api/v1/tournaments/{VAL_TOURNAMENT_ID}", headers=promoted_comm_h).get_json()["data"]
    assert val_after["is_assigned_committee"] is False


def test_desktop_session_persistence_expiry_and_logout_across_window_reload() -> None:
    def make_jwt(exp_offset_seconds: int) -> str:
        header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
        payload_bytes = json.dumps({"sub": "sb-u-1", "exp": int(time.time()) + exp_offset_seconds}).encode()
        payload = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
        return f"{header}.{payload}.signature"

    valid_jwt = make_jwt(3600)
    expired_jwt = make_jwt(-60)

    res = _run_hotfix_harness(
        f"""
        const sharedStorage = createMemoryStorage();
        const validJwt = {json.dumps(valid_jwt)};
        const expiredJwt = {json.dumps(expired_jwt)};

        const sbUser = {{
          id: "sb-u-1",
          email: "organizer@turnamen.in",
          username: "garuda_eo",
          full_name: "Nadia SB",
          role: "organizer",
        }};

        // Boot 1: Login in Supabase mode -> session persists in sessionStorage without passwords
        let allowMe = true;
        const makeFetch = (mode = "supabase") => async (url, opts) => {{
          if (url.includes("/health")) {{
            return makeFetchResponse(200, {{
              success: true,
              data: {{ app_mode: mode, is_simulation: mode === "mock", api_base_url: "http://127.0.0.1:5000/api/v1" }},
            }});
          }}
          if (url.includes("/auth/login")) {{
            return makeFetchResponse(200, {{
              success: true,
              data: {{ token: validJwt, user: sbUser }},
            }});
          }}
          if (url.includes("/auth/me") && opts && opts.method === "PATCH") {{
            const body = JSON.parse(opts.body);
            return makeFetchResponse(200, {{
              success: true,
              data: {{ user: {{ ...sbUser, full_name: body.full_name }} }},
            }});
          }}
          if (url.includes("/auth/me")) {{
            if (!allowMe) {{
              return makeFetchResponse(401, {{ success: false, message: "Expired", error: {{ code: "UNAUTHORIZED", details: {{ status_code: 401 }} }} }});
            }}
            return makeFetchResponse(200, {{ success: true, data: {{ user: sbUser }} }});
          }}
          if (url.includes("/auth/logout")) {{
            return makeFetchResponse(200, {{ success: true, data: {{ logged_out: true }} }});
          }}
          return makeFetchResponse(200, {{ success: true, data: [] }});
        }};

        const env1 = createEnv({{ sessionStorage: sharedStorage, window: {{ fetch: makeFetch("supabase") }} }});
        await env1.window.TurnamenApp.initApp();
        await env1.window.TurnamenAPI.login("organizer@turnamen.in", "pw123456");
        const storedRaw = sharedStorage.getItem("turnamen.auth_session.v1");

        // Reload (env2) with same sessionStorage -> initApp verifies /auth/me & keeps session active
        const env2 = createEnv({{ sessionStorage: sharedStorage, window: {{ fetch: makeFetch("supabase") }} }});
        await env2.window.TurnamenApp.initApp();
        const afterValidReload = env2.window.TurnamenConfig.getState();

        // Reload (env3) when backend /auth/me returns 401 -> session cleared cleanly
        allowMe = false;
        const env3 = createEnv({{ sessionStorage: sharedStorage, window: {{ fetch: makeFetch("supabase") }} }});
        await env3.window.TurnamenApp.initApp();
        const afterUnauthorizedReload = env3.window.TurnamenConfig.getState();

        // Client-side JWT expiry check blocks expired JWT immediately without sending it
        sharedStorage.setItem("turnamen.auth_session.v1", JSON.stringify({{
          appMode: "supabase",
          token: expiredJwt,
          user: sbUser,
          explicitGuest: false,
        }}));
        const env4 = createEnv({{ sessionStorage: sharedStorage, window: {{ fetch: makeFetch("supabase") }} }});
        const afterExpiredBoot = env4.window.TurnamenConfig.getState();

        // Logout removes sessionStorage & keeps Guest across reload
        allowMe = true;
        await env4.window.TurnamenApp.initApp();
        await env4.window.TurnamenAPI.login("organizer@turnamen.in", "pw123456");
        await env4.window.TurnamenApp.handleLogout(null);
        const storedAfterLogout = sharedStorage.getItem("turnamen.auth_session.v1");

        return {{
          storedRaw,
          afterValidReload,
          afterUnauthorizedReload,
          afterExpiredBoot,
          storedAfterLogout,
        }};
        """
    )

    stored_obj = json.loads(res["storedRaw"])
    assert stored_obj["token"] == valid_jwt
    assert "password" not in res["storedRaw"]
    assert "refresh_token" not in res["storedRaw"]
    assert res["afterValidReload"]["token"] == valid_jwt
    assert res["afterValidReload"]["currentUser"]["role"] == "organizer"
    assert res["afterUnauthorizedReload"]["token"] is None
    assert res["afterUnauthorizedReload"]["currentUser"] is None
    assert res["afterExpiredBoot"]["token"] is None
    assert res["afterExpiredBoot"]["currentUser"] is None
    assert res["storedAfterLogout"] is None
