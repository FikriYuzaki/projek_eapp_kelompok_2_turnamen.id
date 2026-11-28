/**
 * Turnamen.in — Frontend Runtime Configuration (`window.TurnamenConfig`)
 * Owner: Fikri (System Integration & Python Eel Developer)
 */
(function (window) {
  "use strict";

  const DEFAULT_API_BASE_URL = "http://127.0.0.1:5000/api/v1";
  const DEFAULT_EEL_PORT = "8080";

  const DEMO_ACCOUNTS = Object.freeze({
    super_admin: Object.freeze({
      id: "11111111-1111-4111-8111-111111111101",
      email: "admin@turnamen.in",
      username: "superadmin",
      full_name: "Raka Pratama (Super Admin)",
      role: "super_admin",
    }),
    organizer: Object.freeze({
      id: "11111111-1111-4111-8111-111111111102",
      email: "organizer@turnamen.in",
      username: "garuda_eo",
      full_name: "Nadia Kusuma (Tournament Organizer)",
      role: "organizer",
    }),
    committee: Object.freeze({
      id: "11111111-1111-4111-8111-111111111103",
      email: "committee@turnamen.in",
      username: "panitia_utama",
      full_name: "Bima Saputra (Head Committee)",
      role: "committee",
    }),
    team_captain: Object.freeze({
      id: "11111111-1111-4111-8111-111111111104",
      email: "captain@turnamen.in",
      username: "garuda_capt",
      full_name: "Dimas Aditya (Team Captain)",
      role: "team_captain",
    }),
    player: Object.freeze({
      id: "11111111-1111-4111-8111-111111111105",
      email: "player@turnamen.in",
      username: "aruna_player",
      full_name: "Rizky Maulana (Player)",
      role: "player",
    }),
  });

  function resolveInitialApiBaseUrl() {
    try {
      const loc = window.location;
      if (
        loc &&
        (loc.protocol === "http:" || loc.protocol === "https:") &&
        (loc.hostname === "127.0.0.1" || loc.hostname === "localhost") &&
        typeof window.eel === "undefined"
      ) {
        if (loc.port !== DEFAULT_EEL_PORT) {
          const portPart = loc.port ? `:${loc.port}` : "";
          return `${loc.protocol}//${loc.hostname}${portPart}/api/v1`;
        }
      }
    } catch (_err) {
      // Ignore location access errors in non-browser environments.
    }
    return DEFAULT_API_BASE_URL;
  }

  function isValidLocalApiBaseUrl(url) {
    if (typeof url !== "string") return false;
    const match = /^https?:\/\/(127\.0\.0\.1|localhost)(?::(\d{1,5}))?\/api\/v1\/?$/.exec(
      url.trim()
    );
    if (!match) return false;
    if (match[2] !== undefined) {
      const port = Number(match[2]);
      if (!Number.isInteger(port) || port < 1 || port > 65535) return false;
    }
    return true;
  }

  const DEFAULT_SELECTED_TOURNAMENT_ID = "33333333-3333-4333-8333-333333333301";
  const SELECTED_TOURNAMENT_STORAGE_KEY = "turnamen.selected_tournament_id.v1";
  const AUTH_SESSION_STORAGE_KEY = "turnamen.auth_session.v1";

  function decodeBase64UrlUtf8(segment) {
    if (typeof segment !== "string" || !segment) return "";
    const normalized = segment.replace(/-/g, "+").replace(/_/g, "/");
    const padLen = (4 - (normalized.length % 4)) % 4;
    const padded = normalized + "=".repeat(padLen);
    if (typeof window.atob === "function") {
      try {
        const bin = window.atob(padded);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i += 1) {
          bytes[i] = bin.charCodeAt(i);
        }
        return typeof TextDecoder === "function"
          ? new TextDecoder("utf-8").decode(bytes)
          : bin;
      } catch (_err) {
        return "";
      }
    }
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let buffer = 0;
    let bits = 0;
    const out = [];
    for (let i = 0; i < padded.length; i += 1) {
      const ch = padded[i];
      if (ch === "=") break;
      const idx = alphabet.indexOf(ch);
      if (idx < 0) return "";
      buffer = (buffer << 6) | idx;
      bits += 6;
      if (bits >= 8) {
        bits -= 8;
        out.push((buffer >> bits) & 0xff);
      }
    }
    if (typeof TextDecoder === "function") {
      try {
        return new TextDecoder("utf-8").decode(new Uint8Array(out));
      } catch (_err) {
        return "";
      }
    }
    return String.fromCharCode(...out);
  }

  function decodeJwtPayload(token) {
    if (typeof token !== "string") return null;
    const parts = token.trim().split(".");
    if (parts.length !== 3 || !parts[1]) return null;
    try {
      const jsonStr = decodeBase64UrlUtf8(parts[1]);
      if (!jsonStr) return null;
      const parsed = JSON.parse(jsonStr);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (_err) {
      return null;
    }
  }

  function isTokenExpired(token) {
    const payload = decodeJwtPayload(token);
    if (!payload || typeof payload.exp !== "number" || !Number.isFinite(payload.exp)) {
      return false;
    }
    return Date.now() >= payload.exp * 1000;
  }

  function sanitizeStoredUser(user) {
    if (!user || typeof user !== "object") return null;
    const id = typeof user.id === "string" ? user.id.trim() : "";
    const email = typeof user.email === "string" ? user.email.trim() : "";
    if (!id && !email) return null;
    return {
      id,
      email,
      username: typeof user.username === "string" ? user.username : "",
      full_name: typeof user.full_name === "string" ? user.full_name : "",
      role: typeof user.role === "string" ? user.role : "player",
      phone: typeof user.phone === "string" ? user.phone : null,
      avatar_url: typeof user.avatar_url === "string" ? user.avatar_url : null,
      is_active: user.is_active !== false,
    };
  }

  function readStoredAuthSession() {
    try {
      if (!window.sessionStorage || typeof window.sessionStorage.getItem !== "function") {
        return null;
      }
      const raw = window.sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return null;

      const appMode =
        parsed.appMode === "supabase" || parsed.appMode === "mock" ? parsed.appMode : "mock";
      const token =
        typeof parsed.token === "string" && parsed.token.trim() ? parsed.token.trim() : null;
      if (token && isTokenExpired(token)) {
        clearStoredAuthSession();
        return {
          appMode,
          token: null,
          user: null,
          simulatedRole: null,
          explicitGuest: true,
        };
      }
      const user = sanitizeStoredUser(parsed.user);
      if (!token && !user) {
        return null;
      }
      const simulatedRole =
        typeof parsed.simulatedRole === "string" && DEMO_ACCOUNTS[parsed.simulatedRole]
          ? parsed.simulatedRole
          : null;
      return {
        appMode,
        token,
        user,
        simulatedRole,
        explicitGuest: Boolean(parsed.explicitGuest),
      };
    } catch (_err) {
      return null;
    }
  }

  function writeStoredAuthSession(snapshot) {
    try {
      if (!window.sessionStorage || typeof window.sessionStorage.setItem !== "function") {
        return;
      }
      const user = sanitizeStoredUser(snapshot && snapshot.user);
      const token =
        snapshot && typeof snapshot.token === "string" && snapshot.token.trim()
          ? snapshot.token.trim()
          : null;
      if (!token && !user) {
        clearStoredAuthSession();
        return;
      }
      if (token && isTokenExpired(token)) {
        clearStoredAuthSession();
        return;
      }
      const payload = {
        appMode: snapshot.appMode === "supabase" ? "supabase" : "mock",
        token,
        user,
        simulatedRole:
          typeof snapshot.simulatedRole === "string" && DEMO_ACCOUNTS[snapshot.simulatedRole]
            ? snapshot.simulatedRole
            : null,
        explicitGuest: Boolean(snapshot.explicitGuest),
      };
      window.sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(payload));
    } catch (_err) {
      // Ignore storage access errors in restricted WebView or non-browser tests.
    }
  }

  function clearStoredAuthSession() {
    try {
      if (window.sessionStorage && typeof window.sessionStorage.removeItem === "function") {
        window.sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
      }
    } catch (_err) {
      // Ignore storage access errors in restricted WebView or non-browser tests.
    }
  }

  function normalizeTournamentId(value) {
    if (typeof value !== "string") return "";
    const trimmed = value.trim();
    return /^[a-zA-Z0-9_-]{4,64}$/.test(trimmed) ? trimmed : "";
  }

  function readStoredSelectedTournamentId() {
    try {
      if (window.sessionStorage && typeof window.sessionStorage.getItem === "function") {
        return normalizeTournamentId(
          window.sessionStorage.getItem(SELECTED_TOURNAMENT_STORAGE_KEY)
        );
      }
    } catch (_err) {
      // Ignore storage access errors in restricted WebView or non-browser tests.
    }
    return "";
  }

  function writeStoredSelectedTournamentId(tournamentId) {
    const clean = normalizeTournamentId(tournamentId);
    if (!clean) return;
    try {
      if (window.sessionStorage && typeof window.sessionStorage.setItem === "function") {
        window.sessionStorage.setItem(SELECTED_TOURNAMENT_STORAGE_KEY, clean);
      }
    } catch (_err) {
      // Ignore storage access errors in restricted WebView or non-browser tests.
    }
  }

  function clearStoredSelectedTournamentId() {
    try {
      if (window.sessionStorage && typeof window.sessionStorage.removeItem === "function") {
        window.sessionStorage.removeItem(SELECTED_TOURNAMENT_STORAGE_KEY);
      }
    } catch (_err) {
      // Ignore storage access errors in restricted WebView or non-browser tests.
    }
  }

  const storedAuthSession = readStoredAuthSession();

  const state = {
    apiBaseUrl: resolveInitialApiBaseUrl(),
    appMode: storedAuthSession ? storedAuthSession.appMode : "mock",
    isSimulation: storedAuthSession ? storedAuthSession.appMode === "mock" : true,
    supabaseHost: "",
    token: storedAuthSession ? storedAuthSession.token : null,
    currentUser: storedAuthSession
      ? storedAuthSession.user
        ? { ...storedAuthSession.user }
        : null
      : { ...DEMO_ACCOUNTS.organizer },
    explicitGuest: storedAuthSession ? storedAuthSession.explicitGuest : false,
    selectedTournamentId: readStoredSelectedTournamentId() || DEFAULT_SELECTED_TOURNAMENT_ID,
  };

  window.TurnamenConfig = {
    DEMO_ACCOUNTS,
    resolveInitialApiBaseUrl,
    isValidLocalApiBaseUrl,
    isTokenExpired,
    getState() {
      return {
        ...state,
        currentUser: state.currentUser ? { ...state.currentUser } : null,
      };
    },
    setRuntimeInfo(info) {
      if (!info || typeof info !== "object") {
        return;
      }
      const source =
        info.data && typeof info.data === "object" && !info.app_mode
          ? info.data
          : info;

      if (typeof source.api_base_url === "string" && isValidLocalApiBaseUrl(source.api_base_url)) {
        let nextApiBaseUrl = source.api_base_url.trim().replace(/\/+$/, "");
        try {
          const loc = window.location;
          if (
            typeof window.eel === "undefined" &&
            loc &&
            (loc.protocol === "http:" || loc.protocol === "https:") &&
            loc.hostname === "localhost"
          ) {
            const parsedMatch = /^https?:\/\/127\.0\.0\.1(?::(\d{1,5}))?\/api\/v1$/.exec(
              nextApiBaseUrl
            );
            const locPort = loc.port || (loc.protocol === "https:" ? "443" : "80");
            const sourcePort =
              parsedMatch && parsedMatch[1]
                ? parsedMatch[1]
                : nextApiBaseUrl.startsWith("https://")
                  ? "443"
                  : "80";
            if (parsedMatch && sourcePort === locPort) {
              const portPart = loc.port ? `:${loc.port}` : "";
              nextApiBaseUrl = `${loc.protocol}//localhost${portPart}/api/v1`;
            }
          }
        } catch (_err) {
          // Ignore location access errors in non-browser environments.
        }
        state.apiBaseUrl = nextApiBaseUrl;
      }

      if (typeof source.app_mode === "string") {
        const normalizedMode = source.app_mode.trim().toLowerCase();
        if (normalizedMode === "mock" || normalizedMode === "supabase") {
          state.appMode = normalizedMode;
          state.isSimulation = normalizedMode === "mock";
        }
      } else if (typeof source.is_simulation === "boolean") {
        state.isSimulation = source.is_simulation;
        state.appMode = source.is_simulation ? "mock" : "supabase";
      }

      if (state.isSimulation) {
        state.supabaseHost = "";
      } else if (typeof source.supabase_host === "string") {
        const cleanHost = source.supabase_host.trim().toLowerCase();
        state.supabaseHost = /^[a-z0-9.-]+$/.test(cleanHost) ? cleanHost : "";
      }

      if (state.token && isTokenExpired(state.token)) {
        state.token = null;
        state.currentUser = null;
        clearStoredAuthSession();
      } else if (!state.isSimulation && state.token && state.token.startsWith("tok_")) {
        state.token = null;
        state.currentUser = null;
        clearStoredAuthSession();
      } else if (state.isSimulation && state.token && !state.token.startsWith("tok_")) {
        state.token = null;
        state.currentUser = state.explicitGuest ? null : { ...DEMO_ACCOUNTS.organizer };
        clearStoredAuthSession();
      }

      if (!state.isSimulation && !state.token) {
        state.currentUser = null;
      } else if (state.isSimulation && !state.currentUser && !state.explicitGuest) {
        state.currentUser = { ...DEMO_ACCOUNTS.organizer };
      }
    },
    setAuthSession(token, user) {
      const cleanToken = typeof token === "string" && token.trim() ? token.trim() : null;
      if (cleanToken && isTokenExpired(cleanToken)) {
        state.token = null;
        state.currentUser = null;
        state.explicitGuest = true;
        clearStoredAuthSession();
        return;
      }
      state.token = cleanToken;
      state.currentUser = user && typeof user === "object" ? { ...user } : null;
      state.explicitGuest = !state.currentUser;
      if (state.token && state.currentUser) {
        writeStoredAuthSession({
          appMode: state.appMode,
          token: state.token,
          user: state.currentUser,
          explicitGuest: false,
        });
      } else {
        clearStoredAuthSession();
      }
    },
    clearAuthSession() {
      state.token = null;
      clearStoredAuthSession();
      if (state.isSimulation && state.appMode === "mock" && !state.explicitGuest) {
        state.currentUser = { ...DEMO_ACCOUNTS.player };
      } else {
        state.currentUser = null;
      }
    },
    enterGuestMode() {
      state.token = null;
      state.currentUser = null;
      state.explicitGuest = true;
      state.selectedTournamentId = null;
      clearStoredAuthSession();
      clearStoredSelectedTournamentId();
    },
    setSimulatedRole(roleName) {
      if (!state.isSimulation || state.appMode !== "mock") {
        return state.currentUser ? { ...state.currentUser } : null;
      }
      if (roleName === "guest") {
        state.token = null;
        state.currentUser = null;
        state.explicitGuest = true;
        clearStoredAuthSession();
        return null;
      }
      if (typeof roleName === "string" && DEMO_ACCOUNTS[roleName]) {
        state.currentUser = { ...DEMO_ACCOUNTS[roleName] };
        state.token = null;
        state.explicitGuest = false;
        writeStoredAuthSession({
          appMode: "mock",
          token: null,
          user: state.currentUser,
          simulatedRole: roleName,
          explicitGuest: false,
        });
      }
      return state.currentUser ? { ...state.currentUser } : null;
    },
    setSelectedTournamentId(tournamentId) {
      const clean = normalizeTournamentId(tournamentId);
      if (clean) {
        state.selectedTournamentId = clean;
        writeStoredSelectedTournamentId(clean);
      }
    },
    clearSelectedTournamentId() {
      state.selectedTournamentId = null;
      clearStoredSelectedTournamentId();
    },
  };
})(window);
