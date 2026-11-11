/**
 * Turnamen.in — Frontend Runtime Configuration (`window.TurnamenConfig`)
 * Owner: Fikri (System Integration & Python Eel Developer)
 */
(function (window) {
  "use strict";

  const DEMO_ACCOUNTS = {
    super_admin: {
      id: "11111111-1111-4111-8111-111111111101",
      email: "admin@turnamen.in",
      username: "superadmin",
      full_name: "Raka Pratama (Super Admin)",
      role: "super_admin",
    },
    organizer: {
      id: "11111111-1111-4111-8111-111111111102",
      email: "organizer@turnamen.in",
      username: "garuda_eo",
      full_name: "Nadia Kusuma (Tournament Organizer)",
      role: "organizer",
    },
    committee: {
      id: "11111111-1111-4111-8111-111111111103",
      email: "committee@turnamen.in",
      username: "panitia_utama",
      full_name: "Bima Saputra (Head Committee)",
      role: "committee",
    },
    team_captain: {
      id: "11111111-1111-4111-8111-111111111104",
      email: "captain@turnamen.in",
      username: "garuda_capt",
      full_name: "Dimas Aditya (Team Captain)",
      role: "team_captain",
    },
    player: {
      id: "11111111-1111-4111-8111-111111111105",
      email: "player@turnamen.in",
      username: "aruna_player",
      full_name: "Rizky Maulana (Player)",
      role: "player",
    },
  };

  const state = {
    apiBaseUrl: "http://127.0.0.1:5000/api/v1",
    appMode: "mock",
    isSimulation: true,
    token: null,
    currentUser: DEMO_ACCOUNTS.organizer,
    selectedTournamentId: "33333333-3333-4333-8333-333333333301",
  };

  window.TurnamenConfig = {
    DEMO_ACCOUNTS,
    getState() {
      return { ...state };
    },
    setRuntimeInfo(info) {
      if (info && info.api_base_url) {
        state.apiBaseUrl = info.api_base_url;
      }
      if (info && info.app_mode) {
        state.appMode = info.app_mode;
        state.isSimulation = info.app_mode === "mock";
      }
    },
    setAuthSession(token, user) {
      state.token = token || null;
      state.currentUser = user || null;
    },
    setSimulatedRole(roleName) {
      if (DEMO_ACCOUNTS[roleName]) {
        state.currentUser = { ...DEMO_ACCOUNTS[roleName] };
        state.token = null;
      }
      return state.currentUser;
    },
    setSelectedTournamentId(tournamentId) {
      state.selectedTournamentId = tournamentId;
    },
  };
})(window);
