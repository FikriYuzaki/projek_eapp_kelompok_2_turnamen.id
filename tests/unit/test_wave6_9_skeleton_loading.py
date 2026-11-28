"""Wave 6.9 Dashboard Skeleton Shimmer, Progressive Loading & Accessibility Tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest

from backend.app import create_app
from backend.core.config import ROOT_DIR, AppConfig
from backend.repositories.mock.mock_repository import MockDataStoreRepository

CSS_PATH = ROOT_DIR / "desktop" / "web" / "assets" / "css" / "components.css"
LAYOUT_CSS_PATH = ROOT_DIR / "desktop" / "web" / "assets" / "css" / "layout.css"
JS_DIR = ROOT_DIR / "desktop" / "web" / "assets" / "js"


def test_skeleton_shimmer_css_accessibility_and_responsive_rules() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    layout_css = LAYOUT_CSS_PATH.read_text(encoding="utf-8")

    # Dark-navy background + cyan shimmer gradient + GPU-friendly keyframes
    assert "@keyframes arena-shimmer" in css
    assert ".arena-skeleton" in css
    assert "#121d33" in css
    assert "rgba(0, 229, 255" in css
    assert "pointer-events: none;" in css

    # Accessibility: prefers-reduced-motion disables shimmer animation
    assert "@media (prefers-reduced-motion: reduce)" in css
    reduced_block = css.split("@media (prefers-reduced-motion: reduce)")[-1]
    assert ".arena-skeleton" in reduced_block
    assert "animation: none;" in reduced_block

    # Responsive rules covering 1366x820 and 1024x768 breakpoints
    assert "@media (max-width: 1024px)" in css
    assert "@media (max-width: 1240px)" in layout_css
    assert "@media (max-width: 1024px)" in layout_css


def test_wave6_9_skeleton_components_progressive_loading_and_states() -> None:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime is not available")

    for rel in ("components/ui-components.js", "pages/app-pages.js"):
        syntax = subprocess.run(
            [node_bin, "--check", str(JS_DIR / rel)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert syntax.returncode == 0, f"Syntax error in {rel}: {syntax.stderr}"

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

const elements = new Map();
function makeEl(id) {{
  if (elements.has(id)) return elements.get(id);
  const attrs = {{}};
  let _html = "";
  const slotCache = new Map();
  const el = {{
    id,
    value: "",
    textContent: "",
    hidden: false,
    disabled: false,
    set innerHTML(v) {{
      _html = String(v || "");
      slotCache.clear();
      // Track slot divs inside main-content for progressive DOM verification
      const matches = _html.matchAll(/id="(sa-[a-z-]+-slot)"/g);
      for (const m of matches) {{
        const slotEl = makeEl(m[1]);
        slotEl._directUpdated = false;
        slotCache.set(m[1], slotEl);
      }}
    }},
    get innerHTML() {{
      let rendered = _html;
      for (const [sid, sEl] of slotCache.entries()) {{
        if (sEl._directUpdated) {{
          rendered += `\\n<!--SLOT:${{sid}}-->` + sEl.innerHTML;
        }}
      }}
      return rendered;
    }},
    setAttribute(k, v) {{ attrs[k] = String(v); }},
    getAttribute(k) {{ return k in attrs ? attrs[k] : null; }},
    classList: {{ add() {{}}, remove() {{}}, toggle() {{}}, contains: () => false }},
    appendChild() {{}},
    remove() {{}},
    addEventListener() {{}},
    focus() {{}},
    closest() {{ return null; }},
    querySelector(sel) {{
      if (sel && sel.startsWith("#")) {{
        const key = sel.slice(1);
        if (_html.includes(`id="${{key}}"`)) {{
          const s = makeEl(key);
          const origSetter = Object.getOwnPropertyDescriptor(s, "innerHTML")?.set;
          s._directUpdated = true;
          slotCache.set(key, s);
          return s;
        }}
      }}
      return null;
    }},
    querySelectorAll() {{ return []; }},
  }};
  elements.set(id, el);
  return el;
}}

let mockScenario = "normal";
let deferredReportResolve = null;
const timeline = [];

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
    const jsonResp = (data, ok = true, status = 200) => ({{
      status,
      ok,
      headers: {{ get: () => "application/json" }},
      text: async () => JSON.stringify({{
        success: ok,
        message: ok ? "OK" : "Simulated endpoint error",
        data: ok ? data : null,
        error: ok ? null : {{ code: "HTTP_ERROR", details: {{}} }},
      }}),
    }});

    if (mockScenario === "error_all") {{
      return jsonResp(null, false, 500);
    }}
    if (mockScenario === "empty_all") {{
      if (url.includes("/reports")) {{
        return jsonResp({{ tournament: {{ id: "t1", title: "Empty" }}, summary: {{ completed_matches: 0, total_matches: 0, completion_percentage: 0 }}, standings: [], recent_activity: [] }});
      }}
      return jsonResp([]);
    }}

    if (url.includes("/games")) {{
      return jsonResp([{{ id: "g1", slug: "mlbb", name: "MLBB", is_active: true }}]);
    }}
    if (url.includes("/tournaments/") && url.endsWith("/reports")) {{
      if (mockScenario === "slow_report") {{
        return await new Promise((resolve) => {{
          deferredReportResolve = () => resolve(jsonResp({{
            tournament: {{ id: "t1", title: "Turnamen Cepat" }},
            summary: {{ completed_matches: 2, total_matches: 4, completion_percentage: 50, approved_teams: 4, max_teams: 8 }},
            standings: [],
            recent_activity: [{{ action: "MATCH_UPDATED", entity_type: "match", created_at: "2026-11-26T10:00:00Z" }}],
          }}));
        }});
      }}
      if (mockScenario === "partial_error") {{
        return jsonResp(null, false, 503);
      }}
      return jsonResp({{
        tournament: {{ id: "t1", title: "Turnamen Cepat" }},
        summary: {{ completed_matches: 2, total_matches: 4, completion_percentage: 50, approved_teams: 4, max_teams: 8 }},
        standings: [{{ rank: 1, team_name: "Alpha", team_tag: "ALP", matches_won: 2, matches_lost: 0, placement_label: "Juara 1 (Champion)" }}],
        recent_activity: [{{ action: "MATCH_UPDATED", entity_type: "match", created_at: "2026-11-26T10:00:00Z" }}],
      }});
    }}
    if (url.includes("/tournaments/") && url.endsWith("/announcements")) {{
      return jsonResp([{{ id: "a1", title: "Jadwal Resmi", content: "Check-in pukul 10:00.", priority: "important", is_pinned: true, author_name: "Panitia" }}]);
    }}
    if (url.endsWith("/tournaments") || url.includes("/tournaments?")) {{
      return jsonResp([{{ id: "t1", title: "Turnamen Cepat", game_id: "g1", game_name: "MLBB", status: "ongoing", max_teams: 8, approved_teams_count: 4, venue: "Online" }}]);
    }}
    if (url.includes("/teams")) {{
      return jsonResp([{{ id: "tm1", name: "Alpha", tag: "ALP", game_id: "g1", region: "ID", member_count: 5, members: [] }}]);
    }}
    if (url.endsWith("/users")) {{
      return jsonResp([{{ id: "u1", email: "admin@turnamen.in", username: "superadmin", full_name: "Super Admin", role: "super_admin", is_auth_linked: true }}]);
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
  const ui = sandbox.TurnamenUI;
  // 1. Check all reusable skeleton component helpers
  const skels = {{
    stat: ui.renderStatCardsSkeleton(4),
    tournaments: ui.renderTournamentCardsSkeleton(2),
    table: ui.renderTableSkeleton({{ rows: 3, columns: 4, title: "Test Table" }}),
    list: ui.renderListSkeleton({{ rows: 3, title: "Test List" }}),
    announcements: ui.renderAnnouncementCardsSkeleton(2),
    report: ui.renderReportChartSkeleton(),
    dashboard: ui.renderDashboardSkeleton("super_admin"),
  }};

  sandbox.TurnamenConfig.setRuntimeInfo({{ app_mode: "supabase", is_simulation: false, supabase_host: "cfdsgxciodfkamskafwe.supabase.co" }});
  sandbox.TurnamenConfig.setAuthSession("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1MSIsImV4cCI6NDAwMDAwMDAwMH0.sig", {{
    id: "u1",
    email: "admin@turnamen.in",
    username: "superadmin",
    full_name: "Super Admin",
    role: "super_admin",
    is_active: true,
  }});

  const main = makeEl("main-content");

  // 2. Slow report: verify skeleton appears immediately, fast slots render before slow report resolves
  mockScenario = "slow_report";
  const navPromise = sandbox.TurnamenApp.navigateTo("dashboard");
  const busyDuringLoad = main.getAttribute("aria-busy");
  const initialHasSkeleton = main.innerHTML.includes('data-skeleton="true"');

  // Wait microtasks for fast Wave 1 endpoints (tournaments, games, teams, users) to finish while report still pending
  await new Promise((r) => setTimeout(r, 40));
  const tourSlot = makeEl("sa-tournaments-slot").innerHTML;
  const usersSlot = makeEl("sa-users-slot").innerHTML;
  const auditHtmlWhilePending = makeEl("sa-audit-slot").innerHTML || main.innerHTML;
  const fastRenderedBeforeSlowReport =
    tourSlot.includes("Turnamen Cepat") &&
    usersSlot.includes("superadmin") &&
    auditHtmlWhilePending.includes('data-skeleton="true"') &&
    auditHtmlWhilePending.includes("Jejak Audit Aktivitas Sistem");

  // Resolve slow report -> verify audit skeleton disappears & aria-busy="false"
  deferredReportResolve();
  await navPromise;
  const busyAfterLoad = main.getAttribute("aria-busy");
  const auditSlotAfterDone = makeEl("sa-audit-slot").innerHTML;
  const noSkeletonLeft =
    !makeEl("sa-metrics-slot").innerHTML.includes('data-skeleton="true"') &&
    !makeEl("sa-tournaments-slot").innerHTML.includes('data-skeleton="true"') &&
    !makeEl("sa-games-slot").innerHTML.includes('data-skeleton="true"') &&
    !makeEl("sa-users-slot").innerHTML.includes('data-skeleton="true"') &&
    !auditSlotAfterDone.includes('data-skeleton="true"');

  // 3. Refresh with cached snapshot preserves previous data while refreshing
  mockScenario = "normal";
  const refreshPromise = sandbox.TurnamenApp.navigateTo("dashboard");
  const refreshHasBannerAndOldData =
    main.innerHTML.includes("Memperbarui data terbaru") &&
    main.innerHTML.includes("Turnamen Cepat");
  await refreshPromise;

  // 4. Test all core pages across normal, empty, and error states
  const pageChecks = {{}};
  for (const page of ["tournament-list", "team-management", "announcements", "reports"]) {{
    mockScenario = "normal";
    await sandbox.TurnamenApp.navigateTo(page);
    pageChecks[`${{page}}_loaded`] =
      main.getAttribute("aria-busy") === "false" &&
      !main.innerHTML.includes('data-skeleton="true"');

    mockScenario = "empty_all";
    await sandbox.TurnamenApp.navigateTo(page);
    pageChecks[`${{page}}_empty`] =
      main.getAttribute("aria-busy") === "false" &&
      !main.innerHTML.includes('data-skeleton="true"');

    mockScenario = "error_all";
    await sandbox.TurnamenApp.navigateTo(page);
    pageChecks[`${{page}}_error`] =
      main.getAttribute("aria-busy") === "false" &&
      !main.innerHTML.includes('data-skeleton="true"');
  }}

  // 5. Partial error on Dashboard report keeps other sections rendered
  mockScenario = "partial_error";
  await sandbox.TurnamenApp.navigateTo("dashboard");
  const finalDashboardHtml = main.innerHTML;
  const partialDashboardOk =
    finalDashboardHtml.includes("Turnamen Cepat") &&
    finalDashboardHtml.includes("superadmin") &&
    finalDashboardHtml.includes("state-box-error") &&
    !finalDashboardHtml.includes('data-skeleton="true"');

  console.log(JSON.stringify({{
    allSkelsValid: Object.values(skels).every((s) => s.includes('data-skeleton="true"') && !s.includes("undefined")),
    busyDuringLoad,
    initialHasSkeleton,
    fastRenderedBeforeSlowReport,
    busyAfterLoad,
    auditHasMatchLog: auditSlotAfterDone.includes("MATCH_UPDATED"),
    noSkeletonLeft,
    refreshHasBannerAndOldData,
    pageChecks,
    partialDashboardOk,
  }}));
}})().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    proc = subprocess.run([node_bin, "-e", harness], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    res = json.loads(proc.stdout.strip().splitlines()[-1])

    assert res["allSkelsValid"] is True
    assert res["busyDuringLoad"] == "true"
    assert res["initialHasSkeleton"] is True
    assert res["fastRenderedBeforeSlowReport"] is True
    assert res["busyAfterLoad"] == "false"
    assert res["auditHasMatchLog"] is True
    assert res["noSkeletonLeft"] is True
    assert res["refreshHasBannerAndOldData"] is True
    assert all(res["pageChecks"].values()), res["pageChecks"]
    assert res["partialDashboardOk"] is True


def test_mock_dashboard_and_core_pages_benchmark_under_3_seconds() -> None:
    app = create_app(
        config=AppConfig(app_mode="mock", secret_key="wave69-bench"),
        repository=MockDataStoreRepository(),
    )
    headers = {"X-Mock-Role": "super_admin"}
    t0 = time.perf_counter()
    with app.test_client() as client:
        for ep in (
            "/api/v1/games?include_inactive=true",
            "/api/v1/tournaments",
            "/api/v1/teams",
            "/api/v1/users",
            "/api/v1/tournaments/33333333-3333-4333-8333-333333333301/reports",
            "/api/v1/tournaments/33333333-3333-4333-8333-333333333301/announcements",
        ):
            r = client.get(ep, headers=headers)
            assert r.status_code == 200
            assert r.get_json()["success"] is True
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0
