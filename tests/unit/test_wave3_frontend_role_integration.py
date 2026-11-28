"""Wave 3 Frontend, UI/UX & Role Integration Regression Tests.

Covers BUG-006, BUG-007, BUG-009 (double-submit + Idempotency-Key), BUG-013,
BUG-016 to BUG-024, and end-to-end verification across all 6 roles:
Guest, Player, Team Captain, Organizer, Committee, and Super Admin.
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

JS_DIR = ROOT_DIR / "desktop" / "web" / "assets" / "js"


def _run_full_frontend_harness(script_body: str) -> dict[str, Any]:
    """Execute real frontend JS modules (`config`, `eel-bridge`, `api-client`,
    `ui-components`, `app-pages`) inside Node VM with a lightweight DOM shim.
    """
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
  const el = {{
    id,
    tagName,
    nodeType: 1,
    value: "",
    disabled: false,
    hidden: false,
    checked: false,
    textContent: "",
    title: "",
    style: {{}},
    dataset: {{}},
    classList: makeClassList(),
    children: [],
    set innerHTML(val) {{ _innerHTML = String(val || ""); }},
    get innerHTML() {{ return _innerHTML; }},
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

function createFrontendEnv(custom = {{}}) {{
  const elements = {{}};
  const shellIds = [
    "topbar-auth-action",
    "topbar-active-user",
    "topbar-role-switcher",
    "topbar-role-switcher-wrap",
    "topbar-user-name",
    "topbar-user-role",
    "topbar-user-avatar",
    "sidebar-nav",
    "sidebar-brand-role",
    "main-content",
    "page-title",
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
  const document = {{
    title: "",
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

  const sandboxWindow = {{
    location: {{ protocol: "http:", hostname: "127.0.0.1", port: "8080" }},
    console: {{ warn: () => {{}}, error: () => {{}}, log: () => {{}} }},
    URL,
    URLSearchParams,
    AbortController,
    encodeURIComponent,
    crypto: require("crypto").webcrypto,
    document,
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
    makeElement,
    makeFetchResponse,
    emitDomReady: () => (docListeners.DOMContentLoaded || []).forEach((fn) => fn()),
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


def _login(client: Any, email: str, password: str = "turnamen123") -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]["token"]


def _json_headers(token: str | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


def test_bug006_logout_enters_guest_cleanly_in_mock_and_supabase_modes() -> None:
    res = _run_full_frontend_harness(
        """
        const fetchCalls = [];
        const env = createFrontendEnv({
          window: {
            fetch: async (url, init) => {
              fetchCalls.push({ url, method: init.method });
              if (url.includes("/auth/logout")) {
                return makeFetchResponse(200, { success: true, data: { logged_out: true } });
              }
              return makeFetchResponse(200, { success: true, data: [] });
            },
          },
        });

        const { window, elements } = env;
        window.TurnamenConfig.setSimulatedRole("organizer");
        const beforeLogoutUser = window.TurnamenConfig.getState().currentUser.role;

        // Logout in Mock Mode must enter Guest (currentUser === null)
        await window.TurnamenAPI.logout();
        window.TurnamenApp.updateUserTopbar(window.TurnamenConfig.getState().currentUser);
        const afterMockLogout = {
          currentUser: window.TurnamenConfig.getState().currentUser,
          explicitGuest: window.TurnamenConfig.getState().explicitGuest,
          authBtnHtml: elements["topbar-auth-action"].textContent,
          authBtnHidden: elements["topbar-auth-action"].hidden,
          switcherVal: elements["topbar-role-switcher"].value,
        };

        // Test role switcher from Guest -> Committee -> Guest
        window.TurnamenConfig.setSimulatedRole("committee");
        window.TurnamenApp.updateUserTopbar(window.TurnamenConfig.getState().currentUser);
        const committeeState = {
          role: window.TurnamenConfig.getState().currentUser.role,
          authBtnHtml: elements["topbar-auth-action"].textContent,
        };
        window.TurnamenConfig.setSimulatedRole("guest");
        const guestViaSwitcher = window.TurnamenConfig.getState().currentUser;

        // Supabase Mode logout must also call backend /auth/logout and enter Guest
        window.TurnamenConfig.setRuntimeInfo({ app_mode: "supabase" });
        window.TurnamenConfig.setAuthSession("sb-jwt-token", {
          id: "u-1",
          role: "team_captain",
          full_name: "Dimas",
        });
        await window.TurnamenAPI.logout();
        const afterSupabaseLogout = {
          token: window.TurnamenConfig.getState().token,
          currentUser: window.TurnamenConfig.getState().currentUser,
          explicitGuest: window.TurnamenConfig.getState().explicitGuest,
          logoutCalls: fetchCalls.filter((c) => c.url.includes("/auth/logout")).length,
        };

        return {
          beforeLogoutUser,
          afterMockLogout,
          committeeState,
          guestViaSwitcher,
          afterSupabaseLogout,
        };
        """
    )

    assert res["beforeLogoutUser"] == "organizer"
    assert res["afterMockLogout"]["currentUser"] is None
    assert res["afterMockLogout"]["explicitGuest"] is True
    assert "Masuk" in res["afterMockLogout"]["authBtnHtml"]
    assert res["afterMockLogout"]["authBtnHidden"] is False
    assert res["afterMockLogout"]["switcherVal"] == "guest"

    assert res["committeeState"]["role"] == "committee"
    assert "Keluar" in res["committeeState"]["authBtnHtml"]
    assert res["guestViaSwitcher"] is None

    assert res["afterSupabaseLogout"]["token"] is None
    assert res["afterSupabaseLogout"]["currentUser"] is None
    assert res["afterSupabaseLogout"]["explicitGuest"] is True
    assert res["afterSupabaseLogout"]["logoutCalls"] >= 1


def test_bug007_committee_assignment_context_and_ui_gating() -> None:
    res = _run_full_frontend_harness(
        """
        const tournaments = [
          {
            id: "t-unassigned-completed",
            title: "Turnamen Tidak Ditugaskan",
            status: "completed",
            game_id: "g-1",
            organizer_id: "org-1",
            is_assigned_committee: false,
            max_teams: 8,
            best_of: 3,
          },
          {
            id: "t-assigned-ongoing",
            title: "Turnamen Ditugaskan Aktif",
            status: "ongoing",
            game_id: "g-1",
            organizer_id: "org-1",
            is_assigned_committee: true,
            max_teams: 8,
            best_of: 3,
          },
        ];

        const env = createFrontendEnv({
          window: {
            fetch: async (url) => {
              if (url.includes("/games")) {
                return makeFetchResponse(200, { success: true, data: [{ id: "g-1", name: "MLBB" }] });
              }
              if (url.includes("/tournaments/") && url.includes("/matches")) {
                const isUnassigned = url.includes("t-unassigned-completed");
                return makeFetchResponse(200, {
                  success: true,
                  data: {
                    tournament_id: isUnassigned ? "t-unassigned-completed" : "t-assigned-ongoing",
                    tournament_title: isUnassigned ? "Turnamen Tidak Ditugaskan" : "Turnamen Ditugaskan Aktif",
                    best_of: 3,
                    matches: [{
                      id: "m-1",
                      tournament_id: isUnassigned ? "t-unassigned-completed" : "t-assigned-ongoing",
                      round_number: 1,
                      round_name: "Final",
                      match_number: 1,
                      status: "scheduled",
                      best_of: 3,
                      score_a: 0,
                      score_b: 0,
                      team_a_id: "tm-a",
                      team_b_id: "tm-b",
                      team_a: { id: "tm-a", name: "Alpha", tag: "ALP" },
                      team_b: { id: "tm-b", name: "Bravo", tag: "BRV" },
                    }],
                  },
                });
              }
              if (url.includes("/tournaments/") && url.includes("/registrations")) {
                return makeFetchResponse(200, { success: true, data: [] });
              }
              if (url.includes("/tournaments")) {
                return makeFetchResponse(200, { success: true, data: tournaments });
              }
              return makeFetchResponse(200, { success: true, data: [] });
            },
          },
        });

        const { window, elements } = env;
        window.TurnamenConfig.setSimulatedRole("committee");

        // 1. Default match-management must auto-pick assigned ongoing tournament
        await window.TurnamenApp.navigateTo("match-management");
        const assignedHtml = elements["main-content"].innerHTML;

        // 2. Switching context to unassigned tournament must block score submission CTA & show notice
        await window.TurnamenApp.navigateTo("match-management", { tournamentId: "t-unassigned-completed" });
        const unassignedHtml = elements["main-content"].innerHTML;

        return { assignedHtml, unassignedHtml };
        """
    )

    assert "Turnamen Ditugaskan Aktif" in res["assignedHtml"]
    assert 'data-action="submit-score"' in res["assignedHtml"]

    assert "Turnamen Tidak Ditugaskan" in res["unassignedHtml"]
    assert "Penugasan Panitia" in res["unassignedHtml"]
    assert 'data-action="submit-score"' not in res["unassignedHtml"]


def test_bug009_double_submit_guard_and_idempotency_key_lifecycle() -> None:
    res = _run_full_frontend_harness(
        """
        const calls = [];
        let resolveFirstFetch = null;
        let patchIndex = 0;

        const env = createFrontendEnv({
          window: {
            fetch: (url, init) => {
              if (url.includes("/games")) {
                return Promise.resolve(makeFetchResponse(200, { success: true, data: [{ id: "g-1", name: "MLBB" }] }));
              }
              if (url.includes("/tournaments/") && url.includes("/matches")) {
                return Promise.resolve(makeFetchResponse(200, { success: true, data: { matches: [] } }));
              }
              if (url.includes("/tournaments/t-1")) {
                return Promise.resolve(makeFetchResponse(200, {
                  success: true,
                  data: {
                    id: "t-1",
                    title: "Turnamen Aktif",
                    status: "ongoing",
                    organizer_id: "11111111-1111-4111-8111-111111111102",
                    is_assigned_committee: true,
                    best_of: 3,
                  },
                }));
              }
              if (url.includes("/tournaments")) {
                return Promise.resolve(makeFetchResponse(200, {
                  success: true,
                  data: [{
                    id: "t-1",
                    title: "Turnamen Aktif",
                    status: "ongoing",
                    organizer_id: "11111111-1111-4111-8111-111111111102",
                    is_assigned_committee: true,
                    best_of: 3,
                  }],
                }));
              }
              if (!url.includes("/matches/") || !init || init.method !== "PATCH") {
                return Promise.resolve(makeFetchResponse(200, { success: true, data: [] }));
              }

              patchIndex += 1;
              const body = init && init.body ? JSON.parse(init.body) : {};
              const headers = (init && init.headers) || {};
              calls.push({ url, method: init.method, body, headers });

              if (patchIndex === 1) {
                return new Promise((resolve) => {
                  resolveFirstFetch = () => resolve(
                    makeFetchResponse(503, {
                      success: false,
                      message: "Upstream timeout",
                      error: { code: "SERVICE_UNAVAILABLE" },
                    })
                  );
                });
              }

              return Promise.resolve(
                makeFetchResponse(200, {
                  success: true,
                  data: { match: { id: "m-1", status: "completed" } },
                })
              );
            },
          },
        });

        const { window, elements, makeElement } = env;
        window.TurnamenConfig.setSimulatedRole("committee");

        elements["score-a-m-1"] = Object.assign(makeElement("score-a-m-1"), { value: "2" });
        elements["score-b-m-1"] = Object.assign(makeElement("score-b-m-1"), { value: "1" });
        const btn = Object.assign(makeElement("btn-submit"), { textContent: "Sahkan" });

        // Launch 1st submission (pending) + immediate 2nd click (must be blocked)
        const firstPromise = window.TurnamenApp.submitScore("m-1", "t-1", btn);
        await new Promise((r) => setTimeout(r, 20));
        const busyDuringFlight = { disabled: btn.disabled, innerHTML: btn.innerHTML, text: btn.textContent };
        await window.TurnamenApp.submitScore("m-1", "t-1", btn);
        const callsWhilePending = calls.length;

        resolveFirstFetch();
        await firstPromise;
        const firstKey = calls[0].headers["Idempotency-Key"];

        // Retry with IDENTICAL payload after 503 -> MUST reuse exact same Idempotency-Key
        await window.TurnamenApp.submitScore("m-1", "t-1", btn);
        const secondKeySamePayload = calls[1].headers["Idempotency-Key"];

        // After success, key was cleared, so a new submission gets a fresh key:
        elements["score-b-m-1"].value = "0";
        await window.TurnamenApp.submitScore("m-1", "t-1", btn);
        const thirdKeyNewPayload = calls[2].headers["Idempotency-Key"];

        // Test modal busy lock prevents accidental backdrop close while busy
        window.TurnamenUI.openModal({ title: "Judul Modal", bodyHtml: "<p>Body</p>" });
        window.TurnamenUI.setModalBusy(true);
        window.TurnamenUI.closeModal(false);
        const overlayHiddenWhileBusy = elements["app-modal-backdrop"].classList.contains("hidden");
        window.TurnamenUI.setModalBusy(false);
        window.TurnamenUI.closeModal(false);
        const overlayHiddenWhenIdle = elements["app-modal-backdrop"].classList.contains("hidden");

        return {
          busyDuringFlight,
          callsWhilePending,
          totalCalls: calls.length,
          firstKey,
          firstBodyKey: calls[0].body.idempotency_key,
          secondKeySamePayload,
          thirdKeyNewPayload,
          overlayHiddenWhileBusy,
          overlayHiddenWhenIdle,
        };
        """
    )

    assert res["busyDuringFlight"]["disabled"] is True
    assert "Mengesahkan" in (res["busyDuringFlight"]["innerHTML"] + res["busyDuringFlight"]["text"])
    assert res["callsWhilePending"] == 1
    assert res["totalCalls"] == 3
    assert res["firstKey"] and len(res["firstKey"]) >= 16
    assert res["firstBodyKey"] == res["firstKey"]
    assert res["secondKeySamePayload"] == res["firstKey"]
    assert res["thirdKeyNewPayload"] != res["firstKey"]
    assert res["overlayHiddenWhileBusy"] is False
    assert res["overlayHiddenWhenIdle"] is True


def test_bug009_idempotency_key_rotates_on_payload_change_after_retryable_error() -> None:
    res = _run_full_frontend_harness(
        """
        const calls = [];
        let failMode = true;
        const env = createFrontendEnv({
          window: {
            fetch: async (url, init) => {
              if (url.includes("/tournaments/") && url.includes("/matches")) {
                return makeFetchResponse(200, { success: true, data: { matches: [] } });
              }
              if (url.includes("/tournaments/t-1")) {
                return makeFetchResponse(200, {
                  success: true,
                  data: {
                    id: "t-1",
                    title: "Turnamen Aktif",
                    status: "ongoing",
                    organizer_id: "11111111-1111-4111-8111-111111111102",
                    is_assigned_committee: true,
                    best_of: 3,
                  },
                });
              }
              if (url.includes("/tournaments")) {
                return makeFetchResponse(200, {
                  success: true,
                  data: [{
                    id: "t-1",
                    title: "Turnamen Aktif",
                    status: "ongoing",
                    organizer_id: "11111111-1111-4111-8111-111111111102",
                    is_assigned_committee: true,
                    best_of: 3,
                  }],
                });
              }

              const body = init && init.body ? JSON.parse(init.body) : {};
              const headers = (init && init.headers) || {};
              calls.push({ body, headers });
              if (failMode) {
                return makeFetchResponse(502, { success: false, message: "Bad Gateway" });
              }
              return makeFetchResponse(200, {
                success: true,
                data: { match: { id: "m-9", status: "completed" } },
              });
            },
          },
        });

        const { window, elements, makeElement } = env;
        window.TurnamenConfig.setSimulatedRole("organizer");
        elements["score-a-m-9"] = Object.assign(makeElement("score-a-m-9"), { value: "2" });
        elements["score-b-m-9"] = Object.assign(makeElement("score-b-m-9"), { value: "1" });

        await window.TurnamenApp.submitScore("m-9", "t-1");
        const keyAttempt1 = calls[0].headers["Idempotency-Key"];

        // Change score while retry key was stored -> must rotate to NEW key
        elements["score-b-m-9"].value = "0";
        failMode = false;
        await window.TurnamenApp.submitScore("m-9", "t-1");
        const keyAttempt2 = calls[1].headers["Idempotency-Key"];

        return { keyAttempt1, keyAttempt2 };
        """
    )

    assert res["keyAttempt1"]
    assert res["keyAttempt2"]
    assert res["keyAttempt1"] != res["keyAttempt2"]


def test_bug013_and_bug016_to_024_ui_rendering_contracts() -> None:
    res = _run_full_frontend_harness(
        """
        let includeManagerFields = false;
        const sampleTournament = {
          id: "t-1",
          title: "Turnamen Uji",
          status: "draft",
          game_id: "g-1",
          organizer_id: "org-1",
          max_teams: 8,
          best_of: 3,
          approved_count: 2,
          prize_pool: "Rp 5.000.000",
        };
        const announcements = [
          { id: "a-old-pinned", title: "Pinned Lama", content: "Penting", target_role: "all", is_pinned: true, published_at: "2026-11-01T10:00:00Z" },
          { id: "a-new", title: "Terbaru Biasa", content: "Baru", target_role: "all", is_pinned: false, published_at: "2026-11-20T10:00:00Z" },
          { id: "a-old", title: "Lama Biasa", content: "Lama", target_role: "all", is_pinned: false, published_at: "2026-11-05T10:00:00Z" },
        ];

        const env = createFrontendEnv({
          window: {
            fetch: async (url) => {
              if (url.includes("/games")) {
                return makeFetchResponse(200, { success: true, data: [{ id: "g-1", name: "MLBB" }] });
              }
              if (url.includes("/reports")) {
                const summary = {
                  completion_percentage: 50,
                  completed_matches: 1,
                  total_matches: 2,
                  approved_teams: 2,
                  max_teams: 8,
                  scheduled_matches: 1,
                  champion_team: null,
                };
                if (includeManagerFields) {
                  summary.pending_registrations = 3;
                  summary.total_registrations = 11;
                }
                return makeFetchResponse(200, {
                  success: true,
                  data: {
                    tournament: sampleTournament,
                    summary,
                    standings: [],
                    recent_activity: includeManagerFields ? [{ action: "VERIFY", entity_type: "registration", created_at: "2026-11-10T10:00:00Z" }] : [],
                  },
                });
              }
              if (url.includes("/announcements")) {
                return makeFetchResponse(200, { success: true, data: announcements });
              }
              if (url.includes("/matches")) {
                const byeMatch = {
                  id: "m-bye",
                  round_number: 1,
                  round_name: "Quarter Final",
                  match_number: 1,
                  status: "bye",
                  best_of: 3,
                  score_a: 0,
                  score_b: 0,
                  team_a_id: "tm-a",
                  team_a_name: "Garuda",
                  team_a_tag: "GRD",
                  team_b_id: null,
                  winner_team_id: "tm-a",
                  next_match_id: "m-final",
                  next_slot: "A",
                };
                const finalMatch = {
                  id: "m-final",
                  round_number: 2,
                  round_name: "Final",
                  match_number: 1,
                  status: "scheduled",
                  best_of: 3,
                  score_a: 0,
                  score_b: 0,
                  team_a_id: "tm-a",
                  team_a_name: "Garuda",
                  team_a_tag: "GRD",
                  team_b_id: null,
                };
                return makeFetchResponse(200, {
                  success: true,
                  data: {
                    tournament_id: "t-1",
                    tournament_title: "Turnamen Uji",
                    best_of: 3,
                    matches: [byeMatch, finalMatch],
                    rounds: [
                      { round_number: 1, round_name: "Quarter Final", matches: [byeMatch] },
                      { round_number: 2, round_name: "Final", matches: [finalMatch] },
                    ],
                  },
                });
              }
              if (url.includes("/registrations")) {
                return makeFetchResponse(200, { success: true, data: [] });
              }
              if (url.includes("/tournaments/t-1")) {
                return makeFetchResponse(200, { success: true, data: sampleTournament });
              }
              if (url.includes("/tournaments")) {
                return makeFetchResponse(200, { success: true, data: [sampleTournament] });
              }
              if (url.includes("/teams/tm-a")) {
                return makeFetchResponse(200, { success: true, data: { id: "tm-a", name: "Garuda", tag: "GRD", captain_id: "11111111-1111-4111-8111-111111111104" } });
              }
              if (url.includes("/teams")) {
                return makeFetchResponse(200, { success: true, data: [{ id: "tm-a", name: "Garuda", tag: "GRD", captain_id: "11111111-1111-4111-8111-111111111104" }] });
              }
              return makeFetchResponse(200, { success: true, data: [] });
            },
          },
        });

        const { window, elements } = env;

        // 1. Public Report as Guest
        window.TurnamenConfig.setSimulatedRole("guest");
        await window.TurnamenApp.navigateTo("reports");
        const publicReportHtml = elements["main-content"].innerHTML;

        // 2. Manager Report as Organizer
        includeManagerFields = true;
        window.TurnamenConfig.setSimulatedRole("organizer");
        await window.TurnamenApp.navigateTo("reports");
        const managerReportHtml = elements["main-content"].innerHTML;

        // 3. Draft Tournament Detail as Team Captain -> registration form MUST stay hidden
        window.TurnamenConfig.setSimulatedRole("team_captain");
        await window.TurnamenApp.navigateTo("tournament-detail");
        const draftDetailHtml = elements["main-content"].innerHTML;

        // 4. BYE Match Card & Bracket card rendering
        const byeCardHtml = window.TurnamenUI.renderMatchCard({
          id: "m-bye",
          round_name: "Quarter Final",
          match_number: 1,
          status: "bye",
          best_of: 3,
          score_a: 0,
          score_b: 0,
          team_a_id: "tm-a",
          team_a_name: "Garuda",
          team_a_tag: "GRD",
          team_b_id: null,
          winner_team_id: "tm-a",
        });
        await window.TurnamenApp.navigateTo("bracket");
        const bracketHtml = elements["main-content"].innerHTML;

        // 5. Announcements sorting: Pinned first, then newest date
        await window.TurnamenApp.navigateTo("announcements");
        const annHtml = elements["main-content"].innerHTML;

        // 6. Add member modal includes optional user_id field; Edit tournament limits transitions
        window.TurnamenConfig.setSimulatedRole("super_admin");
        await window.TurnamenApp.openAddMemberModal("tm-a");
        const addMemberHtml = elements["app-modal-body"].innerHTML;

        await window.TurnamenApp.openEditTournamentModal("t-1");
        const editTournamentHtml = elements["app-modal-body"].innerHTML;

        await window.TurnamenApp.openCreateTournamentModal();
        const createTournamentHtml = elements["app-modal-body"].innerHTML;

        return {
          publicReportHtml,
          managerReportHtml,
          draftDetailHtml,
          byeCardHtml,
          bracketHtml,
          annHtml,
          addMemberHtml,
          editTournamentHtml,
          createTournamentHtml,
        };
        """
    )

    # BUG-013 public vs manager report
    assert "Mode Ringkas Publik" in res["publicReportHtml"]
    assert "Menunggu verifikasi:" not in res["publicReportHtml"]
    assert "Log Audit Aktivitas Turnamen" not in res["publicReportHtml"]

    assert "Menunggu verifikasi: 3 (Total pendaftar: 11)" in res["managerReportHtml"]
    assert "Log Audit Aktivitas Turnamen" in res["managerReportHtml"]

    # BUG-013 draft tournament cannot accept registration from captain
    assert "reg-team-select" not in res["draftDetailHtml"]

    # BUG-016 BYE rendering & bracket card state
    assert "BYE" in res["byeCardHtml"]
    assert "ADV" in res["byeCardHtml"]
    assert "TBD" not in res["byeCardHtml"]
    assert "is-bye-match" in res["bracketHtml"]
    assert 'data-completed="true"' in res["bracketHtml"]

    # Announcements pinned first, then newest
    idx_pinned = res["annHtml"].find("Pinned Lama")
    idx_new = res["annHtml"].find("Terbaru Biasa")
    idx_old = res["annHtml"].find("Lama Biasa")
    assert 0 <= idx_pinned < idx_new < idx_old

    # Modals: user_id input, legal transitions on edit, and Bo7 on create
    assert 'id="member-user-id"' in res["addMemberHtml"]
    assert 'value="open_registration"' in res["editTournamentHtml"]
    assert 'value="ongoing"' not in res["editTournamentHtml"]
    assert "Bo7" in res["createTournamentHtml"]


def test_all_6_roles_flask_api_consistency_and_idempotency_replay() -> None:
    app = create_app(load_config(overrides={"app_mode": "mock"}), repository=MockDataStoreRepository())
    client = app.test_client()

    t_ongoing = "33333333-3333-4333-8333-333333333301"
    m_sched = "88888888-8888-4888-8888-888888888804"

    # 1. Guest: public report without internal fields; approved-only registrations; mutating endpoints rejected
    guest_rep = client.get(f"/api/v1/tournaments/{t_ongoing}/reports")
    assert guest_rep.status_code == 200
    guest_data = guest_rep.get_json()["data"]
    assert "pending_registrations" not in guest_data["summary"]
    assert guest_data.get("recent_activity", []) == []
    guest_regs = client.get(f"/api/v1/tournaments/{t_ongoing}/registrations")
    assert guest_regs.status_code == 200
    assert all(r["status"] == "approved" for r in guest_regs.get_json()["data"])
    assert client.post(
        f"/api/v1/tournaments/{t_ongoing}/announcements",
        json={"title": "Test", "content": "Unauthorized post"},
    ).status_code == 401

    # 2. Player: public report without internal fields; cannot submit match or post announcement
    player_tok = _login(client, "player@turnamen.in")
    player_rep = client.get(f"/api/v1/tournaments/{t_ongoing}/reports", headers=_json_headers(player_tok))
    assert player_rep.status_code == 200
    assert "pending_registrations" not in player_rep.get_json()["data"]["summary"]
    assert player_rep.get_json()["data"].get("recent_activity", []) == []
    assert client.patch(
        f"/api/v1/matches/{m_sched}/result",
        json={"score_a": 2, "score_b": 0},
        headers=_json_headers(player_tok),
    ).status_code == 403

    # 3. Team Captain: registration list returns approved + owned entries; report is public summary
    cap_tok = _login(client, "captain@turnamen.in")
    cap_regs = client.get(f"/api/v1/tournaments/{t_ongoing}/registrations", headers=_json_headers(cap_tok))
    assert cap_regs.status_code == 200
    assert all(
        r["status"] == "approved" or r["team_id"] == "44444444-4444-4444-8444-444444444401"
        for r in cap_regs.get_json()["data"]
    )
    assert "pending_registrations" not in client.get(
        f"/api/v1/tournaments/{t_ongoing}/reports",
        headers=_json_headers(cap_tok),
    ).get_json()["data"]["summary"]

    # 4. Organizer: manager report with pending_registrations + recent_activity
    org_tok = _login(client, "organizer@turnamen.in")
    org_rep = client.get(f"/api/v1/tournaments/{t_ongoing}/reports", headers=_json_headers(org_tok)).get_json()["data"]
    assert "pending_registrations" in org_rep["summary"]
    assert len(org_rep["recent_activity"]) >= 1

    # 5. Committee (assigned): assignment flag + manager report + Idempotency-Key replay
    com_tok = _login(client, "committee@turnamen.in")
    com_tours = client.get("/api/v1/tournaments", headers=_json_headers(com_tok)).get_json()["data"]
    ongoing_item = next(t for t in com_tours if t["id"] == t_ongoing)
    assert ongoing_item["is_assigned_committee"] is True

    idem_key = "wave3-idem-header-001"
    first_sub = client.patch(
        f"/api/v1/matches/{m_sched}/result",
        json={"score_a": 2, "score_b": 1, "notes": "Verified by Committee"},
        headers=_json_headers(com_tok, {"Idempotency-Key": idem_key}),
    )
    assert first_sub.status_code == 200, first_sub.get_json()
    first_data = first_sub.get_json()["data"]

    replay_sub = client.patch(
        f"/api/v1/matches/{m_sched}/result",
        json={"score_a": 2, "score_b": 1, "notes": "Verified by Committee"},
        headers=_json_headers(com_tok, {"Idempotency-Key": idem_key}),
    )
    assert replay_sub.status_code == 200
    assert replay_sub.get_json()["data"]["match"]["winner_team_id"] == first_data["match"]["winner_team_id"]

    conflict_sub = client.patch(
        f"/api/v1/matches/{m_sched}/result",
        json={"score_a": 2, "score_b": 0, "notes": "Different payload"},
        headers=_json_headers(com_tok, {"Idempotency-Key": idem_key}),
    )
    assert conflict_sub.status_code == 409

    # 6. Super Admin: full manager report & full registrations list
    admin_tok = _login(client, "admin@turnamen.in")
    admin_rep = client.get(f"/api/v1/tournaments/{t_ongoing}/reports", headers=_json_headers(admin_tok)).get_json()["data"]
    assert "pending_registrations" in admin_rep["summary"]
    assert len(client.get(f"/api/v1/tournaments/{t_ongoing}/registrations", headers=_json_headers(admin_tok)).get_json()["data"]) == 8
