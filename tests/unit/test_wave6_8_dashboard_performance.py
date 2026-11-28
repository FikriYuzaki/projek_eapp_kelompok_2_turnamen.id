"""Wave 6.8 Dashboard performance, concurrency, and N+1 regression tests."""

from __future__ import annotations

import base64
from collections import Counter
import json
import shutil
import subprocess
import time
from typing import Any

import gevent
import pytest

from backend.app import create_app
from backend.core.config import ROOT_DIR, AppConfig
from backend.modules.auth.service import AuthService
from backend.modules.reports.service import ReportService
from backend.repositories.mock.mock_data import build_initial_mock_store
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
import desktop.bridge.eel_bridge as eel_bridge


def _make_jwt(payload: dict[str, Any]) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode("ascii").rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    return f"{header}.{body}.sig_wave68"


def test_eel_bridge_parallel_gevent_threadpool_prevents_serialization(monkeypatch) -> None:
    def _slow_forward(_cfg: AppConfig, _method: str, endpoint: str, _payload=None, _headers=None) -> dict[str, Any]:
        # Simulate blocking network I/O (`time.sleep` is unpatched OS sleep).
        time.sleep(0.25)
        return {"success": True, "message": "ok", "data": {"endpoint": endpoint}, "error": None}

    monkeypatch.setattr(eel_bridge, "forward_api_request", _slow_forward)
    eel_bridge._ACTIVE_CONFIG = AppConfig(app_mode="mock", secret_key="wave68-test")

    t0 = time.perf_counter()
    jobs = [
        gevent.spawn(eel_bridge.eel_api_request, "GET", f"/api/v1/tournaments/{idx}")
        for idx in range(4)
    ]
    gevent.joinall(jobs)
    elapsed = time.perf_counter() - t0

    results = [job.value for job in jobs]
    assert all(r["success"] is True for r in results)
    # 4 x 250ms serial would take >= 1.00s; threadpool offload runs concurrently in ~0.25-0.45s.
    assert elapsed < 0.65, f"Eel bridge blocked gevent loop: elapsed={elapsed:.3f}s"


def test_supabase_repo_eliminates_n_plus_1_and_reuses_token_clients() -> None:
    store = build_initial_mock_store()
    for p in store["profiles"]:
        p["auth_user_id"] = p["id"]
    # Expand dataset to 5 tournaments and 6 teams to verify O(1) query counts.
    base_t = dict(store["tournaments"][0])
    for idx in range(3):
        t_extra = dict(base_t)
        t_extra["id"] = f"33333333-3333-4333-8333-33333333331{idx}"
        t_extra["slug"] = f"extra-tour-{idx}"
        t_extra["title"] = f"Extra Tournament {idx}"
        store["tournaments"].append(t_extra)

    counts: Counter[str] = Counter()
    factory_tokens: list[str | None] = []
    limit_seen: list[int | None] = []

    class _FakeResp:
        def __init__(self, data: list[dict[str, Any]]) -> None:
            self.data = data

    class _FakeQuery:
        def __init__(self, table_name: str) -> None:
            self._table = table_name
            self._filters: list[tuple[str, Any]] = []
            self._limit: int | None = None

        def select(self, _cols: str = "*") -> _FakeQuery:
            return self

        def eq(self, key: str, value: Any) -> _FakeQuery:
            self._filters.append((key, value))
            return self

        def in_(self, key: str, values: list[Any]) -> _FakeQuery:
            self._filters.append((key, set(values)))
            return self

        def order(self, *_args: Any, **_kwargs: Any) -> _FakeQuery:
            return self

        def limit(self, value: int) -> _FakeQuery:
            self._limit = value
            return self

        def execute(self) -> _FakeResp:
            counts[f"table:{self._table}"] += 1
            counts["total_queries"] += 1
            if self._table == "activity_logs":
                limit_seen.append(self._limit)
            rows = list(store.get(self._table, []))
            for key, value in self._filters:
                if isinstance(value, set):
                    rows = [r for r in rows if r.get(key) in value]
                else:
                    rows = [r for r in rows if r.get(key) == value]
            if self._limit is not None:
                rows = rows[: self._limit]
            return _FakeResp(rows)

    class _FakeAuth:
        def get_user(self, jwt: str | None = None) -> Any:
            counts["auth.get_user"] += 1
            sub = "11111111-1111-4111-8111-111111111101"
            if jwt == token_user_b:
                sub = "11111111-1111-4111-8111-111111111102"
            user_obj = type("User", (), {"id": sub, "email": "u@example.com"})()
            return type("Resp", (), {"user": user_obj})()

        def sign_out(self) -> None:
            return None

    class _FakeClient:
        def __init__(self) -> None:
            self.auth = _FakeAuth()

        def table(self, name: str) -> _FakeQuery:
            return _FakeQuery(name)

        def rpc(self, fn_name: str, params: dict[str, Any] | None = None) -> Any:
            class _RpcExec:
                def execute(_self) -> _FakeResp:
                    counts[f"rpc:{fn_name}"] += 1
                    counts["total_queries"] += 1
                    tid = (params or {}).get("p_tournament_id")
                    return _FakeResp(
                        [a for a in store["announcements"] if a["tournament_id"] == tid]
                    )

            return _RpcExec()

    def _factory(_cfg: AppConfig, access_token: str | None = None) -> _FakeClient:
        factory_tokens.append(access_token)
        return _FakeClient()

    token_user_a = _make_jwt({"sub": "11111111-1111-4111-8111-111111111101", "exp": 4000000000})
    token_user_b = _make_jwt({"sub": "11111111-1111-4111-8111-111111111102", "exp": 4000000000})

    cfg = AppConfig(
        app_mode="supabase",
        secret_key="wave68-secret",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_wave68",
    )
    repo = SupabaseDataStoreRepository(cfg, client_factory=_factory)
    auth = AuthService(repo)
    reports = ReportService(repo)

    # Initial __init__ creates 1 anon client; subsequent calls for token_user_a reuse 1 client.
    assert len(factory_tokens) == 1
    actor = auth.get_user_by_token(token_user_a)
    assert actor is not None and actor["role"] == "super_admin"

    # 5 tournaments -> must be <= 3 DB queries (tournaments, games, registrations batch), zero teams scan
    counts.clear()
    with repo.with_access_token(token_user_a):
        tours = repo.list_tournaments()
    assert len(tours) == 5
    assert counts["total_queries"] == 3
    assert counts["table:teams"] == 0

    # All teams -> must be <= 3 DB queries (teams, games, team_members batch), zero N+1
    counts.clear()
    with repo.with_access_token(token_user_a):
        teams = repo.list_teams()
    assert len(teams) >= 4
    assert counts["total_queries"] == 3
    assert counts["table:team_members"] == 1

    # Report -> no duplicate tournament/registrations/matches scans and zero list_teams() N+1
    counts.clear()
    with repo.with_access_token(token_user_a):
        report = reports.get_tournament_report("33333333-3333-4333-8333-333333333301", actor=actor)
    assert "summary" in report and "standings" in report
    assert counts["table:tournaments"] == 1
    assert counts["table:team_members"] == 0
    assert limit_seen == [10]

    # Repeated auth_get_user via AuthService hits 5s identity cache (0 extra remote auth calls)
    auth_calls_before = counts["auth.get_user"]
    for _ in range(4):
        again = auth.get_user_by_token(token_user_a)
        assert again is not None and again["role"] == "super_admin"
    assert counts["auth.get_user"] == auth_calls_before

    # Client reuse for token_user_a and isolation for token_user_b + eviction on logout
    assert token_user_a in factory_tokens
    clients_count_before_b = len(factory_tokens)
    actor_b = auth.get_user_by_token(token_user_b)
    assert actor_b is not None and actor_b["role"] == "organizer"
    assert len(factory_tokens) > clients_count_before_b
    auth.logout(token_user_a)
    assert auth._get_cached_verified_identity(token_user_a) is None


def test_mock_mode_super_admin_dashboard_endpoints_under_3_seconds() -> None:
    app = create_app(
        config=AppConfig(app_mode="mock", secret_key="wave68-mock-secret"),
        repository=MockDataStoreRepository(),
    )
    headers = {"X-Mock-Role": "super_admin"}
    t0 = time.perf_counter()
    with app.test_client() as client:
        for ep in (
            "/api/v1/games?include_inactive=1",
            "/api/v1/tournaments",
            "/api/v1/teams",
            "/api/v1/users",
            "/api/v1/tournaments/33333333-3333-4333-8333-333333333301/reports",
        ):
            resp = client.get(ep, headers=headers)
            assert resp.status_code == 200
            assert resp.get_json()["success"] is True
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0


def test_frontend_super_admin_dashboard_parallel_waves_and_partial_failure_resilience() -> None:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime is not available")

    js_dir = ROOT_DIR / "desktop" / "web" / "assets" / "js"
    for rel in ("core/eel-bridge.js", "pages/app-pages.js"):
        syntax = subprocess.run(
            [node_bin, "--check", str(js_dir / rel)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert syntax.returncode == 0, f"Syntax error in {rel}: {syntax.stderr}"

    harness = f"""
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const jsDir = {json.dumps(str(js_dir))};
const configCode = fs.readFileSync(path.join(jsDir, "core", "config.js"), "utf8");
const bridgeCode = fs.readFileSync(path.join(jsDir, "core", "eel-bridge.js"), "utf8");
const apiCode = fs.readFileSync(path.join(jsDir, "core", "api-client.js"), "utf8");
const uiCode = fs.readFileSync(path.join(jsDir, "components", "ui-components.js"), "utf8");
const appCode = fs.readFileSync(path.join(jsDir, "pages", "app-pages.js"), "utf8");

const apiCalls = [];
const elements = new Map();
function makeEl(id) {{
  if (elements.has(id)) return elements.get(id);
  const el = {{
    id,
    value: "",
    innerHTML: "",
    textContent: "",
    hidden: false,
    disabled: false,
    classList: {{ add() {{}}, remove() {{}}, toggle() {{}}, contains: () => false }},
    appendChild() {{}},
    remove() {{}},
    setAttribute() {{}},
    getAttribute() {{ return ""; }},
    addEventListener() {{}},
    focus() {{}},
    closest() {{ return null; }},
    querySelector: () => null,
    querySelectorAll: () => [],
  }};
  elements.set(id, el);
  return el;
}}

const sandbox = {{
  window: null,
  document: {{
    getElementById: (id) => makeEl(id),
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: (tag) => makeEl(`dyn_${{tag}}_${{elements.size}}`),
    addEventListener() {{}},
  }},
  localStorage: {{ getItem: () => null, setItem() {{}}, removeItem() {{}} }},
  sessionStorage: {{ getItem: () => null, setItem() {{}}, removeItem() {{}} }},
  location: {{ protocol: "http:", hostname: "127.0.0.1", port: "8080", origin: "http://127.0.0.1:8080", pathname: "/index.html", search: "", hash: "" }},
  history: {{ replaceState() {{}} }},
  URL,
  URLSearchParams,
  fetch: async (url) => {{
    apiCalls.push(url);
    const jsonResp = (data, ok = true, status = 200) => ({{
      status,
      ok,
      headers: {{ get: () => "application/json" }},
      text: async () => JSON.stringify({{ success: ok, message: ok ? "OK" : "Report timeout simulation", data: ok ? data : null, error: ok ? null : {{ code: "BRIDGE_TIMEOUT", details: {{}} }} }}),
    }});
    if (url.endsWith("/games?include_inactive=true")) {{
      return jsonResp([{{ id: "g1", slug: "mlbb", name: "MLBB", is_active: true }}]);
    }}
    if (url.endsWith("/tournaments")) {{
      return jsonResp([{{ id: "t1", title: "Turnamen Uji", game_id: "g1", game_name: "MLBB", status: "ongoing", max_teams: 8, approved_teams_count: 4, venue: "Online" }}]);
    }}
    if (url.endsWith("/teams")) {{
      return jsonResp([{{ id: "tm1", name: "Alpha", tag: "ALP", game_id: "g1", member_count: 5 }}]);
    }}
    if (url.endsWith("/users")) {{
      return jsonResp([{{ id: "u1", email: "admin@turnamen.in", username: "superadmin", full_name: "Super Admin", role: "super_admin", is_auth_linked: true }}]);
    }}
    if (url.includes("/reports")) {{
      // Simulate single-section report failure without crashing entire dashboard
      return jsonResp(null, false, 504);
    }}
    return jsonResp({{}});
  }},
  console,
  setTimeout,
  clearTimeout,
}};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(configCode, sandbox);
vm.runInContext(bridgeCode, sandbox);
vm.runInContext(apiCode, sandbox);
vm.runInContext(uiCode, sandbox);
vm.runInContext(appCode, sandbox);

(async () => {{
  sandbox.TurnamenConfig.setRuntimeInfo({{ app_mode: "supabase", is_simulation: false, supabase_host: "cfdsgxciodfkamskafwe.supabase.co" }});
  sandbox.TurnamenConfig.setAuthSession("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1MSIsImV4cCI6NDAwMDAwMDAwMH0.sig", {{
    id: "u1",
    email: "admin@turnamen.in",
    username: "superadmin",
    full_name: "Super Admin",
    role: "super_admin",
    is_active: true,
  }});

  await sandbox.TurnamenApp.navigateTo("dashboard");
  const html = makeEl("main-content").innerHTML;
  console.log(JSON.stringify({{
    apiCalls,
    hasDashboardHeading: html.includes("Administrasi Sistem Turnamen.in"),
    hasTournamentsTable: html.includes("Turnamen Uji"),
    hasUsersSection: html.includes("superadmin"),
    hasPerCardReportFallback: html.includes("Report timeout simulation"),
  }}));
}})().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    proc = subprocess.run([node_bin, "-e", harness], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    res = json.loads(proc.stdout.strip().splitlines()[-1])
    endpoints = [u.split("/api/v1")[1] for u in res["apiCalls"]]
    assert len(endpoints) == 5
    assert set(endpoints[:4]) == {
        "/games?include_inactive=true",
        "/tournaments",
        "/teams",
        "/users",
    }
    assert endpoints[4] == "/tournaments/t1/reports"
    assert res["hasDashboardHeading"] is True
    assert res["hasTournamentsTable"] is True
    assert res["hasUsersSection"] is True
    assert res["hasPerCardReportFallback"] is True
