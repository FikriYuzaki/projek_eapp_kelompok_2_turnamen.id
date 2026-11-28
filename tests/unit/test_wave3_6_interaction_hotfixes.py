"""Wave 3.6 Live Desktop Interaction Hotfix Regression Tests.

Covers:
1. BUG-006: Topbar auth button ('Masuk') must not be overwritten back to 'Keluar' after logout across all roles & modes.
2. BUG-019: Active modal closes cleanly on navigateTo() and stale async modal fetches are canceled safely.
3. BUG-022: Role switcher preserves authorized pages (bracket, tournament-detail) and redirects unauthorized pages cleanly.
4. BUG-024: selectedTournamentId persists across reload via sessionStorage, clears on logout, and validates on deleted/unauthorized fallback.
5. Eel Bridge: ALLOWED_BASE_HEADERS forwards Idempotency-Key header without duplicate results or activity log entries.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

import pytest

from backend.app import create_app
from backend.core.config import ROOT_DIR, load_config
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from desktop.bridge import eel_bridge

JS_DIR = ROOT_DIR / "desktop" / "web" / "assets" / "js"


def _run_hotfix_harness(script_body: str) -> dict[str, Any]:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime is not available")

    harness = f"""
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const jsDir = {json.dumps(str(JS_DIR))};
const configCode = fs.readFileSync(path.join(jsDir, "core", "config.js"), "utf8");
const bridgeCode = fs.readFileSync(path.join(jsDir, "core", "eel-bridge.js"), "utf8");
const apiCode = fs.readFileSync(path.join(jsDir, "core", "api-client.js"), "utf8");
const uiCode = fs.readFileSync(path.join(jsDir, "components", "ui-components.js"), "utf8");
const appCode = fs.readFileSync(path.join(jsDir, "pages", "app-pages.js"), "utf8");

function makeFetchResponse(status, payload) {{
  return {{
    status,
    ok: status >= 200 && status < 300,
    headers: {{ get: () => "application/json" }},
    text: async () => JSON.stringify(payload),
    json: async () => payload,
  }};
}}

function makeClassList(initial = []) {{
  const set = new Set(initial);
  return {{
    add: (...cls) => cls.forEach((c) => set.add(c)),
    remove: (...cls) => cls.forEach((c) => set.delete(c)),
    toggle: (c, force) => {{
      if (force === undefined) {{
        if (set.has(c)) {{ set.delete(c); return false; }}
        set.add(c); return true;
      }}
      if (force) {{ set.add(c); return true; }}
      set.delete(c); return false;
    }},
    contains: (c) => set.has(c),
    toString: () => Array.from(set).join(" "),
  }};
}}

function makeElement(id = "", tagName = "DIV") {{
  const attrs = {{}};
  const listeners = {{}};
  let _innerHTML = "";
  let _textContent = "";
  const el = {{
    id,
    tagName,
    nodeType: 1,
    isConnected: true,
    value: "",
    disabled: false,
    hidden: false,
    checked: false,
    title: "",
    style: {{}},
    dataset: {{}},
    classList: makeClassList(),
    children: [],
    set innerHTML(val) {{ _innerHTML = String(val || ""); _textContent = _innerHTML; }},
    get innerHTML() {{ return _innerHTML; }},
    set textContent(val) {{ _textContent = String(val || ""); _innerHTML = _textContent; }},
    get textContent() {{ return _textContent; }},
    setAttribute: (k, v) => {{
      attrs[k] = String(v);
      if (k === "disabled") el.disabled = true;
    }},
    getAttribute: (k) => (k in attrs ? attrs[k] : null),
    removeAttribute: (k) => {{
      delete attrs[k];
      if (k === "disabled") el.disabled = false;
    }},
    hasAttribute: (k) => k in attrs,
    addEventListener: (ev, fn) => {{
      listeners[ev] = listeners[ev] || [];
      listeners[ev].push(fn);
    }},
    removeEventListener: (ev, fn) => {{
      if (!listeners[ev]) return;
      listeners[ev] = listeners[ev].filter((f) => f !== fn);
    }},
    dispatchEvent: (ev) => {{
      (listeners[ev.type] || []).forEach((fn) => fn(ev));
    }},
    appendChild: (child) => {{ el.children.push(child); return child; }},
    remove: () => {{}},
    focus: () => {{}},
    click: () => {{
      (listeners.click || []).forEach((fn) => fn({{ target: el, preventDefault: () => {{}} }}));
    }},
    closest: () => null,
    contains: () => false,
    querySelector: () => null,
    querySelectorAll: () => [],
  }};
  return el;
}}

function createMemoryStorage() {{
  const map = new Map();
  return {{
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(String(k), String(v)),
    removeItem: (k) => map.delete(String(k)),
    _dump: () => Object.fromEntries(map.entries()),
  }};
}}

function createEnv(custom = {{}}) {{
  const elements = {{}};
  const shellIds = [
    "topbar-auth-action",
    "topbar-active-user",
    "topbar-role-switcher",
    "topbar-role-switcher-wrap",
    "topbar-page-title",
    "sidebar-nav",
    "sidebar-brand-role",
    "main-content",
    "app-modal-backdrop",
    "app-modal-title",
    "app-modal-body",
    "app-modal-footer",
    "app-modal-close-btn",
    "toast-container",
    "runtime-badge",
    "runtime-label",
  ];
  shellIds.forEach((id) => {{
    elements[id] = makeElement(id);
  }});
  elements["app-modal-backdrop"].classList.add("hidden");

  const docListeners = {{}};
  const body = Object.assign(makeElement("body", "BODY"), {{
    classList: makeClassList(),
    style: {{}},
  }});
  const document = {{
    title: "",
    body,
    getElementById: (id) => {{
      if (!elements[id]) elements[id] = makeElement(id);
      return elements[id];
    }},
    createElement: (tag) => makeElement("", String(tag).toUpperCase()),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: (ev, fn) => {{
      docListeners[ev] = docListeners[ev] || [];
      docListeners[ev].push(fn);
    }},
    removeEventListener: (ev, fn) => {{
      if (!docListeners[ev]) return;
      docListeners[ev] = docListeners[ev].filter((f) => f !== fn);
    }},
    activeElement: null,
  }};

  const sessionStorage = custom.sessionStorage || createMemoryStorage();
  const sandboxWindow = {{
    location: {{ protocol: "http:", hostname: "127.0.0.1", port: "8080" }},
    console: {{ warn: () => {{}}, error: () => {{}}, log: () => {{}} }},
    URL,
    URLSearchParams,
    AbortController,
    encodeURIComponent,
    crypto: require("crypto").webcrypto,
    document,
    sessionStorage,
    setTimeout,
    clearTimeout,
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    addEventListener: () => {{}},
    removeEventListener: () => {{}},
    ...(custom.window || {{}}),
  }};
  sandboxWindow.window = sandboxWindow;
  sandboxWindow.document = document;

  const ctx = vm.createContext(sandboxWindow);
  vm.runInContext(configCode, ctx);
  vm.runInContext(bridgeCode, ctx);
  vm.runInContext(apiCode, ctx);
  vm.runInContext(uiCode, ctx);
  vm.runInContext(appCode, ctx);

  return {{
    window: sandboxWindow,
    document,
    elements,
    sessionStorage,
    makeFetchResponse,
  }};
}}

(async () => {{
  {script_body}
}})()
  .then((res) => process.stdout.write(JSON.stringify(res)))
  .catch((err) => {{
    console.error(err);
    process.exit(1);
  }});
"""
    proc = subprocess.run(
        [node_bin, "-e", harness],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return json.loads(proc.stdout)


def test_bug006_handle_logout_updates_auth_button_to_masuk_across_roles_and_modes() -> None:
    res = _run_hotfix_harness(
        """
        const env = createEnv({
          window: {
            fetch: async (url) => {
              if (url.includes("/auth/logout")) {
                return makeFetchResponse(200, { success: true, data: { logged_out: true } });
              }
              return makeFetchResponse(200, { success: true, data: [] });
            },
          },
        });
        const { window, elements } = env;
        const authBtn = elements["topbar-auth-action"];

        const results = {};
        for (const role of ["player", "team_captain", "organizer", "super_admin"]) {
          window.TurnamenConfig.setSimulatedRole(role);
          window.TurnamenApp.updateUserTopbar(window.TurnamenConfig.getState().currentUser);
          const beforeText = authBtn.textContent;

          await window.TurnamenApp.handleLogout(authBtn);
          const afterUser = window.TurnamenConfig.getState().currentUser;

          await window.TurnamenApp.navigateTo("match-management");
          const privateBlocked = elements["main-content"].innerHTML.includes("Ditolak");

          results[role] = {
            beforeText,
            afterText: authBtn.textContent,
            afterDisabled: authBtn.disabled,
            ariaBusy: authBtn.getAttribute("aria-busy"),
            userIsNull: afterUser === null,
            privateBlocked,
          };
        }

        // Also test Supabase Mode authenticated logout
        window.TurnamenConfig.setRuntimeInfo({ app_mode: "supabase" });
        window.TurnamenConfig.setAuthSession("sb-token-1", {
          id: "u-sb-1",
          role: "organizer",
          full_name: "Nadia SB",
        });
        window.TurnamenApp.updateUserTopbar(window.TurnamenConfig.getState().currentUser);
        const sbBefore = authBtn.textContent;
        await window.TurnamenApp.handleLogout(authBtn);
        const sbAfter = {
          text: authBtn.textContent,
          disabled: authBtn.disabled,
          userIsNull: window.TurnamenConfig.getState().currentUser === null,
          tokenIsNull: window.TurnamenConfig.getState().token === null,
        };

        return { results, sbBefore, sbAfter };
        """
    )

    for role in ("player", "team_captain", "organizer", "super_admin"):
        row = res["results"][role]
        assert row["beforeText"] == "Keluar"
        assert row["afterText"] == "Masuk", role
        assert row["afterDisabled"] is False
        assert row["ariaBusy"] is None
        assert row["userIsNull"] is True
        assert row["privateBlocked"] is True

    assert res["sbBefore"] == "Keluar"
    assert res["sbAfter"]["text"] == "Masuk"
    assert res["sbAfter"]["disabled"] is False
    assert res["sbAfter"]["userIsNull"] is True
    assert res["sbAfter"]["tokenIsNull"] is True


def test_bug019_modals_close_on_navigation_and_stale_async_modals_do_not_appear() -> None:
    res = _run_hotfix_harness(
        """
        let holdTeamFetch = null;
        const env = createEnv({
          window: {
            fetch: (url) => {
              if (url.includes("/teams/tm-delayed")) {
                return new Promise((resolve) => {
                  holdTeamFetch = () => resolve(makeFetchResponse(200, {
                    success: true,
                    data: { id: "tm-delayed", name: "Slow Team", tag: "SLW", captain_id: "11111111-1111-4111-8111-111111111104" },
                  }));
                });
              }
              if (url.includes("/teams/tm-1")) {
                return Promise.resolve(makeFetchResponse(200, {
                  success: true,
                  data: { id: "tm-1", name: "Garuda", tag: "GRD", captain_id: "11111111-1111-4111-8111-111111111104" },
                }));
              }
              if (url.includes("/tournaments/t-1")) {
                return Promise.resolve(makeFetchResponse(200, {
                  success: true,
                  data: {
                    id: "t-1",
                    title: "Arena Cup",
                    status: "open_registration",
                    organizer_id: "11111111-1111-4111-8111-111111111102",
                    is_assigned_committee: true,
                    max_teams: 8,
                    best_of: 3,
                  },
                }));
              }
              if (url.includes("/reports")) {
                return Promise.resolve(makeFetchResponse(200, {
                  success: true,
                  data: {
                    tournament: { id: "t-1", title: "Arena Cup" },
                    summary: { completion_percentage: 0, approved_teams: 0, max_teams: 8, pending_registrations: 0, total_registrations: 0 },
                    standings: [],
                    recent_activity: [],
                  },
                }));
              }
              if (url.includes("/tournaments")) {
                return Promise.resolve(makeFetchResponse(200, {
                  success: true,
                  data: [{
                    id: "t-1",
                    title: "Arena Cup",
                    status: "open_registration",
                    organizer_id: "11111111-1111-4111-8111-111111111102",
                    is_assigned_committee: true,
                    max_teams: 8,
                    best_of: 3,
                  }],
                }));
              }
              return Promise.resolve(makeFetchResponse(200, { success: true, data: [] }));
            },
          },
        });

        const { window, document, elements } = env;
        const backdrop = elements["app-modal-backdrop"];
        const closedStates = {};

        window.TurnamenConfig.setSimulatedRole("super_admin");
        for (const [label, openFn] of [
          ["addMember", () => window.TurnamenApp.openAddMemberModal("tm-1")],
          ["editTeam", () => window.TurnamenApp.openEditTeamModal("tm-1")],
          ["editTournament", () => window.TurnamenApp.openEditTournamentModal("t-1")],
          ["announcement", () => window.TurnamenApp.openAnnouncementModal("t-1")],
        ]) {
          await openFn();
          const openBeforeNav = !backdrop.classList.contains("hidden");
          await window.TurnamenApp.navigateTo("reports");
          closedStates[label] = {
            openBeforeNav,
            hiddenAfterNav: backdrop.classList.contains("hidden"),
            bodyHasModalOpen: document.body.classList.contains("modal-open"),
            bodyOverflow: document.body.style.overflow,
          };
        }

        // Fast navigation while async openAddMemberModal fetch is in flight -> stale modal must NOT appear!
        const delayedPromise = window.TurnamenApp.openAddMemberModal("tm-delayed");
        await window.TurnamenApp.navigateTo("reports");
        if (holdTeamFetch) holdTeamFetch();
        await delayedPromise;
        const staleAsyncModalHidden = backdrop.classList.contains("hidden");

        return { closedStates, staleAsyncModalHidden };
        """
    )

    for label in ("addMember", "editTeam", "editTournament", "announcement"):
        st = res["closedStates"][label]
        assert st["openBeforeNav"] is True, label
        assert st["hiddenAfterNav"] is True, label
        assert st["bodyHasModalOpen"] is False, label
        assert st["bodyOverflow"] == "", label
    assert res["staleAsyncModalHidden"] is True


def test_role_switcher_preserves_authorized_pages_and_redirects_unauthorized() -> None:
    res = _run_hotfix_harness(
        """
        const env = createEnv({
          window: {
            fetch: async (url) => {
              const singleT = {
                id: "t-1",
                title: "Cup",
                status: "open_registration",
                organizer_id: "11111111-1111-4111-8111-111111111102",
                is_assigned_committee: true,
                max_teams: 8,
                best_of: 3,
              };
              if (url.includes("/tournaments/") && url.includes("/matches")) {
                return makeFetchResponse(200, {
                  success: true,
                  data: { tournament_id: "t-1", tournament_title: "Cup", best_of: 3, matches: [], rounds: [] },
                });
              }
              if (url.includes("/tournaments/") && url.includes("/registrations")) {
                return makeFetchResponse(200, { success: true, data: [] });
              }
              if (url.includes("/tournaments/t-1")) {
                return makeFetchResponse(200, { success: true, data: singleT });
              }
              if (url.includes("/tournaments")) {
                return makeFetchResponse(200, { success: true, data: [singleT] });
              }
              return makeFetchResponse(200, { success: true, data: [] });
            },
          },
        });
        const { window, elements } = env;
        window.TurnamenApp.initApp();
        const switcher = elements["topbar-role-switcher"];
        const switchRole = async (role) => {
          switcher.value = role;
          switcher.dispatchEvent({ type: "change", target: switcher });
          await new Promise((r) => setTimeout(r, 60));
        };

        // 1. Organizer -> Committee on Bracket => MUST stay on Bracket
        await switchRole("organizer");
        await window.TurnamenApp.navigateTo("bracket");
        await switchRole("committee");
        const orgToComBracket = {
          title: elements["topbar-page-title"].textContent,
          role: window.TurnamenConfig.getState().currentUser.role,
        };

        // 2. Committee -> Player from Match Management => MUST redirect away from private Match Management
        await window.TurnamenApp.navigateTo("match-management");
        await switchRole("player");
        const comToPlayerMatch = {
          title: elements["topbar-page-title"].textContent,
          role: window.TurnamenConfig.getState().currentUser.role,
        };

        // 3. Team Captain -> Organizer on Tournament Detail => MUST stay on Tournament Detail with Organizer controls
        await switchRole("team_captain");
        await window.TurnamenApp.navigateTo("tournament-detail");
        await switchRole("organizer");
        const capToOrgDetail = {
          title: elements["topbar-page-title"].textContent,
          hasEditTourBtn: elements["main-content"].innerHTML.includes("open-edit-tournament"),
        };

        // 4. Super Admin -> Guest from Match Management => MUST redirect to Arena Publik (dashboard)
        await switchRole("super_admin");
        await window.TurnamenApp.navigateTo("match-management");
        await switchRole("guest");
        const adminToGuestPrivate = {
          title: elements["topbar-page-title"].textContent,
          currentUser: window.TurnamenConfig.getState().currentUser,
        };

        return { orgToComBracket, comToPlayerMatch, capToOrgDetail, adminToGuestPrivate };
        """
    )

    assert res["orgToComBracket"]["title"] == "Bracket Turnamen"
    assert res["orgToComBracket"]["role"] == "committee"

    assert res["comToPlayerMatch"]["role"] == "player"
    assert res["comToPlayerMatch"]["title"] == "Arena Utama Player"

    assert res["capToOrgDetail"]["title"] == "Detail & Peserta Turnamen"
    assert res["capToOrgDetail"]["hasEditTourBtn"] is True

    assert res["adminToGuestPrivate"]["currentUser"] is None
    assert res["adminToGuestPrivate"]["title"] == "Arena Publik Turnamen.in"


def test_bug024_selected_tournament_persists_validates_and_clears_on_logout() -> None:
    res = _run_hotfix_harness(
        """
        const sharedStorage = createMemoryStorage();
        const env1 = createEnv({ sessionStorage: sharedStorage });
        env1.window.TurnamenConfig.setSelectedTournamentId("33333333-3333-4333-8333-333333333302");
        const storedAfterSet = sharedStorage._dump();

        // Reload 1: Tournament ...02 still exists -> stays ...02
        let availableTours = [
          { id: "33333333-3333-4333-8333-333333333301", title: "T1", status: "ongoing", organizer_id: "org-1" },
          { id: "33333333-3333-4333-8333-333333333302", title: "T2", status: "open_registration", organizer_id: "org-1" },
        ];
        const env2 = createEnv({
          sessionStorage: sharedStorage,
          window: {
            fetch: async (url) => {
              if (url.includes("/tournaments")) {
                return makeFetchResponse(200, { success: true, data: availableTours });
              }
              return makeFetchResponse(200, { success: true, data: [] });
            },
          },
        });
        const onBootBeforeFetch = env2.window.TurnamenConfig.getState().selectedTournamentId;
        await env2.window.TurnamenApp.navigateTo("reports");
        const afterValidResolve = env2.window.TurnamenConfig.getState().selectedTournamentId;

        // Reload 2: Selected tournament ...02 deleted -> must fall back cleanly to ...01
        availableTours = [{ id: "33333333-3333-4333-8333-333333333301", title: "T1", status: "ongoing", organizer_id: "org-1" }];
        const env3 = createEnv({
          sessionStorage: sharedStorage,
          window: {
            fetch: async (url) => {
              if (url.includes("/tournaments")) {
                return makeFetchResponse(200, { success: true, data: availableTours });
              }
              return makeFetchResponse(200, { success: true, data: [] });
            },
          },
        });
        await env3.window.TurnamenApp.navigateTo("reports");
        const afterDeletedFallback = env3.window.TurnamenConfig.getState().selectedTournamentId;

        // Role switch check: Organizer selects a draft tournament -> Player must fall back to public tournament
        availableTours = [
          { id: "33333333-3333-4333-8333-333333333301", title: "T1", status: "ongoing" },
          { id: "t-draft-priv", title: "Private Draft", status: "draft" },
        ];
        env3.window.TurnamenConfig.setSimulatedRole("organizer");
        env3.window.TurnamenConfig.setSelectedTournamentId("t-draft-priv");
        env3.window.TurnamenConfig.setSimulatedRole("player");
        await env3.window.TurnamenApp.navigateTo("reports");
        const playerAfterDraftInvalid = env3.window.TurnamenConfig.getState().selectedTournamentId;

        // Logout clears stored selectedTournamentId
        env3.window.TurnamenConfig.setSelectedTournamentId("33333333-3333-4333-8333-333333333301");
        env3.window.TurnamenConfig.enterGuestMode();
        const storageAfterLogout = sharedStorage._dump();

        // Storage unavailability graceful fallback (throwing sessionStorage)
        const brokenStorage = {
          getItem: () => { throw new Error("Blocked"); },
          setItem: () => { throw new Error("Blocked"); },
          removeItem: () => { throw new Error("Blocked"); },
        };
        const env4 = createEnv({ sessionStorage: brokenStorage });
        env4.window.TurnamenConfig.setSelectedTournamentId("33333333-3333-4333-8333-333333333302");
        const brokenStorageInMemory = env4.window.TurnamenConfig.getState().selectedTournamentId;

        return {
          storedAfterSet,
          onBootBeforeFetch,
          afterValidResolve,
          afterDeletedFallback,
          playerAfterDraftInvalid,
          storageAfterLogout,
          brokenStorageInMemory,
        };
        """
    )

    assert res["storedAfterSet"] == {
        "turnamen.selected_tournament_id.v1": "33333333-3333-4333-8333-333333333302"
    }
    assert res["onBootBeforeFetch"] == "33333333-3333-4333-8333-333333333302"
    assert res["afterValidResolve"] == "33333333-3333-4333-8333-333333333302"
    assert res["afterDeletedFallback"] == "33333333-3333-4333-8333-333333333301"
    assert res["playerAfterDraftInvalid"] == "33333333-3333-4333-8333-333333333301"
    assert res["storageAfterLogout"] == {}
    assert res["brokenStorageInMemory"] == "33333333-3333-4333-8333-333333333302"


def test_eel_bridge_forwards_idempotency_key_header_without_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(overrides={"app_mode": "mock"})
    app = create_app(cfg, repository=MockDataStoreRepository())
    client = app.test_client()

    # Login as committee to obtain token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "committee@turnamen.in", "password": "turnamen123"},
    )
    assert login_res.status_code == 200
    token = login_res.get_json()["data"]["token"]

    forwarded_headers: list[dict[str, str]] = []

    class _FlaskSessionAdapter:
        def request(
            self,
            *,
            method: str,
            url: str,
            headers: dict[str, str],
            json: Any = None,
            timeout: float = 8.0,
            allow_redirects: bool = False,
        ) -> Any:
            forwarded_headers.append(dict(headers))
            path = url.split(":5000", 1)[1]
            resp = client.open(
                path,
                method=method,
                headers=headers,
                json=json,
            )

            class _Resp:
                status_code = resp.status_code

                @staticmethod
                def json() -> Any:
                    return resp.get_json()

            return _Resp()

    monkeypatch.setattr(eel_bridge, "_get_local_http_session", lambda: _FlaskSessionAdapter())

    match_id = "88888888-8888-4888-8888-888888888804"
    idem_key = "wave36-eel-header-001"

    first = eel_bridge.forward_api_request(
        cfg,
        "PATCH",
        f"/matches/{match_id}/result",
        payload={"score_a": 2, "score_b": 1, "notes": "Eel verify"},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key, "X-Evil": "drop-me"},
    )
    assert first["success"] is True

    # Retry with same Idempotency-Key -> MUST replay cleanly without duplicate audit logs
    retry = eel_bridge.forward_api_request(
        cfg,
        "PATCH",
        f"/matches/{match_id}/result",
        payload={"score_a": 2, "score_b": 1, "notes": "Eel verify"},
        headers={"Authorization": f"Bearer {token}", "idempotency-key": idem_key},
    )
    assert retry["success"] is True

    assert forwarded_headers[0]["Idempotency-Key"] == idem_key
    assert "X-Evil" not in forwarded_headers[0]
    assert forwarded_headers[1]["Idempotency-Key"] == idem_key

    rep = client.get(
        "/api/v1/tournaments/33333333-3333-4333-8333-333333333301/reports",
        headers={"Authorization": f"Bearer {token}"},
    ).get_json()["data"]
    match_logs = [log for log in rep["recent_activity"] if log.get("entity_id") == match_id]
    assert len(match_logs) == 1
