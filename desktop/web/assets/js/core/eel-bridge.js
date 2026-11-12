/**
 * Turnamen.in — Safe Python Eel Wrapper (`window.TurnamenBridge`)
 * Owner: Fikri (System Integration & Python Eel Developer)
 */
(function (window) {
  "use strict";

  const BRIDGE_CALL_TIMEOUT_MS = 8000;

  function sanitizeDiagnosticMessage(err) {
    const raw = String(err && err.message ? err.message : err || "Unknown bridge error");
    return raw
      .replace(/(Bearer\s+)[A-Za-z0-9\-._~+/]+=*/gi, "$1***REDACTED***")
      .replace(/((?:password|token|secret|key)['"\s:=]+)[^\s,'"}]+/gi, "$1***REDACTED***");
  }

  function logDiagnostic(operation, err) {
    if (typeof console !== "undefined" && typeof console.warn === "function") {
      console.warn(
        `[TurnamenBridge] ${operation} gagal, beralih ke fallback HTTP bila tersedia:`,
        sanitizeDiagnosticMessage(err)
      );
    }
  }

  function callWithTimeout(promiseFactory, operation) {
    return new Promise((resolve, reject) => {
      let settled = false;
      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          reject(new Error(`Timeout (${BRIDGE_CALL_TIMEOUT_MS}ms) pada ${operation}`));
        }
      }, BRIDGE_CALL_TIMEOUT_MS);

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
        if (res && typeof res === "object" && window.TurnamenConfig) {
          window.TurnamenConfig.setRuntimeInfo(res.data || res);
        }
        return res;
      } catch (err) {
        logDiagnostic("eel_get_runtime_info", err);
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
        return null;
      }
    }
    return null;
  }

  async function proxyApiRequest(method, endpoint, payload = null, headers = {}) {
    if (hasEel()) {
      try {
        const res = await callWithTimeout(
          () => window.eel.eel_api_request(method, endpoint, payload, headers)(),
          `eel_api_request(${method} ${endpoint})`
        );
        if (res && typeof res === "object") {
          return res;
        }
        return null;
      } catch (err) {
        logDiagnostic(`eel_api_request(${method} ${endpoint})`, err);
        return null;
      }
    }
    return null;
  }

  window.TurnamenBridge = {
    hasEel,
    getRuntimeInfo,
    checkApiHealth,
    proxyApiRequest,
  };
})(window);
