"""Wave 6.10 Real Game Artwork Integration, Mapping, Lazy Loading & Fallback Tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest

from backend.app import create_app
from backend.core.config import ROOT_DIR, AppConfig
from backend.repositories.mock.mock_data import build_initial_mock_store
from backend.repositories.mock.mock_repository import MockDataStoreRepository

CSS_PATH = ROOT_DIR / "desktop" / "web" / "assets" / "css" / "components.css"
JS_DIR = ROOT_DIR / "desktop" / "web" / "assets" / "js"


def test_artwork_css_preserves_poster_ratio_and_object_fit() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".artwork-img" in css
    assert "object-fit: cover;" in css
    assert "aspect-ratio: 16 / 9;" in css
    assert ".game-chip-thumb" in css
    assert ".artwork-fallback-svg.is-visible" in css


def test_real_game_artwork_mapping_lazy_loading_cache_and_fallback() -> None:
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

    seed_games = build_initial_mock_store()["games"]

    harness = f"""
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const jsDir = {json.dumps(str(JS_DIR))};
const seedGames = {json.dumps(seed_games)};
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
  const el = {{
    id,
    value: "",
    textContent: "",
    hidden: false,
    disabled: false,
    set innerHTML(v) {{ _html = String(v || ""); }},
    get innerHTML() {{ return _html; }},
    setAttribute(k, v) {{ attrs[k] = String(v); }},
    getAttribute(k) {{ return k in attrs ? attrs[k] : null; }},
    classList: {{ add() {{}}, remove() {{}}, toggle() {{}}, contains: () => false }},
    appendChild() {{}},
    remove() {{}},
    addEventListener() {{}},
    focus() {{}},
    closest() {{ return null; }},
    querySelector() {{ return null; }},
    querySelectorAll() {{ return []; }},
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
    const jsonResp = (data) => ({{
      status: 200,
      ok: true,
      headers: {{ get: () => "application/json" }},
      text: async () => JSON.stringify({{ success: true, message: "OK", data }}),
    }});
    if (url.includes("/games")) return jsonResp(seedGames);
    if (url.endsWith("/tournaments")) {{
      return jsonResp([
        {{
          id: "t1",
          title: "MLBB Open",
          game_id: seedGames[0].id,
          game_name: seedGames[0].name,
          status: "ongoing",
          max_teams: 8,
          approved_teams_count: 4,
          best_of: 3,
          prize_pool: 1000000,
          venue: "Online",
        }},
      ]);
    }}
    if (url.endsWith("/teams")) {{
      return jsonResp([
        {{
          id: "tm1",
          name: "Garuda",
          tag: "GRD",
          game_id: seedGames[0].id,
          game_name: seedGames[0].name,
          member_count: 5,
          members: [],
        }},
      ]);
    }}
    if (url.endsWith("/users")) {{
      return jsonResp([
        {{ id: "u1", email: "admin@turnamen.in", username: "superadmin", full_name: "Super Admin", role: "super_admin", is_auth_linked: true }},
      ]);
    }}
    if (url.includes("/reports")) {{
      return jsonResp({{ tournament: {{ id: "t1", title: "MLBB Open" }}, summary: {{ completed_matches: 1, total_matches: 2, completion_percentage: 50 }}, standings: [], recent_activity: [] }});
    }}
    if (url.includes("/announcements")) {{
      return jsonResp([]);
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
  ui.clearArtworkCache();

  // 1. Verify all 3 official game URLs & ID/slug resolution without mismatches
  const resolvedBySeed = seedGames.map((g) => {{
    const art = ui.resolveGameArtwork(g);
    return {{ id: g.id, slug: g.slug, resolvedSlug: art.slug, src: art.src, official: art.hasOfficialArtwork }};
  }});

  // Wrong name does not override exact ID mapping; unknown game does not borrow existing art
  const resolvedIdWins = ui.resolveGameArtwork({{
    id: seedGames[1].id,
    slug: "custom-val-edition",
    name: "Something Mobile Legends Like",
  }});
  const resolvedUnknown = ui.resolveGameArtwork({{
    id: "99999999-9999-4999-8999-999999999999",
    slug: "dota-2-custom",
    name: "Dota 2 Custom",
  }});

  // 2. Security validation of custom icon_url
  const safeChecks = {{
    validHttps: ui.isSafeArtworkUrl("https://cdn.example.com/poster.jpg"),
    rejectHttp: ui.isSafeArtworkUrl("http://cdn.example.com/poster.jpg"),
    rejectJavascript: ui.isSafeArtworkUrl("javascript:alert(1)"),
    rejectCreds: ui.isSafeArtworkUrl("https://user:pass@cdn.example.com/poster.jpg"),
    rejectTokenQuery: ui.isSafeArtworkUrl("https://cdn.example.com/poster.jpg?api_key=secret123"),
    allowLocalAsset: ui.isSafeArtworkUrl("assets/images/games/default-arena.svg"),
    rejectTraversal: ui.isSafeArtworkUrl("assets/images/../../secret.txt"),
  }};

  // 3. Lazy loading & markup consistency + dual-stage error fallback + cache
  const posterHtml = ui.renderGameArtwork(seedGames[0], "", {{ hideCaption: true }});
  const chipHtml = ui.renderGameChip(seedGames[2]);

  // Simulate load cache hit + failure fallback -> cache prevents retrying broken CDN URL
  const svgClasses = [];
  const fakeFallbackSvg = {{
    classList: {{
      add(cls) {{ svgClasses.push(cls); }},
      remove() {{}},
    }},
  }};
  const fakeImg = {{
    attrs: {{
      "data-primary-src": resolvedBySeed[1].src,
      src: resolvedBySeed[1].src,
    }},
    src: resolvedBySeed[1].src,
    dataset: {{}},
    style: {{}},
    nextElementSibling: fakeFallbackSvg,
    getAttribute(k) {{ return this.attrs[k] || ""; }},
    setAttribute(k, v) {{ this.attrs[k] = v; }},
  }};
  // First failure switches to local SVG fallback
  ui.handleArtworkError(fakeImg, "assets/images/games/valorant.svg");
  const afterFirstErrorSrc = fakeImg.src;
  // Second failure (even fallback broken) reveals inline SVG
  ui.handleArtworkError(fakeImg, "assets/images/games/valorant.svg");
  const afterSecondErrorDisplay = fakeImg.style.display;
  const cachedResolutionAfterFail = ui.resolveGameArtwork(seedGames[1]).src;

  // Clear cache and mark loaded
  ui.clearArtworkCache();
  ui.handleArtworkLoad({{
    dataset: {{}},
    getAttribute(k) {{ return k === "data-primary-src" ? resolvedBySeed[0].src : ""; }},
  }});
  const cacheStats = ui.getArtworkCacheStats();

  // 4. Verify rendered Dashboard & pages consistently use artwork without eager blocking
  sandbox.TurnamenConfig.setRuntimeInfo({{ app_mode: "supabase", is_simulation: false }});
  sandbox.TurnamenConfig.setAuthSession("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1MSIsImV4cCI6NDAwMDAwMDAwMH0.sig", {{
    id: "u1",
    email: "admin@turnamen.in",
    username: "superadmin",
    full_name: "Super Admin",
    role: "super_admin",
    is_active: true,
  }});
  await sandbox.TurnamenApp.navigateTo("dashboard");
  const dashHtml = makeEl("main-content").innerHTML;

  // Also test guest/player dashboard (poster gallery + featured banner)
  sandbox.TurnamenConfig.enterGuestMode();
  await sandbox.TurnamenApp.navigateTo("dashboard");
  const guestHtml = makeEl("main-content").innerHTML;

  console.log(JSON.stringify({{
    resolvedBySeed,
    resolvedIdWinsSlug: resolvedIdWins.slug,
    resolvedUnknown: {{ slug: resolvedUnknown.slug, official: resolvedUnknown.hasOfficialArtwork, src: resolvedUnknown.src }},
    safeChecks,
    posterHasLazy: posterHtml.includes('loading="lazy"') && posterHtml.includes('decoding="async"') && posterHtml.includes('referrerpolicy="no-referrer"'),
    chipHasOfficialThumb: chipHtml.includes('class="game-chip-thumb"') && chipHtml.includes("capsule_616x353.jpg"),
    afterFirstErrorSrc,
    afterSecondErrorDisplay,
    svgVisibleAdded: svgClasses.includes("is-visible"),
    cachedResolutionAfterFail,
    cacheStats,
    dashHasRealMlbbThumb: dashHtml.includes("akmweb.youngjoygame.com/web/gms/image/c3d1596795b86dc26e5f1ef2d48c3dfd.jpg"),
    dashHasRealValThumb: dashHtml.includes("cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/a3d06721391f4c274e588c380ca6903c8b3e129e-1920x1080.jpg"),
    dashHasRealFcThumb: dashHtml.includes("shared.fastly.steamstatic.com/store_item_assets/steam/apps/2669320/capsule_616x353.jpg"),
    guestHasNoEagerLoading: !guestHtml.includes('loading="eager"'),
    guestHasAll3RealPosters:
      guestHtml.includes("akmweb.youngjoygame.com") &&
      guestHtml.includes("cmsassets.rgpub.io") &&
      guestHtml.includes("shared.fastly.steamstatic.com/store_item_assets/steam/apps/2669320/capsule_616x353.jpg"),
  }}));
}})().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    proc = subprocess.run([node_bin, "-e", harness], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    res = json.loads(proc.stdout.strip().splitlines()[-1])

    assert [item["resolvedSlug"] for item in res["resolvedBySeed"]] == [
        "mobile-legends",
        "valorant",
        "ea-sports-fc",
    ]
    assert all(item["official"] is True and item["src"].startswith("https://") for item in res["resolvedBySeed"])
    assert res["resolvedIdWinsSlug"] == "valorant"
    assert res["resolvedUnknown"] == {
        "slug": "default-arena",
        "official": False,
        "src": "assets/images/games/default-arena.svg",
    }
    assert res["safeChecks"] == {
        "validHttps": True,
        "rejectHttp": False,
        "rejectJavascript": False,
        "rejectCreds": False,
        "rejectTokenQuery": False,
        "allowLocalAsset": True,
        "rejectTraversal": False,
    }
    assert res["posterHasLazy"] is True
    assert res["chipHasOfficialThumb"] is True
    assert res["afterFirstErrorSrc"] == "assets/images/games/valorant.svg"
    assert res["afterSecondErrorDisplay"] == "none"
    assert res["svgVisibleAdded"] is True
    assert res["cachedResolutionAfterFail"] == "assets/images/games/valorant.svg"
    assert res["cacheStats"]["size"] == 1
    assert res["dashHasRealMlbbThumb"] is True
    assert res["dashHasRealValThumb"] is True
    assert res["dashHasRealFcThumb"] is True
    assert res["guestHasNoEagerLoading"] is True
    assert res["guestHasAll3RealPosters"] is True


def test_dashboard_performance_not_degraded_with_artwork() -> None:
    app = create_app(
        config=AppConfig(app_mode="mock", secret_key="wave610-perf"),
        repository=MockDataStoreRepository(),
    )
    t0 = time.perf_counter()
    with app.test_client() as client:
        for ep in (
            "/api/v1/games?include_inactive=true",
            "/api/v1/tournaments",
            "/api/v1/teams",
            "/api/v1/users",
            "/api/v1/tournaments/33333333-3333-4333-8333-333333333301/reports",
        ):
            r = client.get(ep, headers={"X-Mock-Role": "super_admin"})
            assert r.status_code == 200
            assert len(r.get_json()["data"]) >= 1
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0
