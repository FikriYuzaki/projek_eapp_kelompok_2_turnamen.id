"""Unit and integration tests for Supabase Auth PASSWORD_RECOVERY flow."""

from __future__ import annotations

import base64
import json
import logging
import shutil
import subprocess
from typing import Any

import pytest

from backend.app import create_app
from backend.core.config import ROOT_DIR, AppConfig
from backend.core.exceptions import (
    DomainForbiddenError,
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.core.logging_config import SecretRedactingFilter, redact_sensitive_text
from backend.modules.auth.service import AuthService
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from backend.repositories.supabase.supabase_repository import SupabaseDataStoreRepository
from desktop.bridge.eel_bridge import _normalize_and_validate_endpoint


def _make_jwt(payload: dict[str, Any]) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode("ascii").rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    return f"{header}.{body}.sig_test_123"


class _FakeUserObj:
    def __init__(self, user_id: str, email: str) -> None:
        self.id = user_id
        self.email = email


class _FakeSessionObj:
    def __init__(self, access_token: str, refresh_token: str = "ref_123") -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token


class _FakeAuthResponse:
    def __init__(
        self,
        *,
        user: _FakeUserObj | None = None,
        session: _FakeSessionObj | None = None,
    ) -> None:
        self.user = user
        self.session = session


class _FakeTableQuery:
    def __init__(self, engine: _FakeSupabaseEngine, table_name: str) -> None:
        self._engine = engine
        self._table = table_name
        self._op = "select"
        self._filters: list[tuple[str, Any]] = []

    def select(self, _cols: str = "*") -> _FakeTableQuery:
        self._op = "select"
        return self

    def insert(self, payload: Any) -> _FakeTableQuery:
        self._engine.mutations.append((self._table, "insert", payload))
        self._op = "insert"
        return self

    def update(self, payload: Any) -> _FakeTableQuery:
        self._engine.mutations.append((self._table, "update", payload))
        self._op = "update"
        return self

    def eq(self, key: str, value: Any) -> _FakeTableQuery:
        self._filters.append((key, value))
        return self

    def limit(self, _count: int) -> _FakeTableQuery:
        return self

    def execute(self) -> Any:
        if self._op != "select":
            raise AssertionError(f"Unexpected mutation on {self._table}: {self._op}")
        rows = list(self._engine.profiles)
        for key, value in self._filters:
            rows = [r for r in rows if r.get(key) == value]

        class _Resp:
            def __init__(self, data: list[dict[str, Any]]) -> None:
                self.data = data

        return _Resp(rows)


class _FakeAuthClient:
    def __init__(self, engine: _FakeSupabaseEngine, access_token: str | None = None) -> None:
        self._engine = engine
        self._access_token = access_token
        self._session_access_token: str | None = None

    def reset_password_for_email(self, email: str, options: dict[str, Any] | None = None) -> None:
        self._engine.recovery_requests.append({"email": email, "options": dict(options or {})})

    def get_user(self, jwt: str | None = None) -> _FakeAuthResponse:
        tok = jwt or self._access_token or ""
        if tok == "expired-jwt-token" or tok == self._engine.expired_token:
            raise Exception("JWT expired")
        if tok == self._engine.valid_recovery_token:
            return _FakeAuthResponse(
                user=_FakeUserObj(self._engine.auth_user_id, "admin@example.com")
            )
        raise Exception("Invalid JWT")

    def set_session(self, access_token: str, refresh_token: str = "") -> _FakeAuthResponse:
        if access_token == self._engine.expired_token:
            raise Exception("Token has expired or is invalid")
        self._engine.set_session_calls.append(
            {"access_token": access_token, "refresh_token": refresh_token}
        )
        self._session_access_token = access_token
        return _FakeAuthResponse(
            user=_FakeUserObj(self._engine.auth_user_id, "admin@example.com"),
            session=_FakeSessionObj(access_token, refresh_token),
        )

    def verify_otp(self, params: dict[str, Any]) -> _FakeAuthResponse:
        if params.get("token_hash") != "valid-token-hash" or params.get("type") != "recovery":
            raise Exception("Token hash invalid or expired")
        self._engine.verify_otp_calls.append(dict(params))
        self._session_access_token = self._engine.valid_recovery_token
        return _FakeAuthResponse(
            user=_FakeUserObj(self._engine.auth_user_id, "admin@example.com"),
            session=_FakeSessionObj(self._engine.valid_recovery_token),
        )

    def update_user(self, attributes: dict[str, Any]) -> _FakeAuthResponse:
        if not self._session_access_token:
            raise Exception("Auth session missing!")
        self._engine.update_user_calls.append(dict(attributes))
        return _FakeAuthResponse(
            user=_FakeUserObj(self._engine.auth_user_id, "admin@example.com")
        )


class _FakeSupabaseClient:
    def __init__(self, engine: _FakeSupabaseEngine, access_token: str | None = None) -> None:
        self.auth = _FakeAuthClient(engine, access_token=access_token)
        self._engine = engine

    def table(self, name: str) -> _FakeTableQuery:
        return _FakeTableQuery(self._engine, name)


class _FakeSupabaseEngine:
    def __init__(self) -> None:
        self.auth_user_id = "abc811ac-a57a-4d63-8c90-92280e4962c4"
        self.profile_id = "11111111-1111-4111-8111-111111111101"
        self.valid_recovery_token = _make_jwt(
            {"sub": self.auth_user_id, "role": "authenticated", "exp": 4000000000}
        )
        self.expired_token = _make_jwt(
            {"sub": self.auth_user_id, "role": "authenticated", "exp": 1000}
        )
        self.profiles = [
            {
                "id": self.profile_id,
                "auth_user_id": self.auth_user_id,
                "email": "admin@example.com",
                "username": "superadmin",
                "full_name": "Super Admin",
                "role": "super_admin",
                "is_active": True,
            }
        ]
        self.recovery_requests: list[dict[str, Any]] = []
        self.set_session_calls: list[dict[str, Any]] = []
        self.verify_otp_calls: list[dict[str, Any]] = []
        self.update_user_calls: list[dict[str, Any]] = []
        self.mutations: list[tuple[str, str, Any]] = []

    def client_factory(
        self, _cfg: AppConfig, access_token: str | None = None
    ) -> _FakeSupabaseClient:
        return _FakeSupabaseClient(self, access_token=access_token)


def _supabase_test_config() -> AppConfig:
    return AppConfig(
        app_mode="supabase",
        secret_key="test-flask-secret",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test_key_12345",
        eel_host="127.0.0.1",
        eel_port=8080,
        eel_start_page="index.html",
    )


def test_supabase_repository_password_recovery_and_update_user_without_profile_mutation() -> None:
    engine = _FakeSupabaseEngine()
    repo = SupabaseDataStoreRepository(
        _supabase_test_config(),
        client_factory=engine.client_factory,
    )

    req_result = repo.auth_request_password_recovery(
        "admin@example.com",
        redirect_to="http://127.0.0.1:8080/index.html",
    )
    assert req_result == {"recovery_requested": True}
    assert len(engine.recovery_requests) == 1
    assert engine.recovery_requests[0]["options"] == {
        "redirect_to": "http://127.0.0.1:8080/index.html"
    }

    upd_result = repo.auth_update_password(
        new_password="NewStrongPassword#2026",
        access_token=engine.valid_recovery_token,
        refresh_token="refresh_tok_1",
    )
    assert upd_result == {"auth_user_id": engine.auth_user_id, "password_updated": True}
    assert len(engine.set_session_calls) == 1
    assert engine.update_user_calls == [{"password": "NewStrongPassword#2026"}]
    assert engine.mutations == []


def test_supabase_repository_password_recovery_rejects_expired_and_token_hash_flow() -> None:
    engine = _FakeSupabaseEngine()
    repo = SupabaseDataStoreRepository(
        _supabase_test_config(),
        client_factory=engine.client_factory,
    )

    with pytest.raises(DomainUnauthorizedError):
        repo.auth_update_password(
            new_password="NewStrongPassword#2026",
            access_token=engine.expired_token,
        )

    with pytest.raises(DomainUnauthorizedError):
        repo.auth_update_password(
            new_password="NewStrongPassword#2026",
            access_token="tok_mock_token",
        )

    otp_res = repo.auth_update_password(
        new_password="OtpUpdatedPassword#2026",
        token_hash="valid-token-hash",
    )
    assert otp_res["password_updated"] is True
    assert engine.verify_otp_calls == [{"token_hash": "valid-token-hash", "type": "recovery"}]
    assert engine.update_user_calls[-1] == {"password": "OtpUpdatedPassword#2026"}
    assert engine.mutations == []


def test_auth_service_and_flask_endpoints_for_supabase_password_recovery() -> None:
    engine = _FakeSupabaseEngine()
    repo = SupabaseDataStoreRepository(
        _supabase_test_config(),
        client_factory=engine.client_factory,
    )
    app = create_app(config=_supabase_test_config(), repository=repo)
    client = app.test_client()

    # Reject external redirect_to
    bad_redirect = client.post(
        "/api/v1/auth/password-recovery",
        json={
            "email": "admin@example.com",
            "redirect_to": "https://evil.example.com/steal",
        },
    )
    assert bad_redirect.status_code == 400
    assert bad_redirect.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Accept localhost / 127.0.0.1 redirect
    ok_req = client.post(
        "/api/v1/auth/password-recovery",
        json={"email": "admin@example.com"},
    )
    assert ok_req.status_code == 200
    assert ok_req.get_json()["data"]["recovery_requested"] is True
    assert engine.recovery_requests[0]["options"] == {
        "redirect_to": "http://127.0.0.1:8080/index.html"
    }

    # Short password rejected before hitting GoTrue update_user()
    short_pw = client.post(
        "/api/v1/auth/password-recovery/update",
        headers={"Authorization": f"Bearer {engine.valid_recovery_token}"},
        json={"new_password": "123"},
    )
    assert short_pw.status_code == 400
    assert engine.update_user_calls == []

    # Valid PASSWORD_RECOVERY update calls update_user() and preserves role & profile untouched
    ok_upd = client.post(
        "/api/v1/auth/password-recovery/update",
        headers={"Authorization": f"Bearer {engine.valid_recovery_token}"},
        json={"new_password": "UpdatedSuperAdmin#2026", "refresh_token": "ref_abc"},
    )
    assert ok_upd.status_code == 200
    assert ok_upd.get_json()["data"] == {
        "password_updated": True,
        "auth_user_id": engine.auth_user_id,
    }
    assert engine.update_user_calls == [{"password": "UpdatedSuperAdmin#2026"}]
    assert engine.mutations == []
    assert engine.profiles[0]["role"] == "super_admin"
    assert engine.profiles[0]["auth_user_id"] == engine.auth_user_id


def test_auth_service_blocks_inactive_profile_on_recovery_update() -> None:
    engine = _FakeSupabaseEngine()
    engine.profiles[0]["is_active"] = False
    repo = SupabaseDataStoreRepository(
        _supabase_test_config(),
        client_factory=engine.client_factory,
    )
    service = AuthService(repo)

    with pytest.raises(DomainForbiddenError):
        service.complete_password_recovery(
            new_password="ValidNewPassword#2026",
            access_token=engine.valid_recovery_token,
        )
    assert engine.update_user_calls == []


def test_mock_mode_password_recovery_compatibility_and_bridge_endpoints() -> None:
    assert _normalize_and_validate_endpoint("/auth/password-recovery") == "/api/v1/auth/password-recovery"
    assert (
        _normalize_and_validate_endpoint("/auth/password-recovery/update")
        == "/api/v1/auth/password-recovery/update"
    )

    repo = MockDataStoreRepository()
    app = create_app(
        config=AppConfig(app_mode="mock", secret_key="mock-secret"),
        repository=repo,
    )
    client = app.test_client()

    health_mock = client.get("/api/v1/health").get_json()["data"]
    assert health_mock["supabase_host"] == ""

    sb_cfg = _supabase_test_config()
    assert sb_cfg.to_safe_dict()["supabase_host"] == "example.supabase.co"
    sb_engine = _FakeSupabaseEngine()
    sb_app = create_app(
        config=sb_cfg,
        repository=SupabaseDataStoreRepository(sb_cfg, client_factory=sb_engine.client_factory),
    )
    sb_health = sb_app.test_client().get("/api/v1/health").get_json()["data"]
    assert sb_health["supabase_host"] == "example.supabase.co"

    res = client.post(
        "/api/v1/auth/password-recovery",
        json={"email": "admin@turnamen.in"},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["mode"] == "mock"

    # Logging redaction sanity check for recovery fields
    raw_log = (
        'POST /auth/password-recovery/update Authorization="Bearer eyJhbGciOiJIUzI1NiJ9.abcdef123456.sig123456" '
        'new_password="VerySecretPassword123" token_hash="hash_secret_val"'
    )
    redacted = redact_sensitive_text(raw_log)
    assert "VerySecretPassword123" not in redacted
    assert "eyJhbGciOiJIUzI1NiJ9" not in redacted

    record = logging.LogRecord("turnamen_in", logging.INFO, "", 0, raw_log, (), None)
    SecretRedactingFilter().filter(record)
    assert "VerySecretPassword123" not in record.getMessage()


def test_frontend_password_recovery_url_handler_and_api_client_behavior() -> None:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime is not available")

    js_dir = ROOT_DIR / "desktop" / "web" / "assets" / "js"
    # Syntax check both edited JS modules
    for rel in ("core/api-client.js", "pages/app-pages.js"):
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

const fetchCalls = [];
const replaceStateCalls = [];
const storageMap = new Map();
const elements = new Map();

function makeElement(id) {{
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

const mainContent = makeElement("main-content");
const fakeDocument = {{
  getElementById: (id) => makeElement(id),
  querySelector: () => null,
  querySelectorAll: () => [],
  createElement: (tag) => makeElement(`dyn_${{tag}}_${{elements.size}}`),
  addEventListener: () => {{}},
}};

const fakeLocation = {{
  protocol: "http:",
  hostname: "127.0.0.1",
  port: "8080",
  origin: "http://127.0.0.1:8080",
  pathname: "/index.html",
  search: "",
  hash: "#access_token=jwt.recovery.token&refresh_token=ref_tok_9&type=recovery",
  href: "http://127.0.0.1:8080/index.html#access_token=jwt.recovery.token&refresh_token=ref_tok_9&type=recovery",
}};

const sandbox = {{
  window: null,
  document: fakeDocument,
  localStorage: {{
    getItem: (k) => (storageMap.has(k) ? storageMap.get(k) : null),
    setItem: (k, v) => storageMap.set(k, String(v)),
    removeItem: (k) => storageMap.delete(k),
  }},
  location: fakeLocation,
  history: {{
    replaceState: (_s, _t, url) => replaceStateCalls.push(url),
  }},
  URL,
  URLSearchParams,
  fetch: async (url, options) => {{
    fetchCalls.push({{ url, options }});
    if (url.endsWith("/health")) {{
      return {{
        status: 200,
        ok: true,
        headers: {{ get: () => "application/json" }},
        text: async () => JSON.stringify({{
          success: true,
          data: {{
            app_mode: "supabase",
            is_simulation: false,
            supabase_host: "cfdsgxciodfkamskafwe.supabase.co",
            status: "healthy",
          }},
        }}),
      }};
    }}
    if (url.endsWith("/games")) {{
      return {{
        status: 200,
        ok: true,
        headers: {{ get: () => "application/json" }},
        text: async () => JSON.stringify({{ success: true, data: [] }}),
      }};
    }}
    if (url.endsWith("/auth/password-recovery/update")) {{
      return {{
        status: 200,
        ok: true,
        headers: {{ get: () => "application/json" }},
        text: async () => JSON.stringify({{
          success: true,
          message: "OK",
          data: {{ password_updated: true, auth_user_id: "abc811ac" }},
        }}),
      }};
    }}
    return {{
      status: 200,
      ok: true,
      headers: {{ get: () => "application/json" }},
      text: async () => JSON.stringify({{ success: true, data: {{}} }}),
    }};
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
  await sandbox.TurnamenApp.initApp();
  const rendered = mainContent.innerHTML;
  const parsedImplicit = sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
    "http://127.0.0.1:8080/index.html#access_token=abc.def.ghi&refresh_token=r1&type=recovery"
  );
  const parsedHashOtp = sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
    "http://127.0.0.1:8080/index.html?token_hash=th_123&type=recovery"
  );
  const parsedSupabaseVerify = sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
    "https://cfdsgxciodfkamskafwe.supabase.co/auth/v1/verify?token=pkce_verify_tok_789&type=recovery&redirect_to=http%3A%2F%2F127.0.0.1%3A8080%2Findex.html"
  );
  const parsedSupabaseVerifyNoRedirect = sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
    "https://cfdsgxciodfkamskafwe.supabase.co/auth/v1/verify?token=hex_tok_456&type=recovery"
  );

  // Invalid / untrusted hosts, wrong paths, bad redirects, or non-recovery types
  const invalidUrls = {{
    spoofedSupabaseHost: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "https://attacker.supabase.co/auth/v1/verify?token=tok_evil&type=recovery&redirect_to=http://127.0.0.1:8080/index.html"
    ),
    arbitraryHost: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "https://evil.example.com/auth/v1/verify?token=tok_evil&type=recovery"
    ),
    wrongPath: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "https://cfdsgxciodfkamskafwe.supabase.co/auth/v1/authorize?token=tok_123&type=recovery"
    ),
    insecureHttpVerify: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "http://cfdsgxciodfkamskafwe.supabase.co/auth/v1/verify?token=tok_123&type=recovery"
    ),
    externalRedirectInVerify: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "https://cfdsgxciodfkamskafwe.supabase.co/auth/v1/verify?token=tok_123&type=recovery&redirect_to=https://evil.example.com/phish"
    ),
    externalCallbackHost: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "https://evil.example.com/index.html#access_token=abc.def.ghi&type=recovery"
    ),
    nonRecoveryVerifyType: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "https://cfdsgxciodfkamskafwe.supabase.co/auth/v1/verify?token=tok_123&type=signup"
    ),
    parsedNonRecovery: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "http://127.0.0.1:8080/index.html#access_token=abc.def.ghi&type=signup"
    ),
    missingTokenVerify: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "https://cfdsgxciodfkamskafwe.supabase.co/auth/v1/verify?type=recovery"
    ),
    bareTokenFragment: sandbox.TurnamenApp.parseSupabaseRecoveryUrl(
      "#token=tok_123&type=recovery"
    ),
  }};

  // Paste original Supabase verify URL into #recovery-url-paste -> clears input and submits token_hash
  const pasteInput = fakeDocument.getElementById("recovery-url-paste");
  pasteInput.value =
    "https://cfdsgxciodfkamskafwe.supabase.co/auth/v1/verify?token=pkce_verify_tok_789&type=recovery&redirect_to=http%3A%2F%2F127.0.0.1%3A8080%2Findex.html";
  await sandbox.TurnamenApp.handleRecoveryLinkPasteSubmit();
  const pasteInputClearedAfterRead = pasteInput.value === "";

  const newPwEl = fakeDocument.getElementById("recovery-new-password");
  const confirmPwEl = fakeDocument.getElementById("recovery-confirm-password");
  newPwEl.value = "UpdatedVerifyPassword#2026";
  confirmPwEl.value = "UpdatedVerifyPassword#2026";
  await sandbox.TurnamenApp.handleRecoveryUpdateSubmit();

  // Also test bearer update helper
  const updRes = await sandbox.TurnamenAPI.updatePasswordWithRecoveryToken(
    {{ accessToken: "jwt.recovery.token", refreshToken: "ref_tok_9" }},
    "StrongNewPassword#2026"
  );

  const updateCalls = fetchCalls.filter((c) => c.url.endsWith("/auth/password-recovery/update"));
  const pasteVerifyPayload = updateCalls[0] ? JSON.parse(updateCalls[0].options.body) : null;
  const bearerUpdateCall = updateCalls[1] || null;
  console.log(JSON.stringify({{
    replaceStateCalls,
    hasRecoveryUpdateHeading: rendered.includes("Atur Password Baru (PASSWORD_RECOVERY)"),
    hasForgotPasswordButton: rendered.includes('data-action="open-password-recovery"') && rendered.includes("Lupa password?"),
    recoveryUpdateHiddenRemoved: !rendered.includes('id="panel-auth-recovery-update"\\n            aria-label="Atur Password Baru"\\n            hidden'),
    parsedImplicit,
    parsedHashOtp,
    parsedSupabaseVerify,
    parsedSupabaseVerifyNoRedirect,
    invalidUrls,
    pasteInputClearedAfterRead,
    pasteVerifyPayload,
    newPwClearedAfterSubmit: newPwEl.value === "" && confirmPwEl.value === "",
    redirectUrl: sandbox.TurnamenApp.getDesktopRecoveryRedirectUrl(),
    updSuccess: updRes.success,
    updateAuthHeader: bearerUpdateCall ? bearerUpdateCall.options.headers.Authorization : null,
    storedSessionAfterRecovery: storageMap.get("turnamen.auth_session.v1") || null,
  }}));
}})().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    proc = subprocess.run(
        [node_bin, "-e", harness],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Node harness failed: {proc.stderr}"
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result["replaceStateCalls"] == ["/index.html"]
    assert result["hasRecoveryUpdateHeading"] is True
    assert result["hasForgotPasswordButton"] is True
    assert result["parsedImplicit"]["type"] == "recovery"
    assert result["parsedImplicit"]["accessToken"] == "abc.def.ghi"
    assert result["parsedHashOtp"]["tokenHash"] == "th_123"
    assert result["parsedSupabaseVerify"] == {
        "type": "recovery",
        "accessToken": "",
        "refreshToken": "",
        "tokenHash": "pkce_verify_tok_789",
    }
    assert result["parsedSupabaseVerifyNoRedirect"]["tokenHash"] == "hex_tok_456"
    assert all(val is None for val in result["invalidUrls"].values()), result["invalidUrls"]
    assert result["pasteInputClearedAfterRead"] is True
    assert result["pasteVerifyPayload"] == {
        "new_password": "UpdatedVerifyPassword#2026",
        "token_hash": "pkce_verify_tok_789",
    }
    assert result["newPwClearedAfterSubmit"] is True
    assert result["redirectUrl"] == "http://127.0.0.1:8080/index.html"
    assert result["updSuccess"] is True
    assert result["updateAuthHeader"] == "Bearer jwt.recovery.token"
    assert result["storedSessionAfterRecovery"] is None
