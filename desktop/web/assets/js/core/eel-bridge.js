/**
 * Turnamen.in — Safe Python Eel Wrapper (`window.TurnamenBridge`)
 * Owner: Fikri (System Integration & Python Eel Developer)
 */
(function (window) {
  "use strict";

  function hasEel() {
    return typeof window.eel !== "undefined" && typeof window.eel.eel_api_request === "function";
  }

  async function getRuntimeInfo() {
    if (hasEel() && typeof window.eel.eel_get_runtime_info === "function") {
      try {
        return await window.eel.eel_get_runtime_info()();
      } catch (_err) {
        return null;
      }
    }
    return null;
  }

  async function proxyApiRequest(method, endpoint, payload, headers) {
    if (hasEel()) {
      try {
        return await window.eel.eel_api_request(method, endpoint, payload, headers)();
      } catch (_err) {
        return null;
      }
    }
    return null;
  }

  window.TurnamenBridge = {
    hasEel,
    getRuntimeInfo,
    proxyApiRequest,
  };
})(window);
