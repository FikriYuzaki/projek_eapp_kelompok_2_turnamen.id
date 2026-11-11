/**
 * Turnamen.in — Centralized REST API Client (`window.TurnamenAPI`)
 * Owner: Fikri (System Integration & Python Eel Developer)
 * Implements all contract methods defined in `docs/contracts/frontend-contract.md`.
 */
(function (window) {
  "use strict";

  async function request(method, path, payload = null) {
    const cfg = window.TurnamenConfig.getState();
    const headers = {
      "Content-Type": "application/json",
    };

    if (cfg.token) {
      headers["Authorization"] = `Bearer ${cfg.token}`;
    } else if (cfg.isSimulation && cfg.currentUser) {
      headers["X-Mock-Role"] = cfg.currentUser.role;
      headers["X-Mock-User-Id"] = cfg.currentUser.id;
    }

    // Try Eel bridge proxy first if running inside Python Eel desktop container
    if (window.TurnamenBridge && window.TurnamenBridge.hasEel()) {
      const bridged = await window.TurnamenBridge.proxyApiRequest(
        method,
        path,
        payload,
        headers
      );
      if (bridged) {
        return bridged;
      }
    }

    const url = `${cfg.apiBaseUrl}${path.startsWith("/") ? path : "/" + path}`;
    const options = {
      method: method.toUpperCase(),
      headers,
    };
    if (payload !== null && method.toUpperCase() !== "GET") {
      options.body = JSON.stringify(payload);
    }

    try {
      const response = await fetch(url, options);
      const data = await response.json();
      return data;
    } catch (err) {
      return {
        success: false,
        message: "Tidak dapat terhubung ke server API lokal (127.0.0.1:5000).",
        error: {
          code: "NETWORK_ERROR",
          details: { reason: String(err) },
        },
      };
    }
  }

  window.TurnamenAPI = {
    request,

    // Health
    getHealth() {
      return request("GET", "/health");
    },

    // Auth
    async login(email, password) {
      const res = await request("POST", "/auth/login", { email, password });
      if (res.success && res.data) {
        window.TurnamenConfig.setAuthSession(res.data.token, res.data.user);
      }
      return res;
    },
    async register(payload) {
      const res = await request("POST", "/auth/register", payload);
      if (res.success && res.data) {
        window.TurnamenConfig.setAuthSession(res.data.token, res.data.user);
      }
      return res;
    },
    async logout() {
      const res = await request("POST", "/auth/logout");
      window.TurnamenConfig.setSimulatedRole("player");
      return res;
    },
    getCurrentUser() {
      return request("GET", "/auth/me");
    },
    setSimulatedRole(roleName) {
      return window.TurnamenConfig.setSimulatedRole(roleName);
    },

    // Games
    getGames() {
      return request("GET", "/games");
    },
    getGameById(gameId) {
      return request("GET", `/games/${encodeURIComponent(gameId)}`);
    },

    // Tournaments
    getTournaments(filters = {}) {
      const params = new URLSearchParams();
      if (filters.status) params.set("status", filters.status);
      if (filters.game_id) params.set("game_id", filters.game_id);
      const qs = params.toString();
      return request("GET", `/tournaments${qs ? "?" + qs : ""}`);
    },
    getTournamentById(tournamentId) {
      return request("GET", `/tournaments/${encodeURIComponent(tournamentId)}`);
    },
    createTournament(payload) {
      return request("POST", "/tournaments", payload);
    },
    updateTournament(tournamentId, payload) {
      return request("PATCH", `/tournaments/${encodeURIComponent(tournamentId)}`, payload);
    },
    deleteTournament(tournamentId) {
      return request("DELETE", `/tournaments/${encodeURIComponent(tournamentId)}`);
    },

    // Teams
    getTeams(gameId = "") {
      const qs = gameId ? `?game_id=${encodeURIComponent(gameId)}` : "";
      return request("GET", `/teams${qs}`);
    },
    getTeamById(teamId) {
      return request("GET", `/teams/${encodeURIComponent(teamId)}`);
    },
    createTeam(payload) {
      return request("POST", "/teams", payload);
    },
    updateTeam(teamId, payload) {
      return request("PATCH", `/teams/${encodeURIComponent(teamId)}`, payload);
    },
    addTeamMember(teamId, payload) {
      return request("POST", `/teams/${encodeURIComponent(teamId)}/members`, payload);
    },

    // Registrations
    getTournamentRegistrations(tournamentId) {
      return request(
        "GET",
        `/tournaments/${encodeURIComponent(tournamentId)}/registrations`
      );
    },
    registerTeamToTournament(tournamentId, payload) {
      return request(
        "POST",
        `/tournaments/${encodeURIComponent(tournamentId)}/registrations`,
        payload
      );
    },
    updateRegistrationStatus(registrationId, status, notes = "") {
      return request(
        "PATCH",
        `/registrations/${encodeURIComponent(registrationId)}/status`,
        { status, notes }
      );
    },

    // Matches & Bracket
    getTournamentMatches(tournamentId) {
      return request("GET", `/tournaments/${encodeURIComponent(tournamentId)}/matches`);
    },
    generateBracket(tournamentId, payload = {}) {
      return request(
        "POST",
        `/tournaments/${encodeURIComponent(tournamentId)}/bracket/generate`,
        payload
      );
    },
    submitMatchResult(matchId, payload) {
      return request(
        "PATCH",
        `/matches/${encodeURIComponent(matchId)}/result`,
        payload
      );
    },

    // Announcements & Reports
    getAnnouncements(tournamentId) {
      return request(
        "GET",
        `/tournaments/${encodeURIComponent(tournamentId)}/announcements`
      );
    },
    createAnnouncement(tournamentId, payload) {
      return request(
        "POST",
        `/tournaments/${encodeURIComponent(tournamentId)}/announcements`,
        payload
      );
    },
    getTournamentReport(tournamentId) {
      return request("GET", `/tournaments/${encodeURIComponent(tournamentId)}/reports`);
    },
    getTournamentStandings(tournamentId) {
      return request(
        "GET",
        `/tournaments/${encodeURIComponent(tournamentId)}/standings`
      );
    },
  };
})(window);
