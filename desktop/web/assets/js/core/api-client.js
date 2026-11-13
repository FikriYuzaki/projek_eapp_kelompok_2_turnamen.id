/**
 * Turnamen.in — Centralized REST API Client (`window.TurnamenAPI`)
 * Owner: Fikri (System Integration & Python Eel Developer)
 * Implements all contract methods defined in `docs/contracts/frontend-contract.md`.
 */
(function (window) {
  "use strict";

  const REQUEST_TIMEOUT_MS = 8000;
  const ALLOWED_METHODS = new Set(["GET", "POST", "PATCH", "PUT", "DELETE"]);
  const SAFE_HTTP_FALLBACK_METHODS = new Set(["GET"]);
  let runtimeBootstrapPromise = null;

  function isPlainObject(value) {
    return Boolean(value && typeof value === "object" && !Array.isArray(value));
  }

  function hasValidUserIdentity(user) {
    if (!isPlainObject(user)) {
      return false;
    }
    const hasId = typeof user.id === "string" && user.id.trim().length > 0;
    const hasEmail = typeof user.email === "string" && user.email.trim().length > 0;
    return hasId || hasEmail;
  }

  function clearLocalAuthSession() {
    if (!window.TurnamenConfig) {
      return;
    }
    if (typeof window.TurnamenConfig.clearAuthSession === "function") {
      window.TurnamenConfig.clearAuthSession();
    } else if (typeof window.TurnamenConfig.setAuthSession === "function") {
      window.TurnamenConfig.setAuthSession(null, null);
    }
  }

  function buildErrorResponse(message, code, details = {}) {
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

  function normalizeResponse(raw, fallbackStatus = 200) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      return buildErrorResponse(
        "Respons dari server API lokal tidak sesuai format kontrak JSON.",
        "INVALID_RESPONSE_FORMAT",
        { status_code: fallbackStatus }
      );
    }

    const isSuccess = Boolean(raw.success);
    const message =
      typeof raw.message === "string" && raw.message.trim()
        ? raw.message
        : isSuccess
          ? "Operasi berhasil"
          : `Permintaan gagal (HTTP ${fallbackStatus}).`;

    if (isSuccess) {
      return {
        success: true,
        message,
        data: raw.data !== undefined ? raw.data : {},
        error: null,
      };
    }

    const rawErr = raw.error && typeof raw.error === "object" ? raw.error : {};
    return {
      success: false,
      message,
      data: null,
      error: {
        code: typeof rawErr.code === "string" && rawErr.code ? rawErr.code : "HTTP_ERROR",
        details:
          rawErr.details && typeof rawErr.details === "object"
            ? rawErr.details
            : { status_code: fallbackStatus },
      },
    };
  }

  function validateAndNormalizePath(path) {
    if (typeof path !== "string") {
      return null;
    }
    const trimmed = path.trim();
    if (!trimmed) {
      return null;
    }
    if (
      trimmed.includes("://") ||
      trimmed.startsWith("//") ||
      trimmed.includes("\\") ||
      trimmed.includes("..") ||
      trimmed.includes("@") ||
      /[\r\n\t]/.test(trimmed)
    ) {
      return null;
    }
    return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  }

  function encodeSegment(value, fieldName = "id") {
    const str = String(value ?? "").trim();
    if (!str) {
      throw new Error(`Parameter '${fieldName}' wajib diisi.`);
    }
    return encodeURIComponent(str);
  }

  async function bootstrapRuntime() {
    if (runtimeBootstrapPromise) {
      return runtimeBootstrapPromise;
    }
    runtimeBootstrapPromise = (async () => {
      if (window.TurnamenBridge && window.TurnamenBridge.hasEel()) {
        const info = await window.TurnamenBridge.getRuntimeInfo();
        if (
          info &&
          typeof info === "object" &&
          info.success !== false &&
          window.TurnamenConfig
        ) {
          window.TurnamenConfig.setRuntimeInfo(info.data || info);
        }
      }
    })();
    return runtimeBootstrapPromise;
  }

  async function request(method, path, payload = null) {
    const normalizedMethod = String(method || "GET").trim().toUpperCase();
    if (!ALLOWED_METHODS.has(normalizedMethod)) {
      return buildErrorResponse(
        `Metode HTTP '${normalizedMethod}' tidak didukung.`,
        "INVALID_METHOD",
        { method: normalizedMethod }
      );
    }

    const cleanPath = validateAndNormalizePath(path);
    if (!cleanPath) {
      return buildErrorResponse(
        "Path endpoint API tidak valid. Hanya path relatif lokal yang diizinkan.",
        "INVALID_ENDPOINT",
        { path: String(path ?? "") }
      );
    }

    await bootstrapRuntime();

    const cfg = window.TurnamenConfig.getState();
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };

    if (cfg.token) {
      headers["Authorization"] = `Bearer ${cfg.token}`;
    } else if (cfg.isSimulation && cfg.appMode === "mock" && cfg.currentUser) {
      headers["X-Mock-Role"] = cfg.currentUser.role;
      headers["X-Mock-User-Id"] = cfg.currentUser.id;
    }

    if (window.TurnamenBridge && window.TurnamenBridge.hasEel()) {
      const bridged = await window.TurnamenBridge.proxyApiRequest(
        normalizedMethod,
        cleanPath,
        payload,
        headers
      );
      if (bridged && typeof bridged === "object" && !Array.isArray(bridged)) {
        const bridgeErrorCode =
          bridged.error && typeof bridged.error === "object"
            ? bridged.error.code
            : null;
        // Never retry timeouts or mutations over HTTP because the Python call may still be running.
        const canFallbackToHttp =
          SAFE_HTTP_FALLBACK_METHODS.has(normalizedMethod) &&
          (bridgeErrorCode === "BRIDGE_EXECUTION_ERROR" ||
            bridgeErrorCode === "BRIDGE_INVALID_RESPONSE");
        if (!canFallbackToHttp) {
          return normalizeResponse(bridged);
        }
      } else if (!SAFE_HTTP_FALLBACK_METHODS.has(normalizedMethod)) {
        return buildErrorResponse(
          "Permintaan mutasi melalui Python Eel bridge tidak mengembalikan kepastian status; proses di sisi Python mungkin masih berjalan sehingga pengulangan HTTP tidak dilakukan untuk mencegah duplikasi operasi.",
          "BRIDGE_UNCERTAIN_STATE",
          { method: normalizedMethod, endpoint: cleanPath }
        );
      }
    }

    const url = `${cfg.apiBaseUrl}${cleanPath}`;
    const controller =
      typeof AbortController !== "undefined" ? new AbortController() : null;
    const timeoutId = controller
      ? setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
      : null;

    const options = {
      method: normalizedMethod,
      headers,
      signal: controller ? controller.signal : undefined,
    };
    if (payload !== null && normalizedMethod !== "GET") {
      options.body = JSON.stringify(payload);
    }

    try {
      const response = await fetch(url, options);
      const rawText = await response.text();
      if (!rawText) {
        return buildErrorResponse(
          `Server API lokal mengembalikan respons kosong (HTTP ${response.status}).`,
          response.ok ? "EMPTY_RESPONSE" : "HTTP_ERROR",
          { status_code: response.status, endpoint: cleanPath }
        );
      }

      let parsed;
      try {
        parsed = JSON.parse(rawText);
      } catch (_parseErr) {
        return buildErrorResponse(
          response.ok
            ? "Respons dari server API lokal bukan format JSON yang valid."
            : `Server API lokal mengembalikan kesalahan HTTP ${response.status}.`,
          response.ok ? "INVALID_RESPONSE_FORMAT" : "HTTP_ERROR",
          { status_code: response.status, endpoint: cleanPath }
        );
      }

      return normalizeResponse(parsed, response.status);
    } catch (err) {
      if (err && err.name === "AbortError") {
        return buildErrorResponse(
          "Permintaan ke server API lokal melebihi batas waktu tunggu.",
          "REQUEST_TIMEOUT",
          { endpoint: cleanPath, timeout_ms: REQUEST_TIMEOUT_MS }
        );
      }
      return buildErrorResponse(
        `Tidak dapat terhubung ke server API lokal (${cfg.apiBaseUrl}).`,
        "NETWORK_ERROR",
        { endpoint: cleanPath }
      );
    } finally {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    }
  }

  function safeSegmentCall(fn) {
    try {
      return Promise.resolve(fn());
    } catch (err) {
      return Promise.resolve(
        buildErrorResponse(
          err && err.message ? err.message : "Parameter endpoint tidak valid.",
          "VALIDATION_ERROR"
        )
      );
    }
  }

  window.TurnamenAPI = {
    request,
    bootstrapRuntime,

    async getHealth() {
      const res = await request("GET", "/health");
      if (res.success && res.data && window.TurnamenConfig) {
        window.TurnamenConfig.setRuntimeInfo(res.data);
      }
      return res;
    },

    async login(email, password) {
      const res = await request("POST", "/auth/login", { email, password });
      if (!res.success) {
        return res;
      }

      const rawData = isPlainObject(res.data) ? res.data : {};
      const requiresEmailConfirmation =
        rawData.requires_email_confirmation === true;
      const token =
        typeof rawData.token === "string" && rawData.token.trim()
          ? rawData.token.trim()
          : null;
      const validUser = hasValidUserIdentity(rawData.user) ? rawData.user : null;
      const shouldCreateSession = Boolean(
        !requiresEmailConfirmation && token && validUser
      );

      if (isPlainObject(res.data)) {
        res.data = {
          ...rawData,
          token: shouldCreateSession ? token : null,
        };
      }

      if (shouldCreateSession && window.TurnamenConfig) {
        window.TurnamenConfig.setAuthSession(token, validUser);
      } else {
        clearLocalAuthSession();
      }
      return res;
    },
    async register(payload) {
      const res = await request("POST", "/auth/register", payload);
      if (!res.success) {
        return res;
      }

      const rawData = isPlainObject(res.data) ? res.data : {};
      const requiresEmailConfirmation =
        rawData.requires_email_confirmation === true;
      const token =
        typeof rawData.token === "string" && rawData.token.trim()
          ? rawData.token.trim()
          : null;
      const validUser = hasValidUserIdentity(rawData.user) ? rawData.user : null;
      const shouldCreateSession = Boolean(
        !requiresEmailConfirmation && token && validUser
      );

      res.data = {
        ...rawData,
        token: shouldCreateSession ? token : null,
        requires_email_confirmation: requiresEmailConfirmation,
      };

      if (shouldCreateSession && window.TurnamenConfig) {
        window.TurnamenConfig.setAuthSession(token, validUser);
      } else {
        clearLocalAuthSession();
      }
      return res;
    },
    async logout() {
      const res = await request("POST", "/auth/logout");
      if (typeof window.TurnamenConfig.clearAuthSession === "function") {
        window.TurnamenConfig.clearAuthSession();
      } else {
        window.TurnamenConfig.setSimulatedRole("player");
      }
      return res;
    },
    getCurrentUser() {
      return request("GET", "/auth/me");
    },
    setSimulatedRole(roleName) {
      return window.TurnamenConfig.setSimulatedRole(roleName);
    },

    getGames() {
      return request("GET", "/games");
    },
    getGameById(gameId) {
      return safeSegmentCall(() =>
        request("GET", `/games/${encodeSegment(gameId, "gameId")}`)
      );
    },

    getTournaments(filters = {}) {
      const params = new URLSearchParams();
      if (filters && typeof filters === "object") {
        if (filters.status) params.set("status", String(filters.status).trim());
        if (filters.game_id) params.set("game_id", String(filters.game_id).trim());
      }
      const qs = params.toString();
      return request("GET", `/tournaments${qs ? "?" + qs : ""}`);
    },
    getTournamentById(tournamentId) {
      return safeSegmentCall(() =>
        request("GET", `/tournaments/${encodeSegment(tournamentId, "tournamentId")}`)
      );
    },
    createTournament(payload) {
      return request("POST", "/tournaments", payload);
    },
    updateTournament(tournamentId, payload) {
      return safeSegmentCall(() =>
        request(
          "PATCH",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}`,
          payload
        )
      );
    },
    deleteTournament(tournamentId) {
      return safeSegmentCall(() =>
        request("DELETE", `/tournaments/${encodeSegment(tournamentId, "tournamentId")}`)
      );
    },

    getTeams(filtersOrGameId = "") {
      const params = new URLSearchParams();
      if (typeof filtersOrGameId === "string" && filtersOrGameId.trim()) {
        params.set("game_id", filtersOrGameId.trim());
      } else if (
        filtersOrGameId &&
        typeof filtersOrGameId === "object" &&
        filtersOrGameId.game_id
      ) {
        params.set("game_id", String(filtersOrGameId.game_id).trim());
      }
      const qs = params.toString();
      return request("GET", `/teams${qs ? "?" + qs : ""}`);
    },
    getTeamById(teamId) {
      return safeSegmentCall(() =>
        request("GET", `/teams/${encodeSegment(teamId, "teamId")}`)
      );
    },
    createTeam(payload) {
      return request("POST", "/teams", payload);
    },
    updateTeam(teamId, payload) {
      return safeSegmentCall(() =>
        request("PATCH", `/teams/${encodeSegment(teamId, "teamId")}`, payload)
      );
    },
    addTeamMember(teamId, payload) {
      return safeSegmentCall(() =>
        request("POST", `/teams/${encodeSegment(teamId, "teamId")}/members`, payload)
      );
    },

    getTournamentRegistrations(tournamentId) {
      return safeSegmentCall(() =>
        request(
          "GET",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/registrations`
        )
      );
    },
    registerTeamToTournament(tournamentId, payload) {
      return safeSegmentCall(() =>
        request(
          "POST",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/registrations`,
          payload
        )
      );
    },
    updateRegistrationStatus(registrationId, status, notes = "") {
      return safeSegmentCall(() =>
        request(
          "PATCH",
          `/registrations/${encodeSegment(registrationId, "registrationId")}/status`,
          { status, notes }
        )
      );
    },

    getTournamentMatches(tournamentId) {
      return safeSegmentCall(() =>
        request(
          "GET",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/matches`
        )
      );
    },
    generateBracket(tournamentId, payload = {}) {
      return safeSegmentCall(() =>
        request(
          "POST",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/bracket/generate`,
          payload
        )
      );
    },
    submitMatchResult(matchId, payload) {
      return safeSegmentCall(() =>
        request("PATCH", `/matches/${encodeSegment(matchId, "matchId")}/result`, payload)
      );
    },

    getAnnouncements(tournamentId) {
      return safeSegmentCall(() =>
        request(
          "GET",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/announcements`
        )
      );
    },
    createAnnouncement(tournamentId, payload) {
      return safeSegmentCall(() =>
        request(
          "POST",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/announcements`,
          payload
        )
      );
    },
    getTournamentReport(tournamentId) {
      return safeSegmentCall(() =>
        request(
          "GET",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/reports`
        )
      );
    },
    getTournamentStandings(tournamentId) {
      return safeSegmentCall(() =>
        request(
          "GET",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/standings`
        )
      );
    },
  };
})(window);
