"""Wave 6.11 Custom Game Artwork Management Tests (Backend, Storage Security, Rollback & Cross-Page UI)."""

from __future__ import annotations

import base64
import io
import json
import shutil
import struct
import subprocess
import time
import zlib

import pytest

from backend.app import create_app
from backend.core.config import ROOT_DIR, AppConfig
from backend.core.exceptions import DomainForbiddenError, DomainValidationError
from backend.repositories.mock.mock_data import build_initial_mock_store
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
from backend.modules.tournaments.artwork_validator import MAX_GAME_ARTWORK_BYTES

JS_DIR = ROOT_DIR / "desktop" / "web" / "assets" / "js"
MLBB_GAME_ID = "22222222-2222-4222-8222-222222222201"
VAL_GAME_ID = "22222222-2222-4222-8222-222222222202"
FC_GAME_ID = "22222222-2222-4222-8222-222222222203"


def _make_valid_png(width: int = 640, height: int = 360) -> bytes:
    """Build a minimal valid PNG binary with exact IHDR dimensions."""
    def _chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_scanlines = b"".join(b"\x00" + (b"\x00\x20\x40" * 1) for _ in range(1))
    # Minimal valid PNG for header/signature + IHDR inspection and browser tests
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw_scanlines))
        + _chunk(b"IEND", b"")
    )


def _make_valid_jpeg(width: int = 1280, height: int = 720) -> bytes:
    """Build a minimal valid JPEG binary with SOF0 dimensions."""
    sof0_payload = struct.pack(">BHHB", 8, height, width, 1) + b"\x01\x11\x00"
    sof0_seg = b"\xff\xc0" + struct.pack(">H", len(sof0_payload) + 2) + sof0_payload
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + sof0_seg + b"\xff\xd9"


def _make_valid_webp(width: int = 1280, height: int = 720) -> bytes:
    """Build a valid WebP VP8X container with exact dimensions."""
    w_m1 = (width - 1).to_bytes(3, "little")
    h_m1 = (height - 1).to_bytes(3, "little")
    vp8x_data = b"\x00\x00\x00\x00" + w_m1 + h_m1
    riff_size = 4 + 8 + len(vp8x_data)
    return b"RIFF" + struct.pack("<I", riff_size) + b"WEBP" + b"VP8X" + struct.pack("<I", len(vp8x_data)) + vp8x_data


def _make_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"


def test_super_admin_upload_replace_restore_and_rbac_enforcement() -> None:
    repo = MockDataStoreRepository()
    app = create_app(config=AppConfig(app_mode="mock", secret_key="w611-test"), repository=repo)

    png_bytes = _make_valid_png(640, 360)
    jpeg_bytes = _make_valid_jpeg(1280, 720)
    webp_bytes = _make_valid_webp(1280, 720)

    with app.test_client() as client:
        # 1. Anonymous user must be rejected (401)
        anon_res = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            json={
                "filename": "poster.png",
                "content_type": "image/png",
                "image_base64": base64.b64encode(png_bytes).decode(),
            },
        )
        assert anon_res.status_code == 401

        # 2. Normal roles (player, organizer, committee, team_captain) must be rejected (403)
        for role_name in ("player", "organizer", "committee", "team_captain"):
            denied_res = client.post(
                f"/api/v1/games/{MLBB_GAME_ID}/artwork",
                headers={"X-Mock-Role": role_name},
                json={
                    "filename": "poster.png",
                    "content_type": "image/png",
                    "image_base64": base64.b64encode(png_bytes).decode(),
                },
            )
            assert denied_res.status_code == 403
            denied_del = client.delete(
                f"/api/v1/games/{MLBB_GAME_ID}/artwork",
                headers={"X-Mock-Role": role_name},
            )
            assert denied_del.status_code == 403

        # 3. Super Admin succeeds uploading PNG (using UUID object path, NOT user's filename)
        up1 = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers={"X-Mock-Role": "super_admin"},
            json={
                "filename": "My Cool Poster!!.png",
                "content_type": "image/png",
                "image_base64": base64.b64encode(png_bytes).decode(),
            },
        )
        assert up1.status_code == 200
        g1 = up1.get_json()["data"]
        assert g1["artwork_source"] == "custom"
        path1 = g1["custom_artwork_path"]
        url1 = g1["custom_artwork_url"]
        assert path1.startswith("mobile-legends/") and path1.endswith(".png")
        assert "My Cool Poster" not in path1
        assert url1 == f"/api/v1/games/artwork-assets/{path1}"
        assert g1["custom_artwork_width"] == 640
        assert g1["custom_artwork_height"] == 360

        # Asset route serves exact binary with Cache-Control immutable
        blob1 = client.get(url1)
        assert blob1.status_code == 200
        assert blob1.data == png_bytes
        assert blob1.mimetype == "image/png"

        # 4. Super Admin replaces with WebP via multipart upload -> unique new URL & old blob cleaned up
        up2 = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers={"X-Mock-Role": "super_admin"},
            data={"file": (io.BytesIO(webp_bytes), "updated.webp", "image/webp")},
            content_type="multipart/form-data",
        )
        assert up2.status_code == 200
        g2 = up2.get_json()["data"]
        path2 = g2["custom_artwork_path"]
        url2 = g2["custom_artwork_url"]
        assert path2 != path1 and url2 != url1
        assert g2["custom_artwork_mime_type"] == "image/webp"
        # Old blob must be removed after metadata succeeds
        assert client.get(url1).status_code == 404
        assert client.get(url2).status_code == 200

        # 5. Super Admin also works with JPEG
        up_fc = client.post(
            f"/api/v1/games/{FC_GAME_ID}/artwork",
            headers={"X-Mock-Role": "super_admin"},
            json={
                "filename": "fc-cover.jpg",
                "content_type": "image/jpeg",
                "image_base64": base64.b64encode(jpeg_bytes).decode(),
            },
        )
        assert up_fc.status_code == 200
        assert up_fc.get_json()["data"]["custom_artwork_mime_type"] == "image/jpeg"

        # 6. Restore official artwork deletes metadata & unused storage file cleanly
        rst = client.delete(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers={"X-Mock-Role": "super_admin"},
        )
        assert rst.status_code == 200
        g_restored = rst.get_json()["data"]
        assert g_restored["artwork_source"] == "official"
        assert g_restored["custom_artwork_url"] is None
        assert g_restored["custom_artwork_path"] is None
        assert client.get(url2).status_code == 404


def test_artwork_upload_rejects_oversized_spoofed_svg_and_executables() -> None:
    repo = MockDataStoreRepository()
    app = create_app(config=AppConfig(app_mode="mock", secret_key="w611-val"), repository=repo)
    valid_png = _make_valid_png(640, 360)

    with app.test_client() as client:
        headers = {"X-Mock-Role": "super_admin"}

        # Oversized > 5 MB rejected cleanly
        oversized = b"\x89PNG\r\n\x1a\n" + (b"0" * (MAX_GAME_ARTWORK_BYTES + 100))
        res_big = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers=headers,
            data={"file": (io.BytesIO(oversized), "huge.png", "image/png")},
            content_type="multipart/form-data",
        )
        assert res_big.status_code == 400

        # SVG disguised as .png rejected
        svg_payload = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        res_svg = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers=headers,
            data={"file": (io.BytesIO(svg_payload), "fake.png", "image/png")},
            content_type="multipart/form-data",
        )
        assert res_svg.status_code == 400

        # Windows PE/EXE disguised as .jpg rejected
        exe_payload = b"MZ\x90\x00" + b"\x00" * 128
        res_exe = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers=headers,
            json={
                "filename": "payload.jpg",
                "content_type": "image/jpeg",
                "image_base64": base64.b64encode(exe_payload).decode(),
            },
        )
        assert res_exe.status_code == 400

        # Extension/MIME mismatch (valid PNG signature declared as image/jpeg / .jpg) rejected
        res_spoof = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers=headers,
            json={
                "filename": "spoofed.jpg",
                "content_type": "image/jpeg",
                "image_base64": base64.b64encode(valid_png).decode(),
            },
        )
        assert res_spoof.status_code == 400

        # Too small dimensions (< 320x180) rejected
        tiny_png = _make_valid_png(120, 90)
        res_tiny = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers=headers,
            json={
                "filename": "tiny.png",
                "content_type": "image/png",
                "image_base64": base64.b64encode(tiny_png).decode(),
            },
        )
        assert res_tiny.status_code == 400


def test_upload_failure_and_metadata_rollback_cleanup_with_supabase_adapter() -> None:
    seed = build_initial_mock_store()
    seed["profiles"][0]["auth_user_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
    seed["profiles"][0]["is_active"] = True
    seed["game_artwork_overrides"] = []
    uploaded_objects: dict[str, bytes] = {}
    state_flags = {"fail_storage_upload": False, "fail_override_upsert": False, "missing_table": False}

    class _FakeResp:
        def __init__(self, data):
            self.data = data

    class _FakeStorageBucket:
        def upload(self, *, path: str, file: bytes, file_options=None):
            if state_flags["fail_storage_upload"]:
                raise RuntimeError("403 row-level security policy violation")
            uploaded_objects[path] = file
            return {"path": path}

        def remove(self, paths: list[str]):
            removed = []
            for p in paths:
                if p in uploaded_objects:
                    uploaded_objects.pop(p)
                    removed.append({"name": p})
            return removed

    class _FakeStorage:
        def from_(self, bucket: str):
            assert bucket == "game-artwork"
            return _FakeStorageBucket()

    class _FakeQuery:
        def __init__(self, table_name: str):
            self._table = table_name
            self._filters = []
            self._op = "select"
            self._payload = None

        def select(self, _cols: str = "*"):
            self._op = "select"
            return self

        def eq(self, key: str, value):
            self._filters.append((key, value))
            return self

        def limit(self, _n: int):
            return self

        def upsert(self, payload: dict, on_conflict: str = ""):
            self._op = "upsert"
            self._payload = dict(payload)
            return self

        def insert(self, payload: dict):
            self._op = "insert"
            self._payload = dict(payload)
            return self

        def delete(self):
            self._op = "delete"
            return self

        def execute(self):
            if self._table == "game_artwork_overrides" and state_flags["missing_table"]:
                err = RuntimeError("Could not find the table 'public.game_artwork_overrides' in the schema cache")
                err.code = "PGRST205"
                raise err
            rows = seed.get(self._table, [])
            if self._op == "select":
                out = [
                    r for r in rows
                    if all(r.get(k) == v for k, v in self._filters)
                ]
                return _FakeResp(out)
            if self._op == "upsert" and self._table == "game_artwork_overrides":
                if state_flags["fail_override_upsert"]:
                    raise RuntimeError("new row violates row-level security policy")
                rows[:] = [r for r in rows if r.get("game_id") != self._payload["game_id"]]
                rec = {"id": "ovr-1", "created_at": "2026-11-27T00:00:00Z", "updated_at": "2026-11-27T00:00:00Z", **self._payload}
                rows.append(rec)
                return _FakeResp([rec])
            if self._op == "delete" and self._table == "game_artwork_overrides":
                matched = [r for r in rows if all(r.get(k) == v for k, v in self._filters)]
                rows[:] = [r for r in rows if not all(r.get(k) == v for k, v in self._filters)]
                return _FakeResp(matched)
            if self._op == "insert":
                rows.append(self._payload)
                return _FakeResp([self._payload])
            return _FakeResp([])

    class _FakeAuth:
        def get_user(self, jwt: str | None = None):
            sub = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1" if jwt else None
            return type("Resp", (), {"user": type("U", (), {"id": sub})() if sub else None})()

    class _FakeClient:
        def __init__(self):
            self.storage = _FakeStorage()
            self.auth = _FakeAuth()

        def table(self, name: str):
            return _FakeQuery(name)

    tokens_seen = []
    cfg = AppConfig(
        app_mode="supabase",
        secret_key="w611-supa",
        supabase_url="https://cfdsgxciodfkamskafwe.supabase.co",
        supabase_publishable_key="sb_publishable_test_key",
    )
    repo = SupabaseDataStoreRepository(
        cfg,
        client_factory=lambda _cfg, access_token=None: (tokens_seen.append(access_token), _FakeClient())[1],
    )
    app = create_app(config=cfg, repository=repo)
    super_admin_jwt = _make_jwt({"sub": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1", "exp": 4000000000})
    valid_png = _make_valid_png(640, 360)

    with app.test_client() as client:
        # A. Graceful degrade when migration table is not yet on Cloud
        state_flags["missing_table"] = True
        list_before = client.get("/api/v1/games")
        assert list_before.status_code == 200
        assert all(g["custom_artwork_url"] is None for g in list_before.get_json()["data"])
        state_flags["missing_table"] = False

        # B. Fail-closed window (storage.objects policies not yet created): upload returns 403,
        #    writes nothing to metadata or storage, while GET /api/v1/games still serves official Wave 6.10 artwork.
        state_flags["fail_storage_upload"] = True
        res_up_fail = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers={"Authorization": f"Bearer {super_admin_jwt}"},
            json={"filename": "p.png", "content_type": "image/png", "image_base64": base64.b64encode(valid_png).decode()},
        )
        assert res_up_fail.status_code == 403
        assert len(uploaded_objects) == 0
        assert len(seed["game_artwork_overrides"]) == 0
        games_during_fail_closed = client.get("/api/v1/games")
        assert games_during_fail_closed.status_code == 200
        games_payload = games_during_fail_closed.get_json()["data"]
        assert len(games_payload) >= 3
        assert all(g["artwork_source"] == "official" and g["custom_artwork_url"] is None for g in games_payload)
        state_flags["fail_storage_upload"] = False

        # C. Metadata failure triggers orphan cleanup of uploaded object!
        state_flags["fail_override_upsert"] = True
        res_meta_fail = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers={"Authorization": f"Bearer {super_admin_jwt}"},
            json={"filename": "p.png", "content_type": "image/png", "image_base64": base64.b64encode(valid_png).decode()},
        )
        assert res_meta_fail.status_code == 500 or res_meta_fail.status_code == 403 or not res_meta_fail.get_json()["success"]
        assert len(uploaded_objects) == 0
        assert len(seed["game_artwork_overrides"]) == 0
        state_flags["fail_override_upsert"] = False

        # D. Valid upload uses caller's JWT and builds trusted Supabase Storage public URL
        res_ok = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers={"Authorization": f"Bearer {super_admin_jwt}"},
            json={"filename": "p.png", "content_type": "image/png", "image_base64": base64.b64encode(valid_png).decode()},
        )
        assert res_ok.status_code == 200
        body = res_ok.get_json()["data"]
        assert body["custom_artwork_url"].startswith(
            "https://cfdsgxciodfkamskafwe.supabase.co/storage/v1/object/public/game-artwork/mobile-legends/"
        )
        assert len(uploaded_objects) == 1
        assert super_admin_jwt in tokens_seen


def test_frontend_custom_artwork_ui_preview_cross_page_and_restore() -> None:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime is not available")

    for rel in ("core/api-client.js", "components/ui-components.js", "pages/app-pages.js"):
        syntax = subprocess.run([node_bin, "--check", str(JS_DIR / rel)], capture_output=True, text=True, check=False)
        assert syntax.returncode == 0, f"Syntax error in {rel}: {syntax.stderr}"

    seed_store = build_initial_mock_store()
    valid_png_b64 = base64.b64encode(_make_valid_png(640, 360)).decode()
    svg_b64 = base64.b64encode(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>").decode()

    harness = f"""
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const jsDir = {json.dumps(str(JS_DIR))};
const seedGames = {json.dumps(seed_store["games"])};
const seedTours = {json.dumps(seed_store["tournaments"])};
const seedTeams = {json.dumps(seed_store["teams"])};
const validPngBytes = Uint8Array.from(Buffer.from({json.dumps(valid_png_b64)}, "base64"));
const svgBytes = Uint8Array.from(Buffer.from({json.dumps(svg_b64)}, "base64"));

let activeCustomUrl = null;
let uploadCount = 0;

function currentGames() {{
  return seedGames.map((g) => {{
    if (g.id === {json.dumps(MLBB_GAME_ID)} && activeCustomUrl) {{
      return {{
        ...g,
        custom_artwork_path: "mobile-legends/custom-123.png",
        custom_artwork_url: activeCustomUrl,
        custom_artwork_width: 640,
        custom_artwork_height: 360,
        artwork_source: "custom",
      }};
    }}
    return {{ ...g, custom_artwork_url: null, artwork_source: "official" }};
  }});
}}

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
    style: {{}},
    set innerHTML(v) {{ _html = String(v || ""); }},
    get innerHTML() {{ return _html; }},
    setAttribute(k, v) {{ attrs[k] = String(v); }},
    getAttribute(k) {{ return k in attrs ? attrs[k] : null; }},
    classList: {{ add() {{}}, remove() {{}}, toggle() {{}}, contains: () => false }},
    appendChild() {{}},
    remove() {{}},
    addEventListener() {{}},
    removeEventListener() {{}},
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
    removeEventListener() {{}},
  }},
  localStorage: {{ getItem: () => null, setItem() {{}}, removeItem() {{}} }},
  sessionStorage: {{ getItem: () => null, setItem() {{}}, removeItem() {{}} }},
  location: {{ protocol: "http:", hostname: "127.0.0.1", port: "8080", origin: "http://127.0.0.1:8080", pathname: "/index.html", search: "", hash: "" }},
  history: {{ replaceState() {{}} }},
  URL,
  URLSearchParams,
  btoa: (str) => Buffer.from(str, "binary").toString("base64"),
  atob: (b64) => Buffer.from(b64, "base64").toString("binary"),
  fetch: async (url, init = {{}}) => {{
    const method = (init.method || "GET").toUpperCase();
    const jsonResp = (data, status = 200) => ({{
      status,
      ok: status >= 200 && status < 300,
      headers: {{ get: () => "application/json" }},
      text: async () => JSON.stringify({{ success: status < 400, message: "OK", data }}),
    }});
    if (url.includes(`/games/{MLBB_GAME_ID}/artwork`) && method === "POST") {{
      uploadCount += 1;
      activeCustomUrl = `https://cfdsgxciodfkamskafwe.supabase.co/storage/v1/object/public/game-artwork/mobile-legends/custom-${{uploadCount}}.png`;
      return jsonResp(currentGames()[0]);
    }}
    if (url.includes(`/games/{MLBB_GAME_ID}/artwork`) && method === "DELETE") {{
      activeCustomUrl = null;
      return jsonResp(currentGames()[0]);
    }}
    if (url.includes("/games")) return jsonResp(currentGames());
    if (url.includes("/tournaments/") && url.includes("/reports")) {{
      return jsonResp({{ tournament: seedTours[0], summary: {{ completed_matches: 1, total_matches: 2, completion_percentage: 50 }}, standings: [], recent_activity: [] }});
    }}
    if (url.includes("/tournaments/") && url.includes("/matches")) return jsonResp({{ matches: [] }});
    if (url.includes("/tournaments/") && url.includes("/registrations")) return jsonResp([]);
    if (url.includes("/tournaments/") && url.includes("/announcements")) return jsonResp([]);
    if (url.includes(`/tournaments/${{seedTours[0].id}}`)) return jsonResp({{ ...seedTours[0], game_name: seedGames[0].name }});
    if (url.endsWith("/tournaments")) return jsonResp(seedTours.map((t) => ({{ ...t, game_name: seedGames.find((g) => g.id === t.game_id)?.name || "Game" }})));
    if (url.endsWith("/teams")) return jsonResp(seedTeams.map((tm) => ({{ ...tm, game_name: seedGames.find((g) => g.id === tm.game_id)?.name || "Game" }})));
    if (url.endsWith("/users")) return jsonResp([{{ id: "u1", email: "admin@turnamen.in", username: "superadmin", full_name: "Super Admin", role: "super_admin", is_auth_linked: true }}]);
    return jsonResp({{}});
  }},
  console,
  setTimeout,
  clearTimeout,
}};
sandbox.window = sandbox;
vm.createContext(sandbox);
for (const rel of ["core/config.js", "core/eel-bridge.js", "core/api-client.js", "components/ui-components.js", "pages/app-pages.js"]) {{
  vm.runInContext(fs.readFileSync(path.join(jsDir, rel), "utf8"), sandbox);
}}

(async () => {{
  const app = sandbox.TurnamenApp;
  const ui = sandbox.TurnamenUI;
  const cfg = sandbox.TurnamenConfig;

  // 1. Non-super_admin cannot open Manajemen Game (Access Denied)
  cfg.setSimulatedRole("player");
  await app.navigateTo("game-management");
  const playerBlocked = makeEl("main-content").innerHTML.includes("Akses Halaman Manajemen Game Ditolak");

  // 2. Super Admin opens Manajemen Game -> sees active poster & Ganti Poster
  cfg.setSimulatedRole("super_admin");
  await app.navigateTo("game-management");
  const initialMgmtHtml = makeEl("main-content").innerHTML;
  const hasControls =
    initialMgmtHtml.includes("Ganti Poster") &&
    initialMgmtHtml.includes("Simpan Poster") &&
    initialMgmtHtml.includes("akmweb.youngjoygame.com");

  // 3. Invalid SVG file disguised as .png fails preview preparation cleanly
  let fakeSvgRejected = false;
  try {{
    await app.inspectAndPrepareArtworkFile({{
      name: "evil.png",
      type: "image/png",
      size: svgBytes.length,
      arrayBuffer: async () => svgBytes.buffer.slice(svgBytes.byteOffset, svgBytes.byteOffset + svgBytes.byteLength),
    }});
  }} catch (_err) {{
    fakeSvgRejected = true;
  }}

  // 4. Valid PNG selection updates preview before saving
  await app.handleArtworkFileInputChange({{
    getAttribute: (k) => (k === "data-id" ? {json.dumps(MLBB_GAME_ID)} : ""),
    files: [{{
      name: "new-mlbb.png",
      type: "image/png",
      size: validPngBytes.length,
      arrayBuffer: async () => validPngBytes.buffer.slice(validPngBytes.byteOffset, validPngBytes.byteOffset + validPngBytes.byteLength),
    }}],
  }});
  const previewHtml = makeEl("main-content").innerHTML;
  const hasPreviewBeforeSave =
    previewHtml.includes("Preview Poster Baru") &&
    previewHtml.includes("new-mlbb.png") &&
    previewHtml.includes("data:image/png;base64,");

  // 5. Saving updates poster across Manajemen Game, Super Admin Dashboard, Guest/Player Dashboard, Tournament List, Detail, Team Management
  await app.saveGameArtworkDraft({json.dumps(MLBB_GAME_ID)});
  const mgmtAfterSave = makeEl("main-content").innerHTML;
  const hasRestoreBtnAfterSave = mgmtAfterSave.includes("Kembalikan Artwork Resmi");

  await app.navigateTo("dashboard");
  const saDashHtml = makeEl("main-content").innerHTML;

  await app.navigateTo("tournament-list");
  const listHtml = makeEl("main-content").innerHTML;

  await app.navigateTo("tournament-detail", {{ tournamentId: seedTours[0].id }});
  const detailHtml = makeEl("main-content").innerHTML;

  await app.navigateTo("team-management");
  const teamHtml = makeEl("main-content").innerHTML;

  cfg.setSimulatedRole("player");
  await app.navigateTo("dashboard");
  const playerDashHtml = makeEl("main-content").innerHTML;

  // 6. Cache update + fallback back to Wave 6.10 when custom URL fails
  ui.clearArtworkCache();
  const customUrl = activeCustomUrl;
  const resolvedCustom = ui.resolveGameArtwork({{ id: {json.dumps(MLBB_GAME_ID)}, slug: "mobile-legends", custom_artwork_url: customUrl }});
  ui.handleArtworkError({{
    attrs: {{ "data-primary-src": customUrl, src: customUrl }},
    src: customUrl,
    dataset: {{}},
    style: {{}},
    getAttribute(k) {{ return this.attrs[k] || ""; }},
    setAttribute(k, v) {{ this.attrs[k] = v; }},
  }}, resolvedCustom.fallbackSrc);
  const resolvedAfterFail = ui.resolveGameArtwork({{ id: {json.dumps(MLBB_GAME_ID)}, slug: "mobile-legends", custom_artwork_url: customUrl }});

  // 7. Super Admin opens confirm dialog & restores official Wave 6.10 artwork
  cfg.setSimulatedRole("super_admin");
  await app.navigateTo("game-management");
  app.openRestoreGameArtworkConfirm({json.dumps(MLBB_GAME_ID)});
  const confirmModalShown = makeEl("app-modal-body").innerHTML.includes("Kembalikan") || makeEl("app-modal-footer").innerHTML.includes("submit-restore-game-artwork");
  await app.restoreGameArtworkConfirmed({json.dumps(MLBB_GAME_ID)});
  await app.navigateTo("tournament-detail", {{ tournamentId: seedTours[0].id }});
  const detailAfterRestoreHtml = makeEl("main-content").innerHTML;

  console.log(JSON.stringify({{
    playerBlocked,
    hasControls,
    fakeSvgRejected,
    hasPreviewBeforeSave,
    hasRestoreBtnAfterSave,
    saDashCustom: saDashHtml.includes(customUrl),
    listCustom: listHtml.includes(customUrl),
    detailCustom: detailHtml.includes(customUrl),
    teamCustom: teamHtml.includes(customUrl),
    playerDashCustom: playerDashHtml.includes(customUrl),
    fallbackBackToOfficialOnError: resolvedAfterFail.src.includes("akmweb.youngjoygame.com"),
    confirmModalShown,
    restoredToWave610Official: !detailAfterRestoreHtml.includes(customUrl) && detailAfterRestoreHtml.includes("akmweb.youngjoygame.com"),
  }}));
}})().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    proc = subprocess.run([node_bin, "-e", harness], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    res = json.loads(proc.stdout.strip().splitlines()[-1])
    assert res == {
        "playerBlocked": True,
        "hasControls": True,
        "fakeSvgRejected": True,
        "hasPreviewBeforeSave": True,
        "hasRestoreBtnAfterSave": True,
        "saDashCustom": True,
        "listCustom": True,
        "detailCustom": True,
        "teamCustom": True,
        "playerDashCustom": True,
        "fallbackBackToOfficialOnError": True,
        "confirmModalShown": True,
        "restoredToWave610Official": True,
    }


def test_dashboard_performance_stays_under_3_seconds_with_artwork_overrides() -> None:
    repo = MockDataStoreRepository()
    app = create_app(config=AppConfig(app_mode="mock", secret_key="w611-perf"), repository=repo)
    png_bytes = _make_valid_png(640, 360)
    with app.test_client() as client:
        up = client.post(
            f"/api/v1/games/{MLBB_GAME_ID}/artwork",
            headers={"X-Mock-Role": "super_admin"},
            json={"filename": "p.png", "content_type": "image/png", "image_base64": base64.b64encode(png_bytes).decode()},
        )
        assert up.status_code == 200
        t0 = time.perf_counter()
        for ep in (
            "/api/v1/games?include_inactive=true",
            "/api/v1/tournaments",
            "/api/v1/teams",
            "/api/v1/users",
            "/api/v1/tournaments/33333333-3333-4333-8333-333333333301/reports",
        ):
            resp = client.get(ep, headers={"X-Mock-Role": "super_admin"})
            assert resp.status_code == 200
        elapsed = time.perf_counter() - t0
    assert elapsed < 3.0
