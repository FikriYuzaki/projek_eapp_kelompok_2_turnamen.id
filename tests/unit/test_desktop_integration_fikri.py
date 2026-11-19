"""Regression tests for Fikri's desktop launcher smoke checks, Eel bridge timeout handling,
and frontend API client registration session rules.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any
import pytest
import requests

from backend.app import create_app as real_create_app
from backend.core.config import AppConfig, ROOT_DIR, load_config
from backend.core.exceptions import DomainError
from backend.repositories.mock.mock_repository import MockDataStoreRepository
from desktop.bridge import eel_bridge
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
    URL,
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


def test_eel_bridge_normalize_and_validate_endpoint() -> None:
    valid_cases = {
        "/health": "/api/v1/health",
        "health": "/api/v1/health",
        "/api/v1/health": "/api/v1/health",
        "/tournaments?status=ongoing&game_id=123": "/api/v1/tournaments?status=ongoing&game_id=123",
        "/games/mobile-legends": "/api/v1/games/mobile-legends",
    }
    for raw_ep, expected in valid_cases.items():
        assert eel_bridge._normalize_and_validate_endpoint(raw_ep) == expected

    invalid_cases: tuple[Any, ...] = (
        "",
        "   ",
        None,
        123,
        "/",
        "/api/v1",
        "/api/v1/",
        "/api/v1//",
        "/api/v1?x=1",
        "/api/v10/health",
        "/api/v1//health",
        "/../../",
        "/api/v1/../health",
        "/api/v1/./health",
        "/api/v1/%2e%2e/%2e%2e/index.html",
        "/api/v1/%2E%2E/%2E%2E/assets/js/core/config.js",
        "/api/v1/.%2e/%2e./index.html",
        "/api/v1/..%2f..%2findex.html",
        "/api/v1/..%5c..%5cindex.html",
        "/api/v1/%252e%252e/%252e%252e/index.html",
        "/api/v1/%252f..%252findex.html",
        "/api/v1/%255c..%255cindex.html",
        "/api/v1/%25%32%65%25%32%65/index.html",
        "/api/v1/%25252525252e/health",
        "/games/%2e%2e/auth/me",
        "/games/a%ZZb",
        "/health#fragment",
        "/health?a=1#frag",
        "/health\x00",
        "/health\r\nX-Injected: 1",
        "/health\tbar",
        "http://evil.example/api/v1/health",
        "//evil.example/health",
        "/health@evil.example",
        "\\api\\v1\\health",
    )
    for bad_ep in invalid_cases:
        assert eel_bridge._normalize_and_validate_endpoint(bad_ep) is None, f"Should reject {bad_ep!r}"


def test_eel_bridge_sanitize_headers() -> None:
    raw_headers = {
        "authorization": "Bearer jwt_tok_123",
        "X-MOCK-ROLE": "organizer",
        "x-mock-user-id": "user-123",
        "Cookie": "session=evil",
        "Host": "evil.example",
        "X-Forwarded-For": "10.0.0.1",
        "Accept": "application/json\r\nX-Bad: 1",
        "Content-Type": "application/json",
    }

    mock_sanitized = eel_bridge._sanitize_headers(raw_headers, is_mock_mode=True)
    assert mock_sanitized["Authorization"] == "Bearer jwt_tok_123"
    assert mock_sanitized["X-Mock-Role"] == "organizer"
    assert mock_sanitized["X-Mock-User-Id"] == "user-123"
    assert mock_sanitized["Accept"] == "application/json"
    assert "Cookie" not in mock_sanitized
    assert "Host" not in mock_sanitized
    assert "X-Forwarded-For" not in mock_sanitized

    supa_sanitized = eel_bridge._sanitize_headers(raw_headers, is_mock_mode=False)
    assert supa_sanitized["Authorization"] == "Bearer jwt_tok_123"
    assert "X-Mock-Role" not in supa_sanitized
    assert "X-Mock-User-Id" not in supa_sanitized
    assert "Cookie" not in supa_sanitized


def test_eel_bridge_forward_api_request_blocks_traversal_redirects_and_env_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eel_bridge.close_bridge_sessions()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9999")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9999")
    monkeypatch.delenv("NO_PROXY", raising=False)

    cfg = load_config(overrides={"app_mode": "mock", "api_host": "127.0.0.1", "api_port": 5059})

    # Verify default requests.Session picks up env proxy whereas bridge session isolates it
    default_session = requests.Session()
    try:
        default_proxies = default_session.merge_environment_settings(
            "http://127.0.0.1:5059/api/v1/health", {}, None, None, None
        )["proxies"]
        assert "http" in default_proxies
    finally:
        default_session.close()

    recorded_calls: list[dict[str, Any]] = []

    class DummyResp:
        def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
            self.status_code = status_code
            self._payload = payload

        def json(self) -> dict[str, Any]:
            assert self._payload is not None
            return self._payload

    def fake_session_request(self: requests.Session, method: str, url: str, **kwargs: Any) -> DummyResp:
        env_proxies = self.merge_environment_settings(url, {}, None, None, None)["proxies"]
        recorded_calls.append(
            {
                "session": self,
                "trust_env": self.trust_env,
                "env_proxies": env_proxies,
                "method": method,
                "url": url,
                "kwargs": kwargs,
            }
        )
        if url.endswith("/redirect"):
            return DummyResp(302)
        return DummyResp(200, {"success": True, "message": "OK", "data": {"ok": True}})

    monkeypatch.setattr(requests.Session, "request", fake_session_request)

    try:
        # 1. Traversal payloads rejected BEFORE any session.request call
        for payload in (
            "/api/v1/%2e%2e/%2e%2e/index.html",
            "/api/v1/.%2e/health",
            "/api/v1/..%2findex.html",
            "/api/v1/..%5cindex.html",
            "/api/v1/%252e%252e/index.html",
        ):
            err = eel_bridge.forward_api_request(cfg, "GET", payload)
            assert err["success"] is False
            assert err["error"]["code"] == "BRIDGE_INVALID_ENDPOINT"
        assert len(recorded_calls) == 0

        # 2. Invalid host & invalid method checks
        bad_host_cfg = AppConfig(api_host="0.0.0.0")
        sec_err = eel_bridge.forward_api_request(bad_host_cfg, "GET", "/health")
        assert sec_err["error"]["code"] == "BRIDGE_SECURITY_ERROR"

        method_err = eel_bridge.forward_api_request(cfg, "TRACE", "/health")
        assert method_err["error"]["code"] == "BRIDGE_INVALID_METHOD"
        assert len(recorded_calls) == 0

        # 3. Valid calls reuse per-thread session with trust_env=False and allow_redirects=False
        ok1 = eel_bridge.forward_api_request(
            cfg, "GET", "/health", headers={"Authorization": "Bearer secret-jwt"}
        )
        ok2 = eel_bridge.forward_api_request(
            cfg, "POST", "/tournaments", payload={"title": "Cup"}
        )
        assert ok1["success"] is True
        assert ok2["success"] is True
        assert len(recorded_calls) == 2
        assert recorded_calls[0]["session"] is recorded_calls[1]["session"]
        assert recorded_calls[0]["trust_env"] is False
        assert recorded_calls[0]["env_proxies"] == {}
        assert recorded_calls[0]["kwargs"]["allow_redirects"] is False
        assert recorded_calls[1]["kwargs"]["allow_redirects"] is False

        # 4. 3xx redirect blocked cleanly without following external Location
        redir = eel_bridge.forward_api_request(
            cfg,
            "GET",
            "/redirect",
            headers={"Authorization": "Bearer secret-jwt"},
        )
        assert redir["success"] is False
        assert redir["error"]["code"] == "BRIDGE_REDIRECT_BLOCKED"
        assert redir["error"]["details"]["status_code"] == 302
    finally:
        prev_session = recorded_calls[0]["session"] if recorded_calls else None
        eel_bridge.close_bridge_sessions()
        if prev_session is not None:
            assert prev_session not in eel_bridge._ACTIVE_SESSIONS
            assert not hasattr(eel_bridge._SESSION_LOCAL, "session")


def test_wait_for_api_ready_disables_redirects_and_env_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9999")
    monkeypatch.delenv("NO_PROXY", raising=False)
    cfg = load_config(overrides={"app_mode": "mock", "api_host": "127.0.0.1", "api_port": 5060})

    observed: list[dict[str, Any]] = []
    mode_state = {"status": 302}

    class DummyResp:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

        def json(self) -> dict[str, Any]:
            return {"success": True, "data": {"status": "healthy"}}

    def fake_session_get(self: requests.Session, url: str, **kwargs: Any) -> DummyResp:
        observed.append(
            {
                "trust_env": self.trust_env,
                "proxies": self.merge_environment_settings(url, {}, None, None, None)["proxies"],
                "allow_redirects": kwargs.get("allow_redirects"),
            }
        )
        return DummyResp(mode_state["status"])

    monkeypatch.setattr(requests.Session, "get", fake_session_get)

    assert app_launcher.wait_for_api_ready(cfg, timeout=0.15, poll_interval=0.01) is False
    assert len(observed) >= 1
    assert all(entry["trust_env"] is False for entry in observed)
    assert all(entry["proxies"] == {} for entry in observed)
    assert all(entry["allow_redirects"] is False for entry in observed)

    observed.clear()
    mode_state["status"] = 200
    assert app_launcher.wait_for_api_ready(cfg, timeout=0.5, poll_interval=0.01) is True
    assert len(observed) == 1
    assert observed[0]["trust_env"] is False
    assert observed[0]["allow_redirects"] is False


def test_frontend_resolve_initial_api_base_url_and_localhost_cors() -> None:
    result = _run_js_harness(
        """
        function checkUrl(customLoc, withEel = false) {
          const custom = { location: customLoc };
          if (withEel) {
            custom.eel = { eel_api_request: () => () => {} };
          }
          const env = createEnv(custom);
          return {
            resolved: env.window.TurnamenConfig.resolveInitialApiBaseUrl(),
            initialStateUrl: env.window.TurnamenConfig.getState().apiBaseUrl,
            env,
          };
        }

        const localhost5000 = checkUrl({ protocol: "http:", hostname: "localhost", port: "5000" });
        const loopback5000 = checkUrl({ protocol: "http:", hostname: "127.0.0.1", port: "5000" });
        const localhost5055 = checkUrl({ protocol: "http:", hostname: "localhost", port: "5055" });
        const httpsLocalhost8443 = checkUrl({ protocol: "https:", hostname: "localhost", port: "8443" });
        const httpsLoopbackDefault = checkUrl({ protocol: "https:", hostname: "127.0.0.1", port: "" });
        const eelPortFallback = checkUrl({ protocol: "http:", hostname: "127.0.0.1", port: "8080" });
        const eelPresentFallback = checkUrl({ protocol: "http:", hostname: "localhost", port: "5000" }, true);
        const externalHostFallback = checkUrl({ protocol: "https:", hostname: "evil.example", port: "5000" });

        // Calling setRuntimeInfo with 127.0.0.1:5000 while browsing http://localhost:5000/ must keep localhost origin
        localhost5000.env.window.TurnamenConfig.setRuntimeInfo({
          app_mode: "mock",
          is_simulation: true,
          api_base_url: "http://127.0.0.1:5000/api/v1",
        });
        const afterRuntimeSync = localhost5000.env.window.TurnamenConfig.getState().apiBaseUrl;

        // isValidLocalApiBaseUrl allows http/https localhost/127.0.0.1 with valid port and rejects invalid hosts/ports
        const validatorChecks = {
          httpLocalhost: localhost5000.env.window.TurnamenConfig.isValidLocalApiBaseUrl("http://localhost:5000/api/v1"),
          httpsLocalhost: localhost5000.env.window.TurnamenConfig.isValidLocalApiBaseUrl("https://localhost:8443/api/v1"),
          httpsLoopbackNoPort: localhost5000.env.window.TurnamenConfig.isValidLocalApiBaseUrl("https://127.0.0.1/api/v1"),
          invalidPortZero: localhost5000.env.window.TurnamenConfig.isValidLocalApiBaseUrl("http://localhost:0/api/v1"),
          invalidPortHigh: localhost5000.env.window.TurnamenConfig.isValidLocalApiBaseUrl("http://localhost:70000/api/v1"),
          invalidExternal: localhost5000.env.window.TurnamenConfig.isValidLocalApiBaseUrl("https://evil.example:5000/api/v1"),
        };

        return {
          localhost5000: localhost5000.resolved,
          localhost5000State: localhost5000.initialStateUrl,
          loopback5000: loopback5000.resolved,
          localhost5055: localhost5055.resolved,
          httpsLocalhost8443: httpsLocalhost8443.resolved,
          httpsLoopbackDefault: httpsLoopbackDefault.resolved,
          eelPortFallback: eelPortFallback.resolved,
          eelPresentFallback: eelPresentFallback.resolved,
          externalHostFallback: externalHostFallback.resolved,
          afterRuntimeSync,
          validatorChecks,
        };
        """
    )

    assert result["localhost5000"] == "http://localhost:5000/api/v1"
    assert result["localhost5000State"] == "http://localhost:5000/api/v1"
    assert result["loopback5000"] == "http://127.0.0.1:5000/api/v1"
    assert result["localhost5055"] == "http://localhost:5055/api/v1"
    assert result["httpsLocalhost8443"] == "https://localhost:8443/api/v1"
    assert result["httpsLoopbackDefault"] == "https://127.0.0.1/api/v1"
    assert result["eelPortFallback"] == "http://127.0.0.1:5000/api/v1"
    assert result["eelPresentFallback"] == "http://127.0.0.1:5000/api/v1"
    assert result["externalHostFallback"] == "http://127.0.0.1:5000/api/v1"
    assert result["afterRuntimeSync"] == "http://localhost:5000/api/v1"
    assert result["validatorChecks"] == {
        "httpLocalhost": True,
        "httpsLocalhost": True,
        "httpsLoopbackNoPort": True,
        "invalidPortZero": False,
        "invalidPortHigh": False,
        "invalidExternal": False,
    }


def test_frontend_validate_and_normalize_path_and_request_blocks_traversal() -> None:
    result = _run_js_harness(
        """
        let fetchCalls = [];
        let eelCalls = [];
        const env = createEnv({
          location: { protocol: "http:", hostname: "localhost", port: "5000" },
          eel: {
            eel_get_runtime_info: () => () => ({
              success: true,
              data: { app_mode: "mock", is_simulation: true, api_base_url: "http://127.0.0.1:5000/api/v1" },
            }),
            eel_api_request: (method, endpoint) => () => {
              eelCalls.push({ method, endpoint });
              return { success: true, message: "OK", data: {} };
            },
          },
          fetch: async (url, options) => {
            fetchCalls.push({ url, options });
            return {
              ok: true,
              status: 200,
              text: async () => JSON.stringify({ success: true, data: {} }),
            };
          },
        });

        const validDirect = {
          health: env.window.TurnamenAPI.validateAndNormalizePath("/health"),
          noSlash: env.window.TurnamenAPI.validateAndNormalizePath("health"),
          withPrefix: env.window.TurnamenAPI.validateAndNormalizePath("/api/v1/health"),
          withQuery: env.window.TurnamenAPI.validateAndNormalizePath("/tournaments?status=ongoing&game_id=123"),
        };

        const traversalPayloads = [
          "/../../",
          "/api/v1/../health",
          "/api/v1/%2e%2e/%2e%2e/index.html",
          "/api/v1/%2E%2E/%2E%2E/config.js",
          "/games/.%2e/auth/me",
          "/games/%2e./auth/me",
          "/games/..%2f..%2findex.html",
          "/games/..%5c..%5cindex.html",
          "/games/%252e%252e/auth/me",
          "/games/%252f..%252findex.html",
          "/games/%255c..%255cindex.html",
          "/games/%25%32%65%25%32%65/auth/me",
          "/games/.",
          "/games/..",
          "/api/v1",
          "/api/v1/",
          "/api/v1//",
          "/api/v10/health",
          "/health#frag",
          "/health\\r\\nX-Test: 1",
          "/health\\u0000",
          "http://evil.example/api/v1/health",
          "//evil.example/health",
          "/health@evil.example",
          "/games/%ZZ",
        ];

        const directRejected = traversalPayloads.map((p) => ({
          payload: p,
          result: env.window.TurnamenAPI.validateAndNormalizePath(p),
        }));

        const requestRejected = [];
        for (const p of traversalPayloads) {
          const res = await env.window.TurnamenAPI.request("GET", p);
          requestRejected.push({ payload: p, success: res.success, code: res.error && res.error.code });
        }

        const dotSegmentRes = await env.window.TurnamenAPI.getGameById(".");
        const dotDotSegmentRes = await env.window.TurnamenAPI.getGameById("..");
        const countsAfterBlocks = { fetch: fetchCalls.length, eel: eelCalls.length };

        // Verify fetch uses redirect: "manual" and blocks 3xx redirects without Eel
        let redirectFetchOptions = null;
        const envHttp = createEnv({
          location: { protocol: "http:", hostname: "localhost", port: "5000" },
          fetch: async (url, options) => {
            redirectFetchOptions = { url, redirect: options.redirect };
            return {
              ok: false,
              status: 302,
              type: "basic",
              text: async () => "",
            };
          },
        });
        const redirectRes = await envHttp.window.TurnamenAPI.getHealth();

        return {
          validDirect,
          directRejected,
          requestRejected,
          dotSegmentRes,
          dotDotSegmentRes,
          countsAfterBlocks,
          redirectFetchOptions,
          redirectRes,
        };
        """
    )

    assert result["validDirect"] == {
        "health": "/health",
        "noSlash": "/health",
        "withPrefix": "/health",
        "withQuery": "/tournaments?status=ongoing&game_id=123",
    }
    assert all(item["result"] is None for item in result["directRejected"])
    assert all(
        item["success"] is False and item["code"] == "INVALID_ENDPOINT"
        for item in result["requestRejected"]
    )
    assert result["dotSegmentRes"]["success"] is False
    assert result["dotSegmentRes"]["error"]["code"] == "VALIDATION_ERROR"
    assert result["dotDotSegmentRes"]["success"] is False
    assert result["dotDotSegmentRes"]["error"]["code"] == "VALIDATION_ERROR"
    assert result["countsAfterBlocks"] == {"fetch": 0, "eel": 0}
    assert result["redirectFetchOptions"] == {
        "url": "http://localhost:5000/api/v1/health",
        "redirect": "manual",
    }
    assert result["redirectRes"]["success"] is False
    assert result["redirectRes"]["error"]["code"] == "REDIRECT_BLOCKED"
