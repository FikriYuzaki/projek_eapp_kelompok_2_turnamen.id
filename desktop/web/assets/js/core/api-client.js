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

  const MAX_PERCENT_DECODE_ROUNDS = 5;
  const ENCODED_TRAVERSAL_RE = /%(?:2e|2f|5c)/i;
  const MALFORMED_PERCENT_RE = /%(?![0-9a-fA-F]{2})/;
  const CONTROL_CHAR_RE = /[\x00-\x1f\x7f]/;

  function hasUnsafeDecodedPath(value) {
    if (
      ENCODED_TRAVERSAL_RE.test(value) ||
      CONTROL_CHAR_RE.test(value) ||
      value.includes("\\") ||
      value.includes("@") ||
      value.includes("#") ||
      value.includes("//")
    ) {
      return true;
    }
    const segments = value.split("/");
    return segments.includes(".") || segments.includes("..");
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
      CONTROL_CHAR_RE.test(trimmed) ||
      trimmed.includes("\\") ||
      trimmed.includes("@") ||
      trimmed.includes("#") ||
      trimmed.includes("://") ||
      trimmed.startsWith("//")
    ) {
      return null;
    }

    const qIdx = trimmed.indexOf("?");
    const rawPathPart = qIdx >= 0 ? trimmed.slice(0, qIdx) : trimmed;
    const rawQueryPart = qIdx >= 0 ? trimmed.slice(qIdx) : "";

    const rawPath = rawPathPart.startsWith("/") ? rawPathPart : `/${rawPathPart}`;
    if (
      rawPath === "/" ||
      rawPath === "/api/v1" ||
      (rawPath.startsWith("/api/v1") && !rawPath.startsWith("/api/v1/"))
    ) {
      return null;
    }

    const relativePath = rawPath.startsWith("/api/v1/")
      ? rawPath.slice("/api/v1".length)
      : rawPath;
    if (!relativePath || relativePath === "/") {
      return null;
    }

    const fullPath = `/api/v1${relativePath}`;
    if (/\s/.test(fullPath) || fullPath.includes("//") || MALFORMED_PERCENT_RE.test(fullPath)) {
      return null;
    }

    let current = fullPath;
    let decodeStabilized = false;
    for (let round = 0; round < MAX_PERCENT_DECODE_ROUNDS; round += 1) {
      if (hasUnsafeDecodedPath(current)) {
        return null;
      }
      let decoded;
      try {
        decoded = decodeURIComponent(current);
      } catch (_decodeErr) {
        return null;
      }
      if (decoded === current) {
        decodeStabilized = true;
        break;
      }
      current = decoded;
    }
    if (!decodeStabilized) {
      try {
        if (decodeURIComponent(current) !== current) {
          return null;
        }
      } catch (_decodeErr) {
        return null;
      }
    }

    if (
      hasUnsafeDecodedPath(current) ||
      !current.startsWith("/api/v1/") ||
      current.length <= "/api/v1/".length
    ) {
      return null;
    }

    if (typeof URL === "function") {
      try {
        const resolved = new URL(fullPath, "http://127.0.0.1");
        if (
          resolved.origin !== "http://127.0.0.1" ||
          resolved.pathname !== fullPath ||
          !resolved.pathname.startsWith("/api/v1/") ||
          resolved.pathname.length <= "/api/v1/".length ||
          resolved.hash !== ""
        ) {
          return null;
        }
      } catch (_urlErr) {
        return null;
      }
    }

    if (rawQueryPart) {
      if (CONTROL_CHAR_RE.test(rawQueryPart)) {
        return null;
      }
      try {
        if (CONTROL_CHAR_RE.test(decodeURIComponent(rawQueryPart))) {
          return null;
        }
      } catch (_queryErr) {
        return null;
      }
    }

    return `${relativePath}${rawQueryPart}`;
  }

  function encodeSegment(value, fieldName = "id") {
    const str = String(value ?? "").trim();
    if (
      !str ||
      str === "." ||
      str === ".." ||
      str.includes("/") ||
      str.includes("\\") ||
      CONTROL_CHAR_RE.test(str)
    ) {
      throw new Error(`Parameter '${fieldName}' wajib diisi dengan nilai yang valid.`);
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

  async function request(method, path, payload = null, requestOptions = {}) {
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

    if (requestOptions && isPlainObject(requestOptions.headers)) {
      Object.entries(requestOptions.headers).forEach(([k, v]) => {
        if (typeof k === "string" && k.trim() && typeof v === "string" && v.trim()) {
          headers[k.trim()] = v.trim();
        }
      });
    }

    if (
      cfg.token &&
      window.TurnamenConfig &&
      typeof window.TurnamenConfig.isTokenExpired === "function" &&
      window.TurnamenConfig.isTokenExpired(cfg.token) &&
      cleanPath !== "/auth/login" &&
      cleanPath !== "/auth/register" &&
      cleanPath !== "/auth/password-recovery" &&
      cleanPath !== "/auth/password-recovery/update" &&
      cleanPath !== "/health"
    ) {
      clearLocalAuthSession();
      return buildErrorResponse(
        "Sesi autentikasi telah kedaluwarsa. Silakan masuk kembali.",
        "UNAUTHORIZED",
        { reason: "token_expired" }
      );
    }

    if (
      !headers["Authorization"] &&
      cleanPath !== "/auth/password-recovery" &&
      cleanPath !== "/auth/password-recovery/update"
    ) {
      if (cfg.token) {
        headers["Authorization"] = `Bearer ${cfg.token}`;
      } else if (cfg.isSimulation && cfg.appMode === "mock" && cfg.currentUser) {
        headers["X-Mock-Role"] = cfg.currentUser.role;
        headers["X-Mock-User-Id"] = cfg.currentUser.id;
      }
    }

    const finalizeAuthenticatedResponse = (normalizedRes) => {
      if (
        normalizedRes &&
        !normalizedRes.success &&
        cfg.token &&
        normalizedRes.error &&
        normalizedRes.error.code === "UNAUTHORIZED" &&
        cleanPath !== "/auth/login" &&
        cleanPath !== "/auth/register" &&
        cleanPath !== "/auth/logout" &&
        cleanPath !== "/auth/password-recovery" &&
        cleanPath !== "/auth/password-recovery/update"
      ) {
        clearLocalAuthSession();
      }
      return normalizedRes;
    };

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
          return finalizeAuthenticatedResponse(normalizeResponse(bridged));
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
      redirect: "manual",
      signal: controller ? controller.signal : undefined,
    };
    if (payload !== null && normalizedMethod !== "GET") {
      options.body = JSON.stringify(payload);
    }

    try {
      const response = await fetch(url, options);
      if (
        response.type === "opaqueredirect" ||
        (response.status >= 300 && response.status < 400)
      ) {
        return buildErrorResponse(
          "Server API lokal mengembalikan redirect yang tidak diizinkan.",
          "REDIRECT_BLOCKED",
          { status_code: response.status, endpoint: cleanPath }
        );
      }
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

      return finalizeAuthenticatedResponse(normalizeResponse(parsed, response.status));
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

  function createIdempotencyKey() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  window.TurnamenAPI = {
    request,
    bootstrapRuntime,
    validateAndNormalizePath,
    createIdempotencyKey,

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
      if (typeof window.TurnamenConfig.enterGuestMode === "function") {
        window.TurnamenConfig.enterGuestMode();
      } else if (typeof window.TurnamenConfig.clearAuthSession === "function") {
        window.TurnamenConfig.clearAuthSession();
      } else {
        window.TurnamenConfig.setSimulatedRole("guest");
      }
      return res;
    },
    getCurrentUser() {
      return request("GET", "/auth/me");
    },
    requestPasswordRecovery(email, redirectTo = null) {
      const payload = { email };
      if (typeof redirectTo === "string" && redirectTo.trim()) {
        payload.redirect_to = redirectTo.trim();
      }
      return request("POST", "/auth/password-recovery", payload);
    },
    updatePasswordWithRecoveryToken(recoverySession, newPassword) {
      const session = isPlainObject(recoverySession) ? recoverySession : {};
      const accessToken =
        typeof session.accessToken === "string" ? session.accessToken.trim() : "";
      const refreshToken =
        typeof session.refreshToken === "string" ? session.refreshToken.trim() : "";
      const tokenHash =
        typeof session.tokenHash === "string" ? session.tokenHash.trim() : "";

      const payload = { new_password: newPassword };
      if (refreshToken) payload.refresh_token = refreshToken;
      if (tokenHash) payload.token_hash = tokenHash;

      const options = accessToken
        ? { headers: { Authorization: `Bearer ${accessToken}` } }
        : {};
      return request("POST", "/auth/password-recovery/update", payload, options);
    },
    async updateProfile(payload) {
      const res = await request("PATCH", "/auth/me", payload);
      if (res.success && res.data && res.data.user && window.TurnamenConfig) {
        const cfg = window.TurnamenConfig.getState();
        if (cfg.token) {
          window.TurnamenConfig.setAuthSession(cfg.token, res.data.user);
        } else if (cfg.isSimulation && cfg.appMode === "mock") {
          window.TurnamenConfig.setAuthSession(null, res.data.user);
        }
      }
      return res;
    },
    getUsers() {
      return request("GET", "/users");
    },
    assignUserRole(userId, role) {
      return safeSegmentCall(() =>
        request("PATCH", `/users/${encodeSegment(userId, "userId")}/role`, { role })
      );
    },
    setSimulatedRole(roleName) {
      return window.TurnamenConfig.setSimulatedRole(roleName);
    },

    getGames(options = {}) {
      const includeInactive = Boolean(options && options.includeInactive);
      return request("GET", `/games${includeInactive ? "?include_inactive=true" : ""}`);
    },
    getGameById(gameId) {
      return safeSegmentCall(() =>
        request("GET", `/games/${encodeSegment(gameId, "gameId")}`)
      );
    },
    createGame(payload) {
      return request("POST", "/games", payload);
    },
    updateGame(gameId, payload) {
      return safeSegmentCall(() =>
        request("PATCH", `/games/${encodeSegment(gameId, "gameId")}`, payload)
      );
    },
    uploadGameArtwork(gameId, payload) {
      return safeSegmentCall(() =>
        request("POST", `/games/${encodeSegment(gameId, "gameId")}/artwork`, payload)
      );
    },
    restoreGameArtwork(gameId) {
      return safeSegmentCall(() =>
        request("DELETE", `/games/${encodeSegment(gameId, "gameId")}/artwork`)
      );
    },

    getCommitteeCandidates() {
      return request("GET", "/staff/candidates");
    },
    getTournamentStaff(tournamentId) {
      return safeSegmentCall(() =>
        request("GET", `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/staff`)
      );
    },
    addTournamentStaff(tournamentId, payload) {
      return safeSegmentCall(() =>
        request(
          "POST",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/staff`,
          payload
        )
      );
    },
    removeTournamentStaff(tournamentId, userId) {
      return safeSegmentCall(() =>
        request(
          "DELETE",
          `/tournaments/${encodeSegment(tournamentId, "tournamentId")}/staff/${encodeSegment(userId, "userId")}`
        )
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
    submitMatchResult(matchId, payload, options = {}) {
      return safeSegmentCall(() => {
        const body = isPlainObject(payload) ? { ...payload } : {};
        const optKey =
          options && typeof options.idempotencyKey === "string" ? options.idempotencyKey.trim() : "";
        const bodyKey =
          typeof body.idempotency_key === "string" ? body.idempotency_key.trim() : "";
        const idempotencyKey = optKey || bodyKey || createIdempotencyKey();
        body.idempotency_key = idempotencyKey;
        return request(
          "PATCH",
          `/matches/${encodeSegment(matchId, "matchId")}/result`,
          body,
          { headers: { "Idempotency-Key": idempotencyKey } }
        );
      });
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
