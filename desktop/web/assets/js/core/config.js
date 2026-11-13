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
        loc.port &&
        loc.port !== DEFAULT_EEL_PORT &&
        typeof window.eel === "undefined"
      ) {
        return `http://127.0.0.1:${loc.port}/api/v1`;
      }
    } catch (_err) {
      // Ignore location access errors in non-browser environments.
    }
    return DEFAULT_API_BASE_URL;
  }

  function isValidLocalApiBaseUrl(url) {
    if (typeof url !== "string") return false;
    return /^http:\/\/(127\.0\.0\.1|localhost):\d{1,5}\/api\/v1\/?$/.test(url.trim());
  }

  const state = {
    apiBaseUrl: resolveInitialApiBaseUrl(),
    appMode: "mock",
    isSimulation: true,
    token: null,
    currentUser: { ...DEMO_ACCOUNTS.organizer },
    selectedTournamentId: "33333333-3333-4333-8333-333333333301",
  };

  window.TurnamenConfig = {
    DEMO_ACCOUNTS,
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
        state.apiBaseUrl = source.api_base_url.trim().replace(/\/+$/, "");
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

      if (!state.isSimulation && !state.token) {
        state.currentUser = null;
      } else if (state.isSimulation && !state.currentUser) {
        state.currentUser = { ...DEMO_ACCOUNTS.organizer };
      }
    },
    setAuthSession(token, user) {
      state.token = typeof token === "string" && token.trim() ? token.trim() : null;
      state.currentUser = user && typeof user === "object" ? { ...user } : null;
    },
    clearAuthSession() {
      state.token = null;
      if (state.isSimulation && state.appMode === "mock") {
        state.currentUser = { ...DEMO_ACCOUNTS.player };
      } else {
        state.currentUser = null;
      }
    },
    setSimulatedRole(roleName) {
      if (!state.isSimulation || state.appMode !== "mock") {
        return state.currentUser ? { ...state.currentUser } : null;
      }
      if (typeof roleName === "string" && DEMO_ACCOUNTS[roleName]) {
        state.currentUser = { ...DEMO_ACCOUNTS[roleName] };
        state.token = null;
      }
      return state.currentUser ? { ...state.currentUser } : null;
    },
    setSelectedTournamentId(tournamentId) {
      if (typeof tournamentId === "string" && tournamentId.trim()) {
        state.selectedTournamentId = tournamentId.trim();
      }
    },
  };
})(window);
