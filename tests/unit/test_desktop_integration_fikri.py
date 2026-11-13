"""Regression tests for Fikri's desktop launcher smoke checks, Eel bridge timeout handling,
and frontend API client registration session rules.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any
import pytest

from backend.app import create_app as real_create_app
from backend.core.config import AppConfig, ROOT_DIR, load_config
from backend.core.exceptions import DomainError
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from desktop.launcher import app_launcher
import run as run_entry

JS_CORE_DIR = ROOT_DIR / "desktop" / "web" / "assets" / "js" / "core"


def _run_js_harness(script_body: str) -> dict[str, Any]:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime is not available")

    harness = f"""
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const coreDir = {json.dumps(str(JS_CORE_DIR))};
const configCode = fs.readFileSync(path.join(coreDir, "config.js"), "utf8");
const bridgeCode = fs.readFileSync(path.join(coreDir, "eel-bridge.js"), "utf8");
const apiCode = fs.readFileSync(path.join(coreDir, "api-client.js"), "utf8");

function createEnv(customWindow = {{}}) {{
  const timers = [];
  const immediateTimeout = Boolean(customWindow.immediateTimeout);
  const sandboxWindow = {{
    location: {{ protocol: "http:", hostname: "127.0.0.1", port: "8080" }},
    console: {{ warn: () => {{}}, error: () => {{}}, log: () => {{}} }},
    URLSearchParams,
    AbortController,
    encodeURIComponent,
    setTimeout: (fn, ms) => {{
      const entry = {{ fn, ms, cleared: false }};
      timers.push(entry);
      if (immediateTimeout) {{
        Promise.resolve()
          .then(() => Promise.resolve())
          .then(() => Promise.resolve())
          .then(() => Promise.resolve())
          .then(() => {{
            if (!entry.cleared) {{
              entry.fn();
            }}
          }});
      }}
      return entry;
    }},
    clearTimeout: (entry) => {{
      if (entry) entry.cleared = true;
    }},
    ...customWindow,
  }};
  sandboxWindow.window = sandboxWindow;
  const ctx = vm.createContext(sandboxWindow);
  vm.runInContext(configCode, ctx);
  vm.runInContext(bridgeCode, ctx);
  vm.runInContext(apiCode, ctx);
  return {{ window: sandboxWindow, timers }};
}}

(async () => {{
  {script_body}
}})().then((res) => {{
  process.stdout.write(JSON.stringify(res));
}}).catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    proc = subprocess.run(
        [node_bin, "-e", harness],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return json.loads(proc.stdout)


def test_smoke_check_healthy_and_repository_healthy(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = load_config(overrides={"app_mode": "mock"})
    summary = app_launcher.run_smoke_check(cfg)

    assert summary["health_ok"] is True
    assert summary["repository_ok"] is True
    assert summary["games_count"] >= 3
    assert summary["tournaments_count"] >= 2
    assert "error" not in summary

    exit_code = run_entry.main(["--check", "--mode", "mock"])
    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["health_ok"] is True
    assert captured["repository_ok"] is True


def test_smoke_check_health_ok_but_games_query_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = load_config(
        overrides={
            "app_mode": "mock",
            "secret_key": "super_secret_ smoke_key_999",
        }
    )

    def _broken_create_app(config: AppConfig | None = None) -> Any:
        repo = MockDataStoreRepository()

        def _failing_list_games() -> list[dict[str, Any]]:
            raise DomainError(
                "Gagal membaca daftar game password=rahasia_db_123 Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig123456"
            )

        monkeypatch.setattr(repo, "list_games", _failing_list_games)
        return real_create_app(config=config, repository=repo)

    monkeypatch.setattr(app_launcher, "create_app", _broken_create_app)

    summary = app_launcher.run_smoke_check(cfg)
    assert summary["health_ok"] is True
    assert summary["repository_ok"] is False
    assert summary["games_count"] == 0
    assert "error" in summary
    assert "Query games gagal" in summary["error"]
    assert "rahasia_db_123" not in summary["error"]
    assert "sig123456" not in summary["error"]
    assert "***REDACTED***" in summary["error"]

    exit_code = run_entry.main(["--check", "--mode", "mock"])
    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["health_ok"] is True
    assert captured["repository_ok"] is False
    assert "rahasia_db_123" not in captured["error"]


def test_smoke_check_health_ok_but_tournaments_query_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = load_config(overrides={"app_mode": "mock"})

    def _broken_create_app(config: AppConfig | None = None) -> Any:
        repo = MockDataStoreRepository()

        def _failing_list_tournaments(
            status: str | None = None,
            game_id: str | None = None,
        ) -> list[dict[str, Any]]:
            raise RuntimeError("Koneksi tabel tournaments gagal: apikey=my_secret_apikey_777")

        monkeypatch.setattr(repo, "list_tournaments", _failing_list_tournaments)
        return real_create_app(config=config, repository=repo)

    monkeypatch.setattr(app_launcher, "create_app", _broken_create_app)

    summary = app_launcher.run_smoke_check(cfg)
    assert summary["health_ok"] is True
    assert summary["repository_ok"] is False
    assert summary["games_count"] >= 3
    assert summary["tournaments_count"] == 0
    assert "error" in summary
    assert "Query tournaments gagal" in summary["error"]
    assert "my_secret_apikey_777" not in summary["error"]
    assert "***REDACTED***" in summary["error"]

    exit_code = run_entry.main(["--check", "--mode", "mock"])
    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["health_ok"] is True
    assert captured["repository_ok"] is False
    assert "my_secret_apikey_777" not in captured["error"]


def test_smoke_check_rejects_non_list_query_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(overrides={"app_mode": "mock"})

    def _non_list_create_app(config: AppConfig | None = None) -> Any:
        app = real_create_app(config=config, fresh_mock=True)
        app.view_functions["api_v1.list_games"] = lambda: (
            {"success": True, "message": "OK", "data": {"unexpected": "dict"}},
            200,
        )
        return app

    monkeypatch.setattr(app_launcher, "create_app", _non_list_create_app)
    summary = app_launcher.run_smoke_check(cfg)
    assert summary["health_ok"] is True
    assert summary["repository_ok"] is False
    assert summary["games_count"] == 0
    assert "list yang valid" in summary["error"]


def test_smoke_check_repository_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = load_config(overrides={"app_mode": "mock"})

    def _no_repo_create_app(config: AppConfig | None = None) -> Any:
        app = real_create_app(config=config, fresh_mock=True)
        app.config["TURNAMEN_REPO"] = None
        return app

    monkeypatch.setattr(app_launcher, "create_app", _no_repo_create_app)

    summary = app_launcher.run_smoke_check(cfg)
    assert summary["health_ok"] is True
    assert summary["repository_ok"] is False
    assert summary["games_count"] == 0
    assert summary["tournaments_count"] == 0
    assert "Repository tidak tersedia" in summary["error"]

    exit_code = run_entry.main(["--check", "--mode", "mock"])
    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["health_ok"] is True
    assert captured["repository_ok"] is False


def test_smoke_check_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    invalid_cfg = AppConfig(
        app_mode="supabase",
        api_host="0.0.0.0",
        supabase_url="",
        supabase_anon_key="secret_anon_token_value_12345",
    )
    summary = app_launcher.run_smoke_check(invalid_cfg)
    assert summary["health_ok"] is False
    assert summary["repository_ok"] is False
    assert summary["games_count"] == 0
    assert summary["tournaments_count"] == 0
    assert "error" in summary
    assert "secret_anon_token_value_12345" not in summary["error"]

    def _raise_invalid_config(overrides: dict[str, object] | None = None) -> AppConfig:
        raise ValueError("Konfigurasi gagal untuk token=my_super_secret_token_999")

    monkeypatch.setattr(run_entry, "load_config", _raise_invalid_config)
    exit_code = run_entry.main(["--check"])
    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["health_ok"] is False
    assert captured["repository_ok"] is False
    assert "my_super_secret_token_999" not in captured["error"]
    assert "***REDACTED***" in captured["error"]


def test_frontend_register_email_confirmation_vs_mock_token() -> None:
    result = _run_js_harness(
        """
        // 1. Supabase mode registration requiring email confirmation (token: null)
        let fetchCalls = [];
        const envConfirm = createEnv({
          fetch: async (url, options) => {
            fetchCalls.push({ url, method: options.method });
            return {
              ok: true,
              status: 201,
              text: async () => JSON.stringify({
                success: true,
                message: "Registrasi akun berhasil",
                data: {
                  token: null,
                  requires_email_confirmation: true,
                  user: {
                    id: "u-pending-1",
                    email: "pending@turnamen.in",
                    username: "pending_user",
                    full_name: "Pending User",
                    role: "player",
                  },
                },
              }),
            };
          },
        });

        // Pre-populate an active session to verify unauthenticated registration clears it
        envConfirm.window.TurnamenConfig.setRuntimeInfo({ app_mode: "supabase", is_simulation: false });
        envConfirm.window.TurnamenConfig.setAuthSession("old_token_123", {
          id: "u-old",
          email: "old@turnamen.in",
          role: "player",
        });

        const confirmRes = await envConfirm.window.TurnamenAPI.register({
          email: "pending@turnamen.in",
          username: "pending_user",
          full_name: "Pending User",
          password: "password123",
          role: "player",
        });
        const stateAfterConfirm = envConfirm.window.TurnamenConfig.getState();

        // 2. Mock mode registration returning immediate valid token
        const envMock = createEnv({
          fetch: async () => ({
            ok: true,
            status: 201,
            text: async () => JSON.stringify({
              success: true,
              message: "Registrasi akun berhasil",
              data: {
                token: "tok_mock_valid_999",
                user: {
                  id: "u-mock-1",
                  email: "mock_new@turnamen.in",
                  username: "mock_new",
                  full_name: "Mock New User",
                  role: "team_captain",
                },
              },
            }),
          }),
        });

        const mockRes = await envMock.window.TurnamenAPI.register({
          email: "mock_new@turnamen.in",
          username: "mock_new",
          full_name: "Mock New User",
          password: "password123",
          role: "team_captain",
        });
        const stateAfterMock = envMock.window.TurnamenConfig.getState();

        // 3. Incomplete success payload (e.g. token without valid user, or token + requires_email_confirmation: true)
        const envIncomplete = createEnv({
          fetch: async () => ({
            ok: true,
            status: 201,
            text: async () => JSON.stringify({
              success: true,
              message: "Registrasi parsial",
              data: {
                token: "tok_should_not_persist",
                requires_email_confirmation: true,
                user: {},
              },
            }),
          }),
        });
        envIncomplete.window.TurnamenConfig.setRuntimeInfo({
          app_mode: "supabase",
          is_simulation: false,
        });
        envIncomplete.window.TurnamenConfig.setAuthSession("tok_prev", {
          id: "u-prev",
          email: "prev@turnamen.in",
          role: "player",
        });
        const incompleteRes = await envIncomplete.window.TurnamenAPI.register({
          email: "incomplete@turnamen.in",
        });
        const stateAfterIncomplete = envIncomplete.window.TurnamenConfig.getState();

        return {
          confirmRes,
          stateAfterConfirm,
          mockRes,
          stateAfterMock,
          incompleteRes,
          stateAfterIncomplete,
        };
        """
    )

    assert result["confirmRes"]["success"] is True
    assert result["confirmRes"]["data"]["requires_email_confirmation"] is True
    assert result["confirmRes"]["data"]["token"] is None
    assert result["stateAfterConfirm"]["token"] is None
    assert result["stateAfterConfirm"]["currentUser"] is None

    assert result["mockRes"]["success"] is True
    assert result["mockRes"]["data"]["requires_email_confirmation"] is False
    assert result["stateAfterMock"]["token"] == "tok_mock_valid_999"
    assert result["stateAfterMock"]["currentUser"]["email"] == "mock_new@turnamen.in"
    assert result["stateAfterMock"]["currentUser"]["role"] == "team_captain"

    assert result["incompleteRes"]["success"] is True
    assert result["incompleteRes"]["data"]["requires_email_confirmation"] is True
    assert result["incompleteRes"]["data"]["token"] is None
    assert result["stateAfterIncomplete"]["token"] is None
    assert result["stateAfterIncomplete"]["currentUser"] is None


def test_frontend_login_session_validation_and_cleanup() -> None:
    result = _run_js_harness(
        """
        function makeLoginEnv(responseBody, status = 200, appMode = "supabase") {
          const env = createEnv({
            fetch: async () => ({
              ok: status >= 200 && status < 300,
              status,
              text: async () => JSON.stringify(responseBody),
            }),
          });
          env.window.TurnamenConfig.setRuntimeInfo({
            app_mode: appMode,
            is_simulation: appMode === "mock",
          });
          env.window.TurnamenConfig.setAuthSession("existing_token_abc", {
            id: "u-existing-1",
            email: "existing@turnamen.in",
            username: "existing_user",
            role: "organizer",
          });
          return env;
        }

        // 1. Login sukses dengan token dan user valid -> session dibuat
        const envValid = makeLoginEnv({
          success: true,
          message: "Login berhasil",
          data: {
            token: "tok_new_valid_777",
            user: {
              id: "u-new-777",
              email: "new777@turnamen.in",
              username: "new777",
              role: "team_captain",
            },
          },
        });
        const validRes = await envValid.window.TurnamenAPI.login("new777@turnamen.in", "pass123");
        const stateAfterValid = envValid.window.TurnamenConfig.getState();

        // 2. Login sukses dengan token kosong -> session lama dibersihkan (tanpa panggilan setAuthSession redundan)
        const envEmptyToken = makeLoginEnv({
          success: true,
          message: "Login dengan token kosong",
          data: {
            token: "   ",
            user: {
              id: "u-new-777",
              email: "new777@turnamen.in",
            },
          },
        });
        let clearCalls = 0;
        let setCallsAfterInit = 0;
        const origClear = envEmptyToken.window.TurnamenConfig.clearAuthSession;
        const origSet = envEmptyToken.window.TurnamenConfig.setAuthSession;
        envEmptyToken.window.TurnamenConfig.clearAuthSession = function () {
          clearCalls += 1;
          return origClear.apply(this, arguments);
        };
        envEmptyToken.window.TurnamenConfig.setAuthSession = function () {
          setCallsAfterInit += 1;
          return origSet.apply(this, arguments);
        };
        const emptyTokenRes = await envEmptyToken.window.TurnamenAPI.login("new777@turnamen.in", "pass123");
        const stateAfterEmptyToken = envEmptyToken.window.TurnamenConfig.getState();

        // 3. Login sukses dengan user tanpa id/email -> session lama dibersihkan (juga uji konsistensi mode mock)
        const envInvalidUserSupabase = makeLoginEnv({
          success: true,
          message: "Login tanpa identitas user",
          data: {
            token: "tok_valid_but_no_user_identity",
            user: { username: "anonymous_only", role: "player" },
          },
        }, 200, "supabase");
        await envInvalidUserSupabase.window.TurnamenAPI.login("anon@turnamen.in", "pass123");
        const stateAfterInvalidUserSupabase = envInvalidUserSupabase.window.TurnamenConfig.getState();

        const envInvalidUserMock = makeLoginEnv({
          success: true,
          message: "Login tanpa identitas user (mock)",
          data: {
            token: "tok_valid_but_no_user_identity",
            user: { username: "anonymous_only" },
          },
        }, 200, "mock");
        await envInvalidUserMock.window.TurnamenAPI.login("anon@turnamen.in", "pass123");
        const stateAfterInvalidUserMock = envInvalidUserMock.window.TurnamenConfig.getState();

        // 4. Login sukses dengan data null atau objek tidak lengkap -> session lama dibersihkan
        const envNullData = makeLoginEnv({
          success: true,
          message: "Data null",
          data: null,
        });
        await envNullData.window.TurnamenAPI.login("null@turnamen.in", "pass123");
        const stateAfterNullData = envNullData.window.TurnamenConfig.getState();

        const envIncompleteData = makeLoginEnv({
          success: true,
          message: "Data objek kosong",
          data: {},
        });
        await envIncompleteData.window.TurnamenAPI.login("empty@turnamen.in", "pass123");
        const stateAfterIncompleteData = envIncompleteData.window.TurnamenConfig.getState();

        // 5. Login gagal (success: false) -> session lama TIDAK diubah
        const envFailedLogin = makeLoginEnv({
          success: false,
          message: "Email atau password tidak sesuai.",
          error: { code: "UNAUTHORIZED", details: {} },
        }, 401);
        const failedLoginRes = await envFailedLogin.window.TurnamenAPI.login("wrong@turnamen.in", "wrong");
        const stateAfterFailedLogin = envFailedLogin.window.TurnamenConfig.getState();

        // 6. Konfirmasi email diperlukan (requires_email_confirmation: true) -> session tidak dibuat & sesi lama dibersihkan
        const envEmailConfirm = makeLoginEnv({
          success: true,
          message: "Verifikasi email diperlukan",
          data: {
            token: "tok_unverified_999",
            requires_email_confirmation: true,
            user: {
              id: "u-unverified",
              email: "unverified@turnamen.in",
              role: "player",
            },
          },
        });
        const emailConfirmRes = await envEmailConfirm.window.TurnamenAPI.login("unverified@turnamen.in", "pass123");
        const stateAfterEmailConfirm = envEmailConfirm.window.TurnamenConfig.getState();

        return {
          validRes,
          stateAfterValid,
          emptyTokenRes,
          stateAfterEmptyToken,
          clearCalls,
          setCallsAfterInit,
          stateAfterInvalidUserSupabase,
          stateAfterInvalidUserMock,
          stateAfterNullData,
          stateAfterIncompleteData,
          failedLoginRes,
          stateAfterFailedLogin,
          emailConfirmRes,
          stateAfterEmailConfirm,
        };
        """
    )

    assert result["validRes"]["success"] is True
    assert result["stateAfterValid"]["token"] == "tok_new_valid_777"
    assert result["stateAfterValid"]["currentUser"]["id"] == "u-new-777"
    assert result["stateAfterValid"]["currentUser"]["email"] == "new777@turnamen.in"

    assert result["emptyTokenRes"]["success"] is True
    assert result["emptyTokenRes"]["data"]["token"] is None
    assert result["stateAfterEmptyToken"]["token"] is None
    assert result["stateAfterEmptyToken"]["currentUser"] is None
    assert result["clearCalls"] == 1
    assert result["setCallsAfterInit"] == 0

    assert result["stateAfterInvalidUserSupabase"]["token"] is None
    assert result["stateAfterInvalidUserSupabase"]["currentUser"] is None

    assert result["stateAfterInvalidUserMock"]["token"] is None
    assert result["stateAfterInvalidUserMock"]["currentUser"]["id"] != "u-existing-1"
    assert result["stateAfterInvalidUserMock"]["currentUser"]["role"] == "player"

    assert result["stateAfterNullData"]["token"] is None
    assert result["stateAfterNullData"]["currentUser"] is None
    assert result["stateAfterIncompleteData"]["token"] is None
    assert result["stateAfterIncompleteData"]["currentUser"] is None

    assert result["failedLoginRes"]["success"] is False
    assert result["stateAfterFailedLogin"]["token"] == "existing_token_abc"
    assert result["stateAfterFailedLogin"]["currentUser"]["id"] == "u-existing-1"
    assert result["stateAfterFailedLogin"]["currentUser"]["email"] == "existing@turnamen.in"

    assert result["emailConfirmRes"]["success"] is True
    assert result["emailConfirmRes"]["data"]["token"] is None
    assert result["stateAfterEmailConfirm"]["token"] is None
    assert result["stateAfterEmailConfirm"]["currentUser"] is None


def test_bridge_timeout_and_mutation_retry_safety() -> None:
    result = _run_js_harness(
        """
        // 1. Bridge unavailable (!hasEel): proxyApiRequest returns null and HTTP fallback works for POST & GET
        let noEelFetchCalls = [];
        const envNoEel = createEnv({
          fetch: async (url, options) => {
            noEelFetchCalls.push({ url, method: options.method });
            return {
              ok: true,
              status: 200,
              text: async () => JSON.stringify({
                success: true,
                message: "OK",
                data: { via: "http_fallback" },
              }),
            };
          },
        });
        const directProxyNull = await envNoEel.window.TurnamenBridge.proxyApiRequest("GET", "/games");
        const noEelPostRes = await envNoEel.window.TurnamenAPI.createTournament({ title: "Cup" });

        // 2. Bridge available, timeout occurs on POST, PATCH, DELETE, and GET:
        // Must return structured BRIDGE_TIMEOUT and NEVER duplicate via HTTP fetch
        let timeoutFetchCalls = [];
        let eelCalls = [];
        const envTimeout = createEnv({
          immediateTimeout: true,
          eel: {
            eel_get_runtime_info: () => () => ({
              success: true,
              data: { app_mode: "mock", is_simulation: true },
            }),
            eel_api_request: (method, endpoint) => () => {
              eelCalls.push({ method, endpoint });
              return new Promise(() => {}); // Never settles; triggers timeout
            },
          },
          fetch: async (url, options) => {
            timeoutFetchCalls.push({ url, method: options.method });
            return {
              ok: true,
              status: 200,
              text: async () => JSON.stringify({ success: true, data: {} }),
            };
          },
        });

        const postTimeoutRes = await envTimeout.window.TurnamenAPI.createTournament({
          title: "Test Cup",
        });
        const patchTimeoutRes = await envTimeout.window.TurnamenAPI.updateTournament(
          "t-1",
          { title: "Updated" }
        );
        const deleteTimeoutRes = await envTimeout.window.TurnamenAPI.deleteTournament("t-1");
        const getTimeoutRes = await envTimeout.window.TurnamenAPI.getGames();

        // 3. Bridge available, non-timeout execution error:
        // GET is allowed to fall back to HTTP, while POST/PATCH/DELETE must NOT fall back to HTTP
        let execErrFetchCalls = [];
        const envExecErr = createEnv({
          eel: {
            eel_get_runtime_info: () => () => Promise.resolve({
              success: true,
              data: { app_mode: "mock", is_simulation: true },
            }),
            eel_api_request: () => () => Promise.reject(new Error("WebSocket disconnected")),
          },
          fetch: async (url, options) => {
            execErrFetchCalls.push({ url, method: options.method });
            return {
              ok: true,
              status: 200,
              text: async () => JSON.stringify({
                success: true,
                message: "Recovered via HTTP GET",
                data: [{ id: "g1" }],
              }),
            };
          },
        });

        const getFallbackRes = await envExecErr.window.TurnamenAPI.getGames();
        const postBlockedRes = await envExecErr.window.TurnamenAPI.createTeam({ name: "Garuda" });
        const allExecTimersCleared = envExecErr.timers.every((t) => t.cleared === true);

        // 4. Bridge returns null during mutation -> BRIDGE_UNCERTAIN_STATE (no HTTP retry, no cancellation claim)
        let uncertainFetchCalls = [];
        const envUncertain = createEnv({
          eel: {
            eel_get_runtime_info: () => () => Promise.resolve({
              success: true,
              data: { app_mode: "mock", is_simulation: true },
            }),
            eel_api_request: () => () => Promise.resolve(null),
          },
          fetch: async (url, options) => {
            uncertainFetchCalls.push({ url, method: options.method });
            return {
              ok: true,
              status: 200,
              text: async () => JSON.stringify({ success: true, data: {} }),
            };
          },
        });
        envUncertain.window.TurnamenBridge.proxyApiRequest = async () => null;
        const uncertainPostRes = await envUncertain.window.TurnamenAPI.createTeam({ name: "Alpha" });

        return {
          directProxyNull,
          noEelFetchCount: noEelFetchCalls.length,
          noEelPostRes,
          eelCallsCount: eelCalls.length,
          timeoutFetchCount: timeoutFetchCalls.length,
          postTimeoutRes,
          patchTimeoutRes,
          deleteTimeoutRes,
          getTimeoutRes,
          execErrFetchCalls,
          getFallbackRes,
          postBlockedRes,
          allExecTimersCleared,
          uncertainFetchCount: uncertainFetchCalls.length,
          uncertainPostRes,
        };
        """
    )

    assert result["directProxyNull"] is None
    assert result["noEelFetchCount"] == 1
    assert result["noEelPostRes"]["success"] is True

    assert result["eelCallsCount"] == 4
    assert result["timeoutFetchCount"] == 0

    for key in ("postTimeoutRes", "patchTimeoutRes", "deleteTimeoutRes", "getTimeoutRes"):
        res = result[key]
        assert res["success"] is False
        assert res["error"]["code"] == "BRIDGE_TIMEOUT"
        assert "mungkin masih berjalan" in res["message"]
        assert "dibatalkan" not in res["message"].lower()

    assert len(result["execErrFetchCalls"]) == 1
    assert result["execErrFetchCalls"][0]["method"] == "GET"
    assert result["getFallbackRes"]["success"] is True
    assert result["allExecTimersCleared"] is True

    assert result["postBlockedRes"]["success"] is False
    assert result["postBlockedRes"]["error"]["code"] == "BRIDGE_EXECUTION_ERROR"

    assert result["uncertainFetchCount"] == 0
    assert result["uncertainPostRes"]["success"] is False
    assert result["uncertainPostRes"]["error"]["code"] == "BRIDGE_UNCERTAIN_STATE"
    assert "dibatalkan" not in result["uncertainPostRes"]["message"].lower()
