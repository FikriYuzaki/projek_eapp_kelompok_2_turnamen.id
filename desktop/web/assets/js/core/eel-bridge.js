/**
 * Turnamen.in — Safe Python Eel Wrapper (`window.TurnamenBridge`)
 * Owner: Fikri (System Integration & Python Eel Developer)
 */
(function (window) {
  "use strict";

  const BRIDGE_CALL_TIMEOUT_MS = 8000;

  function buildBridgeError(message, code, details = {}) {
    return {
      success: false,
      message,
      data: null,
      error: {
        code,
        details,
      },
    };
  }

  function sanitizeDiagnosticMessage(err) {
    const raw = String(err && err.message ? err.message : err || "Unknown bridge error");
    return raw
      .replace(/(Bearer\s+)[A-Za-z0-9\-._~+/]+=*/gi, "$1***REDACTED***")
      .replace(/\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g, "***REDACTED***")
      .replace(
        /((?:password|passwd|secret_key|supabase_anon_key|service_role|rawg_api_key|api_key|apikey|access_token|refresh_token|auth_token|token|secret|key|authorization)['"\s:=]+)[^\s,'"};&]+/gi,
        "$1***REDACTED***"
      );
  }

  function logDiagnostic(operation, err) {
    if (typeof console !== "undefined" && typeof console.warn === "function") {
      const isTimeout = Boolean(err && (err.code === "BRIDGE_TIMEOUT" || err.isTimeout));
      const prefix = isTimeout
        ? `[TurnamenBridge] ${operation} melebihi batas waktu tunggu (proses Python mungkin masih berjalan):`
        : `[TurnamenBridge] ${operation} mengalami kendala bridge:`;
      console.warn(prefix, sanitizeDiagnosticMessage(err));
    }
  }

  function createBridgeTimeoutError(operation, timeoutMs = BRIDGE_CALL_TIMEOUT_MS) {
    const err = new Error(
      `Timeout (${timeoutMs}ms) pada ${operation}; proses di sisi Python mungkin masih berjalan.`
    );
    err.code = "BRIDGE_TIMEOUT";
    err.isTimeout = true;
    err.timeoutMs = timeoutMs;
    return err;
  }

  function callWithTimeout(promiseFactory, operation, timeoutMs = BRIDGE_CALL_TIMEOUT_MS) {
    return new Promise((resolve, reject) => {
      let settled = false;
      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          reject(createBridgeTimeoutError(operation, timeoutMs));
        }
      }, timeoutMs);

      Promise.resolve()
        .then(promiseFactory)
        .then((result) => {
          if (!settled) {
            settled = true;
            clearTimeout(timer);
            resolve(result);
          }
        })
        .catch((err) => {
          if (!settled) {
            settled = true;
            clearTimeout(timer);
            reject(err);
          }
        });
    });
  }

  function hasEel() {
    return (
      typeof window.eel !== "undefined" &&
      window.eel !== null &&
      typeof window.eel.eel_api_request === "function"
    );
  }

  async function getRuntimeInfo() {
    if (hasEel() && typeof window.eel.eel_get_runtime_info === "function") {
      try {
        const res = await callWithTimeout(
          () => window.eel.eel_get_runtime_info()(),
          "eel_get_runtime_info"
        );
        if (res && typeof res === "object" && !Array.isArray(res)) {
          if (res.success !== false && window.TurnamenConfig) {
            window.TurnamenConfig.setRuntimeInfo(res.data || res);
          }
          return res;
        }
        return null;
      } catch (err) {
        logDiagnostic("eel_get_runtime_info", err);
        if (err && (err.code === "BRIDGE_TIMEOUT" || err.isTimeout)) {
          return buildBridgeError(
            "Permintaan informasi runtime melalui Python Eel bridge melebihi batas waktu tunggu. Proses di sisi Python mungkin masih berjalan.",
            "BRIDGE_TIMEOUT",
            {
              operation: "eel_get_runtime_info",
              timeout_ms: err.timeoutMs || BRIDGE_CALL_TIMEOUT_MS,
              bridge_status: "timeout",
            }
          );
        }
        return null;
      }
    }
    return null;
  }

  async function checkApiHealth() {
    if (hasEel() && typeof window.eel.eel_check_api_health === "function") {
      try {
        return await callWithTimeout(
          () => window.eel.eel_check_api_health()(),
          "eel_check_api_health"
        );
      } catch (err) {
        logDiagnostic("eel_check_api_health", err);
        if (err && (err.code === "BRIDGE_TIMEOUT" || err.isTimeout)) {
          return buildBridgeError(
            "Pemeriksaan kesehatan API melalui Python Eel bridge melebihi batas waktu tunggu. Proses di sisi Python mungkin masih berjalan.",
            "BRIDGE_TIMEOUT",
            {
              operation: "eel_check_api_health",
              endpoint: "/api/v1/health",
              timeout_ms: err.timeoutMs || BRIDGE_CALL_TIMEOUT_MS,
              bridge_status: "timeout",
            }
          );
        }
        return null;
      }
    }
    return null;
  }

  async function proxyApiRequest(method, endpoint, payload = null, headers = {}) {
    if (!hasEel()) {
      return null;
    }

    const normalizedMethod = String(method || "GET").trim().toUpperCase();
    const targetEndpoint = String(endpoint ?? "").trim();
    try {
      const res = await callWithTimeout(
        () => window.eel.eel_api_request(normalizedMethod, endpoint, payload, headers)(),
        `eel_api_request(${normalizedMethod} ${targetEndpoint})`
      );
      if (res && typeof res === "object" && !Array.isArray(res)) {
        return res;
      }
      return buildBridgeError(
        "Python Eel bridge mengembalikan format respons yang tidak valid.",
        "BRIDGE_INVALID_RESPONSE",
        {
          method: normalizedMethod,
          endpoint: targetEndpoint,
          bridge_status: "invalid_response",
        }
      );
    } catch (err) {
      logDiagnostic(`eel_api_request(${normalizedMethod} ${targetEndpoint})`, err);
      if (err && (err.code === "BRIDGE_TIMEOUT" || err.isTimeout)) {
        return buildBridgeError(
          "Permintaan melalui Python Eel bridge melebihi batas waktu tunggu. Proses di sisi Python mungkin masih berjalan.",
          "BRIDGE_TIMEOUT",
          {
            method: normalizedMethod,
            endpoint: targetEndpoint,
            timeout_ms: err.timeoutMs || BRIDGE_CALL_TIMEOUT_MS,
            bridge_status: "timeout",
          }
        );
      }
      return buildBridgeError(
        "Gagal meneruskan permintaan melalui Python Eel bridge.",
        "BRIDGE_EXECUTION_ERROR",
        {
          method: normalizedMethod,
          endpoint: targetEndpoint,
          bridge_status: "error",
        }
      );
    }
  }

  window.TurnamenBridge = {
    hasEel,
    getRuntimeInfo,
    checkApiHealth,
    proxyApiRequest,
  };
})(window);
