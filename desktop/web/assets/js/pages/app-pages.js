/**
 * Turnamen.in: Role-Based Esports Experience Controller (`window.TurnamenApp`)
 * Owner: Fikri (System Integration & Desktop UI/UX)
 * Implements distinct Competitive (Player, Team Captain) & Management (Organizer, Committee, Super Admin)
 * experiences backed strictly by `docs/contracts/role-permissions.md` and `window.TurnamenAPI`.
 */
(function (window, document) {
  "use strict";

  const PAGE_TITLES = {
    dashboard: "Dashboard Arena",
    "tournament-list": "Daftar Turnamen",
    "tournament-detail": "Detail & Peserta Turnamen",
    "team-management": "Manajemen Tim & Roster",
    "game-management": "Manajemen Game",
    "match-management": "Jadwal & Skor Pertandingan",
    bracket: "Bracket Turnamen",
    announcements: "Pengumuman Kompetisi",
    reports: "Laporan & Klasemen",
    profile: "Profil Pengguna & Status Sistem",
    login: "Autentikasi Akun",
  };

  const ROLE_NAV_CONFIG = {
    player: {
      experienceLabel: "Competitive Arena",
      dashboardTitle: "Arena Utama Player",
      sections: [
        {
          label: "Eksplorasi Arena",
          items: [
            { page: "dashboard", label: "Arena Utama", icon: "dashboard" },
            { page: "tournament-list", label: "Jelajah Turnamen", icon: "trophy" },
          ],
        },
        {
          label: "Kompetisi",
          items: [
            { page: "bracket", label: "Bracket & Match", icon: "bracket" },
            { page: "reports", label: "Klasemen", icon: "chart" },
            { page: "team-management", label: "Tim Esports", icon: "shield" },
            { page: "announcements", label: "Pengumuman", icon: "megaphone" },
          ],
        },
        {
          label: "Akun",
          items: [{ page: "profile", label: "Profil Saya", icon: "user" }],
        },
      ],
    },
    team_captain: {
      experienceLabel: "Team Command",
      dashboardTitle: "Markas Tim & Kompetisi",
      sections: [
        {
          label: "Markas Kapten",
          items: [
            { page: "dashboard", label: "Markas Tim", icon: "dashboard" },
            { page: "team-management", label: "Tim & Roster Saya", icon: "shield" },
          ],
        },
        {
          label: "Kompetisi",
          items: [
            { page: "tournament-list", label: "Jelajah Turnamen", icon: "trophy" },
            { page: "tournament-detail", label: "Registrasi & Peserta", icon: "detail" },
            { page: "bracket", label: "Bracket & Jadwal", icon: "bracket" },
            { page: "announcements", label: "Pengumuman", icon: "megaphone" },
            { page: "reports", label: "Klasemen", icon: "chart" },
          ],
        },
        {
          label: "Akun",
          items: [{ page: "profile", label: "Profil Kapten", icon: "user" }],
        },
      ],
    },
    committee: {
      experienceLabel: "Match Operations",
      dashboardTitle: "Dashboard Operasional Panitia",
      sections: [
        {
          label: "Operasional Pertandingan",
          items: [
            { page: "dashboard", label: "Dashboard Operasional", icon: "dashboard" },
            { page: "tournament-detail", label: "Verifikasi Peserta", icon: "detail" },
            { page: "match-management", label: "Jadwal & Skor Match", icon: "swords" },
            { page: "bracket", label: "Bracket Turnamen", icon: "bracket" },
          ],
        },
        {
          label: "Komunikasi & Laporan",
          items: [
            { page: "announcements", label: "Pengumuman", icon: "megaphone" },
            { page: "reports", label: "Laporan & Klasemen", icon: "chart" },
            { page: "tournament-list", label: "Daftar Turnamen", icon: "trophy" },
          ],
        },
        {
          label: "Akun",
          items: [{ page: "profile", label: "Profil Panitia", icon: "user" }],
        },
      ],
    },
    organizer: {
      experienceLabel: "Tournament Suite",
      dashboardTitle: "Dashboard Tournament Organizer",
      sections: [
        {
          label: "Manajemen Turnamen",
          items: [
            { page: "dashboard", label: "Dashboard Organizer", icon: "dashboard" },
            { page: "tournament-list", label: "Kelola Turnamen", icon: "trophy" },
            { page: "tournament-detail", label: "Verifikasi Peserta", icon: "detail" },
            { page: "match-management", label: "Jadwal & Skor Match", icon: "swords" },
            { page: "bracket", label: "Bracket Turnamen", icon: "bracket" },
          ],
        },
        {
          label: "Komunikasi & Laporan",
          items: [
            { page: "announcements", label: "Pengumuman", icon: "megaphone" },
            { page: "reports", label: "Laporan & Klasemen", icon: "chart" },
          ],
        },
        {
          label: "Akun",
          items: [{ page: "profile", label: "Profil Organizer", icon: "user" }],
        },
      ],
    },
    super_admin: {
      experienceLabel: "System Control",
      dashboardTitle: "Dashboard Administrasi Sistem",
      sections: [
        {
          label: "Administrasi Sistem",
          items: [
            { page: "dashboard", label: "Dashboard Sistem", icon: "dashboard" },
            { page: "game-management", label: "Manajemen Game", icon: "image" },
            { page: "tournament-list", label: "Kelola Turnamen", icon: "trophy" },
            { page: "tournament-detail", label: "Verifikasi & Peserta", icon: "detail" },
            { page: "team-management", label: "Manajemen Tim", icon: "shield" },
            { page: "match-management", label: "Jadwal & Skor Match", icon: "swords" },
            { page: "bracket", label: "Bracket Turnamen", icon: "bracket" },
          ],
        },
        {
          label: "Komunikasi & Laporan",
          items: [
            { page: "announcements", label: "Pengumuman", icon: "megaphone" },
            { page: "reports", label: "Laporan & Klasemen", icon: "chart" },
          ],
        },
        {
          label: "Akun",
          items: [{ page: "profile", label: "Profil Admin", icon: "user" }],
        },
      ],
    },
    guest: {
      experienceLabel: "Public Arena",
      dashboardTitle: "Arena Publik Turnamen.in",
      sections: [
        {
          label: "Eksplorasi Publik",
          items: [
            { page: "dashboard", label: "Arena Publik", icon: "dashboard" },
            { page: "tournament-list", label: "Jelajah Turnamen", icon: "trophy" },
            { page: "bracket", label: "Bracket", icon: "bracket" },
            { page: "announcements", label: "Pengumuman", icon: "megaphone" },
            { page: "reports", label: "Klasemen", icon: "chart" },
          ],
        },
        {
          label: "Autentikasi",
          items: [{ page: "login", label: "Masuk / Daftar", icon: "login" }],
        },
      ],
    },
  };

  const ROLE_CAPABILITIES = {
    super_admin: [
      "Akses penuh administrasi turnamen, verifikasi peserta, manajemen tim, bracket, pengesahan skor, pengumuman, dan laporan sistem.",
    ],
    organizer: [
      "Membuat turnamen baru serta mengubah atau menghapus turnamen milik sendiri.",
      "Memverifikasi pendaftaran tim, menyusun bracket, mengesahkan skor, dan mempublikasikan pengumuman pada turnamen miliknya.",
    ],
    committee: [
      "Memverifikasi pendaftaran peserta pada turnamen yang ditugaskan.",
      "Menyusun bracket, menginput atau mengesahkan skor pertandingan, dan mempublikasikan pengumuman.",
    ],
    team_captain: [
      "Membuat tim baru, memperbarui profil tim milik sendiri, dan menambah anggota roster.",
      "Mendaftarkan tim milik sendiri ke turnamen yang membuka pendaftaran serta memantau jadwal dan bracket.",
    ],
    player: [
      "Menjelajahi katalog game, turnamen aktif dan mendatang, profil tim, jadwal pertandingan, bracket, pengumuman, dan klasemen.",
      "Melihat profil pribadi (akses read-only pada operasional turnamen).",
    ],
  };

  let currentPage = "dashboard";
  let navigationSeq = 0;
  let loginActiveTab = "login";
  let pendingRecoverySession = null;
  let pendingAuthNotice = null;
  let selectedCaptainTeamId = "";
  let tournamentFilterState = { status: "", gameId: "", search: "" };
  let teamFilterState = { gameId: "", search: "" };
  let matchRoundFilter = "";
  let matchStatusFilter = "";
  let announcementPriorityFilter = "";

  const inFlightActions = new Set();
  const pendingMatchIdempotency = new Map();
  const pendingArtworkDrafts = new Map();
  const artworkUploadState = new Map();
  const uiPageSnapshots = new Map();

  function getPageSnapshotKey(pageName) {
    const roleKey = getActiveRoleKey();
    const user = getCurrentUserSafe();
    const uid = user && user.id ? String(user.id) : "guest";
    const tid = getRuntimeState().selectedTournamentId || "";
    if (pageName === "tournament-list") {
      return `${roleKey}:${uid}:${pageName}:${tournamentFilterState.status}:${tournamentFilterState.gameId}:${tournamentFilterState.search}`;
    }
    if (pageName === "team-management") {
      return `${roleKey}:${uid}:${pageName}:${teamFilterState.gameId}:${teamFilterState.search}`;
    }
    if (pageName === "announcements") {
      return `${roleKey}:${uid}:${pageName}:${tid}:${announcementPriorityFilter}`;
    }
    if (pageName === "reports") {
      return `${roleKey}:${uid}:${pageName}:${tid}`;
    }
    return `${roleKey}:${uid}:${pageName}`;
  }

  function clearUiPageSnapshots() {
    uiPageSnapshots.clear();
  }

  function generateClientIdempotencyKey() {
    if (window.TurnamenAPI && typeof window.TurnamenAPI.createIdempotencyKey === "function") {
      return window.TurnamenAPI.createIdempotencyKey();
    }
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `idem-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  }

  function resetRoleScopedUiState() {
    selectedCaptainTeamId = "";
    tournamentFilterState = { status: "", gameId: "", search: "" };
    teamFilterState = { gameId: "", search: "" };
    matchRoundFilter = "";
    matchStatusFilter = "";
    announcementPriorityFilter = "";
    cachedTournaments = [];
    adminGamesCache = [];
    pendingMatchIdempotency.clear();
    pendingArtworkDrafts.clear();
    artworkUploadState.clear();
    clearUiPageSnapshots();
  }

  function isRetryableSubmissionError(res) {
    if (!res || res.success) return false;
    const code = res.error && res.error.code ? String(res.error.code) : "";
    const statusCode = Number((res.error && res.error.details && res.error.details.status_code) || 0);
    return (
      code === "REQUEST_TIMEOUT" ||
      code === "NETWORK_ERROR" ||
      code === "BRIDGE_TIMEOUT" ||
      code === "BRIDGE_UNCERTAIN_STATE" ||
      statusCode >= 500
    );
  }

  function getOrCreateMatchIdempotencyKey(slotKey, fingerprint) {
    const existing = pendingMatchIdempotency.get(slotKey);
    if (existing && existing.fingerprint === fingerprint && existing.key) {
      return existing.key;
    }
    const freshKey = generateClientIdempotencyKey();
    pendingMatchIdempotency.set(slotKey, { fingerprint, key: freshKey });
    return freshKey;
  }

  function clearMatchIdempotencyKey(slotKey) {
    pendingMatchIdempotency.delete(slotKey);
  }

  async function withSubmissionGuard(lockKey, triggerEl, loadingLabel, taskFn, options = {}) {
    if (inFlightActions.has(lockKey)) {
      window.TurnamenUI.showToast(
        "Permintaan sebelumnya masih diproses. Mohon tunggu sebentar.",
        "info",
        { group: `busy-${lockKey}` }
      );
      return null;
    }

    inFlightActions.add(lockKey);
    const btn = triggerEl && triggerEl.nodeType === 1 ? triggerEl : null;
    const extraButtons = Array.isArray(options.disableSelectors)
      ? options.disableSelectors
          .map((sel) => document.querySelector(sel))
          .filter((el) => el && el !== btn)
      : [];
    const prevHtml = btn ? btn.innerHTML : "";
    const prevDisabled = btn ? btn.disabled : false;

    if (options.lockModal && window.TurnamenUI && typeof window.TurnamenUI.setModalBusy === "function") {
      window.TurnamenUI.setModalBusy(true);
    }
    if (btn) {
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
      if (loadingLabel) {
        btn.innerHTML = `<span class="arena-spinner-sm" aria-hidden="true"></span><span>${window.TurnamenUI.escapeHtml(loadingLabel)}</span>`;
      }
    }
    extraButtons.forEach((el) => {
      el.disabled = true;
    });

    try {
      return await taskFn();
    } finally {
      inFlightActions.delete(lockKey);
      if (options.lockModal && window.TurnamenUI && typeof window.TurnamenUI.setModalBusy === "function") {
        window.TurnamenUI.setModalBusy(false);
      }
      if (btn && btn.isConnected !== false) {
        btn.disabled = prevDisabled;
        btn.removeAttribute("aria-busy");
        if (!options.skipRestoreHtml) {
          btn.innerHTML = prevHtml;
        }
      }
      extraButtons.forEach((el) => {
        if (el && el.isConnected !== false) el.disabled = false;
      });
    }
  }

  function isModalRequestStale(startNavSeq, startRoleKey) {
    return startNavSeq !== navigationSeq || startRoleKey !== getActiveRoleKey();
  }

  const gamesState = { items: [], loaded: false, error: null };
  let adminGamesCache = [];
  let cachedTournaments = [];
  let bracketResizeListenerBound = false;
  let bracketResizeTimer = null;

  function drawBracketConnectors(stageEl) {
    if (!stageEl) return;
    const svgEl = stageEl.querySelector(".bracket-connectors-svg");
    if (!svgEl) return;

    while (svgEl.firstChild) {
      svgEl.removeChild(svgEl.firstChild);
    }

    const stageRect = stageEl.getBoundingClientRect();
    const width = Math.max(stageEl.scrollWidth || 0, Math.round(stageRect.width));
    const height = Math.max(stageEl.scrollHeight || 0, Math.round(stageRect.height));
    if (width <= 0 || height <= 0) return;

    svgEl.setAttribute("width", String(width));
    svgEl.setAttribute("height", String(height));
    svgEl.setAttribute("viewBox", `0 0 ${width} ${height}`);

    const cards = stageEl.querySelectorAll("[data-match-id][data-next-match-id]");
    const ns = "http://www.w3.org/2000/svg";

    cards.forEach((srcCard) => {
      const nextId = srcCard.getAttribute("data-next-match-id");
      if (!nextId) return;
      const dstCard = stageEl.querySelector(`[data-match-id="${CSS.escape(nextId)}"]`);
      if (!dstCard) return;

      const slot = srcCard.getAttribute("data-next-slot") || "";
      const dstTarget =
        (slot ? dstCard.querySelector(`[data-slot="${CSS.escape(slot)}"]`) : null) || dstCard;

      const srcRect = srcCard.getBoundingClientRect();
      const dstRect = dstCard.getBoundingClientRect();
      const dstRowRect = dstTarget.getBoundingClientRect();

      const x1 = Math.round(srcRect.right - stageRect.left);
      const y1 = Math.round(srcRect.top + srcRect.height / 2 - stageRect.top);
      const x2 = Math.round(dstRect.left - stageRect.left);
      const y2 = Math.round(dstRowRect.top + dstRowRect.height / 2 - stageRect.top);
      if (x2 <= x1) return;

      const midX = Math.round(x1 + (x2 - x1) * 0.5);
      const isDecided = srcCard.getAttribute("data-completed") === "true";

      const path = document.createElementNS(ns, "path");
      path.setAttribute("class", `bracket-connector-path ${isDecided ? "is-decided" : "is-pending"}`);
      path.setAttribute("d", `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`);
      svgEl.appendChild(path);
    });
  }

  function scheduleBracketConnectors() {
    const redraw = () => {
      const stageEl = document.getElementById("bracket-stage");
      if (stageEl) drawBracketConnectors(stageEl);
    };
    window.requestAnimationFrame(redraw);
    if (document.fonts && document.fonts.ready && typeof document.fonts.ready.then === "function") {
      document.fonts.ready.then(() => {
        window.requestAnimationFrame(redraw);
      });
    }
    if (!bracketResizeListenerBound) {
      bracketResizeListenerBound = true;
      window.addEventListener("resize", () => {
        if (bracketResizeTimer) window.clearTimeout(bracketResizeTimer);
        bracketResizeTimer = window.setTimeout(redraw, 90);
      });
    }
  }

  // =========================================================================
  // AUTH, ROLE EXPERIENCE & RBAC HELPERS (UX-ONLY; BACKEND ENFORCES RBAC)
  // =========================================================================
  function getRuntimeState() {
    if (!window.TurnamenConfig || typeof window.TurnamenConfig.getState !== "function") {
      return {
        apiBaseUrl: "",
        appMode: "mock",
        isSimulation: true,
        token: null,
        currentUser: null,
        selectedTournamentId: "",
      };
    }
    return window.TurnamenConfig.getState();
  }

  function isMockMode() {
    const state = getRuntimeState();
    return Boolean(state.isSimulation && state.appMode === "mock");
  }

  function getCurrentUserSafe() {
    const state = getRuntimeState();
    return state.currentUser && typeof state.currentUser === "object" ? state.currentUser : null;
  }

  function getActiveRoleKey() {
    const user = getCurrentUserSafe();
    if (!user || !user.role) return "guest";
    const key = String(user.role).toLowerCase();
    return ROLE_NAV_CONFIG[key] ? key : "player";
  }

  function isCompetitiveRole(roleKey = getActiveRoleKey()) {
    return roleKey === "player" || roleKey === "team_captain" || roleKey === "guest";
  }

  function isManagementRole(roleKey = getActiveRoleKey()) {
    return roleKey === "super_admin" || roleKey === "organizer" || roleKey === "committee";
  }

  function getCommitteeTournamentAssignment(tournament, user) {
    if (!tournament || !user) return null;
    if (typeof tournament.is_assigned_committee === "boolean") {
      return tournament.is_assigned_committee;
    }
    if (Array.isArray(tournament.staff_user_ids)) {
      return tournament.staff_user_ids.includes(user.id);
    }
    if (Array.isArray(tournament.assigned_staff_ids)) {
      return tournament.assigned_staff_ids.includes(user.id);
    }
    return null;
  }

  function renderCommitteeAssignmentNotice(tournament) {
    const user = getCurrentUserSafe();
    if (!user || String(user.role || "").toLowerCase() !== "committee" || !tournament) {
      return "";
    }
    const assigned = getCommitteeTournamentAssignment(tournament, user);
    if (assigned === true) {
      return "";
    }
    if (assigned === false) {
      return `
        <div class="notice-banner notice-banner-warning" role="status">
          <div>
            <strong>Penugasan Panitia Tidak Terdaftar:</strong>
            <span>Akun panitia Anda tidak ditugaskan pada turnamen ini, sehingga aksi mutasi tidak ditampilkan. Otorisasi akhir tetap ditegakkan oleh server API dan RLS.</span>
          </div>
        </div>
      `;
    }
    return `
      <div class="notice-banner notice-banner-warning" role="status">
        <div>
          <strong>Penugasan Panitia Belum Dapat Diverifikasi:</strong>
          <span>Data penugasan panitia (tournament_staff) belum tersedia pada respons API turnamen ini, sehingga tombol aksi mutasi tidak ditampilkan untuk menghindari permintaan HTTP 403. Otorisasi akhir tetap ditegakkan oleh server API dan RLS.</span>
        </div>
      </div>
    `;
  }

  function canPerform(action, context = {}) {
    const user = getCurrentUserSafe();
    if (!user || !user.role) return false;
    const role = String(user.role).toLowerCase();

    switch (action) {
      case "tournament:create":
        return role === "super_admin" || role === "organizer";
      case "tournament:edit":
      case "tournament:delete":
        if (role === "super_admin") return true;
        return (
          role === "organizer" &&
          Boolean(context.tournament && context.tournament.organizer_id === user.id)
        );
      case "team:create":
        return role === "super_admin" || role === "team_captain";
      case "team:manage":
        if (role === "super_admin") return true;
        return (
          role === "team_captain" &&
          Boolean(context.team && context.team.captain_id === user.id)
        );
      case "registration:create":
        return role === "super_admin" || role === "team_captain";
      case "registration:verify":
      case "bracket:generate":
      case "match:submit_result":
      case "announcement:create":
        if (role === "super_admin") return true;
        if (role === "committee") {
          return getCommitteeTournamentAssignment(context.tournament, user) === true;
        }
        if (role === "organizer") {
          return Boolean(context.tournament && context.tournament.organizer_id === user.id);
        }
        return false;
      default:
        return false;
    }
  }

  const ALLOWED_TOURNAMENT_ACTION_ROLES = {
    "tournament:edit": ["super_admin", "organizer"],
    "tournament:delete": ["super_admin", "organizer"],
    "registration:verify": ["super_admin", "organizer", "committee"],
    "bracket:generate": ["super_admin", "organizer", "committee"],
    "match:submit_result": ["super_admin", "organizer", "committee"],
    "announcement:create": ["super_admin", "organizer", "committee"],
  };

  function getDeniedActionMessage(action, tournament) {
    const user = getCurrentUserSafe();
    if (!user || !user.role) {
      return "Silakan masuk terlebih dahulu untuk melakukan aksi ini.";
    }
    const role = String(user.role).toLowerCase();
    if (role === "committee" && tournament) {
      const assigned = getCommitteeTournamentAssignment(tournament, user);
      if (assigned === false) {
        return "Akun panitia Anda tidak ditugaskan pada turnamen ini.";
      }
      if (assigned === null) {
        return "Penugasan panitia pada turnamen ini belum dapat diverifikasi dari data API.";
      }
    }
    if (role === "organizer" && tournament && tournament.organizer_id !== user.id) {
      return "Anda hanya dapat mengelola turnamen milik Anda sendiri.";
    }
    if (action === "tournament:create") {
      return "Hanya Organizer atau Super Admin yang dapat membuat turnamen.";
    }
    if (action === "team:create") {
      return "Hanya Team Captain atau Super Admin yang dapat membuat tim.";
    }
    return "Anda tidak memiliki izin melakukan aksi ini.";
  }

  async function resolveAuthorizedTournament(tournamentId, action) {
    const user = getCurrentUserSafe();
    const role = user && user.role ? String(user.role).toLowerCase() : "";
    const allowedRoles = ALLOWED_TOURNAMENT_ACTION_ROLES[action] || [];
    if (!user || !allowedRoles.includes(role)) {
      window.TurnamenUI.showToast(getDeniedActionMessage(action, null), "danger");
      return null;
    }
    const tid = String(tournamentId || getRuntimeState().selectedTournamentId || "").trim();
    if (!tid) {
      window.TurnamenUI.showToast("Turnamen target tidak valid.", "warning");
      return null;
    }
    const res = await window.TurnamenAPI.getTournamentById(tid);
    if (!res.success || !res.data) {
      window.TurnamenUI.showToast(res.message || "Gagal memuat detail turnamen.", "danger");
      return null;
    }
    if (!canPerform(action, { tournament: res.data })) {
      window.TurnamenUI.showToast(getDeniedActionMessage(action, res.data), "danger");
      return null;
    }
    return res.data;
  }

  async function resolveAuthorizedTeam(
    teamId,
    deniedMessage = "Anda tidak memiliki izin mengelola tim ini."
  ) {
    const user = getCurrentUserSafe();
    const role = user && user.role ? String(user.role).toLowerCase() : "";
    if (!user || (role !== "super_admin" && role !== "team_captain")) {
      window.TurnamenUI.showToast(deniedMessage, "danger");
      return null;
    }
    if (!teamId) {
      window.TurnamenUI.showToast("Tim target tidak valid.", "warning");
      return null;
    }
    const res = await window.TurnamenAPI.getTeamById(teamId);
    if (!res.success || !res.data) {
      window.TurnamenUI.showToast(res.message || "Gagal memuat data tim.", "danger");
      return null;
    }
    if (!canPerform("team:manage", { team: res.data })) {
      window.TurnamenUI.showToast(deniedMessage, "danger");
      return null;
    }
    return res.data;
  }

  function checkPageAccess(pageName) {
    const roleKey = getActiveRoleKey();
    if (pageName === "match-management" && !isManagementRole(roleKey)) {
      return {
        allowed: false,
        title: "Akses Halaman Pengesahan Skor Ditolak",
        message:
          "Halaman Jadwal & Pengesahan Skor hanya dapat diakses oleh Super Admin, Tournament Organizer, atau Committee. Anda dapat memantau jadwal dan hasil pertandingan melalui halaman Bracket.",
        actionHtml:
          roleKey === "guest"
            ? `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket">Lihat Bracket Publik</button><button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="login">Masuk Akun</button>`
            : `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket">Buka Halaman Bracket</button><button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="dashboard">Kembali ke Dashboard</button>`,
      };
    }

    if (pageName === "profile" && roleKey === "guest") {
      return {
        allowed: false,
        title: "Autentikasi Diperlukan",
        message:
          "Halaman Profil Pengguna hanya tersedia bagi akun yang sudah masuk. Silakan masuk atau daftarkan akun terlebih dahulu.",
        actionHtml: `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="login">Masuk / Daftar Akun</button><button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="dashboard">Kembali ke Arena Publik</button>`,
      };
    }

    if (pageName === "game-management" && roleKey !== "super_admin") {
      return {
        allowed: false,
        title: "Akses Halaman Manajemen Game Ditolak",
        message:
          "Pengelolaan katalog dan poster kustom cabang game hanya diizinkan bagi Super Admin aktif.",
        actionHtml:
          roleKey === "guest"
            ? `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="login">Masuk Akun</button><button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="dashboard">Kembali ke Arena Publik</button>`
            : `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="dashboard">Kembali ke Dashboard</button>`,
      };
    }

    return { allowed: true };
  }

  function getEligibleTeamsForRegistration(teams, tournament, existingRegs) {
    const user = getCurrentUserSafe();
    if (!user || !tournament) return [];
    const activeRegisteredIds = new Set(
      (existingRegs || [])
        .filter((r) => r.status !== "withdrawn")
        .map((r) => r.team_id)
    );
    return (teams || []).filter((tm) => {
      if (tm.game_id !== tournament.game_id) return false;
      if (activeRegisteredIds.has(tm.id)) return false;
      if (user.role === "super_admin") return true;
      return user.role === "team_captain" && tm.captain_id === user.id;
    });
  }

  // =========================================================================
  // INITIALIZATION, DYNAMIC ROLE NAVIGATION & SHELL BINDINGS
  // =========================================================================
  function getDesktopRecoveryRedirectUrl() {
    try {
      const loc = window.location;
      if (
        loc &&
        (loc.protocol === "http:" || loc.protocol === "https:") &&
        (loc.hostname === "127.0.0.1" || loc.hostname === "localhost")
      ) {
        const cleanPath = loc.pathname && loc.pathname !== "/" ? loc.pathname : "/index.html";
        return `${loc.origin}${cleanPath}`;
      }
    } catch (_err) {
      // Fall back to default Eel URL if window.location is restricted.
    }
    return "http://127.0.0.1:8080/index.html";
  }

  function isAllowedLocalRedirectUrl(urlObj) {
    if (!urlObj) return false;
    const protocol = String(urlObj.protocol || "").toLowerCase();
    const hostname = String(urlObj.hostname || "").toLowerCase();
    return (
      (protocol === "http:" || protocol === "https:") &&
      !urlObj.username &&
      !urlObj.password &&
      (hostname === "127.0.0.1" || hostname === "localhost")
    );
  }

  function isTrustedSupabaseVerifyUrl(urlObj, expectedSupabaseHost) {
    if (!urlObj || !expectedSupabaseHost) return false;
    const protocol = String(urlObj.protocol || "").toLowerCase();
    const hostname = String(urlObj.hostname || "").toLowerCase();
    if (
      protocol !== "https:" ||
      urlObj.username ||
      urlObj.password ||
      hostname !== expectedSupabaseHost ||
      urlObj.pathname !== "/auth/v1/verify"
    ) {
      return false;
    }

    const redirectRaw = (urlObj.searchParams.get("redirect_to") || "").trim();
    if (redirectRaw) {
      try {
        const redirectObj = new URL(redirectRaw);
        if (!isAllowedLocalRedirectUrl(redirectObj)) {
          return false;
        }
      } catch (_err) {
        return false;
      }
    }
    return true;
  }

  function parseSupabaseRecoveryUrl(rawInput, expectedSupabaseHost = null) {
    const raw = String(rawInput || "").trim();
    if (!raw) return null;

    const configuredHost = (
      typeof expectedSupabaseHost === "string" && expectedSupabaseHost.trim()
        ? expectedSupabaseHost
        : (getRuntimeState().supabaseHost || "")
    )
      .trim()
      .toLowerCase();

    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(raw)) {
      let parsedUrl;
      try {
        parsedUrl = new URL(raw);
      } catch (_err) {
        return null;
      }

      const searchParams = parsedUrl.searchParams;
      const hashPart = parsedUrl.hash || "";
      const hashParams = new URLSearchParams(hashPart.startsWith("#") ? hashPart.slice(1) : hashPart);
      const pick = (key) => (hashParams.get(key) || searchParams.get(key) || "").trim();

      const isVerifyEndpoint =
        parsedUrl.pathname === "/auth/v1/verify" || searchParams.has("token");
      if (isVerifyEndpoint) {
        if (!isTrustedSupabaseVerifyUrl(parsedUrl, configuredHost)) {
          return null;
        }

        const err = (searchParams.get("error") || "").trim();
        const errCode = (searchParams.get("error_code") || "").trim();
        const errDesc = (searchParams.get("error_description") || "").trim();
        if (err || errDesc || errCode) {
          return {
            errorMessage:
              errDesc ||
              "Tautan pemulihan password tidak valid atau sudah kedaluwarsa. Silakan minta email pemulihan baru.",
          };
        }

        const type = (searchParams.get("type") || "").trim().toLowerCase();
        const verifyToken = (searchParams.get("token") || "").trim();
        if (type === "recovery" && verifyToken && !/\s/.test(verifyToken)) {
          return {
            type: "recovery",
            accessToken: "",
            refreshToken: "",
            tokenHash: verifyToken,
          };
        }
        return null;
      }

      if (!isAllowedLocalRedirectUrl(parsedUrl)) {
        return null;
      }

      const error = pick("error");
      const errorCode = pick("error_code");
      const errorDescription = pick("error_description");
      if (error || errorDescription || errorCode) {
        return {
          errorMessage:
            errorDescription ||
            "Tautan pemulihan password tidak valid atau sudah kedaluwarsa. Silakan minta email pemulihan baru.",
        };
      }

      const type = pick("type").toLowerCase();
      const accessToken = pick("access_token");
      const refreshToken = pick("refresh_token");
      const tokenHash = pick("token_hash");
      if (type === "recovery" && (accessToken || tokenHash)) {
        return {
          type: "recovery",
          accessToken,
          refreshToken,
          tokenHash,
        };
      }
      return null;
    }

    let searchPart = "";
    let hashPart = "";
    const hashIdx = raw.indexOf("#");
    const queryIdx = raw.indexOf("?");
    if (hashIdx >= 0) {
      hashPart = raw.slice(hashIdx);
      if (queryIdx >= 0 && queryIdx < hashIdx) {
        searchPart = raw.slice(queryIdx, hashIdx);
      }
    } else if (queryIdx >= 0) {
      searchPart = raw.slice(queryIdx);
    } else if (raw.includes("=")) {
      hashPart = `#${raw}`;
    }

    const hashParams = new URLSearchParams(hashPart.startsWith("#") ? hashPart.slice(1) : hashPart);
    const searchParams = new URLSearchParams(searchPart.startsWith("?") ? searchPart.slice(1) : searchPart);
    const pick = (key) => (hashParams.get(key) || searchParams.get(key) || "").trim();

    const type = pick("type").toLowerCase();
    const accessToken = pick("access_token");
    const refreshToken = pick("refresh_token");
    const tokenHash = pick("token_hash");
    const error = pick("error");
    const errorCode = pick("error_code");
    const errorDescription = pick("error_description");

    if (error || errorDescription || errorCode) {
      return {
        errorMessage:
          errorDescription ||
          "Tautan pemulihan password tidak valid atau sudah kedaluwarsa. Silakan minta email pemulihan baru.",
      };
    }

    if (type === "recovery" && (accessToken || tokenHash)) {
      return {
        type: "recovery",
        accessToken,
        refreshToken,
        tokenHash,
      };
    }
    return null;
  }

  function consumeRecoveryCallbackFromLocation() {
    try {
      const loc = window.location;
      if (!loc || (!loc.hash && !loc.search)) {
        return false;
      }
      const parsed = parseSupabaseRecoveryUrl(`${loc.search || ""}${loc.hash || ""}`);
      if (!parsed) {
        return false;
      }

      // Remove recovery tokens from address bar history immediately.
      if (window.history && typeof window.history.replaceState === "function") {
        window.history.replaceState(null, "", loc.pathname || "/index.html");
      }

      if (parsed.errorMessage) {
        pendingRecoverySession = null;
        loginActiveTab = "recovery-request";
        pendingAuthNotice = {
          message: parsed.errorMessage,
          variant: "danger",
        };
        return true;
      }

      pendingRecoverySession = {
        accessToken: parsed.accessToken || "",
        refreshToken: parsed.refreshToken || "",
        tokenHash: parsed.tokenHash || "",
      };
      loginActiveTab = "recovery-update";
      pendingAuthNotice = {
        message: "Mode PASSWORD_RECOVERY aktif. Masukkan password baru Anda di bawah ini.",
        variant: "success",
      };
      return true;
    } catch (_err) {
      return false;
    }
  }

  function consumeInitialPageRequest() {
    try {
      const loc = window.location;
      if (!loc || !loc.search) return "";
      const params = new URLSearchParams(loc.search);
      const requested = (params.get("page") || "").trim().toLowerCase();
      if (requested === "login") {
        if (window.history && typeof window.history.replaceState === "function") {
          window.history.replaceState(null, "", loc.pathname || "/index.html");
        }
        return "login";
      }
      return "";
    } catch (_err) {
      return "";
    }
  }

  async function initApp() {
    const hasRecoveryCallback = consumeRecoveryCallbackFromLocation();
    const initialRequestedPage = hasRecoveryCallback ? "" : consumeInitialPageRequest();

    bindSidebarNavigation();
    bindResponsiveSidebar();
    bindRoleSwitcher();
    bindTopbarAuthButton();
    bindDelegatedEvents();

    const healthRes = await window.TurnamenAPI.getHealth();
    updateRuntimeIndicators(healthRes);

    if (hasRecoveryCallback) {
      await ensureGamesLoaded(true);
      await navigateTo("login");
      return;
    }

    const restoredState = getRuntimeState();
    if (restoredState.token && healthRes && healthRes.success) {
      const meRes = await window.TurnamenAPI.getCurrentUser();
      if (meRes && meRes.success && meRes.data && meRes.data.user) {
        if (window.TurnamenConfig && typeof window.TurnamenConfig.setAuthSession === "function") {
          window.TurnamenConfig.setAuthSession(restoredState.token, meRes.data.user);
        }
        updateUserTopbar(meRes.data.user);
      } else if (
        meRes &&
        !meRes.success &&
        meRes.error &&
        meRes.error.code === "UNAUTHORIZED"
      ) {
        if (window.TurnamenConfig && typeof window.TurnamenConfig.enterGuestMode === "function") {
          window.TurnamenConfig.enterGuestMode();
        }
        updateUserTopbar(null);
        window.TurnamenUI.showToast(
          "Sesi login sebelumnya telah berakhir. Silakan masuk kembali.",
          "warning"
        );
      }
    }

    await ensureGamesLoaded(true);
    await navigateTo(initialRequestedPage || "dashboard");
  }

  function renderRoleNavigation(activePage = currentPage) {
    const navEl = document.getElementById("sidebar-nav");
    const expEl = document.getElementById("sidebar-experience-label");
    const roleKey = getActiveRoleKey();
    const config = ROLE_NAV_CONFIG[roleKey] || ROLE_NAV_CONFIG.guest;

    if (expEl) {
      expEl.textContent = config.experienceLabel;
    }

    if (!navEl) return;
    navEl.innerHTML = config.sections
      .map((section) => {
        const itemsHtml = section.items
          .map((item) => {
            const isCurrent = item.page === activePage;
            return `
              <button
                type="button"
                class="nav-item ${isCurrent ? "active" : ""}"
                data-page="${window.TurnamenUI.escapeHtml(item.page)}"
                ${isCurrent ? 'aria-current="page"' : ""}
              >
                ${window.TurnamenUI.icon(item.icon, 16, "nav-icon")}
                <span>${window.TurnamenUI.escapeHtml(item.label)}</span>
              </button>
            `;
          })
          .join("");

        return `
          <div class="nav-section-label">${window.TurnamenUI.escapeHtml(section.label)}</div>
          ${itemsHtml}
        `;
      })
      .join("");
  }

  function bindSidebarNavigation() {
    const navEl = document.getElementById("sidebar-nav");
    if (!navEl) return;
    navEl.addEventListener("click", (e) => {
      const btn = e.target && e.target.closest(".nav-item[data-page]");
      if (!btn) return;
      const target = btn.getAttribute("data-page");
      closeMobileSidebar();
      navigateTo(target);
    });
  }

  function bindResponsiveSidebar() {
    const toggleBtn = document.getElementById("sidebar-toggle-btn");
    const closeBtn = document.getElementById("sidebar-close-btn");
    const backdrop = document.getElementById("sidebar-backdrop");

    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        const sidebar = document.getElementById("app-sidebar");
        if (!sidebar) return;
        const willOpen = !sidebar.classList.contains("is-open");
        sidebar.classList.toggle("is-open", willOpen);
        toggleBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
        if (backdrop) backdrop.classList.toggle("hidden", !willOpen);
      });
    }

    if (closeBtn) closeBtn.addEventListener("click", closeMobileSidebar);
    if (backdrop) backdrop.addEventListener("click", closeMobileSidebar);
  }

  function closeMobileSidebar() {
    const sidebar = document.getElementById("app-sidebar");
    const toggleBtn = document.getElementById("sidebar-toggle-btn");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (sidebar) sidebar.classList.remove("is-open");
    if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "false");
    if (backdrop) backdrop.classList.add("hidden");
  }

  async function applySimulatedRoleChange(roleName, toastMode = "switcher") {
    if (!isMockMode()) {
      updateRuntimeIndicators(null);
      return;
    }
    const prevPage = currentPage || "dashboard";
    resetRoleScopedUiState();
    const user = window.TurnamenAPI.setSimulatedRole(roleName);
    updateUserTopbar(user);
    if (!user && roleName !== "guest") {
      window.TurnamenUI.showToast(
        toastMode === "quick" ? "Role simulasi tidak tersedia." : "Gagal mengubah peran simulasi.",
        "warning"
      );
      return;
    }
    if (!user && roleName === "guest") {
      if (
        window.TurnamenConfig &&
        typeof window.TurnamenConfig.clearSelectedTournamentId === "function"
      ) {
        window.TurnamenConfig.clearSelectedTournamentId();
      }
      window.TurnamenUI.showToast(
        "Beralih ke mode Tamu (Public Guest).",
        "info",
        { group: "demo-role-switch" }
      );
    } else if (user) {
      window.TurnamenUI.showToast(
        toastMode === "quick"
          ? `Beralih ke akun demo: ${user.full_name}`
          : `Peran simulasi diubah ke: ${user.full_name} (${user.role})`,
        toastMode === "quick" ? "success" : "info",
        { group: "demo-role-switch" }
      );
    }
    const preserveAllowed =
      Boolean(prevPage) &&
      prevPage !== "login" &&
      checkPageAccess(prevPage).allowed === true;
    await navigateTo(preserveAllowed ? prevPage : "dashboard");
  }

  function bindRoleSwitcher() {
    const switcher = document.getElementById("topbar-role-switcher");
    if (!switcher) return;
    switcher.addEventListener("change", (e) => {
      applySimulatedRoleChange(e.target.value, "switcher");
    });
  }

  function bindTopbarAuthButton() {
    const btn = document.getElementById("topbar-auth-action");
    if (!btn) return;
    btn.addEventListener("click", () => {
      if (getCurrentUserSafe()) {
        handleLogout(btn);
      } else {
        navigateTo("login");
      }
    });
  }

  function updateRuntimeIndicators(healthRes) {
    const modeBadge = document.getElementById("app-mode-badge");
    const apiStatusEl = document.getElementById("sidebar-api-status");
    const switcherWrap = document.getElementById("topbar-role-switcher-wrap");

    if (healthRes && healthRes.success && healthRes.data && window.TurnamenConfig) {
      window.TurnamenConfig.setRuntimeInfo(healthRes.data);
    }

    const state = getRuntimeState();
    const isMock = isMockMode();

    if (switcherWrap) {
      switcherWrap.hidden = !isMock;
    }

    if (modeBadge) {
      if (healthRes && healthRes.success === false) {
        modeBadge.className = "badge badge-danger";
        modeBadge.textContent = "API OFFLINE";
      } else {
        modeBadge.className = isMock ? "badge badge-warning" : "badge badge-success";
        modeBadge.textContent = isMock
          ? "MOCK MODE (SIMULASI LOKAL)"
          : "SUPABASE ONLINE MODE";
      }
    }

    if (apiStatusEl && healthRes) {
      if (healthRes.success) {
        apiStatusEl.innerHTML = `<span class="status-indicator status-indicator-online" aria-hidden="true"></span><span>Flask API Aktif (${window.TurnamenUI.escapeHtml(state.appMode)})</span>`;
      } else {
        apiStatusEl.innerHTML = `<span class="status-indicator status-indicator-offline" aria-hidden="true"></span><span>Flask API Tidak Terhubung</span>`;
      }
    }

    updateUserTopbar(getCurrentUserSafe());
  }

  function updateUserTopbar(user) {
    const label = document.getElementById("topbar-active-user");
    const switcher = document.getElementById("topbar-role-switcher");
    const switcherWrap = document.getElementById("topbar-role-switcher-wrap");
    const authBtn = document.getElementById("topbar-auth-action");
    const isMock = isMockMode();

    if (switcherWrap) {
      switcherWrap.hidden = !isMock;
    }

    if (label) {
      if (user) {
        const displayName = user.username || user.email || "user";
        const displayRole = user.role || "player";
        label.className = "badge badge-info tabular-nums";
        label.textContent = `${displayName} (${displayRole})`;
      } else {
        label.className = "badge badge-neutral";
        label.textContent = "Tamu (Belum Masuk)";
      }
    }

    if (switcher && isMock) {
      switcher.value = user && user.role ? user.role : "guest";
    }

    if (authBtn) {
      authBtn.hidden = false;
      if (user) {
        authBtn.className = "btn btn-secondary btn-sm";
        authBtn.textContent = "Keluar";
      } else {
        authBtn.className = "btn btn-primary btn-sm";
        authBtn.textContent = "Masuk";
      }
    }

    renderRoleNavigation(currentPage);
  }

  // =========================================================================
  // DATA LOADING & TOURNAMENT CONTEXT RESOLUTION
  // =========================================================================
  async function ensureGamesLoaded(force = false) {
    if (!force && gamesState.loaded) {
      return gamesState.items;
    }
    const res = await window.TurnamenAPI.getGames();
    if (res && res.success && Array.isArray(res.data)) {
      gamesState.items = res.data;
      gamesState.loaded = true;
      gamesState.error = null;
    } else {
      gamesState.items = [];
      gamesState.loaded = false;
      gamesState.error = (res && res.message) || "Gagal memuat daftar cabang game.";
    }
    return gamesState.items;
  }

  function renderGamesErrorNotice() {
    if (!gamesState.error) return "";
    return `
      <div class="notice-banner notice-banner-warning" role="alert">
        <div>
          <strong>Daftar game gagal dimuat:</strong>
          <span>${window.TurnamenUI.escapeHtml(gamesState.error)}</span>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" data-action="retry-games">
          ${window.TurnamenUI.icon("refresh", 14)}
          <span>Muat Ulang Game</span>
        </button>
      </div>
    `;
  }

  function isTournamentAccessibleForRole(tournament, roleKey) {
    if (!tournament) return false;
    if (
      (roleKey === "guest" || roleKey === "player" || roleKey === "team_captain") &&
      String(tournament.status || "").toLowerCase() === "draft"
    ) {
      return false;
    }
    return true;
  }

  async function resolveActiveTournamentContext(preloadedList = null) {
    let list = preloadedList;
    if (!Array.isArray(list)) {
      const tourRes = await window.TurnamenAPI.getTournaments();
      if (!tourRes.success) {
        return { error: tourRes.message || "Gagal memuat daftar turnamen.", list: [], active: null };
      }
      list = Array.isArray(tourRes.data) ? tourRes.data : [];
    }

    cachedTournaments = list;
    if (list.length === 0) {
      if (
        window.TurnamenConfig &&
        typeof window.TurnamenConfig.clearSelectedTournamentId === "function"
      ) {
        window.TurnamenConfig.clearSelectedTournamentId();
      }
      return { error: null, list: [], active: null };
    }

    const user = getCurrentUserSafe();
    const roleKey = getActiveRoleKey();
    const selectedId = getRuntimeState().selectedTournamentId;
    let active = list.find((t) => t.id === selectedId);
    if (active && !isTournamentAccessibleForRole(active, roleKey)) {
      active = null;
    }
    if (!active) {
      if (roleKey === "committee" && user) {
        active =
          list.find((t) => getCommitteeTournamentAssignment(t, user) === true && t.status === "ongoing") ||
          list.find((t) => getCommitteeTournamentAssignment(t, user) === true) ||
          list.find((t) => t.status === "ongoing") ||
          list[0];
      } else if (roleKey === "organizer" && user) {
        active =
          list.find((t) => t.organizer_id === user.id && t.status === "ongoing") ||
          list.find((t) => t.organizer_id === user.id) ||
          list.find((t) => t.status === "ongoing") ||
          list[0];
      } else {
        active =
          list.find((t) => isTournamentAccessibleForRole(t, roleKey) && t.status === "ongoing") ||
          list.find((t) => isTournamentAccessibleForRole(t, roleKey)) ||
          list[0];
      }
      if (active && window.TurnamenConfig) {
        window.TurnamenConfig.setSelectedTournamentId(active.id);
      }
    }

    return { error: null, list, active };
  }

  function renderTournamentContextBar(list, active, pageActionsHtml = "") {
    if (!list || list.length === 0 || !active) return "";
    const optionsHtml = list
      .map((t) => {
        const selected = t.id === active.id ? "selected" : "";
        return `<option value="${window.TurnamenUI.escapeHtml(t.id)}" ${selected}>${window.TurnamenUI.escapeHtml(t.title)} (${window.TurnamenUI.escapeHtml(t.game_name)})</option>`;
      })
      .join("");

    return `
      <div class="context-bar">
        <div class="context-bar-group">
          <label for="active-tournament-select" class="context-bar-label">Turnamen Aktif:</label>
          <select id="active-tournament-select" class="form-select form-select-compact" data-action="select-active-tournament">
            ${optionsHtml}
          </select>
          ${window.TurnamenUI.renderStatusBadge(active.status)}
        </div>
        ${pageActionsHtml ? `<div class="context-bar-group">${pageActionsHtml}</div>` : ""}
      </div>
    `;
  }

  function buildGameLookup() {
    const map = {};
    gamesState.items.forEach((g) => {
      map[g.id] = g;
    });
    return map;
  }

  // =========================================================================
  // NAVIGATION WITH RBAC ACCESS GUARD & RACE-CONDITION PROTECTION
  // =========================================================================
  async function navigateTo(pageName, options = {}) {
    if (
      window.TurnamenUI &&
      typeof window.TurnamenUI.closeModal === "function" &&
      !(typeof window.TurnamenUI.isModalBusy === "function" && window.TurnamenUI.isModalBusy())
    ) {
      window.TurnamenUI.closeModal(false);
    }

    const seq = ++navigationSeq;
    const targetPage = PAGE_TITLES[pageName] ? pageName : "dashboard";

    if (options && options.tournamentId && window.TurnamenConfig) {
      window.TurnamenConfig.setSelectedTournamentId(options.tournamentId);
    }

    currentPage = targetPage;
    updateUserTopbar(getCurrentUserSafe());

    const roleKey = getActiveRoleKey();
    const roleCfg = ROLE_NAV_CONFIG[roleKey] || ROLE_NAV_CONFIG.guest;
    const titleEl = document.getElementById("topbar-page-title");
    if (titleEl) {
      titleEl.textContent =
        targetPage === "dashboard"
          ? roleCfg.dashboardTitle
          : PAGE_TITLES[targetPage] || "Turnamen.in";
    }

    const container = document.getElementById("main-content");
    if (!container) return;

    const access = checkPageAccess(targetPage);
    if (!access.allowed) {
      container.setAttribute("aria-busy", "false");
      container.innerHTML = window.TurnamenUI.renderAccessDeniedState(
        access.title,
        access.message,
        access.actionHtml
      );
      return;
    }

    const snapKey = getPageSnapshotKey(targetPage);
    const snapshotHtml = uiPageSnapshots.get(snapKey) || "";
    const hasSnapshot = Boolean(snapshotHtml) && targetPage !== "login";
    container.setAttribute("aria-busy", "true");

    if (hasSnapshot) {
      container.innerHTML = `${window.TurnamenUI.renderRefreshBanner("Memperbarui data terbaru...")}${snapshotHtml}`;
    } else if (targetPage === "dashboard") {
      container.innerHTML = window.TurnamenUI.renderDashboardSkeleton(roleKey);
    } else if (targetPage === "tournament-list") {
      container.innerHTML = isCompetitiveRole()
        ? window.TurnamenUI.renderTournamentCardsSkeleton(4)
        : window.TurnamenUI.renderTableSkeleton({
            rows: 5,
            columns: 4,
            title: "Katalog & Manajemen Turnamen",
          });
    } else if (targetPage === "team-management") {
      container.innerHTML = window.TurnamenUI.renderListSkeleton({
        rows: 5,
        title: "Manajemen Tim & Roster Pemain",
        withAvatar: true,
      });
    } else if (targetPage === "game-management") {
      container.innerHTML = window.TurnamenUI.renderTournamentCardsSkeleton(3);
    } else if (targetPage === "announcements") {
      container.innerHTML = window.TurnamenUI.renderAnnouncementCardsSkeleton(3);
    } else if (targetPage === "reports") {
      container.innerHTML = window.TurnamenUI.renderReportChartSkeleton();
    } else if (targetPage === "login") {
      container.innerHTML = window.TurnamenUI.renderLoadingState(
        `Memuat ${PAGE_TITLES[targetPage] || "halaman"}...`
      );
    } else {
      container.innerHTML = window.TurnamenUI.renderTableSkeleton({ rows: 4, columns: 4 });
    }

    const isStale = () => seq !== navigationSeq;

    try {
      switch (targetPage) {
        case "dashboard":
          await renderDashboard(container, isStale, { hasSnapshot, snapKey });
          break;
        case "tournament-list":
          await renderTournamentList(container, isStale);
          break;
        case "tournament-detail":
          await renderTournamentDetail(container, isStale);
          break;
        case "team-management":
          await renderTeamManagement(container, isStale);
          break;
        case "game-management":
          await renderGameManagement(container, isStale);
          break;
        case "match-management":
          await renderMatchManagement(container, isStale);
          break;
        case "bracket":
          await renderBracketPage(container, isStale);
          break;
        case "announcements":
          await renderAnnouncementsPage(container, isStale);
          break;
        case "reports":
          await renderReportsPage(container, isStale);
          break;
        case "profile":
          await renderProfilePage(container, isStale);
          break;
        case "login":
          await renderLoginPage(container, isStale);
          break;
        default:
          await renderDashboard(container, isStale, { hasSnapshot, snapKey });
      }
      if (
        !isStale() &&
        targetPage !== "login" &&
        !(targetPage === "dashboard" && roleKey === "super_admin") &&
        !container.innerHTML.includes('data-skeleton="true"') &&
        !container.innerHTML.includes("state-box-error")
      ) {
        uiPageSnapshots.set(snapKey, container.innerHTML);
      }
    } finally {
      if (!isStale()) {
        container.setAttribute("aria-busy", "false");
      }
    }
  }

  // =========================================================================
  // 1. ROLE-BASED DASHBOARD DISPATCHER & 5+ ROLE VIEWS
  // =========================================================================
  async function renderDashboard(container, isStale, navOptions = {}) {
    const roleKey = getActiveRoleKey();
    const isSuperAdmin = roleKey === "super_admin";
    if (isSuperAdmin) {
      await renderSuperAdminProgressive(container, isStale, navOptions);
      return;
    }

    const needsTeams =
      roleKey === "player" || roleKey === "team_captain" || roleKey === "guest";
    const noopTeamsPromise = Promise.resolve({ success: true, data: [] });

    // Wave 1: Execute all independent top-level dashboard queries in parallel.
    const [, tourRes, teamsRes] = await Promise.all([
      ensureGamesLoaded(false),
      window.TurnamenAPI.getTournaments(),
      needsTeams ? window.TurnamenAPI.getTeams() : noopTeamsPromise,
    ]);
    if (isStale()) return;

    if (!tourRes.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(tourRes.message, "retry-page");
      return;
    }

    const tournaments = Array.isArray(tourRes.data) ? tourRes.data : [];
    const teamsOk = Boolean(teamsRes && teamsRes.success && Array.isArray(teamsRes.data));
    const teams = teamsOk ? teamsRes.data : [];
    const ctx = await resolveActiveTournamentContext(tournaments);
    if (isStale()) return;

    let activeMatches = [];
    let activeAnnouncements = [];
    let activeReport = null;
    let activeRegs = [];
    let reportError = null;

    if (ctx.active) {
      const needsMatches =
        roleKey === "player" ||
        roleKey === "team_captain" ||
        roleKey === "committee" ||
        roleKey === "guest";
      const needsAnnouncements =
        roleKey === "player" ||
        roleKey === "team_captain" ||
        roleKey === "organizer" ||
        roleKey === "committee" ||
        roleKey === "guest";
      const needsReport =
        roleKey === "organizer" ||
        roleKey === "committee" ||
        roleKey === "player" ||
        roleKey === "guest";
      const needsRegs = roleKey === "organizer" || roleKey === "committee";

      // Wave 2: Fetch only the active-tournament endpoints rendered by this role.
      const [matchRes, annRes, reportRes, regRes] = await Promise.all([
        needsMatches ? window.TurnamenAPI.getTournamentMatches(ctx.active.id) : Promise.resolve(null),
        needsAnnouncements ? window.TurnamenAPI.getAnnouncements(ctx.active.id) : Promise.resolve(null),
        needsReport ? window.TurnamenAPI.getTournamentReport(ctx.active.id) : Promise.resolve(null),
        needsRegs ? window.TurnamenAPI.getTournamentRegistrations(ctx.active.id) : Promise.resolve(null),
      ]);
      if (isStale()) return;
      if (matchRes && matchRes.success && matchRes.data && Array.isArray(matchRes.data.matches)) {
        activeMatches = matchRes.data.matches;
      }
      if (annRes && annRes.success && Array.isArray(annRes.data)) {
        activeAnnouncements = [...annRes.data].sort(
          (a, b) => Number(Boolean(b.is_pinned)) - Number(Boolean(a.is_pinned))
        );
      }
      if (reportRes && reportRes.success && reportRes.data) {
        activeReport = reportRes.data;
      } else if (needsReport && reportRes && !reportRes.success) {
        reportError = reportRes.message || "Ringkasan laporan turnamen gagal dimuat.";
      }
      if (regRes && regRes.success && Array.isArray(regRes.data)) {
        activeRegs = regRes.data;
      }
    }

    const sharedData = {
      tournaments,
      teams,
      teamsOk,
      ctx,
      activeMatches,
      activeAnnouncements,
      activeReport,
      activeRegs,
      reportError,
      gamesById: buildGameLookup(),
    };

    switch (roleKey) {
      case "player":
        renderPlayerDashboard(container, sharedData);
        break;
      case "team_captain":
        await renderCaptainDashboard(container, sharedData, isStale);
        break;
      case "organizer":
        await renderOrganizerDashboard(container, sharedData, isStale);
        break;
      case "committee":
        renderCommitteeDashboard(container, sharedData);
        break;
      default:
        renderGuestDashboard(container, sharedData);
        break;
    }
  }

  function renderGamePosterGallery(tournaments) {
    if (gamesState.items.length === 0) {
      return window.TurnamenUI.renderEmptyState(
        "Katalog Game Belum Tersedia",
        "Daftar cabang game esports belum dapat dimuat saat ini."
      );
    }

    return `
      <div class="game-poster-grid">
        ${gamesState.items
          .map((g) => {
            const tourCount = tournaments.filter((t) => t.game_id === g.id).length;
            return `
            <article class="game-poster-card">
              <div class="game-poster-art">${window.TurnamenUI.renderGameArtwork(g, "", { hideCaption: true })}</div>
              <div class="game-poster-body">
                <h3 class="game-poster-title">${window.TurnamenUI.escapeHtml(g.name)}</h3>
                <div class="game-poster-meta">
                  <span>${window.TurnamenUI.escapeHtml(g.genre || "Esports")}</span>
                  <span aria-hidden="true">|</span>
                  <span>${window.TurnamenUI.escapeHtml(g.platform || "Multi-Platform")}</span>
                  <span aria-hidden="true">|</span>
                  <span class="tabular-nums">${g.team_size || 5}v${g.team_size || 5} Bo${g.default_best_of || 3}</span>
                </div>
                <div class="game-poster-footer">
                  <span class="badge badge-info tabular-nums">${tourCount} Turnamen</span>
                  <button type="button" class="btn btn-secondary btn-sm" data-action="browse-game-tournaments" data-id="${window.TurnamenUI.escapeHtml(g.id)}">Lihat Turnamen</button>
                </div>
              </div>
            </article>
          `;
          })
          .join("")}
      </div>
    `;
  }

  function renderTournamentDiscoveryCards(tournaments, gamesById, options = {}) {
    if (!tournaments || tournaments.length === 0) {
      return window.TurnamenUI.renderEmptyState(
        "Belum Ada Turnamen",
        "Belum ada kompetisi yang terdaftar saat ini."
      );
    }

    const ownedTeamIds = options.ownedTeamIds || [];
    const teams = options.teams || [];

    return `
      <div class="discovery-grid">
        ${tournaments
          .map((t) => {
            const game = gamesById[t.game_id] || { name: t.game_name, slug: t.game_name };
            const maxTeams = Number(t.max_teams || 0);
            const approved = Number(t.approved_teams_count || 0);
            const fillPct = maxTeams > 0 ? Math.round((approved / maxTeams) * 100) : 0;
            const canQuickJoin =
              canPerform("registration:create") &&
              t.status === "open_registration" &&
              teams.some((tm) => ownedTeamIds.includes(tm.id) && tm.game_id === t.game_id);

            return `
            <article class="tournament-card">
              <div class="tournament-card-art">
                ${window.TurnamenUI.renderGameArtwork(game, `BO${t.best_of || 3} SINGLE ELIM`, { hideCaption: true })}
                <div class="tournament-card-overlay-badge">
                  ${window.TurnamenUI.renderStatusBadge(t.status)}
                </div>
              </div>
              <div class="tournament-card-body">
                <div>${window.TurnamenUI.renderGameChip(game)}</div>
                <h3 class="tournament-card-title">${window.TurnamenUI.escapeHtml(t.title)}</h3>
                <div class="tournament-card-meta-grid">
                  <div class="meta-stat-item">
                    <span class="meta-stat-label">Total Hadiah</span>
                    <span class="meta-stat-value tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</span>
                  </div>
                  <div class="meta-stat-item">
                    <span class="meta-stat-label">Venue / Platform</span>
                    <span class="meta-stat-value" title="${window.TurnamenUI.escapeHtml(t.venue || "Online")}">${window.TurnamenUI.escapeHtml(t.venue || "Online")}</span>
                  </div>
                  <div class="meta-stat-item">
                    <span class="meta-stat-label">Tanggal Mulai</span>
                    <span class="meta-stat-value tabular-nums">${window.TurnamenUI.formatDateOnly(t.start_date)}</span>
                  </div>
                </div>
                <div class="progress-wrap">
                  <div class="progress-header">
                    <span>Slot Tim Terverifikasi</span>
                    <span class="tabular-nums">${approved} / ${maxTeams} Tim</span>
                  </div>
                  ${window.TurnamenUI.renderProgressBar(fillPct, `Kuota peserta ${t.title}`)}
                </div>
                <div class="tournament-card-footer">
                  <span class="table-subtext tabular-nums">Biaya Daftar: ${window.TurnamenUI.formatRupiah(t.registration_fee)}</span>
                  <div class="row-actions">
                    <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Detail</button>
                    <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Bracket</button>
                    ${
                      canQuickJoin
                        ? `<button type="button" class="btn btn-violet btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Daftar</button>`
                        : ""
                    }
                  </div>
                </div>
              </div>
            </article>
          `;
          })
          .join("")}
      </div>
    `;
  }

  // A1. PLAYER DASHBOARD (Competitive Experience)
  function renderPlayerDashboard(container, data) {
    const user = getCurrentUserSafe();
    const { tournaments, teams, ctx, activeMatches, activeAnnouncements, activeReport, gamesById } =
      data;

    const featured = ctx.active || tournaments[0] || null;
    const featuredGame = featured
      ? gamesById[featured.game_id] || { name: featured.game_name, slug: featured.game_name }
      : gamesState.items[0] || { name: "Esports Arena", slug: "esports" };

    const playerTeam = user
      ? teams.find((tm) => (tm.members || []).some((m) => m.user_id === user.id))
      : null;
    const playerMemberInfo =
      playerTeam && user
        ? (playerTeam.members || []).find((m) => m.user_id === user.id)
        : null;

    const relevantMatches = playerTeam
      ? activeMatches.filter(
          (m) => m.team_a_id === playerTeam.id || m.team_b_id === playerTeam.id
        )
      : [];
    const displayMatches =
      relevantMatches.length > 0 ? relevantMatches.slice(0, 4) : activeMatches.slice(0, 4);

    const standings =
      activeReport && Array.isArray(activeReport.standings) ? activeReport.standings.slice(0, 5) : [];

    const bannerHtml = featured
      ? `
        <section class="esports-banner" aria-label="Turnamen Pilihan">
          <div class="esports-banner-copy">
            <span class="esports-banner-kicker">Featured Arena Tournament</span>
            <h2 class="esports-banner-title">${window.TurnamenUI.escapeHtml(featured.title)}</h2>
            <p class="esports-banner-desc">${window.TurnamenUI.escapeHtml(featured.description || "Kompetisi esports resmi dengan sistem Single Elimination.")}</p>
            <div class="esports-banner-stats">
              ${window.TurnamenUI.renderStatusBadge(featured.status)}
              <span>Hadiah: <strong class="tabular-nums">${window.TurnamenUI.formatRupiah(featured.prize_pool)}</strong></span>
              <span>Slot: <strong class="tabular-nums">${featured.approved_teams_count || 0}/${featured.max_teams} Tim</strong></span>
              <span>Format: <strong class="tabular-nums">Bo${featured.best_of}</strong></span>
            </div>
            <div class="page-actions">
              <button type="button" class="btn btn-primary" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(featured.id)}">
                ${window.TurnamenUI.icon("bracket", 15)}
                <span>Lihat Bracket &amp; Match</span>
              </button>
              <button type="button" class="btn btn-secondary" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(featured.id)}">Detail Turnamen</button>
            </div>
          </div>
          <div class="esports-banner-art">
            ${window.TurnamenUI.renderGameArtwork(featuredGame, `HADIAH ${window.TurnamenUI.formatRupiah(featured.prize_pool)}`)}
          </div>
        </section>
      `
      : `
        <section class="esports-banner" aria-label="Arena Player">
          <div class="esports-banner-copy">
            <span class="esports-banner-kicker">Turnamen.in Player Hub</span>
            <h2 class="esports-banner-title">Belum Ada Turnamen Berlangsung</h2>
            <p class="esports-banner-desc">Jelajahi katalog cabang game dan pantau daftar turnamen terbaru yang akan dibuka.</p>
          </div>
        </section>
      `;

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      ${bannerHtml}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Galeri Cabang Game Esports</h2>
          <p>Pilih game untuk menemukan turnamen yang sedang berjalan maupun yang segera dibuka.</p>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-list">Jelajahi Semua Turnamen</button>
      </div>
      ${renderGamePosterGallery(tournaments)}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Turnamen Berlangsung &amp; Mendatang</h2>
          <p>Pantau kuota peserta, total hadiah, dan bagan pertandingan setiap kompetisi.</p>
        </div>
      </div>
      ${renderTournamentDiscoveryCards(tournaments, gamesById)}

      <div class="workspace-split">
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">${playerTeam ? "Pertandingan Tim Anda" : "Jadwal &amp; Hasil Pertandingan Terbaru"}</h3>
              <p class="card-subtitle">${window.TurnamenUI.escapeHtml(ctx.active ? ctx.active.title : "Belum ada turnamen aktif")}</p>
            </div>
            ${
              ctx.active
                ? `<button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Bracket Penuh</button>`
                : ""
            }
          </div>
          ${
            displayMatches.length > 0
              ? `<div class="match-card-grid">${displayMatches
                  .map((m) =>
                    window.TurnamenUI.renderMatchCard(m, {
                      highlightTeamIds: playerTeam ? [playerTeam.id] : [],
                    })
                  )
                  .join("")}</div>`
              : window.TurnamenUI.renderEmptyState(
                  "Belum Ada Jadwal Pertandingan",
                  "Pertandingan akan muncul setelah bracket disusun oleh panitia."
                )
          }
        </div>

        <div class="stack-md">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Identitas Tim &amp; Roster Anda</h3>
              ${playerTeam ? `<span class="badge badge-info tabular-nums">${window.TurnamenUI.escapeHtml(playerTeam.tag)}</span>` : ""}
            </div>
            ${
              playerTeam
                ? `
              <div class="row-actions" style="gap:14px; margin-bottom:12px;">
                ${window.TurnamenUI.renderTeamEmblem(playerTeam.tag, 52)}
                <div>
                  <strong>${window.TurnamenUI.escapeHtml(playerTeam.name)}</strong>
                  <div class="table-subtext">${window.TurnamenUI.escapeHtml(playerTeam.game_name)} | ${window.TurnamenUI.escapeHtml(playerTeam.region || "-")}</div>
                </div>
              </div>
              ${
                playerMemberInfo
                  ? `
                <div class="profile-identity-header" style="margin-bottom:10px; padding-bottom:10px;">
                  ${window.TurnamenUI.renderPlayerAvatar(playerMemberInfo.nickname, playerMemberInfo.member_role, 40)}
                  <div>
                    <div class="roster-card-name">${window.TurnamenUI.escapeHtml(playerMemberInfo.nickname)}</div>
                    <div class="roster-card-id">${window.TurnamenUI.escapeHtml(playerMemberInfo.ingame_id)}</div>
                  </div>
                </div>
                <div class="kv-list">
                  <div class="kv-item"><span class="kv-label">Peran Roster</span><span class="kv-value">${window.TurnamenUI.escapeHtml(playerMemberInfo.member_role)}</span></div>
                </div>
              `
                  : ""
              }
            `
                : window.TurnamenUI.renderEmptyState(
                    "Belum Tergabung di Tim",
                    "Hubungi Team Captain untuk ditambahkan ke roster tim esports."
                  )
            }
          </div>

          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Pengumuman Kompetisi</h3>
              <button type="button" class="btn btn-ghost btn-sm" data-action="go-page" data-page="announcements">Semua</button>
            </div>
            ${
              activeAnnouncements.length > 0
                ? `<div class="stack-md">${activeAnnouncements
                    .slice(0, 2)
                    .map(
                      (a) => `
                    <div class="roster-card" style="flex-direction:column; align-items:flex-start;">
                      <div class="row-actions">${window.TurnamenUI.renderStatusBadge(a.priority)}<strong>${window.TurnamenUI.escapeHtml(a.title)}</strong></div>
                      <span class="table-subtext">${window.TurnamenUI.escapeHtml(a.content)}</span>
                    </div>
                  `
                    )
                    .join("")}</div>`
                : window.TurnamenUI.renderEmptyState("Belum Ada Pengumuman", "Belum ada pembaruan dari panitia.")
            }
          </div>
        </div>
      </div>

      ${
        standings.length > 0
          ? `
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Papan Klasemen Teratas: ${window.TurnamenUI.escapeHtml(ctx.active.title)}</h3>
            <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="reports">Klasemen Lengkap</button>
          </div>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Tim</th>
                  <th>Main</th>
                  <th>Menang</th>
                  <th>Kalah</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${standings
                  .map(
                    (row) => `
                  <tr>
                    <td class="tabular-nums"><span class="rank-pill ${row.rank <= 3 ? `rank-pill-${row.rank}` : ""}">#${row.rank}</span></td>
                    <td>
                      <div class="team-cell-inline">
                        ${window.TurnamenUI.renderTeamEmblem(row.team_tag, 24)}
                        <strong>${window.TurnamenUI.escapeHtml(row.team_name)}</strong>
                        <span class="badge badge-neutral">${window.TurnamenUI.escapeHtml(row.team_tag)}</span>
                      </div>
                    </td>
                    <td class="tabular-nums">${row.matches_played}</td>
                    <td class="tabular-nums" style="color:var(--status-success-text);">${row.matches_won}</td>
                    <td class="tabular-nums" style="color:var(--status-danger-text);">${row.matches_lost}</td>
                    <td><span class="badge badge-info">${window.TurnamenUI.escapeHtml(row.placement_label)}</span></td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </div>
      `
          : ""
      }
    `;
  }

  // A2. TEAM CAPTAIN DASHBOARD (Competitive + Team Management Experience)
  async function renderCaptainDashboard(container, data, isStale) {
    const user = getCurrentUserSafe();
    const { tournaments, teams, ctx, activeMatches, activeAnnouncements, gamesById } = data;
    const captainTeams = user ? teams.filter((tm) => tm.captain_id === user.id) : [];

    if (captainTeams.length > 0) {
      const stillValid = captainTeams.some((tm) => tm.id === selectedCaptainTeamId);
      if (!stillValid) selectedCaptainTeamId = captainTeams[0].id;
    } else {
      selectedCaptainTeamId = "";
    }

    const activeTeam =
      captainTeams.find((tm) => tm.id === selectedCaptainTeamId) || captainTeams[0] || null;
    const captainTeamIds = captainTeams.map((tm) => tm.id);

    // Collect registration status across all tournaments for captain's teams
    const regResponses = await Promise.all(
      tournaments.map(async (t) => {
        const res = await window.TurnamenAPI.getTournamentRegistrations(t.id);
        return {
          tournament: t,
          regs: res.success && Array.isArray(res.data) ? res.data : [],
        };
      })
    );
    if (isStale()) return;

    const joinedEntries = [];
    const openTournamentsForCaptain = [];
    regResponses.forEach(({ tournament, regs }) => {
      const myRegs = regs.filter((r) => captainTeamIds.includes(r.team_id));
      myRegs.forEach((r) => {
        joinedEntries.push({ tournament, reg: r });
      });
      const eligible = getEligibleTeamsForRegistration(captainTeams, tournament, regs);
      if (tournament.status === "open_registration" && eligible.length > 0) {
        openTournamentsForCaptain.push({ tournament, eligible });
      }
    });

    const teamMatches = activeTeam
      ? activeMatches.filter(
          (m) => m.team_a_id === activeTeam.id || m.team_b_id === activeTeam.id
        )
      : [];

    const teamHeroHtml = activeTeam
      ? `
        <section class="team-hero" aria-label="Identitas Tim Kapten">
          <div class="team-hero-identity">
            ${window.TurnamenUI.renderTeamEmblem(activeTeam.tag, 72)}
            <div>
              <span class="arena-hero-kicker">Markas Tim Kapten</span>
              <h2 class="team-hero-name">${window.TurnamenUI.escapeHtml(activeTeam.name)}</h2>
              <div class="team-hero-meta">
                <span class="badge badge-info tabular-nums">${window.TurnamenUI.escapeHtml(activeTeam.tag)}</span>
                ${window.TurnamenUI.renderGameChip(activeTeam.game_name, gamesById[activeTeam.game_id] || activeTeam.game_id)}
                <span>Region: <strong>${window.TurnamenUI.escapeHtml(activeTeam.region || "-")}</strong></span>
                <span class="tabular-nums"><strong>${(activeTeam.members || []).length}</strong> Roster</span>
              </div>
            </div>
          </div>
          <div class="page-actions">
            ${
              captainTeams.length > 1
                ? `
              <label for="captain-team-select" class="sr-only">Pilih tim aktif kapten</label>
              <select id="captain-team-select" class="form-select form-select-compact">
                ${captainTeams
                  .map(
                    (tm) =>
                      `<option value="${window.TurnamenUI.escapeHtml(tm.id)}" ${tm.id === activeTeam.id ? "selected" : ""}>${window.TurnamenUI.escapeHtml(tm.name)} [${window.TurnamenUI.escapeHtml(tm.tag)}]</option>`
                  )
                  .join("")}
              </select>
            `
                : ""
            }
            <button type="button" class="btn btn-primary btn-sm" data-action="open-add-member" data-id="${window.TurnamenUI.escapeHtml(activeTeam.id)}">${window.TurnamenUI.icon("plus", 14)}<span>Tambah Anggota</span></button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="open-edit-team" data-id="${window.TurnamenUI.escapeHtml(activeTeam.id)}">${window.TurnamenUI.icon("edit", 14)}<span>Edit Tim</span></button>
            <button type="button" class="btn btn-ghost btn-sm" data-action="open-create-team">+ Tim Baru</button>
          </div>
        </section>
      `
      : `
        <section class="team-hero" aria-label="Markas Tim Kapten">
          <div>
            <span class="arena-hero-kicker">Markas Tim Kapten</span>
            <h2 class="team-hero-name">Anda Belum Memiliki Tim Esports</h2>
            <p class="card-subtitle">Buat tim pertama Anda untuk mulai mengisi roster dan mendaftar ke turnamen terbuka.</p>
          </div>
          <button type="button" class="btn btn-primary" data-action="open-create-team">${window.TurnamenUI.icon("plus", 15)}<span>Buat Tim Baru</span></button>
        </section>
      `;

    const rosterMembers = activeTeam && Array.isArray(activeTeam.members) ? activeTeam.members : [];

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      ${teamHeroHtml}

      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Roster Anggota Tim</h3>
            <p class="card-subtitle">${activeTeam ? `${window.TurnamenUI.escapeHtml(activeTeam.name)} (${rosterMembers.length} pemain terdaftar)` : "Belum ada tim dipilih"}</p>
          </div>
          ${
            activeTeam
              ? `<button type="button" class="btn btn-secondary btn-sm" data-action="open-add-member" data-id="${window.TurnamenUI.escapeHtml(activeTeam.id)}">+ Anggota</button>`
              : ""
          }
        </div>
        ${
          !activeTeam
            ? window.TurnamenUI.renderEmptyState("Belum Ada Tim", "Buat tim untuk mengelola roster pemain.")
            : rosterMembers.length === 0
              ? window.TurnamenUI.renderEmptyState(
                  "Roster Masih Kosong",
                  "Tambahkan anggota beserta nickname dan In-Game ID untuk memenuhi syarat registrasi turnamen.",
                  `<button type="button" class="btn btn-primary btn-sm" data-action="open-add-member" data-id="${window.TurnamenUI.escapeHtml(activeTeam.id)}">Tambah Anggota Pertama</button>`
                )
              : `
            <div class="player-roster-grid">
              ${rosterMembers
                .map(
                  (m) => `
                <article class="player-card">
                  <div class="player-card-head">
                    ${window.TurnamenUI.renderPlayerAvatar(m.nickname, m.member_role, 40)}
                    <div class="player-card-identity">
                      <div class="roster-card-name">${window.TurnamenUI.escapeHtml(m.nickname)}</div>
                      <div class="roster-card-id">${window.TurnamenUI.escapeHtml(m.ingame_id)}</div>
                    </div>
                  </div>
                  <div class="player-card-foot">
                    <span class="badge ${m.member_role === "captain" ? "badge-violet" : "badge-info"}">${window.TurnamenUI.escapeHtml(m.member_role || "starter")}</span>
                    <span class="badge badge-neutral tabular-nums">${window.TurnamenUI.escapeHtml(activeTeam.tag)}</span>
                  </div>
                </article>
              `
                )
                .join("")}
            </div>
          `
        }
      </div>

      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Turnamen Diikuti &amp; Status Registrasi</h3>
            <p class="card-subtitle">Status pendaftaran seluruh tim yang Anda kelola.</p>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-list">Jelajah Turnamen</button>
        </div>
        ${
          joinedEntries.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Belum Terdaftar di Turnamen",
                "Pilih turnamen dengan pendaftaran terbuka untuk mendaftarkan tim Anda."
              )
            : `
          <div class="participation-grid">
            ${joinedEntries
              .map(({ tournament, reg }) => {
                const tGame = gamesById[tournament.game_id] || {
                  name: tournament.game_name,
                  slug: tournament.game_name,
                };
                return `
                <article class="participation-card">
                  <div class="participation-card-art">
                    ${window.TurnamenUI.renderGameArtwork(tGame, `BO${tournament.best_of || 3} SINGLE ELIM`, { hideCaption: true })}
                    <div class="tournament-card-overlay-badge">
                      ${window.TurnamenUI.renderStatusBadge(reg.status)}
                    </div>
                  </div>
                  <div class="participation-card-body">
                    <div class="participation-card-head">
                      ${window.TurnamenUI.renderTeamEmblem(reg.team_tag, 38)}
                      <div style="min-width:0; flex:1;">
                        ${window.TurnamenUI.renderGameChip(tournament.game_name, tGame)}
                        <h4 class="participation-card-title">${window.TurnamenUI.escapeHtml(tournament.title)}</h4>
                        <div class="participation-card-meta">
                          <span class="badge badge-neutral tabular-nums">${window.TurnamenUI.escapeHtml(reg.team_tag)}</span>
                          <span class="tabular-nums">Seed <strong>#${reg.seed_number || "-"}</strong></span>
                          <span class="tabular-nums">${window.TurnamenUI.formatRupiah(tournament.prize_pool)}</span>
                        </div>
                      </div>
                    </div>
                    <div class="participation-card-foot">
                      <span class="table-subtext tabular-nums">Mulai: ${window.TurnamenUI.formatDateOnly(tournament.start_date)}</span>
                      <div class="row-actions">
                        <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(tournament.id)}">Detail</button>
                        <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(tournament.id)}">Bracket</button>
                      </div>
                    </div>
                  </div>
                </article>
              `;
              })
              .join("")}
          </div>
        `
        }
      </div>

      ${
        openTournamentsForCaptain.length > 0
          ? `
        <div class="page-header">
          <div class="page-header-copy">
            <h2>Turnamen Terbuka untuk Tim Anda</h2>
            <p>Turnamen yang sesuai dengan cabang game tim Anda dan masih membuka registrasi.</p>
          </div>
        </div>
        ${renderTournamentDiscoveryCards(
          openTournamentsForCaptain.map((x) => x.tournament),
          gamesById,
          { ownedTeamIds: captainTeamIds, teams: captainTeams }
        )}
      `
          : ""
      }

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Jadwal &amp; Hasil Pertandingan Tim</h3>
              <p class="card-subtitle">${window.TurnamenUI.escapeHtml(ctx.active ? ctx.active.title : "Turnamen aktif")}</p>
            </div>
            ${
              ctx.active
                ? `<button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Lihat Bracket</button>`
                : ""
            }
          </div>
          ${
            teamMatches.length > 0
              ? `<div class="stack-md">${teamMatches
                  .map((m) =>
                    window.TurnamenUI.renderMatchCard(m, { highlightTeamIds: captainTeamIds })
                  )
                  .join("")}</div>`
              : window.TurnamenUI.renderEmptyState(
                  "Belum Ada Match untuk Tim Ini",
                  "Pertandingan untuk tim terpilih pada turnamen aktif akan tampil di sini."
                )
          }
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Pengumuman Panitia</h3>
            <button type="button" class="btn btn-ghost btn-sm" data-action="go-page" data-page="announcements">Semua</button>
          </div>
          ${
            activeAnnouncements.length > 0
              ? `<div class="stack-md">${activeAnnouncements
                  .slice(0, 3)
                  .map(
                    (a) => `
                  <div class="roster-card" style="flex-direction:column; align-items:flex-start;">
                    <div class="row-actions">${window.TurnamenUI.renderStatusBadge(a.priority)}<strong>${window.TurnamenUI.escapeHtml(a.title)}</strong></div>
                    <span class="table-subtext">${window.TurnamenUI.escapeHtml(a.content)}</span>
                  </div>
                `
                  )
                  .join("")}</div>`
              : window.TurnamenUI.renderEmptyState("Belum Ada Pengumuman", "Belum ada instruksi check-in atau pembaruan jadwal.")
          }
        </div>
      </div>
    `;

    const teamSelector = document.getElementById("captain-team-select");
    if (teamSelector) {
      teamSelector.addEventListener("change", (e) => {
        selectedCaptainTeamId = e.target.value;
        navigateTo("dashboard");
      });
    }
  }

  // B1. ORGANIZER DASHBOARD (Management Tournament Control)
  async function renderOrganizerDashboard(container, data, isStale) {
    const user = getCurrentUserSafe();
    const { tournaments, ctx, activeReport, activeRegs, activeAnnouncements, gamesById } = data;
    const myTournaments = user
      ? tournaments.filter((t) => t.organizer_id === user.id)
      : [];

    const regDetails = await Promise.all(
      myTournaments.map(async (t) => {
        const res = await window.TurnamenAPI.getTournamentRegistrations(t.id);
        return res.success && Array.isArray(res.data) ? res.data : [];
      })
    );
    if (isStale()) return;

    const allMyRegs = regDetails.flat();
    const pendingCount = allMyRegs.filter((r) => r.status === "pending").length;
    const approvedTotal = allMyRegs.filter((r) => r.status === "approved").length;
    const activeSummary = activeReport && activeReport.summary ? activeReport.summary : null;
    const pendingActiveRegs = activeRegs.filter((r) => r.status === "pending");
    const canAnnounceActive = Boolean(
      ctx.active && canPerform("announcement:create", { tournament: ctx.active })
    );
    const canVerifyActive = Boolean(
      ctx.active && canPerform("registration:verify", { tournament: ctx.active })
    );

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Kontrol Turnamen &amp; Operasional Organizer</h2>
          <p>Kelola turnamen milik Anda, verifikasi peserta, susun bracket, dan pantau pengesahan skor.</p>
        </div>
        <div class="page-actions">
          ${
            canAnnounceActive
              ? `<button type="button" class="btn btn-secondary" data-action="open-announcement-modal" data-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">+ Pengumuman</button>`
              : ""
          }
          <button type="button" class="btn btn-primary" data-action="open-create-tournament">${window.TurnamenUI.icon("plus", 15)}<span>Buat Turnamen Baru</span></button>
        </div>
      </div>

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Turnamen Dikelola</div>
          <div class="metric-value">${myTournaments.length}</div>
          <div class="metric-note">Dari total ${tournaments.length} turnamen di sistem</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Peserta Terverifikasi</div>
          <div class="metric-value">${approvedTotal}</div>
          <div class="metric-note">Total registrasi disetujui pada turnamen Anda</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Antrean Verifikasi Pending</div>
          <div class="metric-value">${pendingCount}</div>
          <div class="metric-note">${pendingCount > 0 ? "Memerlukan persetujuan panitia/EO" : "Seluruh pendaftar telah diproses"}</div>
        </div>
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Progres Turnamen Aktif</div>
          <div class="metric-value">${activeSummary ? `${activeSummary.completed_matches} / ${activeSummary.total_matches}` : "0 / 0"}</div>
          <div class="metric-note">${activeSummary ? `${activeSummary.completion_percentage}% selesai` : "Belum ada jadwal"}</div>
        </div>
      </div>

      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Turnamen Milik Anda</h3>
            <p class="card-subtitle">Akses cepat ke peserta, bracket, pengesahan skor, dan edit data turnamen.</p>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-list">Semua Turnamen</button>
        </div>
        ${
          myTournaments.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Belum Ada Turnamen Dikelola",
                "Buat turnamen pertama Anda untuk memulai pendaftaran dan bracket.",
                `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-tournament">Buat Turnamen Baru</button>`
              )
            : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th class="col-title">Turnamen</th>
                  <th class="col-game">Game</th>
                  <th class="col-quota">Kuota Terisi</th>
                  <th class="col-money">Prize Pool</th>
                  <th class="col-status">Status</th>
                  <th class="col-actions">Aksi Pengelolaan</th>
                </tr>
              </thead>
              <tbody>
                ${myTournaments
                  .map((t) => {
                    const max = Number(t.max_teams || 0);
                    const app = Number(t.approved_teams_count || 0);
                    const pct = max > 0 ? Math.round((app / max) * 100) : 0;
                    const canEdit = canPerform("tournament:edit", { tournament: t });
                    const canDelete =
                      canPerform("tournament:delete", { tournament: t }) &&
                      t.status !== "ongoing" &&
                      t.status !== "completed";
                    return `
                    <tr>
                      <td class="col-title">
                        <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>
                        <div class="table-subtext">${window.TurnamenUI.escapeHtml(t.venue || "Online")} | Bo${t.best_of}</div>
                      </td>
                      <td class="col-game">${window.TurnamenUI.renderGameChip(t.game_name, gamesById[t.game_id] || t.game_id)}</td>
                      <td class="col-quota">
                        <div class="tabular-nums" style="font-size:12px; margin-bottom:4px;">${app} / ${max} Tim</div>
                        ${window.TurnamenUI.renderProgressBar(pct, `Kuota ${t.title}`)}
                      </td>
                      <td class="col-money tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</td>
                      <td class="col-status">${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                      <td class="col-actions">
                        <div class="row-actions">
                          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Peserta</button>
                          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="match-management" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Skor</button>
                          <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Bracket</button>
                          ${
                            canEdit
                              ? `<button type="button" class="btn btn-ghost btn-sm" data-action="open-edit-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}" aria-label="Edit ${window.TurnamenUI.escapeHtml(t.title)}">${window.TurnamenUI.icon("edit", 14)}</button>`
                              : ""
                          }
                          ${
                            canDelete
                              ? `<button type="button" class="btn btn-danger btn-sm" data-action="confirm-delete-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}" aria-label="Hapus ${window.TurnamenUI.escapeHtml(t.title)}">${window.TurnamenUI.icon("trash", 14)}</button>`
                              : ""
                          }
                        </div>
                      </td>
                    </tr>
                  `;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        }
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Verifikasi Registrasi (${window.TurnamenUI.escapeHtml(ctx.active ? ctx.active.title : "Turnamen Aktif")})</h3>
            ${
              canVerifyActive
                ? `<button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Kelola Peserta</button>`
                : ""
            }
          </div>
          ${
            !canVerifyActive
              ? window.TurnamenUI.renderEmptyState(
                  "Turnamen Bukan Milik Anda",
                  "Turnamen aktif saat ini dikelola oleh organizer lain. Pilih turnamen dari daftar Turnamen Milik Anda untuk melakukan verifikasi peserta."
                )
              : pendingActiveRegs.length > 0
                ? `
            <div class="table-container">
              <table class="data-table">
                <thead><tr><th>Tim</th><th>Seed</th><th>Aksi</th></tr></thead>
                <tbody>
                  ${pendingActiveRegs
                    .map(
                      (r) => `
                    <tr>
                      <td>
                        <div class="team-cell-inline">
                          ${window.TurnamenUI.renderTeamEmblem(r.team_tag, 24)}
                          <strong>${window.TurnamenUI.escapeHtml(r.team_name)}</strong>
                          <span class="badge badge-neutral">${window.TurnamenUI.escapeHtml(r.team_tag)}</span>
                        </div>
                      </td>
                      <td class="tabular-nums">#${r.seed_number || "-"}</td>
                      <td>
                        <div class="row-actions">
                          <button type="button" class="btn btn-success btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}" data-status="approved">Setujui</button>
                          <button type="button" class="btn btn-danger btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}" data-status="rejected">Tolak</button>
                        </div>
                      </td>
                    </tr>
                  `
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `
                : window.TurnamenUI.renderEmptyState(
                    "Tidak Ada Antrean Pending",
                    `${activeRegs.length} registrasi pada turnamen aktif sudah berada dalam status terverifikasi/selesai.`
                  )
          }
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Audit Aktivitas &amp; Pengumuman</h3>
            <span class="badge badge-info tabular-nums">${activeAnnouncements.length} Pengumuman</span>
          </div>
          ${
            activeReport && Array.isArray(activeReport.recent_activity) && activeReport.recent_activity.length > 0
              ? `
            <div class="table-container">
              <table class="data-table">
                <thead><tr><th>Aksi</th><th>Entitas</th><th>Waktu</th></tr></thead>
                <tbody>
                  ${activeReport.recent_activity
                    .slice(0, 6)
                    .map(
                      (log) => `
                    <tr>
                      <td><code>${window.TurnamenUI.escapeHtml(log.action)}</code></td>
                      <td>${window.TurnamenUI.escapeHtml(log.entity_type)}</td>
                      <td class="tabular-nums">${window.TurnamenUI.formatDateTime(log.created_at)}</td>
                    </tr>
                  `
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `
              : window.TurnamenUI.renderEmptyState("Belum Ada Log Aktivitas", "Belum ada log terbaru pada turnamen aktif.")
          }
        </div>
      </div>
    `;
  }

  // B2. COMMITTEE DASHBOARD (Operational Match & Verification Desk)
  function renderCommitteeDashboard(container, data) {
    const user = getCurrentUserSafe();
    const { tournaments, ctx, activeMatches, activeRegs, activeAnnouncements, activeReport } = data;
    const playableMatches = activeMatches.filter(
      (m) => m.team_a_id && m.team_b_id && m.status !== "completed" && m.status !== "bye"
    );
    const settledMatches = activeMatches.filter(
      (m) => m.status === "completed" || m.status === "bye"
    );
    const pendingRegs = activeRegs.filter((r) => r.status === "pending");
    const assignedTournaments = (tournaments || []).filter(
      (t) => getCommitteeTournamentAssignment(t, user) === true
    );
    const committeeAssignment = ctx.active
      ? getCommitteeTournamentAssignment(ctx.active, user)
      : null;
    const canAnnounce = Boolean(
      ctx.active && canPerform("announcement:create", { tournament: ctx.active })
    );
    const canSubmitScore = Boolean(
      ctx.active && canPerform("match:submit_result", { tournament: ctx.active })
    );
    const canVerifyRegs = Boolean(
      ctx.active && canPerform("registration:verify", { tournament: ctx.active })
    );
    const unverifiedLabel =
      committeeAssignment === false
        ? "Tidak ditugaskan pada turnamen ini"
        : "Penugasan belum dapat diverifikasi";

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      ${renderTournamentContextBar(
        ctx.list,
        ctx.active,
        ctx.active
          ? `
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Bracket</button>
          ${
            canAnnounce
              ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-announcement-modal" data-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">+ Buat Pengumuman</button>`
              : ""
          }
        `
          : ""
      )}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Meja Operasional Panitia &amp; Wasit</h2>
          <p>Fokus pada validasi peserta, pengesahan skor pertandingan, dan pengumuman teknis turnamen.</p>
        </div>
        <button type="button" class="btn btn-primary" data-action="go-page" data-page="match-management">Buka Jadwal &amp; Skor Penuh</button>
      </div>
      ${renderCommitteeAssignmentNotice(ctx.active)}

      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Turnamen Ditugaskan kepada Anda</h3>
            <p class="card-subtitle">Pilih turnamen yang menugaskan akun panitia Anda untuk mulai memverifikasi peserta dan mengesahkan skor.</p>
          </div>
          <span class="badge badge-info tabular-nums">${assignedTournaments.length} Ditugaskan</span>
        </div>
        ${
          assignedTournaments.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Belum Ada Penugasan Turnamen",
                "Belum ada turnamen yang menugaskan akun panitia Anda saat ini. Hubungi Organizer atau Super Admin untuk penugasan."
              )
            : `
          <div class="row-actions" style="flex-wrap:wrap; gap:8px;">
            ${assignedTournaments
              .map((t) => {
                const isSelected = ctx.active && ctx.active.id === t.id;
                return `<button type="button" class="btn ${isSelected ? "btn-primary" : "btn-secondary"} btn-sm" data-action="go-page" data-page="dashboard" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">${window.TurnamenUI.escapeHtml(t.title)} (${window.TurnamenUI.escapeHtml(t.status)})</button>`;
              })
              .join("")}
          </div>
        `
        }
      </div>

      <div class="grid-4">
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Match Siap Disahkan</div>
          <div class="metric-value">${playableMatches.length}</div>
          <div class="metric-note">Menunggu hasil skor pertandingan</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Match Selesai &amp; BYE</div>
          <div class="metric-value">${settledMatches.length}</div>
          <div class="metric-note">Dari total ${activeMatches.length} match bracket</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Verifikasi Pending</div>
          <div class="metric-value">${pendingRegs.length}</div>
          <div class="metric-note">Total ${activeRegs.length} registrasi pada turnamen ini</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Pengumuman Aktif</div>
          <div class="metric-value">${activeAnnouncements.length}</div>
          <div class="metric-note">Informasi teknis untuk peserta</div>
        </div>
      </div>

      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Antrean Pengesahan Skor Cepat</h3>
            <p class="card-subtitle">Pertandingan yang sudah memiliki kedua tim dan siap disahkan panitia.</p>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="match-management">Semua Pertandingan</button>
        </div>
        ${
          playableMatches.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Tidak Ada Match Menunggu Skor",
                "Semua pertandingan yang siap dimainkan sudah disahkan atau masih menunggu pemenang babak sebelumnya."
              )
            : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Babak</th>
                  <th>Match</th>
                  <th>Team A</th>
                  <th>Team B</th>
                  <th>Status</th>
                  <th>Input &amp; Sahkan Skor</th>
                </tr>
              </thead>
              <tbody>
                ${playableMatches
                  .map((m) => {
                    const maxWin = Math.ceil(Number(m.best_of || 3) / 2);
                    const scoreActionHtml = canSubmitScore
                      ? `
                        <div class="score-inline-form">
                          <label for="score-a-${window.TurnamenUI.escapeHtml(m.id)}" class="sr-only">Skor ${window.TurnamenUI.escapeHtml(m.team_a_name)}</label>
                          <input id="score-a-${window.TurnamenUI.escapeHtml(m.id)}" type="number" min="0" max="${maxWin}" value="${m.score_a}" class="form-input tabular-nums score-inline-input" />
                          <span aria-hidden="true">:</span>
                          <label for="score-b-${window.TurnamenUI.escapeHtml(m.id)}" class="sr-only">Skor ${window.TurnamenUI.escapeHtml(m.team_b_name)}</label>
                          <input id="score-b-${window.TurnamenUI.escapeHtml(m.id)}" type="number" min="0" max="${maxWin}" value="${m.score_b}" class="form-input tabular-nums score-inline-input" />
                          <button type="button" class="btn btn-primary btn-sm" data-action="submit-score" data-id="${window.TurnamenUI.escapeHtml(m.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Sahkan</button>
                        </div>
                      `
                      : `<span class="table-subtext">${unverifiedLabel}</span>`;
                    return `
                    <tr>
                      <td><strong>${window.TurnamenUI.escapeHtml(m.round_name)}</strong></td>
                      <td class="tabular-nums">#${m.match_number} (Bo${m.best_of})</td>
                      <td>
                        <div class="team-cell-inline">
                          ${m.team_a_id ? window.TurnamenUI.renderTeamEmblem(m.team_a_tag, 22) : ""}
                          <span>${window.TurnamenUI.escapeHtml(m.team_a_name)}</span>
                        </div>
                      </td>
                      <td>
                        <div class="team-cell-inline">
                          ${m.team_b_id ? window.TurnamenUI.renderTeamEmblem(m.team_b_tag, 22) : ""}
                          <span>${window.TurnamenUI.escapeHtml(m.team_b_name)}</span>
                        </div>
                      </td>
                      <td>${window.TurnamenUI.renderStatusBadge(m.status)}</td>
                      <td>${scoreActionHtml}</td>
                    </tr>
                  `;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        }
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Antrean Verifikasi Peserta</h3>
            <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail">Panel Peserta</button>
          </div>
          ${
            !canVerifyRegs
              ? window.TurnamenUI.renderEmptyState(
                  committeeAssignment === false ? "Bukan Penugasan Anda" : "Penugasan Belum Diverifikasi",
                  "Akun panitia Anda hanya dapat memverifikasi peserta pada turnamen yang ditugaskan kepada Anda."
                )
              : pendingRegs.length > 0
                ? `
            <div class="table-container">
              <table class="data-table">
                <thead><tr><th>Tim</th><th>Status</th><th>Aksi</th></tr></thead>
                <tbody>
                  ${pendingRegs
                    .map(
                      (r) => `
                    <tr>
                      <td>
                        <div class="team-cell-inline">
                          ${window.TurnamenUI.renderTeamEmblem(r.team_tag, 24)}
                          <strong>${window.TurnamenUI.escapeHtml(r.team_name)}</strong>
                          <span class="badge badge-neutral">${window.TurnamenUI.escapeHtml(r.team_tag)}</span>
                        </div>
                      </td>
                      <td>${window.TurnamenUI.renderStatusBadge(r.status)}</td>
                      <td>
                        <div class="row-actions">
                          <button type="button" class="btn btn-success btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}" data-status="approved">Setujui</button>
                          <button type="button" class="btn btn-danger btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}" data-status="rejected">Tolak</button>
                        </div>
                      </td>
                    </tr>
                  `
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `
                : window.TurnamenUI.renderEmptyState(
                    "Semua Peserta Terverifikasi",
                    `${activeRegs.length} tim pendaftar sudah diproses.`
                  )
          }
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Audit Log Operasional</h3>
            <span class="badge badge-violet">Audit Trail</span>
          </div>
          ${
            activeReport && Array.isArray(activeReport.recent_activity) && activeReport.recent_activity.length > 0
              ? `
            <div class="table-container">
              <table class="data-table">
                <thead><tr><th>Aksi</th><th>Entitas</th><th>Waktu</th></tr></thead>
                <tbody>
                  ${activeReport.recent_activity
                    .slice(0, 6)
                    .map(
                      (log) => `
                    <tr>
                      <td><code>${window.TurnamenUI.escapeHtml(log.action)}</code></td>
                      <td>${window.TurnamenUI.escapeHtml(log.entity_type)}</td>
                      <td class="tabular-nums">${window.TurnamenUI.formatDateTime(log.created_at)}</td>
                    </tr>
                  `
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `
              : window.TurnamenUI.renderEmptyState("Belum Ada Aktivitas", "Belum ada log operasional terbaru.")
          }
        </div>
      </div>
    `;
  }

  // B3. SUPER ADMIN DASHBOARD (System Administration & Cross-Tournament Telemetry)
  const USER_ROLE_LABELS = {
    player: "Player",
    team_captain: "Team Captain",
    committee: "Committee / Panitia",
    organizer: "Tournament Organizer",
    super_admin: "Super Admin",
  };

  function buildSuperAdminMetricsHtml(saState) {
    const ongoingCount = saState.tournaments.filter((t) => t.status === "ongoing").length;
    const openCount = saState.tournaments.filter((t) => t.status === "open_registration").length;
    const totalRosterPlayers = saState.teams.reduce(
      (sum, tm) => sum + Number(tm.member_count ?? (tm.members ? tm.members.length : 0)),
      0
    );
    const summary =
      saState.activeReport && saState.activeReport.summary ? saState.activeReport.summary : null;

    const metricCardSkeleton = (label) => `
      <div class="metric-card skeleton-metric-card" role="status" aria-busy="true">
        <div class="metric-label">${label}</div>
        <span class="arena-skeleton arena-skeleton-line is-xl" style="width:44%;"></span>
        <span class="arena-skeleton arena-skeleton-line is-xs" style="width:72%;"></span>
      </div>
    `;

    const tournamentsCard = !saState.tournamentsReady
      ? metricCardSkeleton("Total Turnamen Sistem")
      : saState.tourError
        ? `
          <div class="metric-card">
            <div class="metric-label">Total Turnamen Sistem</div>
            <div class="metric-value">-</div>
            <div class="metric-note">${window.TurnamenUI.escapeHtml(saState.tourError)}</div>
          </div>
        `
        : `
          <div class="metric-card">
            <div class="metric-label">Total Turnamen Sistem</div>
            <div class="metric-value">${saState.tournaments.length}</div>
            <div class="metric-note">${ongoingCount} berlangsung, ${openCount} buka pendaftaran</div>
          </div>
        `;

    const gamesCard = !saState.gamesReady
      ? metricCardSkeleton("Cabang Game Sistem")
      : `
          <div class="metric-card">
            <div class="metric-label">Cabang Game Sistem</div>
            <div class="metric-value">${saState.adminGames.length}</div>
            <div class="metric-note">${saState.adminGames.filter((g) => g.is_active !== false).length} cabang game aktif</div>
          </div>
        `;

    const teamsCard = !saState.teamsReady
      ? metricCardSkeleton("Total Tim &amp; Pemain")
      : `
          <div class="metric-card">
            <div class="metric-label">Total Tim &amp; Pemain</div>
            <div class="metric-value">${saState.teamsOk ? saState.teams.length : "-"}</div>
            <div class="metric-note">${saState.teamsOk ? `${totalRosterPlayers} total pemain pada roster` : window.TurnamenUI.escapeHtml(saState.teamsError || "Data tim gagal dimuat")}</div>
          </div>
        `;

    const reportCard = !saState.reportReady
      ? metricCardSkeleton("Progres Turnamen Aktif")
      : `
          <div class="metric-card metric-card-accent">
            <div class="metric-label">Progres Turnamen Aktif</div>
            <div class="metric-value">${summary ? `${summary.completed_matches} / ${summary.total_matches}` : saState.reportError ? "-" : "0 / 0"}</div>
            <div class="metric-note">${summary ? `${summary.completion_percentage}% selesai` : saState.reportError ? window.TurnamenUI.escapeHtml(saState.reportError) : "Belum ada pertandingan"}</div>
          </div>
        `;

    return `<div class="grid-4">${tournamentsCard}${gamesCard}${teamsCard}${reportCard}</div>`;
  }

  function buildSuperAdminTournamentsCardHtml(saState) {
    if (!saState.tournamentsReady) {
      return window.TurnamenUI.renderTableSkeleton({
        rows: 4,
        columns: 4,
        title: "Kontrol Seluruh Turnamen",
      });
    }
    return `
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Kontrol Seluruh Turnamen</h3>
            <p class="card-subtitle">Akses administrasi penuh untuk mengubah, mengaudit, atau memantau bracket.</p>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-list">Kelola Lengkap</button>
        </div>
        ${
          saState.tourError
            ? window.TurnamenUI.renderErrorState(saState.tourError, "retry-page")
            : saState.tournaments.length === 0
              ? window.TurnamenUI.renderEmptyState("Belum Ada Turnamen", "Sistem belum memiliki data turnamen.")
              : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th class="col-title">Turnamen</th>
                  <th class="col-quota">Peserta</th>
                  <th class="col-status">Status</th>
                  <th class="col-actions">Aksi</th>
                </tr>
              </thead>
              <tbody>
                ${saState.tournaments
                  .map(
                    (t) => `
                  <tr>
                    <td class="col-title">
                      <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>
                      <div class="table-subtext">${window.TurnamenUI.escapeHtml(t.game_name)} | ${window.TurnamenUI.escapeHtml(t.venue || "Online")}</div>
                    </td>
                    <td class="col-quota tabular-nums">${t.approved_teams_count || 0} / ${t.max_teams}</td>
                    <td class="col-status">${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                    <td class="col-actions">
                      <div class="row-actions">
                        <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Peserta</button>
                        <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Bracket</button>
                        <button type="button" class="btn btn-ghost btn-sm" data-action="open-edit-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}" aria-label="Edit ${window.TurnamenUI.escapeHtml(t.title)}">${window.TurnamenUI.icon("edit", 14)}</button>
                      </div>
                    </td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        }
      </div>
    `;
  }

  function buildSuperAdminGamesCardHtml(saState) {
    if (!saState.gamesReady) {
      return window.TurnamenUI.renderListSkeleton({
        rows: 3,
        title: "Katalog & Pengaturan Game",
        withAvatar: false,
      });
    }
    return `
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Katalog &amp; Pengaturan Game</h3>
            <p class="card-subtitle">Tambah, ubah konfigurasi, atau ganti poster resmi cabang game.</p>
          </div>
          <div class="row-actions">
            <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="game-management">${window.TurnamenUI.icon("image", 14)}<span>Kelola Poster</span></button>
            <button type="button" class="btn btn-primary btn-sm" data-action="open-create-game">${window.TurnamenUI.icon("plus", 14)}<span>Tambah</span></button>
          </div>
        </div>
        ${
          saState.gamesError && saState.adminGames.length === 0
            ? window.TurnamenUI.renderErrorState(saState.gamesError, "retry-games")
            : saState.adminGames.length > 0
              ? `
          <div class="kv-list">
            ${saState.adminGames
              .map((g) => {
                const gTours = saState.tournaments.filter((t) => t.game_id === g.id).length;
                const gTeams = saState.teams.filter((tm) => tm.game_id === g.id).length;
                const inactiveTag =
                  g.is_active === false ? ' <span class="badge badge-neutral">Nonaktif</span>' : "";
                const customTag = g.custom_artwork_url
                  ? ' <span class="badge badge-info">Poster Kustom</span>'
                  : "";
                return `
                <div class="kv-item">
                  <span class="kv-label">${window.TurnamenUI.renderGameChip(g)}${customTag}${inactiveTag}</span>
                  <span class="kv-value row-actions">
                    <span class="tabular-nums">${gTours} Turnamen | ${gTeams} Tim</span>
                    <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="game-management" aria-label="Kelola poster ${window.TurnamenUI.escapeHtml(g.name)}">${window.TurnamenUI.icon("image", 14)}<span>Poster</span></button>
                    <button type="button" class="btn btn-ghost btn-sm" data-action="open-edit-game" data-id="${window.TurnamenUI.escapeHtml(g.id)}" aria-label="Edit game ${window.TurnamenUI.escapeHtml(g.name)}">${window.TurnamenUI.icon("edit", 14)}</button>
                  </span>
                </div>
              `;
              })
              .join("")}
          </div>
        `
              : window.TurnamenUI.renderEmptyState("Game Kosong", "Belum ada cabang game terdaftar.")
        }
      </div>
    `;
  }

  function buildSuperAdminTelemetryCardHtml(state) {
    return `
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Telemetri Lingkungan Sistem</h3>
          <span class="badge ${isMockMode() ? "badge-warning" : "badge-success"}">${window.TurnamenUI.escapeHtml(state.appMode.toUpperCase())}</span>
        </div>
        <div class="kv-list">
          <div class="kv-item">
            <span class="kv-label">Endpoint API</span>
            <span class="kv-value"><code>${window.TurnamenUI.escapeHtml(state.apiBaseUrl)}</code></span>
          </div>
          <div class="kv-item">
            <span class="kv-label">Transport</span>
            <span class="kv-value">${window.TurnamenBridge && window.TurnamenBridge.hasEel() ? "Python Eel Bridge" : "HTTP REST Lokal"}</span>
          </div>
        </div>
      </div>
    `;
  }

  function buildSuperAdminUsersCardHtml(saState) {
    if (!saState.usersReady) {
      return window.TurnamenUI.renderTableSkeleton({
        rows: 4,
        columns: 5,
        title: "Manajemen Pengguna & Penetapan Role",
      });
    }
    return `
      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Manajemen Pengguna &amp; Penetapan Role</h3>
            <p class="card-subtitle">Hanya Super Admin yang dapat mengubah role pengguna yang sudah tertaut dengan akun Auth yang sah.</p>
          </div>
          <span class="badge badge-info tabular-nums">${saState.systemUsers.length} Akun</span>
        </div>
        ${
          saState.usersError
            ? window.TurnamenUI.renderErrorState(saState.usersError, "retry-page")
            : saState.systemUsers.length === 0
              ? window.TurnamenUI.renderEmptyState(
                  "Daftar Pengguna Belum Tersedia",
                  "Belum ada data akun pengguna."
                )
              : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Pengguna</th>
                  <th>Email</th>
                  <th>Status Auth</th>
                  <th>Role Saat Ini</th>
                  <th>Ubah Role</th>
                </tr>
              </thead>
              <tbody>
                ${saState.systemUsers
                  .map((u) => {
                    const currentRole = String(u.role || "player").toLowerCase();
                    const linkedBadge = u.is_auth_linked
                      ? `<span class="badge badge-success">Tertaut Auth</span>`
                      : `<span class="badge badge-warning">Belum Tertaut</span>`;
                    const roleOptions = Object.keys(USER_ROLE_LABELS)
                      .map(
                        (rk) =>
                          `<option value="${window.TurnamenUI.escapeHtml(rk)}" ${currentRole === rk ? "selected" : ""}>${window.TurnamenUI.escapeHtml(USER_ROLE_LABELS[rk])}</option>`
                      )
                      .join("");
                    return `
                    <tr>
                      <td>
                        <strong>${window.TurnamenUI.escapeHtml(u.full_name || u.username || "-")}</strong>
                        <div class="table-subtext">@${window.TurnamenUI.escapeHtml(u.username || "-")}</div>
                      </td>
                      <td class="tabular-nums">${window.TurnamenUI.escapeHtml(u.email || "-")}</td>
                      <td>${linkedBadge}</td>
                      <td>${window.TurnamenUI.renderRoleBadge(currentRole)}</td>
                      <td>
                        <div class="row-actions">
                          <label for="user-role-select-${window.TurnamenUI.escapeHtml(u.id)}" class="sr-only">Pilih role untuk ${window.TurnamenUI.escapeHtml(u.username || u.email)}</label>
                          <select id="user-role-select-${window.TurnamenUI.escapeHtml(u.id)}" class="form-select form-select-compact">${roleOptions}</select>
                          <button type="button" class="btn btn-primary btn-sm" data-action="assign-user-role" data-id="${window.TurnamenUI.escapeHtml(u.id)}">Simpan Role</button>
                        </div>
                      </td>
                    </tr>
                  `;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        }
      </div>
    `;
  }

  function buildSuperAdminAuditCardHtml(saState) {
    if (!saState.reportReady) {
      return window.TurnamenUI.renderTableSkeleton({
        rows: 4,
        columns: 3,
        title: "Jejak Audit Aktivitas Sistem",
      });
    }
    const activeTitle =
      saState.ctx && saState.ctx.active ? saState.ctx.active.title : "Turnamen Aktif";
    return `
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Jejak Audit Aktivitas Sistem (${window.TurnamenUI.escapeHtml(activeTitle)})</h3>
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="reports">Laporan Lengkap</button>
        </div>
        ${
          saState.reportError && !saState.activeReport
            ? window.TurnamenUI.renderErrorState(saState.reportError, "retry-page")
            : saState.activeReport &&
                Array.isArray(saState.activeReport.recent_activity) &&
                saState.activeReport.recent_activity.length > 0
              ? `
          <div class="table-container">
            <table class="data-table">
              <thead><tr><th>Aksi</th><th>Entitas</th><th>Waktu</th></tr></thead>
              <tbody>
                ${saState.activeReport.recent_activity
                  .map(
                    (log) => `
                  <tr>
                    <td><code>${window.TurnamenUI.escapeHtml(log.action)}</code></td>
                    <td>${window.TurnamenUI.escapeHtml(log.entity_type)}</td>
                    <td class="tabular-nums">${window.TurnamenUI.formatDateTime(log.created_at)}</td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        `
              : window.TurnamenUI.renderEmptyState(
                  "Belum Ada Aktivitas",
                  "Belum ada log audit pada turnamen aktif."
                )
        }
      </div>
    `;
  }

  function buildSuperAdminFullHtml(saState, runtimeState) {
    return `
      <div id="sa-games-notice-slot">${saState.gamesError && saState.adminGames.length === 0 ? "" : renderGamesErrorNotice()}</div>
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Administrasi Sistem Turnamen.in</h2>
          <p>Kontrol penuh lintas organizer, katalog game, manajemen role pengguna, dan audit operasional.</p>
        </div>
        <div class="page-actions">
          <button type="button" class="btn btn-secondary" data-action="open-create-game">${window.TurnamenUI.icon("plus", 14)}<span>Tambah Game</span></button>
          <button type="button" class="btn btn-secondary" data-action="open-create-team">${window.TurnamenUI.icon("plus", 14)}<span>Buat Tim</span></button>
          <button type="button" class="btn btn-primary" data-action="open-create-tournament">${window.TurnamenUI.icon("plus", 14)}<span>Buat Turnamen</span></button>
        </div>
      </div>

      <div id="sa-metrics-slot">${buildSuperAdminMetricsHtml(saState)}</div>

      <div class="workspace-split">
        <div id="sa-tournaments-slot">${buildSuperAdminTournamentsCardHtml(saState)}</div>

        <div class="stack-md">
          <div id="sa-games-slot">${buildSuperAdminGamesCardHtml(saState)}</div>
          ${buildSuperAdminTelemetryCardHtml(runtimeState)}
        </div>
      </div>

      <div id="sa-users-slot">${buildSuperAdminUsersCardHtml(saState)}</div>
      <div id="sa-audit-slot">${buildSuperAdminAuditCardHtml(saState)}</div>
    `;
  }

  async function renderSuperAdminProgressive(container, isStale, navOptions = {}) {
    const runtimeState = getRuntimeState();
    const hasSnapshot = Boolean(navOptions.hasSnapshot);
    const saState = {
      tournamentsReady: false,
      gamesReady: false,
      teamsReady: false,
      usersReady: false,
      reportReady: false,
      tournaments: [],
      tourError: null,
      adminGames: gamesState.items.slice(),
      gamesError: null,
      teams: [],
      teamsOk: false,
      teamsError: null,
      systemUsers: [],
      usersError: null,
      ctx: { error: null, list: [], active: null },
      activeReport: null,
      reportError: null,
    };

    const getSlot = (selector) =>
      typeof container.querySelector === "function" ? container.querySelector(selector) : null;
    const canPatchSlots = () => !hasSnapshot && Boolean(getSlot("#sa-metrics-slot"));
    const updateSlot = (selector, htmlBuilder) => {
      if (isStale()) return;
      const slot = getSlot(selector);
      if (slot) {
        slot.innerHTML = htmlBuilder(saState);
      }
    };

    if (!hasSnapshot) {
      container.innerHTML = buildSuperAdminFullHtml(saState, runtimeState);
    }

    // Launch all independent Wave 1 requests concurrently; Wave 2 starts as soon as tournaments resolve.
    const gamesTask = window.TurnamenAPI.getGames({ includeInactive: true }).then((gamesRes) => {
      if (isStale()) return;
      saState.gamesReady = true;
      if (gamesRes && gamesRes.success && Array.isArray(gamesRes.data)) {
        saState.adminGames = gamesRes.data;
        adminGamesCache = gamesRes.data;
        gamesState.items = gamesRes.data.filter((g) => g.is_active !== false);
        gamesState.loaded = true;
        gamesState.error = null;
      } else {
        saState.gamesError =
          (gamesRes && gamesRes.message) || "Gagal memuat daftar cabang game.";
        gamesState.items = [];
        gamesState.loaded = false;
        gamesState.error = saState.gamesError;
      }
      if (canPatchSlots()) {
        updateSlot("#sa-games-slot", buildSuperAdminGamesCardHtml);
        updateSlot("#sa-metrics-slot", buildSuperAdminMetricsHtml);
      }
    });

    const teamsTask = window.TurnamenAPI.getTeams().then((teamsRes) => {
      if (isStale()) return;
      saState.teamsReady = true;
      if (teamsRes && teamsRes.success && Array.isArray(teamsRes.data)) {
        saState.teamsOk = true;
        saState.teams = teamsRes.data;
      } else {
        saState.teamsOk = false;
        saState.teams = [];
        saState.teamsError = (teamsRes && teamsRes.message) || "Data tim gagal dimuat";
      }
      if (canPatchSlots()) {
        updateSlot("#sa-metrics-slot", buildSuperAdminMetricsHtml);
        if (saState.gamesReady) {
          updateSlot("#sa-games-slot", buildSuperAdminGamesCardHtml);
        }
      }
    });

    const usersTask = window.TurnamenAPI.getUsers().then((usersRes) => {
      if (isStale()) return;
      saState.usersReady = true;
      if (usersRes && usersRes.success && Array.isArray(usersRes.data)) {
        saState.systemUsers = usersRes.data;
      } else {
        saState.systemUsers = [];
        saState.usersError =
          (usersRes && usersRes.message) || "Daftar pengguna gagal dimuat.";
      }
      if (canPatchSlots()) {
        updateSlot("#sa-users-slot", buildSuperAdminUsersCardHtml);
      }
    });

    const tourAndReportTask = window.TurnamenAPI.getTournaments().then(async (tourRes) => {
      if (isStale()) return;
      saState.tournamentsReady = true;
      if (tourRes && tourRes.success) {
        saState.tournaments = Array.isArray(tourRes.data) ? tourRes.data : [];
        saState.ctx = await resolveActiveTournamentContext(saState.tournaments);
      } else {
        saState.tournaments = [];
        saState.tourError =
          (tourRes && tourRes.message) || "Gagal memuat daftar turnamen.";
      }
      if (isStale()) return;

      if (canPatchSlots()) {
        updateSlot("#sa-tournaments-slot", buildSuperAdminTournamentsCardHtml);
        updateSlot("#sa-metrics-slot", buildSuperAdminMetricsHtml);
        if (saState.gamesReady) {
          updateSlot("#sa-games-slot", buildSuperAdminGamesCardHtml);
        }
      }

      if (saState.ctx && saState.ctx.active) {
        const reportRes = await window.TurnamenAPI.getTournamentReport(saState.ctx.active.id);
        if (isStale()) return;
        saState.reportReady = true;
        if (reportRes && reportRes.success && reportRes.data) {
          saState.activeReport = reportRes.data;
        } else if (reportRes && !reportRes.success) {
          saState.reportError =
            reportRes.message || "Ringkasan laporan turnamen gagal dimuat.";
        }
      } else {
        saState.reportReady = true;
      }

      if (canPatchSlots()) {
        updateSlot("#sa-audit-slot", buildSuperAdminAuditCardHtml);
        updateSlot("#sa-metrics-slot", buildSuperAdminMetricsHtml);
      }
    });

    await Promise.all([gamesTask, teamsTask, usersTask, tourAndReportTask]);
    if (isStale()) return;

    const finalHtml = buildSuperAdminFullHtml(saState, runtimeState);
    if (!canPatchSlots()) {
      container.innerHTML = finalHtml;
    }
    if (
      navOptions.snapKey &&
      !saState.tourError &&
      !saState.gamesError &&
      !saState.teamsError &&
      !saState.usersError &&
      !saState.reportError
    ) {
      uiPageSnapshots.set(navOptions.snapKey, finalHtml);
    }
  }

  async function renderSuperAdminDashboard(container, data, isStale = () => false) {
    const {
      tournaments,
      teams,
      teamsOk,
      ctx,
      activeReport,
      reportError,
      preloadedUsersRes,
      preloadedAllGamesRes,
    } = data;
    const state = getRuntimeState();
    let usersRes = preloadedUsersRes || null;
    let allGamesRes = preloadedAllGamesRes || null;
    if (!usersRes || !allGamesRes) {
      const [fetchedUsers, fetchedAllGames] = await Promise.all([
        usersRes ? Promise.resolve(usersRes) : window.TurnamenAPI.getUsers(),
        allGamesRes ? Promise.resolve(allGamesRes) : window.TurnamenAPI.getGames({ includeInactive: true }),
      ]);
      if (isStale()) return;
      usersRes = fetchedUsers;
      allGamesRes = fetchedAllGames;
    }

    const saState = {
      tournamentsReady: true,
      gamesReady: true,
      teamsReady: true,
      usersReady: true,
      reportReady: true,
      tournaments: Array.isArray(tournaments) ? tournaments : [],
      tourError: null,
      adminGames:
        allGamesRes && allGamesRes.success && Array.isArray(allGamesRes.data)
          ? allGamesRes.data
          : gamesState.items,
      gamesError: allGamesRes && !allGamesRes.success ? allGamesRes.message : null,
      teams: Array.isArray(teams) ? teams : [],
      teamsOk: Boolean(teamsOk),
      teamsError: null,
      systemUsers:
        usersRes && usersRes.success && Array.isArray(usersRes.data) ? usersRes.data : [],
      usersError: usersRes && !usersRes.success ? usersRes.message : null,
      ctx: ctx || { error: null, list: [], active: null },
      activeReport: activeReport || null,
      reportError: reportError || null,
    };

    container.innerHTML = buildSuperAdminFullHtml(saState, state);
  }

  async function submitAssignUserRole(userId, triggerEl = null) {
    const selectEl = document.getElementById(`user-role-select-${userId}`);
    const newRole = selectEl ? selectEl.value : "";
    if (!newRole) {
      window.TurnamenUI.showToast("Pilih role target yang valid.", "warning");
      return;
    }
    await withSubmissionGuard(`user:assign-role:${userId}`, triggerEl, "Menyimpan...", async () => {
      const res = await window.TurnamenAPI.assignUserRole(userId, newRole);
      if (!res.success) {
        window.TurnamenUI.showToast(res.message, "danger");
        return;
      }
      window.TurnamenUI.showToast("Role pengguna berhasil diperbarui.", "success");
      await navigateTo("dashboard");
    });
  }

  function openCreateGameModal() {
    window.TurnamenUI.openModal({
      title: "Tambah Cabang Game Baru",
      bodyHtml: `
        <div class="form-group">
          <label for="game-form-name" class="form-label">Nama Game</label>
          <input id="game-form-name" class="form-input" placeholder="Contoh: Counter-Strike 2" />
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="game-form-genre" class="form-label">Genre</label>
            <input id="game-form-genre" class="form-input" placeholder="FPS / MOBA / Battle Royale" />
          </div>
          <div class="form-group">
            <label for="game-form-platform" class="form-label">Platform</label>
            <input id="game-form-platform" class="form-input" value="PC / Mobile" />
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="game-form-team-size" class="form-label">Ukuran Tim</label>
            <input id="game-form-team-size" type="number" min="1" max="20" class="form-input tabular-nums" value="5" />
          </div>
          <div class="form-group">
            <label for="game-form-bo" class="form-label">Default Best Of</label>
            <select id="game-form-bo" class="form-select">
              <option value="1">Bo1</option>
              <option value="3" selected>Bo3</option>
              <option value="5">Bo5</option>
              <option value="7">Bo7</option>
            </select>
          </div>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-create-game">Simpan Game</button>
      `,
    });
  }

  async function openEditGameModal(gameId) {
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const res = await window.TurnamenAPI.getGameById(gameId);
    if (isModalRequestStale(startNavSeq, startRoleKey)) return;
    if (!res.success || !res.data) {
      window.TurnamenUI.showToast(res.message || "Gagal memuat detail game.", "danger");
      return;
    }
    const g = res.data;
    window.TurnamenUI.openModal({
      title: `Edit Cabang Game: ${g.name}`,
      bodyHtml: `
        <div class="form-group">
          <label for="game-form-name" class="form-label">Nama Game</label>
          <input id="game-form-name" class="form-input" value="${window.TurnamenUI.escapeHtml(g.name || "")}" />
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="game-form-genre" class="form-label">Genre</label>
            <input id="game-form-genre" class="form-input" value="${window.TurnamenUI.escapeHtml(g.genre || "")}" />
          </div>
          <div class="form-group">
            <label for="game-form-platform" class="form-label">Platform</label>
            <input id="game-form-platform" class="form-input" value="${window.TurnamenUI.escapeHtml(g.platform || "PC / Mobile")}" />
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="game-form-team-size" class="form-label">Ukuran Tim</label>
            <input id="game-form-team-size" type="number" min="1" max="20" class="form-input tabular-nums" value="${Number(g.team_size || 5)}" />
          </div>
          <div class="form-group">
            <label for="game-form-bo" class="form-label">Default Best Of</label>
            <select id="game-form-bo" class="form-select">
              ${[1, 3, 5, 7]
                .map(
                  (bo) =>
                    `<option value="${bo}" ${Number(g.default_best_of || 3) === bo ? "selected" : ""}>Bo${bo}</option>`
                )
                .join("")}
            </select>
          </div>
        </div>
        <div class="form-group">
          <label for="game-form-active" class="form-label">Status Katalog</label>
          <select id="game-form-active" class="form-select">
            <option value="true" ${g.is_active !== false ? "selected" : ""}>Aktif (Ditampilkan)</option>
            <option value="false" ${g.is_active === false ? "selected" : ""}>Nonaktif (Disembunyikan)</option>
          </select>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-edit-game" data-id="${window.TurnamenUI.escapeHtml(g.id)}">Simpan Perubahan</button>
      `,
    });
  }

  async function submitGameModal(gameId = "", triggerEl = null) {
    const isEdit = Boolean(gameId);
    const lockKey = isEdit ? `game:edit:${gameId}` : "game:create";
    await withSubmissionGuard(
      lockKey,
      triggerEl,
      "Menyimpan...",
      async () => {
        const name = (document.getElementById("game-form-name")?.value || "").trim();
        const genre = (document.getElementById("game-form-genre")?.value || "").trim();
        const platform = (document.getElementById("game-form-platform")?.value || "PC / Mobile").trim();
        const teamSize = Number(document.getElementById("game-form-team-size")?.value || 5);
        const defaultBo = Number(document.getElementById("game-form-bo")?.value || 3);
        const activeEl = document.getElementById("game-form-active");

        if (name.length < 2 || genre.length < 2) {
          window.TurnamenUI.showToast("Nama dan genre game minimal 2 karakter.", "warning");
          return;
        }
        const payload = {
          name,
          genre,
          platform,
          team_size: teamSize,
          default_best_of: defaultBo,
        };
        if (isEdit && activeEl) {
          payload.is_active = activeEl.value === "true";
        }
        const res = isEdit
          ? await window.TurnamenAPI.updateGame(gameId, payload)
          : await window.TurnamenAPI.createGame(payload);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.closeModal(true);
        await ensureGamesLoaded(true);
        window.TurnamenUI.showToast(
          isEdit ? "Cabang game berhasil diperbarui." : "Cabang game baru berhasil ditambahkan.",
          "success"
        );
        clearUiPageSnapshots();
        await navigateTo(currentPage === "game-management" ? "game-management" : "dashboard");
      },
      { lockModal: true }
    );
  }

  // =========================================================================
  // WAVE 6.11: MANAJEMEN GAME & CUSTOM ARTWORK POSTER
  // =========================================================================
  const MAX_GAME_ARTWORK_BYTES = 5 * 1024 * 1024;
  const ALLOWED_ARTWORK_MIMES = new Set(["image/jpeg", "image/jpg", "image/png", "image/webp"]);
  const ALLOWED_ARTWORK_EXTS = new Set([".jpg", ".jpeg", ".png", ".webp"]);

  function bytesToBase64(bytes) {
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
    }
    return btoa(binary);
  }

  function detectArtworkSignature(bytes, filename, declaredMime) {
    if (!bytes || bytes.length === 0) {
      return { ok: false, message: "File gambar poster kosong atau tidak terbaca." };
    }
    if (bytes.length > MAX_GAME_ARTWORK_BYTES) {
      return { ok: false, message: "Ukuran gambar poster melebihi batas maksimal 5 MB." };
    }
    const lowerHead = String.fromCharCode.apply(null, bytes.subarray(0, Math.min(256, bytes.length))).toLowerCase();
    if (
      lowerHead.includes("<svg") ||
      lowerHead.includes("<?xml") ||
      lowerHead.includes("<html") ||
      lowerHead.includes("<script") ||
      (bytes[0] === 0x4d && bytes[1] === 0x5a) ||
      (bytes[0] === 0x7f && bytes[1] === 0x45 && bytes[2] === 0x4c && bytes[3] === 0x46)
    ) {
      return {
        ok: false,
        message: "Format SVG, HTML, atau executable tidak diperbolehkan. Gunakan JPEG, PNG, atau WebP.",
      };
    }

    let detectedMime = "";
    if (bytes.length >= 8 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) {
      detectedMime = "image/png";
    } else if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
      detectedMime = "image/jpeg";
    } else if (
      bytes.length >= 12 &&
      bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46 &&
      bytes[8] === 0x57 &&
      bytes[9] === 0x45 &&
      bytes[10] === 0x42 &&
      bytes[11] === 0x50
    ) {
      detectedMime = "image/webp";
    }
    if (!detectedMime) {
      return {
        ok: false,
        message: "Signature file tidak dikenali sebagai JPEG, PNG, atau WebP yang valid.",
      };
    }

    const cleanName = String(filename || "").trim().toLowerCase();
    const dotIdx = cleanName.lastIndexOf(".");
    const ext = dotIdx >= 0 ? cleanName.slice(dotIdx) : "";
    if (ext && !ALLOWED_ARTWORK_EXTS.has(ext)) {
      return { ok: false, message: "Ekstensi file tidak valid. Gunakan .jpg, .jpeg, .png, atau .webp." };
    }
    const extMimeMap = {
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".png": "image/png",
      ".webp": "image/webp",
    };
    if (ext && extMimeMap[ext] !== detectedMime) {
      return {
        ok: false,
        message: "Ekstensi file tidak sesuai dengan isi biner gambar sebenarnya.",
      };
    }
    const normMime = String(declaredMime || "").trim().toLowerCase();
    const normalizedDeclared = normMime === "image/jpg" ? "image/jpeg" : normMime;
    if (normalizedDeclared && normalizedDeclared !== "application/octet-stream" && normalizedDeclared !== detectedMime) {
      return {
        ok: false,
        message: "Tipe MIME file tidak sesuai dengan format gambar sebenarnya.",
      };
    }
    return { ok: true, mimeType: detectedMime };
  }

  async function optimizeArtworkInBrowser(dataUrl, mimeType, bytesLength) {
    if (typeof Image === "undefined" || typeof document.createElement !== "function") {
      return {
        previewUrl: dataUrl,
        imageBase64: dataUrl.split(",")[1] || "",
        contentType: mimeType,
        width: null,
        height: null,
        fileSizeBytes: bytesLength,
        aspectWarning: "",
      };
    }

    const loadedImg = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Gambar gagal dirender untuk preview."));
      img.src = dataUrl;
    }).catch(() => null);

    if (!loadedImg || !loadedImg.naturalWidth || !loadedImg.naturalHeight) {
      return {
        previewUrl: dataUrl,
        imageBase64: dataUrl.split(",")[1] || "",
        contentType: mimeType,
        width: null,
        height: null,
        fileSizeBytes: bytesLength,
        aspectWarning: "",
      };
    }

    const natW = loadedImg.naturalWidth;
    const natH = loadedImg.naturalHeight;
    if (natW < 320 || natH < 180) {
      throw new Error(`Resolusi gambar terlalu kecil (${natW}x${natH} px). Minimal 320x180 px.`);
    }
    const ratio = natW / natH;
    if (ratio < 0.75 || ratio > 2.6) {
      throw new Error(
        `Rasio aspek gambar (${ratio.toFixed(2)}:1) terlalu ekstrem. Gunakan gambar lanskap mendekati 16:9.`
      );
    }

    const targetRatio = 16 / 9;
    const needsCrop = Math.abs(ratio - targetRatio) > 0.08;
    let aspectWarning = needsCrop
      ? `Proporsi asli ${natW}x${natH} px disesuaikan otomatis ke bingkai poster 16:9.`
      : "";

    const canvas = document.createElement("canvas");
    if (canvas && typeof canvas.getContext === "function") {
      const outW = Math.min(1280, Math.max(640, natW));
      const outH = Math.round(outW / targetRatio);
      canvas.width = outW;
      canvas.height = outH;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        let sx = 0;
        let sy = 0;
        let sw = natW;
        let sh = natH;
        if (ratio > targetRatio) {
          sw = Math.round(natH * targetRatio);
          sx = Math.round((natW - sw) / 2);
        } else if (ratio < targetRatio) {
          sh = Math.round(natW / targetRatio);
          sy = Math.round((natH - sh) / 2);
        }
        ctx.drawImage(loadedImg, sx, sy, sw, sh, 0, 0, outW, outH);
        const preferredOutMime = mimeType === "image/png" ? "image/png" : "image/webp";
        const optimizedDataUrl = canvas.toDataURL(preferredOutMime, 0.88);
        if (optimizedDataUrl && optimizedDataUrl.startsWith(`data:${preferredOutMime};base64,`)) {
          const b64 = optimizedDataUrl.split(",")[1] || "";
          const approxBytes = Math.floor((b64.length * 3) / 4);
          if (approxBytes > 0 && (needsCrop || approxBytes < bytesLength || bytesLength > 900 * 1024)) {
            return {
              previewUrl: optimizedDataUrl,
              imageBase64: b64,
              contentType: preferredOutMime,
              width: outW,
              height: outH,
              fileSizeBytes: approxBytes,
              aspectWarning,
            };
          }
        }
      }
    }

    return {
      previewUrl: dataUrl,
      imageBase64: dataUrl.split(",")[1] || "",
      contentType: mimeType,
      width: natW,
      height: natH,
      fileSizeBytes: bytesLength,
      aspectWarning,
    };
  }

  async function inspectAndPrepareArtworkFile(file) {
    if (!file) {
      throw new Error("Pilih file gambar poster terlebih dahulu.");
    }
    const rawName = String(file.name || "poster.jpg");
    const rawType = String(file.type || "").trim().toLowerCase();
    if (rawType && rawType !== "application/octet-stream" && !ALLOWED_ARTWORK_MIMES.has(rawType)) {
      throw new Error("Format file tidak didukung. Pilih gambar JPEG, PNG, atau WebP.");
    }
    if (!file.size || file.size > MAX_GAME_ARTWORK_BYTES) {
      throw new Error("Ukuran gambar harus lebih dari 0 byte dan maksimal 5 MB.");
    }

    let bytes;
    if (typeof file.arrayBuffer === "function") {
      bytes = new Uint8Array(await file.arrayBuffer());
    } else if (file._bytes && ArrayBuffer.isView(file._bytes)) {
      bytes = new Uint8Array(file._bytes.buffer, file._bytes.byteOffset, file._bytes.byteLength);
    } else {
      throw new Error("Browser gagal membaca isi file gambar.");
    }

    const sig = detectArtworkSignature(bytes, rawName, rawType);
    if (!sig.ok) {
      throw new Error(sig.message);
    }

    const b64 = bytesToBase64(bytes);
    const dataUrl = `data:${sig.mimeType};base64,${b64}`;
    const prepared = await optimizeArtworkInBrowser(dataUrl, sig.mimeType, bytes.length);
    if (prepared.fileSizeBytes > MAX_GAME_ARTWORK_BYTES) {
      throw new Error("Hasil gambar masih melebihi batas 5 MB.");
    }
    return {
      filename: rawName,
      contentType: prepared.contentType,
      imageBase64: prepared.imageBase64,
      previewUrl: prepared.previewUrl,
      width: prepared.width,
      height: prepared.height,
      fileSizeBytes: prepared.fileSizeBytes,
      aspectWarning: prepared.aspectWarning,
    };
  }

  function formatByteSize(bytes) {
    const n = Number(bytes || 0);
    if (!Number.isFinite(n) || n <= 0) return "-";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
    return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  }

  function buildGameManagementCardsHtml(games) {
    if (!games || games.length === 0) {
      return window.TurnamenUI.renderEmptyState(
        "Belum Ada Cabang Game",
        "Tambahkan cabang game baru untuk mulai mengatur katalog dan posternya.",
        `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-game">Tambah Cabang Game</button>`
      );
    }

    return `
      <div class="artwork-manager-grid">
        ${games
          .map((g) => {
            const art = window.TurnamenUI.resolveGameArtwork(g);
            const draft = pendingArtworkDrafts.get(g.id) || null;
            const uploadStatus = artworkUploadState.get(g.id) || null;
            const isUploading = Boolean(uploadStatus && uploadStatus.busy);
            const isCustom = Boolean(g.custom_artwork_url);
            const sourceBadge = isCustom
              ? `<span class="badge badge-info">Poster Kustom</span>`
              : art.hasOfficialArtwork
                ? `<span class="badge badge-success">Artwork Resmi</span>`
                : `<span class="badge badge-neutral">Fallback Arena</span>`;
            const inactiveBadge =
              g.is_active === false ? `<span class="badge badge-warning">Nonaktif</span>` : "";
            const dimLabel =
              g.custom_artwork_width && g.custom_artwork_height
                ? `${g.custom_artwork_width}x${g.custom_artwork_height} px`
                : "16:9 Siap";

            return `
              <article class="artwork-manager-card" data-game-card-id="${window.TurnamenUI.escapeHtml(g.id)}">
                <div class="artwork-manager-head">
                  <div>
                    <h3 class="card-title">${window.TurnamenUI.escapeHtml(g.name)}</h3>
                    <div class="table-subtext">${window.TurnamenUI.escapeHtml(g.genre || "-")} | ${window.TurnamenUI.escapeHtml(g.platform || "-")} | <code>${window.TurnamenUI.escapeHtml(g.slug || "")}</code></div>
                  </div>
                  <div class="row-actions">
                    ${sourceBadge}
                    ${inactiveBadge}
                  </div>
                </div>

                <div class="artwork-manager-poster">
                  ${window.TurnamenUI.renderGameArtwork(g, "", { hideCaption: true })}
                </div>

                <div class="artwork-manager-meta">
                  <span>Sumber: <strong>${window.TurnamenUI.escapeHtml(art.sourceLabel || "Artwork Resmi")}</strong></span>
                  <span class="tabular-nums">Dimensi: <strong>${window.TurnamenUI.escapeHtml(dimLabel)}</strong></span>
                  <span class="tabular-nums">Format Default: <strong>${g.team_size || 5}v${g.team_size || 5} Bo${g.default_best_of || 3}</strong></span>
                </div>

                ${
                  draft
                    ? `
                  <div class="artwork-manager-preview-box" data-preview-game-id="${window.TurnamenUI.escapeHtml(g.id)}">
                    <div class="artwork-manager-preview-head">
                      <span>Preview Poster Baru (Belum Disimpan)</span>
                      <button type="button" class="btn btn-ghost btn-sm" data-action="clear-game-artwork-preview" data-id="${window.TurnamenUI.escapeHtml(g.id)}" ${isUploading ? "disabled" : ""}>Batalkan Preview</button>
                    </div>
                    <div class="artwork-manager-preview-frame">
                      <img class="artwork-manager-preview-img" src="${window.TurnamenUI.escapeHtml(draft.previewUrl)}" alt="Preview poster baru ${window.TurnamenUI.escapeHtml(g.name)}" />
                    </div>
                    <div class="artwork-manager-meta">
                      <span>File: <strong>${window.TurnamenUI.escapeHtml(draft.filename)}</strong></span>
                      <span class="tabular-nums">${draft.width && draft.height ? `${draft.width}x${draft.height} px | ` : ""}${formatByteSize(draft.fileSizeBytes)} | ${window.TurnamenUI.escapeHtml(draft.contentType)}</span>
                    </div>
                    ${
                      draft.aspectWarning
                        ? `<div class="notice-banner notice-banner-warning" role="status"><span>${window.TurnamenUI.escapeHtml(draft.aspectWarning)}</span></div>`
                        : ""
                    }
                  </div>
                `
                    : ""
                }

                ${
                  uploadStatus && uploadStatus.error
                    ? `<div class="notice-banner notice-banner-danger" role="alert"><span>${window.TurnamenUI.escapeHtml(uploadStatus.error)}</span></div>`
                    : ""
                }

                ${
                  isUploading
                    ? `
                  <div class="artwork-upload-status" role="status" aria-live="polite">
                    ${window.TurnamenUI.renderProgressBar(uploadStatus.progress || 65, uploadStatus.label || "Mengunggah poster ke Storage...")}
                  </div>
                `
                    : ""
                }

                <div class="artwork-manager-actions">
                  <input
                    id="artwork-file-input-${window.TurnamenUI.escapeHtml(g.id)}"
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                    class="artwork-file-input-sr"
                    data-action="game-artwork-file-input"
                    data-id="${window.TurnamenUI.escapeHtml(g.id)}"
                    aria-label="Pilih poster kustom untuk ${window.TurnamenUI.escapeHtml(g.name)}"
                  />
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    data-action="trigger-game-artwork-picker"
                    data-id="${window.TurnamenUI.escapeHtml(g.id)}"
                    ${isUploading ? "disabled" : ""}
                  >${window.TurnamenUI.icon("image", 14)}<span>Ganti Poster</span></button>
                  <button
                    type="button"
                    class="btn btn-primary btn-sm"
                    data-action="save-game-artwork"
                    data-id="${window.TurnamenUI.escapeHtml(g.id)}"
                    ${!draft || isUploading ? "disabled" : ""}
                  >${isUploading ? "Menyimpan..." : "Simpan Poster"}</button>
                  ${
                    isCustom
                      ? `<button
                          type="button"
                          class="btn btn-ghost btn-sm"
                          data-action="confirm-restore-game-artwork"
                          data-id="${window.TurnamenUI.escapeHtml(g.id)}"
                          ${isUploading ? "disabled" : ""}
                        >${window.TurnamenUI.icon("refresh", 14)}<span>Kembalikan Artwork Resmi</span></button>`
                      : ""
                  }
                  <button
                    type="button"
                    class="btn btn-ghost btn-sm"
                    data-action="open-edit-game"
                    data-id="${window.TurnamenUI.escapeHtml(g.id)}"
                    aria-label="Edit konfigurasi ${window.TurnamenUI.escapeHtml(g.name)}"
                    ${isUploading ? "disabled" : ""}
                  >${window.TurnamenUI.icon("edit", 14)}<span>Edit Data</span></button>
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    `;
  }

  async function renderGameManagement(container, isStale) {
    const res = await window.TurnamenAPI.getGames({ includeInactive: true });
    if (isStale()) return;

    if (!res || !res.success || !Array.isArray(res.data)) {
      container.innerHTML = window.TurnamenUI.renderErrorState(
        (res && res.message) || "Gagal memuat katalog game untuk manajemen poster.",
        "retry-page"
      );
      return;
    }

    const adminGames = res.data;
    adminGamesCache = adminGames;
    gamesState.items = adminGames.filter((g) => g.is_active !== false);
    gamesState.loaded = true;
    gamesState.error = null;

    container.innerHTML = `
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Manajemen Game &amp; Poster Arena</h2>
          <p>Ganti, preview, dan kelola poster cabang game secara langsung. Format didukung: JPEG, PNG, atau WebP maksimal 5 MB.</p>
        </div>
        <div class="page-actions">
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="dashboard">Kembali ke Dashboard</button>
          <button type="button" class="btn btn-primary btn-sm" data-action="open-create-game">${window.TurnamenUI.icon("plus", 14)}<span>Tambah Game</span></button>
        </div>
      </div>

      <div id="game-management-cards-wrap">
        ${buildGameManagementCardsHtml(adminGames)}
      </div>
    `;
  }

  async function handleArtworkFileInputChange(inputEl) {
    const gameId = inputEl ? inputEl.getAttribute("data-id") || "" : "";
    const file = inputEl && inputEl.files && inputEl.files[0] ? inputEl.files[0] : null;
    if (!gameId || !file) return;

    artworkUploadState.delete(gameId);
    try {
      const prepared = await inspectAndPrepareArtworkFile(file);
      pendingArtworkDrafts.set(gameId, prepared);
      window.TurnamenUI.showToast(
        "Preview poster siap. Periksa tampilan lalu klik Simpan Poster.",
        "info"
      );
    } catch (err) {
      pendingArtworkDrafts.delete(gameId);
      const msg = (err && err.message) || "File gambar tidak valid.";
      artworkUploadState.set(gameId, { busy: false, error: msg });
      window.TurnamenUI.showToast(msg, "danger");
    }
    if (currentPage === "game-management") {
      await navigateTo("game-management");
    }
  }

  async function saveGameArtworkDraft(gameId, triggerEl = null) {
    const draft = pendingArtworkDrafts.get(gameId);
    if (!draft) {
      window.TurnamenUI.showToast("Pilih gambar poster terlebih dahulu sebelum menyimpan.", "warning");
      return;
    }

    await withSubmissionGuard(`game:artwork-save:${gameId}`, triggerEl, "Menyimpan...", async () => {
      artworkUploadState.set(gameId, {
        busy: true,
        progress: 55,
        label: "Mengunggah dan memvalidasi poster di server...",
        error: "",
      });
      if (currentPage === "game-management") {
        const wrap = document.getElementById("game-management-cards-wrap");
        if (wrap && adminGamesCache.length > 0) {
          wrap.innerHTML = buildGameManagementCardsHtml(adminGamesCache);
        }
      }

      const res = await window.TurnamenAPI.uploadGameArtwork(gameId, {
        filename: draft.filename,
        content_type: draft.contentType,
        image_base64: draft.imageBase64,
      });
      if (!res || !res.success) {
        const errMsg = (res && res.message) || "Gagal menyimpan poster baru.";
        artworkUploadState.set(gameId, { busy: false, error: errMsg });
        window.TurnamenUI.showToast(errMsg, "danger");
        if (currentPage === "game-management") {
          await navigateTo("game-management");
        }
        return;
      }

      pendingArtworkDrafts.delete(gameId);
      artworkUploadState.delete(gameId);
      clearUiPageSnapshots();
      await ensureGamesLoaded(true);
      window.TurnamenUI.showToast(
        res.data && res.data.aspect_ratio_warning
          ? `Poster disimpan. ${res.data.aspect_ratio_warning}`
          : "Poster game berhasil diperbarui di seluruh aplikasi.",
        "success"
      );
      await navigateTo(currentPage === "game-management" ? "game-management" : "dashboard");
    });
  }

  function openRestoreGameArtworkConfirm(gameId) {
    const game =
      adminGamesCache.find((g) => g.id === gameId) ||
      gamesState.items.find((g) => g.id === gameId);
    const titleLabel = game ? game.name : "Cabang Game";
    window.TurnamenUI.openModal({
      title: "Kembalikan Artwork Resmi",
      bodyHtml: `
        <p style="margin:0 0 10px; color:var(--text-secondary);">
          Yakin ingin menghapus poster kustom untuk <strong>${window.TurnamenUI.escapeHtml(titleLabel)}</strong> dan mengembalikannya ke artwork resmi Wave 6.10?
        </p>
        <p class="table-subtext" style="margin:0;">
          Perubahan ini langsung diterapkan pada Dashboard, Jelajah Game, Daftar Turnamen, dan seluruh chip game.
        </p>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-danger" data-action="submit-restore-game-artwork" data-id="${window.TurnamenUI.escapeHtml(gameId)}">Ya, Kembalikan Artwork Resmi</button>
      `,
    });
  }

  async function restoreGameArtworkConfirmed(gameId, triggerEl = null) {
    await withSubmissionGuard(
      `game:artwork-restore:${gameId}`,
      triggerEl,
      "Mengembalikan...",
      async () => {
        const res = await window.TurnamenAPI.restoreGameArtwork(gameId);
        if (!res || !res.success) {
          window.TurnamenUI.showToast(
            (res && res.message) || "Gagal mengembalikan artwork resmi.",
            "danger"
          );
          return;
        }
        window.TurnamenUI.closeModal(true);
        pendingArtworkDrafts.delete(gameId);
        artworkUploadState.delete(gameId);
        clearUiPageSnapshots();
        await ensureGamesLoaded(true);
        window.TurnamenUI.showToast(
          "Artwork game berhasil dikembalikan ke poster resmi.",
          "success"
        );
        await navigateTo(currentPage === "game-management" ? "game-management" : "dashboard");
      },
      { lockModal: true }
    );
  }

  // GUEST PUBLIC DASHBOARD (currentUser === null)
  function renderGuestDashboard(container, data) {
    const { tournaments, ctx, gamesById } = data;
    const featured = ctx.active || tournaments[0] || null;
    const featuredGame = featured
      ? gamesById[featured.game_id] || { name: featured.game_name, slug: featured.game_name }
      : gamesState.items[0] || { name: "Esports Arena", slug: "esports" };

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      <section class="esports-banner" aria-label="Arena Publik Turnamen.in">
        <div class="esports-banner-copy">
          <span class="esports-banner-kicker">Turnamen.in Public Arena</span>
          <h2 class="esports-banner-title">${window.TurnamenUI.escapeHtml(featured ? featured.title : "Portal Turnamen Esports Turnamen.in")}</h2>
          <p class="esports-banner-desc">Pantau jadwal, bagan Single Elimination, pengumuman panitia, dan klasemen tim secara terbuka. Masuk untuk mendaftarkan tim atau mengelola turnamen sesuai role Anda.</p>
          <div class="page-actions">
            <button type="button" class="btn btn-primary" data-action="go-page" data-page="login">Masuk / Daftar Akun</button>
            ${
              featured
                ? `<button type="button" class="btn btn-secondary" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(featured.id)}">Lihat Bracket</button>`
                : ""
            }
          </div>
        </div>
        <div class="esports-banner-art">
          ${window.TurnamenUI.renderGameArtwork(featuredGame, "PUBLIC ARENA")}
        </div>
      </section>

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Cabang Game Resmi</h2>
          <p>Pilih game untuk menjelajahi kompetisi yang tersedia.</p>
        </div>
      </div>
      ${renderGamePosterGallery(tournaments)}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Kompetisi Aktif &amp; Terbuka</h2>
          <p>Klik Bracket atau Detail untuk melihat klasemen dan pertandingan terkini.</p>
        </div>
      </div>
      ${renderTournamentDiscoveryCards(tournaments, gamesById)}
    `;
  }

  // =========================================================================
  // 2. TOURNAMENT LIST PAGE (ADAPTIVE: DISCOVERY CARDS VS MANAGEMENT TABLE)
  // =========================================================================
  async function renderTournamentList(container, isStale) {
    const apiFilters = {};
    if (tournamentFilterState.status) apiFilters.status = tournamentFilterState.status;
    if (tournamentFilterState.gameId) apiFilters.game_id = tournamentFilterState.gameId;

    const [, res, teamsRes] = await Promise.all([
      ensureGamesLoaded(false),
      window.TurnamenAPI.getTournaments(apiFilters),
      canPerform("registration:create") ? window.TurnamenAPI.getTeams() : Promise.resolve({ success: false }),
    ]);
    if (isStale()) return;

    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message, "retry-page");
      return;
    }

    const rawList = Array.isArray(res.data) ? res.data : [];
    const teams = teamsRes.success && Array.isArray(teamsRes.data) ? teamsRes.data : [];
    const user = getCurrentUserSafe();
    const ownedTeamIds = user
      ? teams.filter((tm) => tm.captain_id === user.id || user.role === "super_admin").map((tm) => tm.id)
      : [];

    const searchQuery = tournamentFilterState.search.trim().toLowerCase();
    const list = searchQuery
      ? rawList.filter((t) => {
          const hay = `${t.title || ""} ${t.game_name || ""} ${t.venue || ""}`.toLowerCase();
          return hay.includes(searchQuery);
        })
      : rawList;

    if (!searchQuery && !tournamentFilterState.status && !tournamentFilterState.gameId) {
      cachedTournaments = rawList;
    }

    const canCreate = canPerform("tournament:create");
    const competitiveView = isCompetitiveRole();
    const gamesById = buildGameLookup();

    const gameFilterOptions = gamesState.items
      .map(
        (g) =>
          `<option value="${window.TurnamenUI.escapeHtml(g.id)}" ${tournamentFilterState.gameId === g.id ? "selected" : ""}>${window.TurnamenUI.escapeHtml(g.name)}</option>`
      )
      .join("");

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      <div class="page-header">
        <div class="page-header-copy">
          <h2>${competitiveView ? "Jelajah Turnamen Esports" : "Katalog &amp; Manajemen Turnamen"}</h2>
          <p>${
            competitiveView
              ? "Temukan turnamen lintas cabang game, periksa slot tersisa, dan ikuti progres bracket."
              : "Kelola seluruh turnamen lintas cabang game esports dengan status dan kuota peserta aktual."
          }</p>
        </div>
        ${
          canCreate
            ? `<button type="button" class="btn btn-primary" data-action="open-create-tournament">${window.TurnamenUI.icon("plus", 15)}<span>Buat Turnamen Baru</span></button>`
            : ""
        }
      </div>

      <div class="filter-bar">
        <div class="search-field">
          <span class="search-field-icon">${window.TurnamenUI.icon("search", 15)}</span>
          <label for="filter-tournament-search" class="sr-only">Cari turnamen</label>
          <input
            id="filter-tournament-search"
            type="search"
            class="form-input"
            placeholder="Cari judul turnamen, game, atau venue..."
            value="${window.TurnamenUI.escapeHtml(tournamentFilterState.search)}"
          />
        </div>
        <div>
          <label for="filter-tournament-status" class="sr-only">Filter status turnamen</label>
          <select id="filter-tournament-status" class="form-select">
            <option value="" ${tournamentFilterState.status === "" ? "selected" : ""}>Semua Status</option>
            <option value="ongoing" ${tournamentFilterState.status === "ongoing" ? "selected" : ""}>Sedang Berlangsung</option>
            <option value="open_registration" ${tournamentFilterState.status === "open_registration" ? "selected" : ""}>Pendaftaran Dibuka</option>
            <option value="registration_closed" ${tournamentFilterState.status === "registration_closed" ? "selected" : ""}>Pendaftaran Ditutup</option>
            <option value="draft" ${tournamentFilterState.status === "draft" ? "selected" : ""}>Draft</option>
            <option value="completed" ${tournamentFilterState.status === "completed" ? "selected" : ""}>Selesai</option>
            <option value="cancelled" ${tournamentFilterState.status === "cancelled" ? "selected" : ""}>Dibatalkan</option>
          </select>
        </div>
        <div>
          <label for="filter-tournament-game" class="sr-only">Filter cabang game</label>
          <select id="filter-tournament-game" class="form-select">
            <option value="" ${tournamentFilterState.gameId === "" ? "selected" : ""}>Semua Game</option>
            ${gameFilterOptions}
          </select>
        </div>
      </div>

      <div id="tournament-list-results">
        ${renderTournamentListContent(list, rawList.length, canCreate, competitiveView, gamesById, ownedTeamIds, teams)}
      </div>
    `;

    const searchInput = document.getElementById("filter-tournament-search");
    const statusSelect = document.getElementById("filter-tournament-status");
    const gameSelect = document.getElementById("filter-tournament-game");

    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        tournamentFilterState.search = e.target.value;
        const q = tournamentFilterState.search.trim().toLowerCase();
        const filtered = q
          ? rawList.filter((t) => {
              const hay = `${t.title || ""} ${t.game_name || ""} ${t.venue || ""}`.toLowerCase();
              return hay.includes(q);
            })
          : rawList;
        const resultsEl = document.getElementById("tournament-list-results");
        if (resultsEl) {
          resultsEl.innerHTML = renderTournamentListContent(
            filtered,
            rawList.length,
            canCreate,
            competitiveView,
            gamesById,
            ownedTeamIds,
            teams
          );
        }
      });
    }
    if (statusSelect) {
      statusSelect.addEventListener("change", (e) => {
        tournamentFilterState.status = e.target.value;
        navigateTo("tournament-list");
      });
    }
    if (gameSelect) {
      gameSelect.addEventListener("change", (e) => {
        tournamentFilterState.gameId = e.target.value;
        navigateTo("tournament-list");
      });
    }
  }

  function renderTournamentListContent(
    list,
    rawTotal,
    canCreate,
    competitiveView,
    gamesById,
    ownedTeamIds,
    teams
  ) {
    const hasFilter = Boolean(
      tournamentFilterState.search.trim() ||
        tournamentFilterState.status ||
        tournamentFilterState.gameId
    );
    if (list.length === 0) {
      const emptyActions = [];
      if (hasFilter) {
        emptyActions.push(
          `<button type="button" class="btn btn-secondary btn-sm" data-action="reset-tournament-filters">Reset Filter</button>`
        );
      }
      if (canCreate) {
        emptyActions.push(
          `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-tournament">Buat Turnamen Baru</button>`
        );
      }
      return `
        <div class="card">
          ${window.TurnamenUI.renderEmptyState(
            "Tidak Ada Turnamen Ditemukan",
            rawTotal === 0 && !hasFilter
              ? "Belum ada turnamen tersedia. Buat turnamen pertama untuk memulai."
              : "Tidak ada turnamen yang cocok dengan kata kunci atau filter saat ini.",
            emptyActions.join("")
          )}
        </div>
      `;
    }

    if (competitiveView) {
      return renderTournamentDiscoveryCards(list, gamesById, { ownedTeamIds, teams });
    }

    const user = getCurrentUserSafe();
    const roleKey = getActiveRoleKey();

    return `
      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th class="col-title">Judul Turnamen</th>
                <th class="col-game">Game</th>
                <th class="col-format">Format</th>
                <th class="col-quota">Kuota Tim</th>
                <th class="col-money">Total Hadiah</th>
                <th class="col-status">Status</th>
                <th class="col-actions">Aksi</th>
              </tr>
            </thead>
            <tbody>
              ${list
                .map((t) => {
                  const canEdit = canPerform("tournament:edit", { tournament: t });
                  const canDelete =
                    canPerform("tournament:delete", { tournament: t }) &&
                    t.status !== "ongoing" &&
                    t.status !== "completed";
                  const committeeAssign =
                    roleKey === "committee" ? getCommitteeTournamentAssignment(t, user) : null;
                  const assignBadge =
                    roleKey === "committee"
                      ? committeeAssign === true
                        ? `<span class="badge badge-info">Ditugaskan</span>`
                        : `<span class="badge badge-neutral">Lihat Saja</span>`
                      : "";
                  return `
                  <tr>
                    <td class="col-title">
                      <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>
                      <div class="table-subtext">${window.TurnamenUI.escapeHtml(t.venue || "Online")} | ${window.TurnamenUI.formatDateOnly(t.start_date)} ${assignBadge}</div>
                    </td>
                    <td class="col-game">${window.TurnamenUI.renderGameChip(t.game_name, gamesById[t.game_id] || t.game_id)}</td>
                    <td class="col-format tabular-nums">Single Elim (Bo${t.best_of})</td>
                    <td class="col-quota tabular-nums">${t.approved_teams_count || 0} / ${t.max_teams} Tim</td>
                    <td class="col-money tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</td>
                    <td class="col-status">${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                    <td class="col-actions">
                      <div class="row-actions">
                        <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Peserta</button>
                        <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Bracket</button>
                        ${
                          canEdit
                            ? `<button type="button" class="btn btn-ghost btn-sm" data-action="open-edit-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}" aria-label="Edit ${window.TurnamenUI.escapeHtml(t.title)}">${window.TurnamenUI.icon("edit", 14)}</button>`
                            : ""
                        }
                        ${
                          canDelete
                            ? `<button type="button" class="btn btn-danger btn-sm" data-action="confirm-delete-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}" aria-label="Hapus ${window.TurnamenUI.escapeHtml(t.title)}">${window.TurnamenUI.icon("trash", 14)}</button>`
                            : ""
                        }
                      </div>
                    </td>
                  </tr>
                `;
                })
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  async function openCreateTournamentModal() {
    if (!canPerform("tournament:create")) {
      window.TurnamenUI.showToast(
        "Hanya Organizer atau Super Admin yang dapat membuat turnamen.",
        "warning"
      );
      return;
    }
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const games = await ensureGamesLoaded(false);
    if (isModalRequestStale(startNavSeq, startRoleKey)) return;
    const gameOptions =
      games.length > 0
        ? games
            .map(
              (g) =>
                `<option value="${window.TurnamenUI.escapeHtml(g.id)}">${window.TurnamenUI.escapeHtml(g.name)}</option>`
            )
            .join("")
        : `<option value="">Daftar game belum tersedia</option>`;

    window.TurnamenUI.openModal({
      title: "Buat Turnamen Esports Baru",
      bodyHtml: `
        <div class="form-group">
          <label for="new-tour-title" class="form-label">Judul Turnamen</label>
          <input id="new-tour-title" class="form-input" placeholder="Contoh: Piala Kampus Nasional 2026" />
        </div>
        <div class="form-group">
          <label for="new-tour-game" class="form-label">Cabang Game</label>
          <select id="new-tour-game" class="form-select">${gameOptions}</select>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="new-tour-max-teams" class="form-label">Kuota Tim (Max Teams)</label>
            <select id="new-tour-max-teams" class="form-select">
              <option value="4">4 Tim</option>
              <option value="8" selected>8 Tim</option>
              <option value="16">16 Tim</option>
              <option value="32">32 Tim</option>
            </select>
          </div>
          <div class="form-group">
            <label for="new-tour-bo" class="form-label">Format Seri (Best Of)</label>
            <select id="new-tour-bo" class="form-select">
              <option value="1">Best of 1 (Bo1)</option>
              <option value="3" selected>Best of 3 (Bo3)</option>
              <option value="5">Best of 5 (Bo5)</option>
              <option value="7">Best of 7 (Bo7)</option>
            </select>
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="new-tour-fee" class="form-label">Biaya Registrasi (Rp)</label>
            <input id="new-tour-fee" type="number" min="0" class="form-input tabular-nums" value="50000" />
          </div>
          <div class="form-group">
            <label for="new-tour-prize" class="form-label">Total Hadiah (Rp)</label>
            <input id="new-tour-prize" type="number" min="0" class="form-input tabular-nums" value="5000000" />
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="new-tour-venue" class="form-label">Venue / Platform</label>
            <input id="new-tour-venue" class="form-input" value="Online" />
          </div>
          <div class="form-group">
            <label for="new-tour-start" class="form-label">Tanggal Mulai</label>
            <input id="new-tour-start" type="date" class="form-input tabular-nums" value="2026-12-01" />
          </div>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-create-tournament">Simpan Turnamen</button>
      `,
    });
  }

  async function submitCreateTournament(triggerEl = null) {
    if (!canPerform("tournament:create")) {
      window.TurnamenUI.showToast(getDeniedActionMessage("tournament:create", null), "danger");
      return;
    }
    const title = (document.getElementById("new-tour-title")?.value || "").trim();
    const gameId = document.getElementById("new-tour-game")?.value || "";
    const startRaw = (document.getElementById("new-tour-start")?.value || "").trim();
    if (title.length < 4) {
      window.TurnamenUI.showToast("Judul turnamen wajib minimal 4 karakter.", "warning");
      return;
    }
    if (!gameId) {
      window.TurnamenUI.showToast("Cabang game wajib dipilih.", "warning");
      return;
    }
    if (!startRaw) {
      window.TurnamenUI.showToast("Tanggal mulai turnamen wajib diisi.", "warning");
      return;
    }

    await withSubmissionGuard(
      "tournament:create",
      triggerEl,
      "Menyimpan...",
      async () => {
        const payload = {
          title,
          game_id: gameId,
          max_teams: Number(document.getElementById("new-tour-max-teams")?.value || 8),
          best_of: Number(document.getElementById("new-tour-bo")?.value || 3),
          registration_fee: Number(document.getElementById("new-tour-fee")?.value || 0),
          prize_pool: Number(document.getElementById("new-tour-prize")?.value || 0),
          venue: (document.getElementById("new-tour-venue")?.value || "Online").trim(),
          start_date: `${startRaw}T10:00:00+07:00`,
          status: "open_registration",
        };

        const res = await window.TurnamenAPI.createTournament(payload);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        if (res.data && res.data.id && window.TurnamenConfig) {
          window.TurnamenConfig.setSelectedTournamentId(res.data.id);
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Turnamen baru berhasil dibuat.", "success");
        await navigateTo("tournament-list");
      },
      { lockModal: true }
    );
  }

  const TOURNAMENT_STATUS_LABELS = {
    draft: "Draft",
    open_registration: "Pendaftaran Dibuka",
    registration_closed: "Pendaftaran Ditutup",
    ongoing: "Sedang Berlangsung",
    completed: "Selesai",
    cancelled: "Dibatalkan",
  };

  const ALLOWED_EDIT_STATUS_MAP = {
    draft: ["draft", "open_registration", "registration_closed", "cancelled"],
    open_registration: ["open_registration", "draft", "registration_closed", "ongoing", "cancelled"],
    registration_closed: ["registration_closed", "open_registration", "ongoing", "cancelled"],
    ongoing: ["ongoing", "completed", "cancelled"],
    completed: ["completed"],
    cancelled: ["cancelled"],
  };

  async function openEditTournamentModal(tournamentId) {
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const t = await resolveAuthorizedTournament(tournamentId, "tournament:edit");
    if (!t || isModalRequestStale(startNavSeq, startRoleKey)) return;

    const legalStatuses = ALLOWED_EDIT_STATUS_MAP[t.status] || [t.status];
    const isTerminalStatus = t.status === "completed" || t.status === "cancelled";

    window.TurnamenUI.openModal({
      title: `Edit Turnamen: ${t.title}`,
      bodyHtml: `
        <div class="form-group">
          <label for="edit-tour-title" class="form-label">Judul Turnamen</label>
          <input id="edit-tour-title" class="form-input" value="${window.TurnamenUI.escapeHtml(t.title)}" />
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="edit-tour-status" class="form-label">Status Turnamen</label>
            <select id="edit-tour-status" class="form-select" ${isTerminalStatus ? "disabled" : ""}>
              ${legalStatuses
                .map(
                  (st) =>
                    `<option value="${window.TurnamenUI.escapeHtml(st)}" ${t.status === st ? "selected" : ""}>${window.TurnamenUI.escapeHtml(TOURNAMENT_STATUS_LABELS[st] || st)}</option>`
                )
                .join("")}
            </select>
            ${isTerminalStatus ? `<p class="form-hint">Status terminal (${window.TurnamenUI.escapeHtml(t.status)}) tidak dapat diubah kembali.</p>` : ""}
          </div>
          <div class="form-group">
            <label for="edit-tour-venue" class="form-label">Venue</label>
            <input id="edit-tour-venue" class="form-input" value="${window.TurnamenUI.escapeHtml(t.venue || "Online")}" />
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="edit-tour-max-teams" class="form-label">Kuota Tim</label>
            <input id="edit-tour-max-teams" type="number" min="2" max="128" class="form-input tabular-nums" value="${t.max_teams}" />
          </div>
          <div class="form-group">
            <label for="edit-tour-prize" class="form-label">Total Hadiah (Rp)</label>
            <input id="edit-tour-prize" type="number" min="0" class="form-input tabular-nums" value="${t.prize_pool || 0}" />
          </div>
        </div>
        <div class="form-group">
          <label for="edit-tour-desc" class="form-label">Deskripsi</label>
          <textarea id="edit-tour-desc" class="form-textarea">${window.TurnamenUI.escapeHtml(t.description || "")}</textarea>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-edit-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}">Simpan Perubahan</button>
      `,
    });
  }

  async function submitEditTournament(tournamentId, triggerEl = null) {
    await withSubmissionGuard(
      `tournament:edit:${tournamentId}`,
      triggerEl,
      "Menyimpan...",
      async () => {
        const t = await resolveAuthorizedTournament(tournamentId, "tournament:edit");
        if (!t) return;
        const title = (document.getElementById("edit-tour-title")?.value || "").trim();
        if (title.length < 4) {
          window.TurnamenUI.showToast("Judul turnamen wajib minimal 4 karakter.", "warning");
          return;
        }
        const payload = {
          title,
          status: document.getElementById("edit-tour-status")?.value || t.status,
          venue: (document.getElementById("edit-tour-venue")?.value || "Online").trim(),
          max_teams: Number(document.getElementById("edit-tour-max-teams")?.value || 8),
          prize_pool: Number(document.getElementById("edit-tour-prize")?.value || 0),
          description: (document.getElementById("edit-tour-desc")?.value || "").trim(),
        };
        const res = await window.TurnamenAPI.updateTournament(t.id, payload);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Data turnamen berhasil diperbarui.", "success");
        await navigateTo(currentPage);
      },
      { lockModal: true }
    );
  }

  async function confirmDeleteTournament(tournamentId) {
    const t = await resolveAuthorizedTournament(tournamentId, "tournament:delete");
    if (!t) return;
    if (t.status === "ongoing" || t.status === "completed") {
      window.TurnamenUI.showToast(
        "Turnamen berstatus ongoing atau completed tidak dapat dihapus.",
        "warning"
      );
      return;
    }
    window.TurnamenUI.openModal({
      title: "Konfirmasi Hapus Turnamen",
      bodyHtml: `
        <p style="margin:0; color:var(--text-secondary);">
          Apakah Anda yakin ingin menghapus turnamen <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>? Turnamen berstatus <code>ongoing</code> atau <code>completed</code> tidak dapat dihapus oleh sistem.
        </p>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-danger" data-action="execute-delete-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}">Hapus Turnamen</button>
      `,
    });
  }

  async function executeDeleteTournament(tournamentId, triggerEl = null) {
    await withSubmissionGuard(
      `tournament:delete:${tournamentId}`,
      triggerEl,
      "Menghapus...",
      async () => {
        const t = await resolveAuthorizedTournament(tournamentId, "tournament:delete");
        if (!t) return;
        const res = await window.TurnamenAPI.deleteTournament(t.id);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Turnamen berhasil dihapus.", "success");
        await navigateTo("tournament-list");
      },
      { lockModal: true }
    );
  }

  // =========================================================================
  // 3. TOURNAMENT DETAIL & REGISTRATIONS PAGE
  // =========================================================================
  async function renderTournamentDetail(container, isStale) {
    await ensureGamesLoaded(false);
    if (isStale()) return;

    const ctx = await resolveActiveTournamentContext();
    if (isStale()) return;

    if (ctx.error) {
      container.innerHTML = window.TurnamenUI.renderErrorState(ctx.error, "retry-page");
      return;
    }
    if (!ctx.active) {
      container.innerHTML = window.TurnamenUI.renderEmptyState(
        "Belum Ada Turnamen",
        "Buat atau pilih turnamen terlebih dahulu untuk melihat detail dan daftar peserta.",
        `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="tournament-list">Buka Daftar Turnamen</button>`
      );
      return;
    }

    const tid = ctx.active.id;
    const [tourRes, regsRes, teamsRes] = await Promise.all([
      window.TurnamenAPI.getTournamentById(tid),
      window.TurnamenAPI.getTournamentRegistrations(tid),
      window.TurnamenAPI.getTeams(),
    ]);
    if (isStale()) return;

    if (!tourRes.success || !tourRes.data) {
      container.innerHTML = window.TurnamenUI.renderErrorState(
        tourRes.message || "Gagal memuat detail turnamen.",
        "retry-page"
      );
      return;
    }

    const t = tourRes.data;
    const regs = regsRes.success && Array.isArray(regsRes.data) ? regsRes.data : [];
    const teams = teamsRes.success && Array.isArray(teamsRes.data) ? teamsRes.data : [];
    const canManageStaff = canPerform("tournament:edit", { tournament: t });
    let staffList = [];
    let committeeCandidates = [];
    if (canManageStaff) {
      const [staffRes, candRes] = await Promise.all([
        window.TurnamenAPI.getTournamentStaff(t.id),
        window.TurnamenAPI.getCommitteeCandidates(),
      ]);
      if (isStale()) return;
      staffList = staffRes && staffRes.success && Array.isArray(staffRes.data) ? staffRes.data : [];
      committeeCandidates =
        candRes && candRes.success && Array.isArray(candRes.data) ? candRes.data : [];
    }
    const gamesById = buildGameLookup();
    const heroGame = gamesById[t.game_id] || { name: t.game_name, slug: t.game_name };
    const teamsById = {};
    teams.forEach((tm) => {
      teamsById[tm.id] = tm;
    });
    const canVerify = canPerform("registration:verify", { tournament: t });
    const canRegister =
      canPerform("registration:create") && t.status === "open_registration";
    const eligibleTeams = canRegister ? getEligibleTeamsForRegistration(teams, t, regs) : [];
    const detailRoleKey = getActiveRoleKey();
    const regsSubtitle = canVerify
      ? "Kelola persetujuan tim pendaftar. Registrasi berstatus disetujui akan masuk ke bagan bracket."
      : detailRoleKey === "team_captain"
        ? "Menampilkan tim peserta yang sudah disetujui serta status pengajuan tim milik Anda."
        : "Menampilkan daftar peserta terverifikasi (approved) yang lolos ke turnamen.";

    let registrationControlHtml = "";
    if (canRegister) {
      if (eligibleTeams.length > 0) {
        registrationControlHtml = `
          <div class="row-actions">
            <label for="reg-team-select" class="sr-only">Pilih tim untuk didaftarkan</label>
            <select id="reg-team-select" class="form-select form-select-compact">
              ${eligibleTeams
                .map(
                  (tm) =>
                    `<option value="${window.TurnamenUI.escapeHtml(tm.id)}">${window.TurnamenUI.escapeHtml(tm.name)} [${window.TurnamenUI.escapeHtml(tm.tag)}]</option>`
                )
                .join("")}
            </select>
            <button
              type="button"
              class="btn btn-primary btn-sm"
              data-action="register-selected-team"
              data-id="${window.TurnamenUI.escapeHtml(t.id)}"
            >
              ${window.TurnamenUI.icon("plus", 14)}
              <span>Daftarkan Tim</span>
            </button>
          </div>
        `;
      } else {
        registrationControlHtml = `
          <div class="row-actions">
            <span class="table-subtext">Belum ada tim ${window.TurnamenUI.escapeHtml(t.game_name)} yang belum terdaftar.</span>
            <button type="button" class="btn btn-secondary btn-sm" data-action="open-create-team">+ Buat Tim Baru</button>
          </div>
        `;
      }
    }

    container.innerHTML = `
      ${renderTournamentContextBar(
        ctx.list,
        t,
        `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Buka Bracket</button>`
      )}

      <section class="tournament-detail-hero" aria-label="Banner Detail Turnamen">
        <div class="tournament-detail-hero-bg">
          ${window.TurnamenUI.renderGameArtwork(heroGame, "", { hideLabels: true })}
        </div>
        <div class="tournament-detail-hero-scrim" aria-hidden="true"></div>
        <div class="tournament-detail-hero-content">
          <div>
            <div class="tournament-detail-hero-badges">
              ${window.TurnamenUI.renderGameChip(heroGame)}
              ${window.TurnamenUI.renderStatusBadge(t.status)}
              <span class="badge badge-info tabular-nums">Single Elim Bo${t.best_of}</span>
            </div>
            <h2 class="tournament-detail-hero-title">${window.TurnamenUI.escapeHtml(t.title)}</h2>
            <p class="tournament-detail-hero-desc">${window.TurnamenUI.escapeHtml(t.description || "Tidak ada deskripsi tambahan untuk turnamen ini.")}</p>
          </div>
          <div class="page-actions">
            ${
              canPerform("tournament:edit", { tournament: t })
                ? `<button type="button" class="btn btn-secondary btn-sm" data-action="open-edit-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}">${window.TurnamenUI.icon("edit", 14)}<span>Edit Info Turnamen</span></button>`
                : ""
            }
            <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">${window.TurnamenUI.icon("bracket", 14)}<span>Buka Bracket</span></button>
          </div>
        </div>
      </section>

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Cabang Game</div>
          <div class="metric-value metric-value-sm">${window.TurnamenUI.escapeHtml(t.game_name)}</div>
          <div class="metric-note">Format Single Elimination (Bo${t.best_of})</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Peserta Terverifikasi</div>
          <div class="metric-value">${t.approved_teams_count || 0} / ${t.max_teams}</div>
          <div class="metric-note">${
            canVerify
              ? `Total Pendaftar: ${t.registered_teams_count ?? regs.length}`
              : `Kuota maksimal: ${t.max_teams} tim`
          }</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Biaya Pendaftaran</div>
          <div class="metric-value metric-value-sm tabular-nums">${window.TurnamenUI.formatRupiah(t.registration_fee)}</div>
          <div class="metric-note">Venue: ${window.TurnamenUI.escapeHtml(t.venue || "Online")}</div>
        </div>
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Prize Pool</div>
          <div class="metric-value metric-value-sm tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</div>
          <div class="metric-note">Mulai: ${window.TurnamenUI.formatDateOnly(t.start_date)}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">${canVerify ? "Daftar Tim Peserta &amp; Verifikasi Registrasi" : "Daftar Peserta Terdaftar"}</h3>
            <p class="card-subtitle">${window.TurnamenUI.escapeHtml(regsSubtitle)}</p>
          </div>
          ${registrationControlHtml}
        </div>
        ${renderCommitteeAssignmentNotice(t)}

        ${
          regs.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Belum Ada Tim Terdaftar",
                "Belum ada tim yang mengirimkan pendaftaran untuk turnamen ini."
              )
            : `
          <div class="participant-grid">
            ${regs
              .map((r) => {
                const fullTeam = teamsById[r.team_id];
                const teamMembers = fullTeam && Array.isArray(fullTeam.members) ? fullTeam.members : [];
                return `
                <article class="participant-card">
                  <div class="participant-card-head">
                    <div class="participant-card-team">
                      ${window.TurnamenUI.renderTeamEmblem(r.team_tag, 44)}
                      <div>
                        <h4 class="participant-card-title">${window.TurnamenUI.escapeHtml(r.team_name)}</h4>
                        <div class="table-subtext tabular-nums">Tag: ${window.TurnamenUI.escapeHtml(r.team_tag)} | Seed #${r.seed_number || "-"}</div>
                      </div>
                    </div>
                    ${window.TurnamenUI.renderStatusBadge(r.status)}
                  </div>
                  <div class="roster-list">
                    ${
                      teamMembers.length > 0
                        ? teamMembers
                            .slice(0, 6)
                            .map(
                              (m) =>
                                `<span class="roster-chip">${window.TurnamenUI.escapeHtml(m.nickname)} (${window.TurnamenUI.escapeHtml(m.member_role || "starter")})</span>`
                            )
                            .join("")
                        : `<span class="table-subtext">${window.TurnamenUI.escapeHtml(r.notes || "Pendaftaran resmi tim")}</span>`
                    }
                  </div>
                  ${
                    canVerify || r.notes || r.status !== "approved"
                      ? `
                    <div class="participant-card-foot">
                      <span class="table-subtext">${window.TurnamenUI.escapeHtml(
                        r.notes ||
                          (r.status === "pending"
                            ? "Menunggu pemeriksaan panitia"
                            : r.status === "rejected"
                              ? "Pengajuan ditolak panitia"
                              : r.status === "withdrawn"
                                ? "Tim mengundurkan diri"
                                : "Terverifikasi panitia")
                      )}</span>
                      ${
                        canVerify
                          ? `
                        <div class="row-actions">
                          <button type="button" class="btn btn-success btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}" data-status="approved">Setujui</button>
                          <button type="button" class="btn btn-danger btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}" data-status="rejected">Tolak</button>
                        </div>
                      `
                          : ""
                      }
                    </div>
                  `
                      : ""
                  }
                </article>
              `;
              })
              .join("")}
          </div>
        `
        }
      </div>
      ${
        canManageStaff
          ? `
        <div class="card" style="margin-top:20px;">
          <div class="card-header">
            <div>
              <h3 class="card-title">Penugasan Panitia (Committee)</h3>
              <p class="card-subtitle">Tugaskan akun panitia agar berwenang memverifikasi peserta, mengisi skor, dan mempublikasikan pengumuman pada turnamen ini.</p>
            </div>
            <div class="row-actions">
              ${
                (() => {
                  const assignedIds = new Set(staffList.map((s) => s.user_id));
                  const available = committeeCandidates.filter((c) => !assignedIds.has(c.id));
                  if (available.length === 0) {
                    return `<span class="table-subtext">${committeeCandidates.length === 0 ? "Tidak ada akun ber-role committee." : "Seluruh kandidat panitia sudah ditugaskan."}</span>`;
                  }
                  return `
                    <label for="staff-candidate-select" class="sr-only">Pilih panitia</label>
                    <select id="staff-candidate-select" class="form-select form-select-compact">
                      ${available
                        .map(
                          (c) =>
                            `<option value="${window.TurnamenUI.escapeHtml(c.id)}">${window.TurnamenUI.escapeHtml(c.full_name || c.username)} (@${window.TurnamenUI.escapeHtml(c.username)})</option>`
                        )
                        .join("")}
                    </select>
                    <label for="staff-role-select" class="sr-only">Peran staf panitia</label>
                    <select id="staff-role-select" class="form-select form-select-compact">
                      <option value="head_committee">Head Committee</option>
                      <option value="referee" selected>Referee</option>
                      <option value="verifier">Verifier</option>
                      <option value="announcer">Announcer</option>
                    </select>
                    <button type="button" class="btn btn-primary btn-sm" data-action="add-tournament-staff" data-id="${window.TurnamenUI.escapeHtml(t.id)}">${window.TurnamenUI.icon("plus", 14)}<span>Tugaskan Panitia</span></button>
                  `;
                })()
              }
            </div>
          </div>
          ${
            staffList.length === 0
              ? window.TurnamenUI.renderEmptyState(
                  "Belum Ada Panitia Ditugaskan",
                  "Tambahkan akun ber-role committee agar panitia dapat membantu pengelolaan turnamen ini."
                )
              : `
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Nama Panitia</th>
                    <th>Username</th>
                    <th>Peran Staf</th>
                    <th>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  ${staffList
                    .map(
                      (s) => `
                    <tr>
                      <td><strong>${window.TurnamenUI.escapeHtml(s.full_name || s.username || "-")}</strong></td>
                      <td class="tabular-nums">@${window.TurnamenUI.escapeHtml(s.username || "-")}</td>
                      <td><span class="badge badge-info">${window.TurnamenUI.escapeHtml(s.staff_role || "referee")}</span></td>
                      <td>
                        <button type="button" class="btn btn-danger btn-sm" data-action="remove-tournament-staff" data-id="${window.TurnamenUI.escapeHtml(s.user_id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Cabut Tugas</button>
                      </td>
                    </tr>
                  `
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `
          }
        </div>
      `
          : ""
      }
    `;
  }

  async function submitAddTournamentStaff(tournamentId, triggerEl = null) {
    const userId = document.getElementById("staff-candidate-select")?.value || "";
    const staffRole = document.getElementById("staff-role-select")?.value || "referee";
    if (!userId) {
      window.TurnamenUI.showToast("Pilih panitia yang valid terlebih dahulu.", "warning");
      return;
    }
    await withSubmissionGuard(`staff:add:${tournamentId}`, triggerEl, "Menugaskan...", async () => {
      const res = await window.TurnamenAPI.addTournamentStaff(tournamentId, {
        user_id: userId,
        staff_role: staffRole,
      });
      if (!res.success) {
        window.TurnamenUI.showToast(res.message, "danger");
        return;
      }
      window.TurnamenUI.showToast("Panitia berhasil ditugaskan.", "success");
      await navigateTo("tournament-detail");
    });
  }

  async function submitRemoveTournamentStaff(tournamentId, userId, triggerEl = null) {
    await withSubmissionGuard(`staff:remove:${tournamentId}:${userId}`, triggerEl, "Mencabut...", async () => {
      const res = await window.TurnamenAPI.removeTournamentStaff(tournamentId, userId);
      if (!res.success) {
        window.TurnamenUI.showToast(res.message, "danger");
        return;
      }
      window.TurnamenUI.showToast("Penugasan panitia berhasil dicabut.", "info");
      await navigateTo("tournament-detail");
    });
  }

  async function registerSelectedTeam(tournamentId, triggerEl = null) {
    if (!canPerform("registration:create")) {
      window.TurnamenUI.showToast(
        "Hanya Team Captain atau Super Admin yang dapat mendaftarkan tim.",
        "danger"
      );
      return;
    }
    const teamId = document.getElementById("reg-team-select")?.value;
    if (!teamId) {
      window.TurnamenUI.showToast("Pilih tim yang valid terlebih dahulu.", "warning");
      return;
    }
    await withSubmissionGuard(
      `registration:create:${tournamentId}`,
      triggerEl,
      "Mendaftarkan...",
      async () => {
        const ownedTeam = await resolveAuthorizedTeam(
          teamId,
          "Anda hanya dapat mendaftarkan tim milik Anda sendiri."
        );
        if (!ownedTeam) return;
        const res = await window.TurnamenAPI.registerTeamToTournament(tournamentId, {
          team_id: ownedTeam.id,
          notes: "Pendaftaran via Desktop UI",
        });
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.showToast("Tim berhasil didaftarkan.", "success");
        await navigateTo("tournament-detail");
      }
    );
  }

  async function verifyRegistration(registrationId, newStatus, tournamentId = "", triggerEl = null) {
    await withSubmissionGuard(
      `registration:verify:${registrationId}`,
      triggerEl,
      "Memproses...",
      async () => {
        const t = await resolveAuthorizedTournament(tournamentId, "registration:verify");
        if (!t) return;
        const res = await window.TurnamenAPI.updateRegistrationStatus(
          registrationId,
          newStatus,
          `Diverifikasi melalui panel panitia (${newStatus})`
        );
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.showToast(`Status pendaftaran diubah ke ${newStatus}.`, "success");
        await navigateTo(currentPage);
      }
    );
  }

  // =========================================================================
  // 4. TEAM MANAGEMENT PAGE (ADAPTIVE PER ROLE)
  // =========================================================================
  async function renderTeamManagement(container, isStale) {
    const [, res] = await Promise.all([
      ensureGamesLoaded(false),
      window.TurnamenAPI.getTeams(
        teamFilterState.gameId ? { game_id: teamFilterState.gameId } : {}
      ),
    ]);
    if (isStale()) return;

    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message, "retry-page");
      return;
    }

    const rawTeams = Array.isArray(res.data) ? res.data : [];
    const searchQuery = teamFilterState.search.trim().toLowerCase();
    const teams = searchQuery
      ? rawTeams.filter((tm) => {
          const hay = `${tm.name || ""} ${tm.tag || ""} ${tm.region || ""} ${tm.game_name || ""}`.toLowerCase();
          return hay.includes(searchQuery);
        })
      : rawTeams;

    const roleKey = getActiveRoleKey();
    const user = getCurrentUserSafe();
    const canCreateTeam = canPerform("team:create");
    const gameOptions = gamesState.items
      .map(
        (g) =>
          `<option value="${window.TurnamenUI.escapeHtml(g.id)}" ${teamFilterState.gameId === g.id ? "selected" : ""}>${window.TurnamenUI.escapeHtml(g.name)}</option>`
      )
      .join("");

    const pageTitle =
      roleKey === "team_captain"
        ? "Tim &amp; Roster Saya"
        : roleKey === "player"
          ? "Direktori Tim Esports"
          : "Manajemen Tim &amp; Roster Pemain";
    const pageDesc =
      roleKey === "team_captain"
        ? "Kelola identitas tim Anda, perbarui detail tim, dan atur anggota roster."
        : roleKey === "player"
          ? "Lihat profil tim peserta, tag resmi, serta susunan roster pemain."
          : "Kelola data tim esports, tag resmi, region, serta daftar anggota beserta ID in-game.";

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      <div class="page-header">
        <div class="page-header-copy">
          <h2>${pageTitle}</h2>
          <p>${pageDesc}</p>
        </div>
        ${
          canCreateTeam
            ? `<button type="button" class="btn btn-primary" data-action="open-create-team">${window.TurnamenUI.icon("plus", 15)}<span>Buat Tim Baru</span></button>`
            : ""
        }
      </div>

      <div class="filter-bar">
        <div class="search-field">
          <span class="search-field-icon">${window.TurnamenUI.icon("search", 15)}</span>
          <label for="filter-team-search" class="sr-only">Cari tim</label>
          <input
            id="filter-team-search"
            type="search"
            class="form-input"
            placeholder="Cari nama tim, tag, atau region..."
            value="${window.TurnamenUI.escapeHtml(teamFilterState.search)}"
          />
        </div>
        <div>
          <label for="filter-team-game" class="sr-only">Filter cabang game tim</label>
          <select id="filter-team-game" class="form-select">
            <option value="" ${teamFilterState.gameId === "" ? "selected" : ""}>Semua Game</option>
            ${gameOptions}
          </select>
        </div>
      </div>

      <div id="team-list-results">
        ${renderTeamManagementContent(teams, canCreateTeam, roleKey, user)}
      </div>
    `;

    const searchInput = document.getElementById("filter-team-search");
    const gameSelect = document.getElementById("filter-team-game");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        teamFilterState.search = e.target.value;
        const q = teamFilterState.search.trim().toLowerCase();
        const filtered = q
          ? rawTeams.filter((tm) => {
              const hay = `${tm.name || ""} ${tm.tag || ""} ${tm.region || ""} ${tm.game_name || ""}`.toLowerCase();
              return hay.includes(q);
            })
          : rawTeams;
        const resultsEl = document.getElementById("team-list-results");
        if (resultsEl) {
          resultsEl.innerHTML = renderTeamManagementContent(filtered, canCreateTeam, roleKey, user);
        }
      });
    }
    if (gameSelect) {
      gameSelect.addEventListener("change", (e) => {
        teamFilterState.gameId = e.target.value;
        navigateTo("team-management");
      });
    }
  }

  function renderTeamManagementContent(teams, canCreateTeam, roleKey, user) {
    const gamesById = buildGameLookup();
    const hasTeamFilter = Boolean(teamFilterState.search.trim() || teamFilterState.gameId);
    if (teams.length === 0) {
      const teamEmptyActions = [];
      if (hasTeamFilter) {
        teamEmptyActions.push(
          `<button type="button" class="btn btn-secondary btn-sm" data-action="reset-team-filters">Reset Filter</button>`
        );
      }
      if (canCreateTeam) {
        teamEmptyActions.push(
          `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-team">Buat Tim Baru</button>`
        );
      }
      return `
        <div class="card">
          ${window.TurnamenUI.renderEmptyState(
            "Belum Ada Tim Ditemukan",
            "Belum ada tim yang sesuai dengan filter saat ini.",
            teamEmptyActions.join("")
          )}
        </div>
      `;
    }

    if (isCompetitiveRole(roleKey)) {
      const sortedTeams = [...teams].sort((a, b) => {
        const aMine =
          user &&
          (a.captain_id === user.id || (a.members || []).some((m) => m.user_id === user.id));
        const bMine =
          user &&
          (b.captain_id === user.id || (b.members || []).some((m) => m.user_id === user.id));
        return Number(Boolean(bMine)) - Number(Boolean(aMine));
      });

      return `
        <div class="discovery-grid">
          ${sortedTeams
            .map((tm) => {
              const canManage = canPerform("team:manage", { team: tm });
              const members = Array.isArray(tm.members) ? tm.members : [];
              const isOwnMember =
                user && (tm.captain_id === user.id || members.some((m) => m.user_id === user.id));
              return `
              <article class="card ${isOwnMember ? "card-elevated" : ""}">
                <div class="card-header">
                  <div class="row-actions" style="gap:12px;">
                    ${window.TurnamenUI.renderTeamEmblem(tm.tag, 42)}
                    <div>
                      <h3 class="card-title">${window.TurnamenUI.escapeHtml(tm.name)}</h3>
                      <div class="table-subtext">${window.TurnamenUI.escapeHtml(tm.game_name)} | ${window.TurnamenUI.escapeHtml(tm.region || "-")}</div>
                    </div>
                  </div>
                  ${isOwnMember ? `<span class="badge badge-info">Tim Anda</span>` : `<span class="badge badge-neutral tabular-nums">${window.TurnamenUI.escapeHtml(tm.tag)}</span>`}
                </div>
                <div class="roster-list" style="margin-bottom:14px;">
                  ${
                    members.length > 0
                      ? members
                          .map(
                            (m) =>
                              `<span class="roster-chip">${window.TurnamenUI.escapeHtml(m.nickname)} (${window.TurnamenUI.escapeHtml(m.ingame_id)})</span>`
                          )
                          .join("")
                      : `<span class="table-subtext">Belum ada anggota terdaftar</span>`
                  }
                </div>
                <div class="row-actions">
                  <button type="button" class="btn btn-secondary btn-sm" data-action="open-team-detail" data-id="${window.TurnamenUI.escapeHtml(tm.id)}">Detail Roster</button>
                  ${
                    canManage
                      ? `
                    <button type="button" class="btn btn-primary btn-sm" data-action="open-add-member" data-id="${window.TurnamenUI.escapeHtml(tm.id)}">+ Anggota</button>
                    <button type="button" class="btn btn-ghost btn-sm" data-action="open-edit-team" data-id="${window.TurnamenUI.escapeHtml(tm.id)}" aria-label="Edit tim ${window.TurnamenUI.escapeHtml(tm.name)}">${window.TurnamenUI.icon("edit", 14)}</button>
                  `
                      : ""
                  }
                </div>
              </article>
            `;
            })
            .join("")}
        </div>
      `;
    }

    return `
      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tag</th>
                <th>Nama Tim</th>
                <th>Cabang Game</th>
                <th>Region</th>
                <th>Jumlah Roster</th>
                <th>Daftar Pemain (In-Game ID)</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody>
              ${teams
                .map((tm) => {
                  const canManage = canPerform("team:manage", { team: tm });
                  const members = Array.isArray(tm.members) ? tm.members : [];
                  return `
                  <tr>
                    <td class="tabular-nums"><span class="badge badge-info">${window.TurnamenUI.escapeHtml(tm.tag)}</span></td>
                    <td>
                      <div class="team-cell-inline">
                        ${window.TurnamenUI.renderTeamEmblem(tm.tag, 26)}
                        <strong>${window.TurnamenUI.escapeHtml(tm.name)}</strong>
                      </div>
                    </td>
                    <td>${window.TurnamenUI.renderGameChip(tm.game_name, gamesById[tm.game_id] || tm.game_id)}</td>
                    <td>${window.TurnamenUI.escapeHtml(tm.region || "-")}</td>
                    <td class="tabular-nums">${tm.member_count ?? members.length} Pemain</td>
                    <td>
                      <div class="roster-list">
                        ${
                          members.length > 0
                            ? members
                                .map(
                                  (m) =>
                                    `<span class="roster-chip">${window.TurnamenUI.escapeHtml(m.nickname)} (${window.TurnamenUI.escapeHtml(m.ingame_id)})</span>`
                                )
                                .join("")
                            : `<span class="table-subtext">Belum ada anggota</span>`
                        }
                      </div>
                    </td>
                    <td>
                      <div class="row-actions">
                        <button type="button" class="btn btn-secondary btn-sm" data-action="open-team-detail" data-id="${window.TurnamenUI.escapeHtml(tm.id)}">Detail</button>
                        ${
                          canManage
                            ? `
                          <button type="button" class="btn btn-ghost btn-sm" data-action="open-add-member" data-id="${window.TurnamenUI.escapeHtml(tm.id)}">+ Anggota</button>
                          <button type="button" class="btn btn-ghost btn-sm" data-action="open-edit-team" data-id="${window.TurnamenUI.escapeHtml(tm.id)}" aria-label="Edit tim ${window.TurnamenUI.escapeHtml(tm.name)}">${window.TurnamenUI.icon("edit", 14)}</button>
                        `
                            : ""
                        }
                      </div>
                    </td>
                  </tr>
                `;
                })
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  async function openCreateTeamModal() {
    if (!canPerform("team:create")) {
      window.TurnamenUI.showToast(
        "Hanya Team Captain atau Super Admin yang dapat membuat tim.",
        "warning"
      );
      return;
    }
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const games = await ensureGamesLoaded(false);
    if (isModalRequestStale(startNavSeq, startRoleKey)) return;
    const gameOptions = games
      .map(
        (g) =>
          `<option value="${window.TurnamenUI.escapeHtml(g.id)}">${window.TurnamenUI.escapeHtml(g.name)}</option>`
      )
      .join("");

    window.TurnamenUI.openModal({
      title: "Registrasi Tim Esports Baru",
      bodyHtml: `
        <div class="form-group">
          <label for="new-team-name" class="form-label">Nama Tim</label>
          <input id="new-team-name" class="form-input" placeholder="Contoh: Krakatau Esports" />
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="new-team-tag" class="form-label">Tag Tim (2-6 Karakter)</label>
            <input id="new-team-tag" class="form-input tabular-nums" placeholder="KRK" maxlength="6" />
          </div>
          <div class="form-group">
            <label for="new-team-region" class="form-label">Kota / Region</label>
            <input id="new-team-region" class="form-input" value="Jakarta" />
          </div>
        </div>
        <div class="form-group">
          <label for="new-team-game" class="form-label">Cabang Game</label>
          <select id="new-team-game" class="form-select">${gameOptions}</select>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-create-team">Simpan Tim</button>
      `,
    });
  }

  async function submitCreateTeam(triggerEl = null) {
    if (!canPerform("team:create")) {
      window.TurnamenUI.showToast(getDeniedActionMessage("team:create", null), "danger");
      return;
    }
    const name = (document.getElementById("new-team-name")?.value || "").trim();
    const tag = (document.getElementById("new-team-tag")?.value || "").trim();
    if (name.length < 3) {
      window.TurnamenUI.showToast("Nama tim wajib minimal 3 karakter.", "warning");
      return;
    }
    if (tag.length < 2 || tag.length > 6) {
      window.TurnamenUI.showToast("Tag tim wajib 2 hingga 6 karakter.", "warning");
      return;
    }

    await withSubmissionGuard(
      "team:create",
      triggerEl,
      "Menyimpan...",
      async () => {
        const payload = {
          name,
          tag,
          region: (document.getElementById("new-team-region")?.value || "Indonesia").trim(),
          game_id: document.getElementById("new-team-game")?.value || "",
        };
        const res = await window.TurnamenAPI.createTeam(payload);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        if (res.data && res.data.id) {
          selectedCaptainTeamId = res.data.id;
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Tim berhasil dibuat.", "success");
        await navigateTo(currentPage);
      },
      { lockModal: true }
    );
  }

  async function openTeamDetailModal(teamId) {
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const res = await window.TurnamenAPI.getTeamById(teamId);
    if (isModalRequestStale(startNavSeq, startRoleKey)) return;
    if (!res.success || !res.data) {
      window.TurnamenUI.showToast(res.message || "Gagal memuat detail tim.", "danger");
      return;
    }
    const tm = res.data;
    const members = Array.isArray(tm.members) ? tm.members : [];
    const canManage = canPerform("team:manage", { team: tm });

    window.TurnamenUI.openModal({
      title: `${tm.name} [${tm.tag}]`,
      bodyHtml: `
        <div class="kv-list" style="margin-bottom:14px;">
          <div class="kv-item">
            <span class="kv-label">Cabang Game</span>
            <span class="kv-value">${window.TurnamenUI.escapeHtml(tm.game_name)}</span>
          </div>
          <div class="kv-item">
            <span class="kv-label">Region</span>
            <span class="kv-value">${window.TurnamenUI.escapeHtml(tm.region || "-")}</span>
          </div>
          <div class="kv-item">
            <span class="kv-label">Total Roster</span>
            <span class="kv-value tabular-nums">${members.length} Pemain</span>
          </div>
        </div>
        <h3 class="card-title" style="margin-bottom:8px;">Daftar Anggota</h3>
        ${
          members.length === 0
            ? `<p class="form-hint">Belum ada pemain terdaftar pada tim ini.</p>`
            : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Nickname</th>
                  <th>ID In-Game</th>
                  <th>Peran</th>
                </tr>
              </thead>
              <tbody>
                ${members
                  .map(
                    (m) => `
                  <tr>
                    <td><strong>${window.TurnamenUI.escapeHtml(m.nickname)}</strong></td>
                    <td class="tabular-nums">${window.TurnamenUI.escapeHtml(m.ingame_id)}</td>
                    <td><span class="badge badge-neutral">${window.TurnamenUI.escapeHtml(m.member_role || "starter")}</span></td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        }
      `,
      footerHtml: `
        ${
          canManage
            ? `<button type="button" class="btn btn-primary" data-action="open-add-member" data-id="${window.TurnamenUI.escapeHtml(tm.id)}">+ Tambah Anggota</button>`
            : ""
        }
        <button type="button" class="btn btn-secondary" data-modal-close="true">Tutup</button>
      `,
    });
  }

  async function openEditTeamModal(teamId) {
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const tm = await resolveAuthorizedTeam(teamId, "Anda tidak memiliki izin mengubah tim ini.");
    if (!tm || isModalRequestStale(startNavSeq, startRoleKey)) return;

    window.TurnamenUI.openModal({
      title: `Edit Tim: ${tm.name}`,
      bodyHtml: `
        <div class="form-group">
          <label for="edit-team-name" class="form-label">Nama Tim</label>
          <input id="edit-team-name" class="form-input" value="${window.TurnamenUI.escapeHtml(tm.name)}" />
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="edit-team-tag" class="form-label">Tag Tim</label>
            <input id="edit-team-tag" class="form-input tabular-nums" maxlength="6" value="${window.TurnamenUI.escapeHtml(tm.tag)}" />
          </div>
          <div class="form-group">
            <label for="edit-team-region" class="form-label">Region</label>
            <input id="edit-team-region" class="form-input" value="${window.TurnamenUI.escapeHtml(tm.region || "")}" />
          </div>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-edit-team" data-id="${window.TurnamenUI.escapeHtml(tm.id)}">Simpan Perubahan</button>
      `,
    });
  }

  async function submitEditTeam(teamId, triggerEl = null) {
    await withSubmissionGuard(
      `team:edit:${teamId}`,
      triggerEl,
      "Menyimpan...",
      async () => {
        const tm = await resolveAuthorizedTeam(teamId, "Anda tidak memiliki izin mengubah tim ini.");
        if (!tm) return;
        const name = (document.getElementById("edit-team-name")?.value || "").trim();
        const tag = (document.getElementById("edit-team-tag")?.value || "").trim();
        if (name.length < 3 || tag.length < 2 || tag.length > 6) {
          window.TurnamenUI.showToast("Nama minimal 3 karakter dan tag wajib 2–6 karakter.", "warning");
          return;
        }
        const payload = {
          name,
          tag,
          region: (document.getElementById("edit-team-region")?.value || "").trim(),
        };
        const res = await window.TurnamenAPI.updateTeam(tm.id, payload);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Data tim berhasil diperbarui.", "success");
        await navigateTo(currentPage);
      },
      { lockModal: true }
    );
  }

  async function openAddMemberModal(teamId) {
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const tm = await resolveAuthorizedTeam(
      teamId,
      "Anda tidak memiliki izin menambah anggota pada tim ini."
    );
    if (!tm || isModalRequestStale(startNavSeq, startRoleKey)) return;

    window.TurnamenUI.openModal({
      title: `Tambah Anggota Roster: ${tm.name} [${tm.tag}]`,
      bodyHtml: `
        <div class="form-group">
          <label for="member-nickname" class="form-label">Nickname Pemain</label>
          <input id="member-nickname" class="form-input" placeholder="Contoh: Skylark" />
        </div>
        <div class="form-group">
          <label for="member-ingame-id" class="form-label">ID In-Game</label>
          <input id="member-ingame-id" class="form-input tabular-nums" placeholder="Contoh: MLBB-901234" />
        </div>
        <div class="form-group">
          <label for="member-role" class="form-label">Peran di Roster</label>
          <select id="member-role" class="form-select">
            <option value="starter" selected>Starter</option>
            <option value="captain">Captain</option>
            <option value="substitute">Substitute</option>
            <option value="coach">Coach</option>
          </select>
        </div>
        <div class="form-group" style="margin-bottom:0;">
          <label for="member-user-id" class="form-label">ID Akun Pemain (Opsional)</label>
          <input id="member-user-id" class="form-input tabular-nums" placeholder="UUID profil pemain jika ingin ditautkan ke akun" />
          <p class="form-hint">Server akan memverifikasi kepemilikan tim dan validitas profil secara aman tanpa membocorkan data pribadi.</p>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-add-member" data-id="${window.TurnamenUI.escapeHtml(tm.id)}">Tambahkan Anggota</button>
      `,
    });
  }

  async function submitAddMember(teamId, triggerEl = null) {
    const nickname = (document.getElementById("member-nickname")?.value || "").trim();
    const ingameId = (document.getElementById("member-ingame-id")?.value || "").trim();
    const memberRole = document.getElementById("member-role")?.value || "starter";
    const userIdRaw = (document.getElementById("member-user-id")?.value || "").trim();
    if (nickname.length < 2 || ingameId.length < 2) {
      window.TurnamenUI.showToast(
        "Nickname pemain dan ID In-Game wajib diisi (minimal 2 karakter).",
        "warning"
      );
      return;
    }

    await withSubmissionGuard(
      `team:add_member:${teamId}`,
      triggerEl,
      "Menambahkan...",
      async () => {
        const tm = await resolveAuthorizedTeam(
          teamId,
          "Anda tidak memiliki izin menambah anggota pada tim ini."
        );
        if (!tm) return;
        const payload = {
          nickname,
          ingame_id: ingameId,
          member_role: memberRole,
        };
        if (userIdRaw) {
          payload.user_id = userIdRaw;
        }
        const res = await window.TurnamenAPI.addTeamMember(tm.id, payload);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Anggota tim berhasil ditambahkan.", "success");
        await navigateTo(currentPage);
      },
      { lockModal: true }
    );
  }

  // =========================================================================
  // 5. MATCH MANAGEMENT & SCORE SUBMISSION PAGE (MANAGEMENT ONLY)
  // =========================================================================
  async function renderMatchManagement(container, isStale) {
    const ctx = await resolveActiveTournamentContext();
    if (isStale()) return;

    if (ctx.error) {
      container.innerHTML = window.TurnamenUI.renderErrorState(ctx.error, "retry-page");
      return;
    }
    if (!ctx.active) {
      container.innerHTML = window.TurnamenUI.renderEmptyState(
        "Belum Ada Turnamen",
        "Buat turnamen terlebih dahulu sebelum mengelola jadwal dan skor pertandingan.",
        `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="tournament-list">Buka Daftar Turnamen</button>`
      );
      return;
    }

    const res = await window.TurnamenAPI.getTournamentMatches(ctx.active.id);
    if (isStale()) return;

    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message, "retry-page");
      return;
    }

    const data = res.data || {};
    const allMatches = Array.isArray(data.matches) ? data.matches : [];
    const roundNames = Array.from(new Set(allMatches.map((m) => m.round_name).filter(Boolean)));
    if (matchRoundFilter && !roundNames.includes(matchRoundFilter)) {
      matchRoundFilter = "";
    }
    const matches = allMatches.filter((m) => {
      if (matchRoundFilter && m.round_name !== matchRoundFilter) return false;
      if (matchStatusFilter === "ready") {
        return Boolean(m.team_a_id && m.team_b_id && m.status !== "completed" && m.status !== "bye");
      }
      if (matchStatusFilter && m.status !== matchStatusFilter) return false;
      return true;
    });

    const canManageMatches = canPerform("match:submit_result", { tournament: ctx.active });
    const completedCount = allMatches.filter((m) => m.status === "completed").length;
    const byeCount = allMatches.filter((m) => m.status === "bye").length;
    const readyCount = allMatches.filter(
      (m) => m.team_a_id && m.team_b_id && m.status !== "completed" && m.status !== "bye"
    ).length;

    container.innerHTML = `
      ${renderTournamentContextBar(
        ctx.list,
        ctx.active,
        `<button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Lihat Bagan Bracket</button>`
      )}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Jadwal &amp; Pengesahan Skor</h2>
          <p>Turnamen: <strong>${window.TurnamenUI.escapeHtml(data.tournament_title || ctx.active.title)}</strong> (Format Best of ${data.best_of || ctx.active.best_of})</p>
        </div>
      </div>
      ${renderCommitteeAssignmentNotice(ctx.active)}

      <div class="grid-3">
        <div class="metric-card">
          <div class="metric-label">Total Match Bracket</div>
          <div class="metric-value">${allMatches.length}</div>
          <div class="metric-note">${byeCount > 0 ? `Termasuk ${byeCount} match BYE otomatis` : "Seluruh babak turnamen"}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Match Siap Bertanding</div>
          <div class="metric-value">${readyCount}</div>
        </div>
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Match Selesai (Terkunci)</div>
          <div class="metric-value">${completedCount}</div>
        </div>
      </div>

      ${
        allMatches.length > 0
          ? `
        <div class="filter-bar">
          <label for="filter-match-round" class="context-bar-label">Filter Babak:</label>
          <select id="filter-match-round" class="form-select form-select-compact">
            <option value="">Semua Babak</option>
            ${roundNames
              .map(
                (rn) =>
                  `<option value="${window.TurnamenUI.escapeHtml(rn)}" ${matchRoundFilter === rn ? "selected" : ""}>${window.TurnamenUI.escapeHtml(rn)}</option>`
              )
              .join("")}
          </select>
          <label for="filter-match-status" class="context-bar-label">Status Match:</label>
          <select id="filter-match-status" class="form-select form-select-compact">
            <option value="" ${matchStatusFilter === "" ? "selected" : ""}>Semua Status</option>
            <option value="ready" ${matchStatusFilter === "ready" ? "selected" : ""}>Siap Disahkan</option>
            <option value="scheduled" ${matchStatusFilter === "scheduled" ? "selected" : ""}>Terjadwal</option>
            <option value="completed" ${matchStatusFilter === "completed" ? "selected" : ""}>Selesai</option>
            <option value="bye" ${matchStatusFilter === "bye" ? "selected" : ""}>BYE Otomatis</option>
          </select>
        </div>
      `
          : ""
      }

      <div class="card">
        ${
          matches.length === 0
            ? window.TurnamenUI.renderEmptyState(
                allMatches.length === 0 ? "Belum Ada Pertandingan" : "Tidak Ada Match Cocok",
                allMatches.length === 0
                  ? "Bracket turnamen ini belum dibuat. Generate bracket untuk menghasilkan jadwal pertandingan."
                  : "Tidak ada pertandingan yang sesuai dengan filter babak/status saat ini.",
                allMatches.length === 0
                  ? `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Buka Halaman Bracket</button>`
                  : `<button type="button" class="btn btn-secondary btn-sm" data-action="reset-match-filters">Reset Filter Match</button>`
              )
            : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Babak</th>
                  <th>Match</th>
                  <th>Team A</th>
                  <th>Skor</th>
                  <th>Team B</th>
                  <th>Pemenang</th>
                  <th>Status</th>
                  <th>Kontrol Skor (Bo${data.best_of || ctx.active.best_of})</th>
                </tr>
              </thead>
              <tbody>
                ${matches
                  .map((m) => {
                    const maxWin = Math.ceil(Number(m.best_of || data.best_of || 3) / 2);
                    const isBye = m.status === "bye";
                    const isReady = Boolean(m.team_a_id && m.team_b_id && m.status !== "completed" && !isBye);
                    let actionCell = `<span class="table-subtext">Menunggu Lawan</span>`;
                    if (m.status === "completed") {
                      actionCell = canManageMatches
                        ? `<button type="button" class="btn btn-ghost btn-sm" data-action="open-override-score" data-id="${window.TurnamenUI.escapeHtml(m.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}" data-team-a="${window.TurnamenUI.escapeHtml(m.team_a_name)}" data-team-b="${window.TurnamenUI.escapeHtml(m.team_b_name)}" data-score-a="${m.score_a}" data-score-b="${m.score_b}" data-max="${maxWin}">Koreksi Audit</button>`
                        : `<span class="table-subtext">Terkunci (Audited)</span>`;
                    } else if (isBye) {
                      actionCell = `<span class="table-subtext">Lolos Otomatis (BYE)</span>`;
                    } else if (isReady) {
                      actionCell = canManageMatches
                        ? `
                        <div class="score-inline-form">
                          <label for="score-a-${window.TurnamenUI.escapeHtml(m.id)}" class="sr-only">Skor ${window.TurnamenUI.escapeHtml(m.team_a_name)}</label>
                          <input id="score-a-${window.TurnamenUI.escapeHtml(m.id)}" type="number" min="0" max="${maxWin}" value="${m.score_a}" class="form-input tabular-nums score-inline-input" />
                          <span aria-hidden="true">:</span>
                          <label for="score-b-${window.TurnamenUI.escapeHtml(m.id)}" class="sr-only">Skor ${window.TurnamenUI.escapeHtml(m.team_b_name)}</label>
                          <input id="score-b-${window.TurnamenUI.escapeHtml(m.id)}" type="number" min="0" max="${maxWin}" value="${m.score_b}" class="form-input tabular-nums score-inline-input" />
                          <button type="button" class="btn btn-primary btn-sm" data-action="submit-score" data-id="${window.TurnamenUI.escapeHtml(m.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Sahkan</button>
                        </div>
                      `
                        : `<span class="table-subtext">Siap Bertanding</span>`;
                    }

                    const scoreDisplay = isBye ? "ADV - BYE" : `${m.score_a} - ${m.score_b}`;
                    const teamBDisplay = m.team_b_name || (isBye ? "BYE" : "TBD");

                    return `
                    <tr>
                      <td><strong>${window.TurnamenUI.escapeHtml(m.round_name)}</strong></td>
                      <td class="tabular-nums">#${m.match_number}</td>
                      <td>
                        <div class="team-cell-inline">
                          ${m.team_a_id ? window.TurnamenUI.renderTeamEmblem(m.team_a_tag, 22) : ""}
                          <span>${window.TurnamenUI.escapeHtml(m.team_a_name || (isBye ? "BYE" : "TBD"))}</span>
                        </div>
                      </td>
                      <td class="tabular-nums"><strong>${scoreDisplay}</strong></td>
                      <td>
                        <div class="team-cell-inline">
                          ${m.team_b_id ? window.TurnamenUI.renderTeamEmblem(m.team_b_tag, 22) : ""}
                          <span>${window.TurnamenUI.escapeHtml(teamBDisplay)}</span>
                        </div>
                      </td>
                      <td>${m.winner_team_name ? `<span class="badge badge-success">${window.TurnamenUI.escapeHtml(m.winner_team_name)}</span>` : "-"}</td>
                      <td>${window.TurnamenUI.renderStatusBadge(m.status)}</td>
                      <td>${actionCell}</td>
                    </tr>
                  `;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        }
      </div>
    `;

    const roundSelect = document.getElementById("filter-match-round");
    const statusSelect = document.getElementById("filter-match-status");
    if (roundSelect) {
      roundSelect.addEventListener("change", (e) => {
        matchRoundFilter = e.target.value;
        navigateTo("match-management");
      });
    }
    if (statusSelect) {
      statusSelect.addEventListener("change", (e) => {
        matchStatusFilter = e.target.value;
        navigateTo("match-management");
      });
    }
  }

  async function submitScore(matchId, tournamentId = "", triggerEl = null) {
    const scoreAInput = document.getElementById(`score-a-${matchId}`);
    const scoreBInput = document.getElementById(`score-b-${matchId}`);
    const rawA = Number(scoreAInput?.value ?? 0);
    const rawB = Number(scoreBInput?.value ?? 0);
    if (!Number.isInteger(rawA) || !Number.isInteger(rawB) || rawA < 0 || rawB < 0) {
      window.TurnamenUI.showToast("Skor harus berupa angka bulat tidak negatif.", "warning");
      return;
    }

    const notes = "Disahkan melalui panel operasional desktop";
    const slotKey = `${matchId}::submit`;
    const fingerprint = `${rawA}|${rawB}|false|${notes}`;
    const idempotencyKey = getOrCreateMatchIdempotencyKey(slotKey, fingerprint);

    await withSubmissionGuard(
      `match:submit:${matchId}`,
      triggerEl,
      "Mengesahkan...",
      async () => {
        const t = await resolveAuthorizedTournament(tournamentId, "match:submit_result");
        if (!t) return;
        window.TurnamenUI.showToast("Memproses pengesahan skor...", "info", {
          group: `match-status-${matchId}`,
          duration: 2400,
        });
        const res = await window.TurnamenAPI.submitMatchResult(
          matchId,
          {
            score_a: rawA,
            score_b: rawB,
            notes,
            idempotency_key: idempotencyKey,
          },
          { idempotencyKey }
        );

        if (!res.success) {
          if (isRetryableSubmissionError(res)) {
            window.TurnamenUI.showToast(
              `${res.message} Klik 'Sahkan' kembali untuk retry aman dengan Idempotency-Key yang sama.`,
              "warning",
              { duration: 6000 }
            );
          } else {
            clearMatchIdempotencyKey(slotKey);
            window.TurnamenUI.showToast(res.message, "danger");
          }
          return;
        }

        clearMatchIdempotencyKey(slotKey);
        const successMsg =
          res.data && res.data.idempotent_replay
            ? "Pengesahan sebelumnya sudah tersimpan; data disinkronkan ulang."
            : "Skor disahkan. Pemenang otomatis maju ke babak berikutnya.";
        window.TurnamenUI.showToast(successMsg, "success");
        await navigateTo(currentPage);
      }
    );
  }

  async function openOverrideScoreModal(matchData) {
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const t = await resolveAuthorizedTournament(
      matchData && matchData.tournamentId,
      "match:submit_result"
    );
    if (!t || isModalRequestStale(startNavSeq, startRoleKey)) return;
    window.TurnamenUI.openModal({
      title: "Koreksi Audit Skor Pertandingan",
      bodyHtml: `
        <p style="margin-top:0; color:var(--text-secondary);">
          Pertandingan ini sudah berstatus selesai. Koreksi skor dicatat pada log audit dengan <code>force_override: true</code> dan dilindungi oleh <code>Idempotency-Key</code>.
        </p>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label for="override-score-a" class="form-label">Skor ${window.TurnamenUI.escapeHtml(matchData.teamA)}</label>
            <input id="override-score-a" type="number" min="0" max="${matchData.maxWin}" value="${matchData.scoreA}" class="form-input tabular-nums" />
          </div>
          <div class="form-group">
            <label for="override-score-b" class="form-label">Skor ${window.TurnamenUI.escapeHtml(matchData.teamB)}</label>
            <input id="override-score-b" type="number" min="0" max="${matchData.maxWin}" value="${matchData.scoreB}" class="form-input tabular-nums" />
          </div>
        </div>
        <div class="form-group">
          <label for="override-notes" class="form-label">Alasan Koreksi Audit</label>
          <textarea id="override-notes" class="form-textarea" placeholder="Jelaskan alasan revisi skor pertandingan..."></textarea>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-danger" data-action="submit-override-score" data-id="${window.TurnamenUI.escapeHtml(matchData.id)}" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Sahkan Koreksi</button>
      `,
    });
  }

  async function submitOverrideScore(matchId, tournamentId = "", triggerEl = null) {
    const scoreA = Number(document.getElementById("override-score-a")?.value ?? 0);
    const scoreB = Number(document.getElementById("override-score-b")?.value ?? 0);
    const notes = (document.getElementById("override-notes")?.value || "").trim();

    if (!Number.isInteger(scoreA) || !Number.isInteger(scoreB) || scoreA < 0 || scoreB < 0) {
      window.TurnamenUI.showToast("Skor koreksi harus berupa angka bulat tidak negatif.", "warning");
      return;
    }
    if (notes.length < 4) {
      window.TurnamenUI.showToast(
        "Catatan alasan koreksi wajib diisi (minimal 4 karakter).",
        "warning"
      );
      return;
    }

    const slotKey = `${matchId}::override`;
    const fingerprint = `${scoreA}|${scoreB}|true|${notes}`;
    const idempotencyKey = getOrCreateMatchIdempotencyKey(slotKey, fingerprint);

    await withSubmissionGuard(
      `match:override:${matchId}`,
      triggerEl,
      "Memproses Koreksi...",
      async () => {
        const t = await resolveAuthorizedTournament(tournamentId, "match:submit_result");
        if (!t) return;
        const res = await window.TurnamenAPI.submitMatchResult(
          matchId,
          {
            score_a: scoreA,
            score_b: scoreB,
            notes,
            force_override: true,
            idempotency_key: idempotencyKey,
          },
          { idempotencyKey }
        );
        if (!res.success) {
          if (isRetryableSubmissionError(res)) {
            window.TurnamenUI.showToast(
              `${res.message} Klik 'Sahkan Koreksi' ulang untuk retry aman dengan Idempotency-Key yang sama.`,
              "warning",
              { duration: 6000 }
            );
          } else {
            clearMatchIdempotencyKey(slotKey);
            window.TurnamenUI.showToast(res.message, "danger");
          }
          return;
        }
        clearMatchIdempotencyKey(slotKey);
        window.TurnamenUI.closeModal(true);
        const successMsg =
          res.data && res.data.idempotent_replay
            ? "Koreksi sebelumnya sudah tersimpan; data disinkronkan ulang."
            : "Koreksi audit skor berhasil disimpan.";
        window.TurnamenUI.showToast(successMsg, "success");
        await navigateTo(currentPage);
      },
      { lockModal: true }
    );
  }

  // =========================================================================
  // 6. BRACKET VISUALIZATION PAGE (SINGLE ELIMINATION)
  // =========================================================================
  async function renderBracketPage(container, isStale) {
    const ctx = await resolveActiveTournamentContext();
    if (isStale()) return;

    if (ctx.error) {
      container.innerHTML = window.TurnamenUI.renderErrorState(ctx.error, "retry-page");
      return;
    }
    if (!ctx.active) {
      container.innerHTML = window.TurnamenUI.renderEmptyState(
        "Belum Ada Turnamen",
        "Buat turnamen terlebih dahulu untuk menyusun dan memantau bracket Single Elimination.",
        `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="tournament-list">Buka Daftar Turnamen</button>`
      );
      return;
    }

    const res = await window.TurnamenAPI.getTournamentMatches(ctx.active.id);
    if (isStale()) return;

    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message, "retry-page");
      return;
    }

    const data = res.data || {};
    const rounds = Array.isArray(data.rounds) ? data.rounds : [];
    const canGenerate = canPerform("bracket:generate", { tournament: ctx.active });
    const canViewScoreDesk = isManagementRole();
    const hasExistingBracket = rounds.length > 0;

    const contextActionsHtml = `
      ${
        canViewScoreDesk
          ? `<button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="match-management" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Kelola Skor</button>`
          : `<button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="reports" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Lihat Klasemen</button>`
      }
      ${
        canGenerate
          ? `<button type="button" class="btn btn-primary btn-sm" data-action="${hasExistingBracket ? "confirm-regenerate-bracket" : "regenerate-bracket"}" data-id="${window.TurnamenUI.escapeHtml(data.tournament_id || ctx.active.id)}">${hasExistingBracket ? "Reset / Generate Ulang Bracket" : "Generate Bracket"}</button>`
          : ""
      }
    `;

    container.innerHTML = `
      ${renderTournamentContextBar(ctx.list, ctx.active, contextActionsHtml)}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Single Elimination Bracket: ${window.TurnamenUI.escapeHtml(data.tournament_title || ctx.active.title)}</h2>
          <p>Pemenang setiap pertandingan otomatis melaju ke slot babak berikutnya setelah skor disahkan.</p>
        </div>
      </div>
      ${renderCommitteeAssignmentNotice(ctx.active)}

      <div class="card">
        <div class="bracket-legend">
          <span><span class="badge badge-info">Sorotan Cyan</span> Pemenang Match</span>
          <span><span class="badge badge-success">Completed</span> Skor Terkunci</span>
          <span><span class="badge badge-neutral">BYE</span> Lolos Otomatis</span>
        </div>

        ${
          rounds.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Bracket Belum Dibuat",
                canGenerate
                  ? "Klik Generate Bracket untuk menyusun jadwal Single Elimination dari tim yang telah disetujui."
                  : "Panitia atau Organizer belum men-generate bracket untuk turnamen ini.",
                canGenerate
                  ? `<button type="button" class="btn btn-primary btn-sm" data-action="regenerate-bracket" data-id="${window.TurnamenUI.escapeHtml(data.tournament_id || ctx.active.id)}">Generate Bracket Sekarang</button>`
                  : ""
              )
            : `
          <div class="bracket-scroll-wrap">
            <div class="bracket-stage" id="bracket-stage">
              <svg class="bracket-connectors-svg" aria-hidden="true"></svg>
              <div class="bracket-board">
                ${rounds
                  .map(
                    (round) => `
                  <section class="bracket-round" aria-label="${window.TurnamenUI.escapeHtml(round.round_name)}">
                    <div class="bracket-round-header">
                      <span>${window.TurnamenUI.escapeHtml(round.round_name)}</span>
                      <span class="tabular-nums">${(round.matches || []).length} Match</span>
                    </div>
                    <div class="bracket-matches-col">
                      ${(round.matches || [])
                        .map((m) => {
                          const isCompleted = m.status === "completed";
                          const isBye = m.status === "bye";
                          const isDecided = isCompleted || isBye;
                          const winA = m.winner_team_id && m.winner_team_id === m.team_a_id;
                          const winB = m.winner_team_id && m.winner_team_id === m.team_b_id;
                          const emptyA = !m.team_a_id;
                          const emptyB = !m.team_b_id;
                          const teamALabel = m.team_a_name || (isBye ? "BYE" : "TBD");
                          const teamBLabel = m.team_b_name || (isBye ? "BYE" : "TBD");
                          const scoreALabel = isBye ? (m.team_a_id ? "ADV" : "-") : m.score_a;
                          const scoreBLabel = isBye ? (m.team_b_id ? "ADV" : "BYE") : m.score_b;
                          return `
                          <article
                            class="bracket-match-card ${isDecided ? "is-completed" : ""} ${isBye ? "is-bye-match" : ""}"
                            data-match-id="${window.TurnamenUI.escapeHtml(m.id)}"
                            data-next-match-id="${window.TurnamenUI.escapeHtml(m.next_match_id || "")}"
                            data-next-slot="${window.TurnamenUI.escapeHtml(m.next_slot || "")}"
                            data-completed="${isDecided ? "true" : "false"}"
                          >
                            <div class="bracket-match-meta">
                              <span class="tabular-nums">Match #${m.match_number} (Bo${m.best_of})</span>
                              ${window.TurnamenUI.renderStatusBadge(m.status)}
                            </div>
                            <div class="bracket-team-row ${winA ? "winner" : ""} ${emptyA ? "bye" : ""}" data-slot="A">
                              <span class="bracket-team-identity">
                                ${m.team_a_id ? window.TurnamenUI.renderTeamEmblem(m.team_a_tag, 22) : ""}
                                <span class="bracket-team-name">${window.TurnamenUI.escapeHtml(teamALabel)}</span>
                              </span>
                              <span class="bracket-score">${scoreALabel}</span>
                            </div>
                            <div class="bracket-team-row ${winB ? "winner" : ""} ${emptyB ? "bye" : ""}" data-slot="B">
                              <span class="bracket-team-identity">
                                ${m.team_b_id ? window.TurnamenUI.renderTeamEmblem(m.team_b_tag, 22) : ""}
                                <span class="bracket-team-name">${window.TurnamenUI.escapeHtml(teamBLabel)}</span>
                              </span>
                              <span class="bracket-score">${scoreBLabel}</span>
                            </div>
                          </article>
                        `;
                        })
                        .join("")}
                    </div>
                  </section>
                `
                  )
                  .join("")}
              </div>
            </div>
          </div>
        `
        }
      </div>
    `;
    scheduleBracketConnectors();
  }

  async function confirmRegenerateBracket(tournamentId) {
    const t = await resolveAuthorizedTournament(tournamentId, "bracket:generate");
    if (!t) return;
    window.TurnamenUI.openModal({
      title: "Konfirmasi Reset Bracket",
      bodyHtml: `
        <p style="margin:0; color:var(--text-secondary);">
          Bracket untuk turnamen ini sudah tersedia. Membuat ulang bracket akan mengganti jadwal pertandingan yang ada berdasarkan daftar tim berstatus <code>approved</code>.
        </p>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="regenerate-bracket" data-id="${window.TurnamenUI.escapeHtml(t.id)}">Lanjutkan Generate Ulang</button>
      `,
    });
  }

  async function regenerateBracket(tournamentId, triggerEl = null) {
    await withSubmissionGuard(
      `bracket:generate:${tournamentId}`,
      triggerEl,
      "Menyusun...",
      async () => {
        const t = await resolveAuthorizedTournament(tournamentId, "bracket:generate");
        if (!t) return;
        const res = await window.TurnamenAPI.generateBracket(t.id);
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Bracket Single Elimination berhasil disusun.", "success");
        await navigateTo("bracket");
      },
      { lockModal: true }
    );
  }

  // =========================================================================
  // 7. ANNOUNCEMENTS PAGE
  // =========================================================================
  async function renderAnnouncementsPage(container, isStale) {
    const ctx = await resolveActiveTournamentContext();
    if (isStale()) return;

    if (ctx.error) {
      container.innerHTML = window.TurnamenUI.renderErrorState(ctx.error, "retry-page");
      return;
    }
    if (!ctx.active) {
      container.innerHTML = window.TurnamenUI.renderEmptyState(
        "Belum Ada Turnamen",
        "Buat atau pilih turnamen untuk melihat papan pengumuman kompetisi.",
        `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="tournament-list">Buka Daftar Turnamen</button>`
      );
      return;
    }

    const tid = ctx.active.id;
    const res = await window.TurnamenAPI.getAnnouncements(tid);
    if (isStale()) return;

    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message, "retry-page");
      return;
    }

    const allItems = Array.isArray(res.data) ? [...res.data] : [];
    allItems.sort((a, b) => {
      const pinDiff = Number(Boolean(b.is_pinned)) - Number(Boolean(a.is_pinned));
      if (pinDiff !== 0) return pinDiff;
      const tA = new Date(a.published_at || a.created_at || 0).getTime() || 0;
      const tB = new Date(b.published_at || b.created_at || 0).getTime() || 0;
      return tB - tA;
    });
    const items = announcementPriorityFilter
      ? allItems.filter((a) => String(a.priority || "").toLowerCase() === announcementPriorityFilter)
      : allItems;

    const canCreate = canPerform("announcement:create", { tournament: ctx.active });

    container.innerHTML = `
      ${renderTournamentContextBar(
        ctx.list,
        ctx.active,
        canCreate
          ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-announcement-modal" data-id="${window.TurnamenUI.escapeHtml(tid)}">${window.TurnamenUI.icon("plus", 14)}<span>Buat Pengumuman</span></button>`
          : ""
      )}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Papan Pengumuman Turnamen</h2>
          <p>Informasi teknis, pembaruan jadwal, dan instruksi check-in resmi dari panitia.</p>
        </div>
      </div>
      ${renderCommitteeAssignmentNotice(ctx.active)}

      <div class="filter-bar">
        <label for="filter-announcement-priority" class="context-bar-label">Prioritas:</label>
        <select id="filter-announcement-priority" class="form-select form-select-compact">
          <option value="" ${announcementPriorityFilter === "" ? "selected" : ""}>Semua Prioritas</option>
          <option value="urgent" ${announcementPriorityFilter === "urgent" ? "selected" : ""}>Mendesak (Urgent)</option>
          <option value="important" ${announcementPriorityFilter === "important" ? "selected" : ""}>Penting (Important)</option>
          <option value="normal" ${announcementPriorityFilter === "normal" ? "selected" : ""}>Info (Normal)</option>
        </select>
      </div>

      <div class="stack-md">
        ${
          items.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Belum Ada Pengumuman",
                "Belum ada pengumuman yang sesuai dengan filter pada turnamen ini.",
                announcementPriorityFilter
                  ? `<button type="button" class="btn btn-secondary btn-sm" data-action="reset-announcement-filters">Tampilkan Semua Prioritas</button>`
                  : ""
              )
            : items
                .map(
                  (a) => `
              <article class="announcement-card is-${window.TurnamenUI.escapeHtml(String(a.priority || "normal").toLowerCase())} ${a.is_pinned ? "is-pinned" : ""}">
                <div class="card-header">
                  <div class="row-actions">
                    ${
                      a.is_pinned
                        ? `<span class="badge badge-violet">${window.TurnamenUI.icon("pin", 12)}<span>Disematkan</span></span>`
                        : ""
                    }
                    ${window.TurnamenUI.renderStatusBadge(a.priority)}
                    <h3 class="card-title">${window.TurnamenUI.escapeHtml(a.title)}</h3>
                  </div>
                  <span class="table-subtext tabular-nums">
                    Oleh ${window.TurnamenUI.escapeHtml(a.author_name || "Panitia")} | ${window.TurnamenUI.formatDateTime(a.published_at || a.created_at)}
                  </span>
                </div>
                <p style="margin:0; color:var(--text-secondary);">${window.TurnamenUI.escapeHtml(a.content)}</p>
              </article>
            `
                )
                .join("")
        }
      </div>
    `;

    const prioritySelect = document.getElementById("filter-announcement-priority");
    if (prioritySelect) {
      prioritySelect.addEventListener("change", (e) => {
        announcementPriorityFilter = e.target.value;
        navigateTo("announcements");
      });
    }
  }

  async function openAnnouncementModal(tournamentId) {
    const startNavSeq = navigationSeq;
    const startRoleKey = getActiveRoleKey();
    const t = await resolveAuthorizedTournament(tournamentId, "announcement:create");
    if (!t || isModalRequestStale(startNavSeq, startRoleKey)) return;
    window.TurnamenUI.openModal({
      title: "Publikasikan Pengumuman Resmi",
      bodyHtml: `
        <div class="form-group">
          <label for="ann-title" class="form-label">Judul Pengumuman</label>
          <input id="ann-title" class="form-input" placeholder="Contoh: Perubahan Jadwal Semi Final" />
        </div>
        <div class="form-group">
          <label for="ann-priority" class="form-label">Prioritas</label>
          <select id="ann-priority" class="form-select">
            <option value="normal">Normal</option>
            <option value="important" selected>Penting (Important)</option>
            <option value="urgent">Mendesak (Urgent)</option>
          </select>
        </div>
        <div class="form-group">
          <label for="ann-content" class="form-label">Isi Pengumuman</label>
          <textarea id="ann-content" rows="4" class="form-textarea" placeholder="Tulis instruksi lengkap untuk peserta..."></textarea>
        </div>
        <div class="form-group" style="margin-bottom:0;">
          <label class="form-checkbox-row" for="ann-pinned">
            <input id="ann-pinned" type="checkbox" />
            <span>Sematkan pengumuman di posisi teratas</span>
          </label>
        </div>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-announcement" data-id="${window.TurnamenUI.escapeHtml(t.id)}">Publikasikan</button>
      `,
    });
  }

  async function submitAnnouncement(tournamentId, triggerEl = null) {
    const title = (document.getElementById("ann-title")?.value || "").trim();
    const priority = document.getElementById("ann-priority")?.value || "normal";
    const content = (document.getElementById("ann-content")?.value || "").trim();
    const isPinned = Boolean(document.getElementById("ann-pinned")?.checked);

    if (title.length < 4 || content.length < 5) {
      window.TurnamenUI.showToast(
        "Judul (minimal 4 karakter) dan isi pengumuman (minimal 5 karakter) wajib diisi.",
        "warning"
      );
      return;
    }

    await withSubmissionGuard(
      `announcement:create:${tournamentId}`,
      triggerEl,
      "Mempublikasikan...",
      async () => {
        const t = await resolveAuthorizedTournament(tournamentId, "announcement:create");
        if (!t) return;
        const res = await window.TurnamenAPI.createAnnouncement(t.id, {
          title,
          priority,
          content,
          is_pinned: isPinned,
        });
        if (!res.success) {
          window.TurnamenUI.showToast(res.message, "danger");
          return;
        }
        window.TurnamenUI.closeModal(true);
        window.TurnamenUI.showToast("Pengumuman berhasil dipublikasikan.", "success");
        await navigateTo(currentPage);
      },
      { lockModal: true }
    );
  }

  // =========================================================================
  // 8. REPORTS & STANDINGS PAGE
  // =========================================================================
  async function renderReportsPage(container, isStale) {
    const ctx = await resolveActiveTournamentContext();
    if (isStale()) return;

    if (ctx.error) {
      container.innerHTML = window.TurnamenUI.renderErrorState(ctx.error, "retry-page");
      return;
    }
    if (!ctx.active) {
      container.innerHTML = window.TurnamenUI.renderEmptyState(
        "Belum Ada Turnamen",
        "Buat turnamen terlebih dahulu untuk melihat statistik dan klasemen akhir.",
        `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="tournament-list">Buka Daftar Turnamen</button>`
      );
      return;
    }

    const res = await window.TurnamenAPI.getTournamentReport(ctx.active.id);
    if (isStale()) return;

    if (!res.success || !res.data) {
      container.innerHTML = window.TurnamenUI.renderErrorState(
        res.message || "Gagal memuat laporan turnamen.",
        "retry-page"
      );
      return;
    }

    const report = res.data;
    const s = report.summary || {};
    const standings = Array.isArray(report.standings) ? report.standings : [];
    const recentActivity = Array.isArray(report.recent_activity) ? report.recent_activity : [];
    const hasManagerReportAccess = s.pending_registrations !== undefined;

    container.innerHTML = `
      ${renderTournamentContextBar(ctx.list, ctx.active)}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Laporan &amp; Klasemen: ${window.TurnamenUI.escapeHtml(report.tournament?.title || ctx.active.title)}</h2>
          <p>Statistik penyelesaian pertandingan dan rekor menang-kalah seluruh tim peserta.</p>
        </div>
        <span class="badge ${hasManagerReportAccess ? "badge-violet" : "badge-neutral"}">
          ${hasManagerReportAccess ? "Akses Manajerial (Audit + Antrean)" : "Ringkasan Publik"}
        </span>
      </div>
      ${
        !hasManagerReportAccess
          ? `
        <div class="notice-banner notice-banner-info" role="status">
          <div>
            <strong>Mode Ringkas Publik:</strong>
            <span>Metrik internal pendaftaran tertunda dan log audit aktivitas hanya ditampilkan kepada Super Admin, Organizer pemilik, atau Committee yang ditugaskan.</span>
          </div>
        </div>
      `
          : ""
      }

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Tingkat Penyelesaian</div>
          <div class="metric-value">${s.completion_percentage ?? 0}%</div>
          <div class="metric-note" style="margin-bottom:8px;">${s.completed_matches ?? 0} dari ${s.total_matches ?? 0} pertandingan selesai</div>
          ${window.TurnamenUI.renderProgressBar(s.completion_percentage ?? 0, "Progres penyelesaian pertandingan")}
        </div>
        <div class="metric-card">
          <div class="metric-label">Tim Terverifikasi</div>
          <div class="metric-value">${s.approved_teams ?? 0} / ${s.max_teams ?? 0}</div>
          <div class="metric-note">${
            hasManagerReportAccess
              ? `Menunggu verifikasi: ${s.pending_registrations ?? 0} (Total pendaftar: ${s.total_registrations ?? 0})`
              : `Kuota maksimal: ${s.max_teams ?? 0} tim terverifikasi`
          }</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Pertandingan Tersisa</div>
          <div class="metric-value">${s.scheduled_matches ?? 0}</div>
          <div class="metric-note">Menunggu hasil pertandingan</div>
        </div>
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Juara Turnamen</div>
          <div class="metric-value metric-value-sm">${window.TurnamenUI.escapeHtml(s.champion_team || "Belum Ditentukan")}</div>
          <div class="metric-note">${s.champion_team ? "Pemenang Grand Final" : "Menunggu Grand Final selesai"}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Tabel Klasemen &amp; Statistik Tim (Standings)</h3>
        </div>
        ${
          standings.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Klasemen Belum Tersedia",
                "Belum ada tim berstatus disetujui pada turnamen ini."
              )
            : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Peringkat</th>
                  <th>Tag</th>
                  <th>Nama Tim</th>
                  <th>Main</th>
                  <th>Menang</th>
                  <th>Kalah</th>
                  <th>Skor Game (W-L)</th>
                  <th>Babak Tertinggi</th>
                  <th>Status Posisi</th>
                </tr>
              </thead>
              <tbody>
                ${standings
                  .map(
                    (row) => `
                  <tr>
                    <td class="tabular-nums"><span class="rank-pill ${row.rank <= 3 ? `rank-pill-${row.rank}` : ""}">#${row.rank}</span></td>
                    <td class="tabular-nums"><span class="badge badge-neutral">${window.TurnamenUI.escapeHtml(row.team_tag)}</span></td>
                    <td>
                      <div class="team-cell-inline">
                        ${window.TurnamenUI.renderTeamEmblem(row.team_tag, 24)}
                        <strong>${window.TurnamenUI.escapeHtml(row.team_name)}</strong>
                      </div>
                    </td>
                    <td class="tabular-nums">${row.matches_played}</td>
                    <td class="tabular-nums" style="color:var(--status-success-text); font-weight:700;">${row.matches_won}</td>
                    <td class="tabular-nums" style="color:var(--status-danger-text);">${row.matches_lost}</td>
                    <td class="tabular-nums">${row.games_won} - ${row.games_lost}</td>
                    <td>${window.TurnamenUI.escapeHtml(row.highest_round_name)}</td>
                    <td><span class="badge ${String(row.placement_label || "").includes("Juara 1") ? "badge-info" : "badge-violet"}">${window.TurnamenUI.escapeHtml(row.placement_label)}</span></td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        `
        }
      </div>

      ${
        hasManagerReportAccess
          ? `
        <div class="card" style="margin-top:20px;">
          <div class="card-header">
            <div>
              <h3 class="card-title">Log Audit Aktivitas Turnamen</h3>
              <p class="card-subtitle">Jejak pengesahan skor, verifikasi peserta, dan perubahan status turnamen.</p>
            </div>
            <span class="badge badge-violet">Audit Trail</span>
          </div>
          ${
            recentActivity.length === 0
              ? window.TurnamenUI.renderEmptyState("Belum Ada Aktivitas", "Belum ada log audit tercatat pada turnamen ini.")
              : `
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Aksi</th>
                    <th>Entitas</th>
                    <th>Waktu</th>
                  </tr>
                </thead>
                <tbody>
                  ${recentActivity
                    .map(
                      (log) => `
                    <tr>
                      <td><code>${window.TurnamenUI.escapeHtml(log.action)}</code></td>
                      <td>${window.TurnamenUI.escapeHtml(log.entity_type)}</td>
                      <td class="tabular-nums">${window.TurnamenUI.formatDateTime(log.created_at)}</td>
                    </tr>
                  `
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `
          }
        </div>
      `
          : ""
      }
    `;
  }

  // =========================================================================
  // 9. USER PROFILE & SYSTEM DIAGNOSTICS PAGE
  // =========================================================================
  async function renderProfilePage(container, isStale) {
    let state = getRuntimeState();
    let user = getCurrentUserSafe();

    if (user && (state.token || isMockMode())) {
      const meRes = await window.TurnamenAPI.getCurrentUser();
      if (isStale()) return;
      if (meRes && meRes.success && meRes.data && meRes.data.user) {
        user = meRes.data.user;
        updateUserTopbar(user);
      }
    }

    state = getRuntimeState();
    const isMock = isMockMode();
    const roleKey = user && user.role ? String(user.role).toLowerCase() : "";
    const capabilities = ROLE_CAPABILITIES[roleKey] || [
      "Akses publik read-only untuk melihat katalog turnamen, bracket, pengumuman, dan klasemen.",
    ];

    container.innerHTML = `
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Profil Pengguna &amp; Diagnostik Sistem</h2>
          <p>Informasi sesi akun aktif, hak akses RBAC, serta konfigurasi mode runtime aplikasi.</p>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Identitas Akun Aktif</h3>
            ${window.TurnamenUI.renderRoleBadge(user ? user.role : null)}
          </div>
          ${
            user
              ? `
            <div class="profile-identity-header">
              ${window.TurnamenUI.renderPlayerAvatar(user.full_name || user.username, user.role, 52)}
              <div>
                <div class="roster-card-name" style="font-size:16px;">${window.TurnamenUI.escapeHtml(user.full_name || user.username || "-")}</div>
                <div class="table-subtext tabular-nums">${window.TurnamenUI.escapeHtml(user.email || "-")}</div>
              </div>
            </div>
            <div class="form-group">
              <label for="profile-fullname" class="form-label">Nama Lengkap</label>
              <input id="profile-fullname" class="form-input" value="${window.TurnamenUI.escapeHtml(user.full_name || "")}" />
            </div>
            <div class="grid-2" style="margin-bottom:0;">
              <div class="form-group">
                <label for="profile-phone" class="form-label">Nomor Telepon</label>
                <input id="profile-phone" class="form-input tabular-nums" placeholder="Contoh: 081234567890" value="${window.TurnamenUI.escapeHtml(user.phone || "")}" />
              </div>
              <div class="form-group">
                <label for="profile-avatar-url" class="form-label">URL Avatar (Opsional)</label>
                <input id="profile-avatar-url" class="form-input" placeholder="https://..." value="${window.TurnamenUI.escapeHtml(user.avatar_url || "")}" />
              </div>
            </div>
            <div class="form-group">
              <label for="profile-username" class="form-label">Username (Tetap)</label>
              <input id="profile-username" class="form-input tabular-nums" value="${window.TurnamenUI.escapeHtml(user.username || "-")}" readonly />
            </div>
            <div class="form-group">
              <label for="profile-email" class="form-label">Email (Tetap)</label>
              <input id="profile-email" class="form-input tabular-nums" value="${window.TurnamenUI.escapeHtml(user.email || "-")}" readonly />
            </div>
            <div class="row-actions">
              <button type="button" class="btn btn-primary" data-action="submit-update-profile">Simpan Profil</button>
              <button type="button" class="btn btn-secondary" data-action="go-page" data-page="login">Ganti Akun</button>
              <button type="button" class="btn btn-danger" data-action="logout">${window.TurnamenUI.icon("logout", 14)}<span>Keluar dari Sesi</span></button>
            </div>
          `
              : `
            <div class="state-box" style="margin-bottom:14px;">
              <div class="state-icon">${window.TurnamenUI.icon("lock", 20)}</div>
              <h3>Belum Masuk ke Akun</h3>
              <p>Anda sedang mengakses Turnamen.in sebagai tamu (read-only). Masuk atau daftar akun untuk melakukan aksi sesuai role RBAC.</p>
              <div class="state-actions">
                <button type="button" class="btn btn-primary" data-action="go-page" data-page="login">Masuk / Daftar Akun</button>
              </div>
            </div>
          `
          }
        </div>

        <div class="stack-md">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Status Runtime &amp; Koneksi</h3>
              <span class="badge ${isMock ? "badge-warning" : "badge-success"}">${window.TurnamenUI.escapeHtml(state.appMode.toUpperCase())}</span>
            </div>
            <div class="kv-list">
              <div class="kv-item">
                <span class="kv-label">Mode Operasi</span>
                <span class="kv-value">${isMock ? "Mock Data Lokal" : "Supabase Cloud"}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">Endpoint REST API</span>
                <span class="kv-value"><code>${window.TurnamenUI.escapeHtml(state.apiBaseUrl)}</code></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">Python Eel Bridge</span>
                <span class="kv-value">${window.TurnamenBridge && window.TurnamenBridge.hasEel() ? "Aktif (Desktop Eel)" : "Browser Lokal"}</span>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Cakupan Izin RBAC</h3>
            </div>
            <ul class="capability-list">
              ${capabilities.map((cap) => `<li>${window.TurnamenUI.escapeHtml(cap)}</li>`).join("")}
            </ul>
          </div>
        </div>
      </div>
    `;
  }

  async function submitUpdateProfile(triggerEl = null) {
    const fullName = (document.getElementById("profile-fullname")?.value || "").trim();
    const phone = (document.getElementById("profile-phone")?.value || "").trim();
    const avatarUrl = (document.getElementById("profile-avatar-url")?.value || "").trim();

    if (fullName.length < 2) {
      window.TurnamenUI.showToast("Nama lengkap wajib minimal 2 karakter.", "warning");
      return;
    }

    await withSubmissionGuard("auth:update-profile", triggerEl, "Menyimpan...", async () => {
      const res = await window.TurnamenAPI.updateProfile({
        full_name: fullName,
        phone: phone || null,
        avatar_url: avatarUrl || null,
      });
      if (!res.success) {
        window.TurnamenUI.showToast(res.message, "danger");
        return;
      }
      const updatedUser = res.data && res.data.user ? res.data.user : getCurrentUserSafe();
      updateUserTopbar(updatedUser);
      window.TurnamenUI.showToast("Profil akun berhasil diperbarui.", "success");
      await navigateTo("profile");
    });
  }

  // =========================================================================
  // 10. LOGIN, REGISTER & MOCK ROLE SIMULATION PAGE
  // =========================================================================
  async function renderLoginPage(container) {
    const isMock = isMockMode();
    const user = getCurrentUserSafe();

    const demoPanelHtml = isMock
      ? `
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Simulasi Cepat 5 Role (Mode Mock)</h3>
              <p class="card-subtitle">Password default seluruh akun demo pada mode mock: <code>turnamen123</code></p>
            </div>
            <span class="badge badge-warning">Mock Only</span>
          </div>
          <div class="stack-md" style="gap:8px;">
            <button type="button" class="btn btn-secondary" data-action="quick-switch-role" data-role="super_admin">1. Super Admin (admin@turnamen.in)</button>
            <button type="button" class="btn btn-secondary" data-action="quick-switch-role" data-role="organizer">2. Tournament Organizer (organizer@turnamen.in)</button>
            <button type="button" class="btn btn-secondary" data-action="quick-switch-role" data-role="committee">3. Committee / Panitia (committee@turnamen.in)</button>
            <button type="button" class="btn btn-secondary" data-action="quick-switch-role" data-role="team_captain">4. Team Captain (captain@turnamen.in)</button>
            <button type="button" class="btn btn-secondary" data-action="quick-switch-role" data-role="player">5. Player (player@turnamen.in)</button>
          </div>
        </div>
      `
      : "";

    container.innerHTML = `
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Autentikasi Akun Turnamen.in</h2>
          <p>${
            isMock
              ? "Masuk dengan akun terdaftar, daftarkan akun baru, atau gunakan pemilih peran simulasi pada mode mock."
              : "Masuk atau daftarkan akun Supabase Anda untuk mengakses fitur sesuai role RBAC."
          }</p>
        </div>
      </div>

      ${
        user
          ? `
        <div class="notice-banner" role="status">
          <div>
            <strong>Sesi aktif:</strong>
            <span>${window.TurnamenUI.escapeHtml(user.full_name || user.username || user.email)} (${window.TurnamenUI.escapeHtml(user.role || "player")})</span>
          </div>
          <button type="button" class="btn btn-danger btn-sm" data-action="logout">${window.TurnamenUI.icon("logout", 14)}<span>Keluar</span></button>
        </div>
      `
          : ""
      }

      <div id="auth-feedback-slot"></div>

      <div class="auth-grid ${isMock ? "" : "auth-grid-single"}">
        <div class="card card-elevated">
          <div class="auth-brand-banner">
            <img src="assets/images/logo.svg" alt="Logo Turnamen.in" width="38" height="38" />
            <div>
              <div class="roster-card-name" style="font-size:15.5px;">Turnamen.in Arena Portal</div>
              <div class="table-subtext">Masuk atau daftarkan akun resmi esports Anda</div>
            </div>
          </div>
          ${
            loginActiveTab === "login" || loginActiveTab === "register"
              ? `
          <div class="tabs-nav" role="tablist" aria-label="Mode Autentikasi">
            <button
              type="button"
              role="tab"
              id="tab-auth-login"
              class="tab-btn"
              aria-selected="${loginActiveTab === "login" ? "true" : "false"}"
              aria-controls="panel-auth-login"
              tabindex="${loginActiveTab === "login" ? "0" : "-1"}"
              data-action="switch-auth-tab"
              data-tab="login"
            >
              Masuk Akun
            </button>
            <button
              type="button"
              role="tab"
              id="tab-auth-register"
              class="tab-btn"
              aria-selected="${loginActiveTab === "register" ? "true" : "false"}"
              aria-controls="panel-auth-register"
              tabindex="${loginActiveTab === "register" ? "0" : "-1"}"
              data-action="switch-auth-tab"
              data-tab="register"
            >
              Daftar Akun Baru
            </button>
          </div>
          `
              : ""
          }

          <section
            id="panel-auth-login"
            role="tabpanel"
            aria-labelledby="tab-auth-login"
            ${loginActiveTab === "login" ? "" : "hidden"}
          >
            <form id="login-form" novalidate>
              <div class="form-group">
                <label for="login-email" class="form-label">Email</label>
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  autocomplete="email"
                  class="form-input"
                  placeholder="nama@domain.com"
                />
              </div>
              <div class="form-group">
                <label for="login-password" class="form-label">Password</label>
                <input
                  id="login-password"
                  name="password"
                  type="password"
                  autocomplete="current-password"
                  class="form-input"
                  placeholder="Masukkan password akun"
                />
              </div>
              <div class="auth-inline-actions">
                <button
                  type="button"
                  class="btn btn-ghost btn-sm auth-link-btn"
                  data-action="open-password-recovery"
                >
                  Lupa password?
                </button>
              </div>
              <button type="submit" class="btn btn-primary" style="width:100%;">Masuk ke Arena</button>
            </form>
          </section>

          <section
            id="panel-auth-register"
            role="tabpanel"
            aria-labelledby="tab-auth-register"
            ${loginActiveTab === "register" ? "" : "hidden"}
          >
            <form id="register-form" novalidate>
              <div class="form-group">
                <label for="reg-fullname" class="form-label">Nama Lengkap</label>
                <input id="reg-fullname" autocomplete="name" class="form-input" placeholder="Nama lengkap Anda" />
              </div>
              <div class="grid-2" style="margin-bottom:0;">
                <div class="form-group">
                  <label for="reg-username" class="form-label">Username</label>
                  <input id="reg-username" autocomplete="username" class="form-input tabular-nums" placeholder="Minimal 3 karakter" />
                </div>
                <div class="form-group">
                  <label for="reg-role" class="form-label">Peran Pendaftaran</label>
                  <select id="reg-role" class="form-select">
                    <option value="player" selected>Player</option>
                    <option value="team_captain">Team Captain</option>
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label for="reg-email" class="form-label">Email</label>
                <input id="reg-email" type="email" autocomplete="email" class="form-input" placeholder="nama@domain.com" />
              </div>
              <div class="form-group">
                <label for="reg-password" class="form-label">Password</label>
                <input id="reg-password" type="password" autocomplete="new-password" class="form-input" placeholder="Minimal 6 karakter" />
              </div>
              <button type="submit" class="btn btn-primary" style="width:100%;">Buat Akun Turnamen.in</button>
            </form>
          </section>

          <section
            id="panel-auth-recovery-request"
            aria-label="Pemulihan Password Akun"
            ${loginActiveTab === "recovery-request" ? "" : "hidden"}
          >
            <div class="auth-recovery-header">
              <h3 class="auth-recovery-title">Pemulihan Password Akun</h3>
              <button
                type="button"
                class="btn btn-ghost btn-sm"
                data-action="switch-auth-tab"
                data-tab="login"
              >
                Kembali ke Masuk
              </button>
            </div>
            <p class="table-subtext" style="margin-bottom:14px;">
              Masukkan alamat email akun terdaftar untuk mengirim tautan reset password dari Supabase Auth ke kotak masuk Anda.
            </p>
            <form id="recovery-request-form" novalidate>
              <div class="form-group">
                <label for="recovery-email" class="form-label">Email Akun Terdaftar</label>
                <input
                  id="recovery-email"
                  name="recovery_email"
                  type="email"
                  autocomplete="email"
                  class="form-input"
                  placeholder="nama@domain.com"
                />
              </div>
              <button type="submit" class="btn btn-primary" style="width:100%;">Kirim Email Pemulihan</button>
            </form>

            <div class="auth-recovery-box">
              <p class="table-subtext" style="margin-top:0;margin-bottom:10px;">
                Tempel tautan pemulihan dari email Supabase (<code>/auth/v1/verify?token=...</code>) atau URL hasil redirect di browser (<code>#access_token=...</code>) di bawah ini:
              </p>
              <form id="recovery-link-paste-form" novalidate>
                <div class="form-group">
                  <label for="recovery-url-paste" class="form-label">Tautan Pemulihan dari Email</label>
                  <input
                    id="recovery-url-paste"
                    name="recovery_url"
                    type="password"
                    autocomplete="off"
                    class="form-input"
                    placeholder="Tempel tautan pemulihan dari email atau URL redirect"
                  />
                </div>
                <button type="submit" class="btn btn-secondary" style="width:100%;">Gunakan Tautan Pemulihan</button>
              </form>
            </div>
          </section>

          <section
            id="panel-auth-recovery-update"
            aria-label="Atur Password Baru"
            ${loginActiveTab === "recovery-update" ? "" : "hidden"}
          >
            <div class="auth-recovery-header">
              <h3 class="auth-recovery-title">Atur Password Baru (PASSWORD_RECOVERY)</h3>
            </div>
            <p class="table-subtext" style="margin-bottom:14px;">
              Password baru akan diperbarui langsung di Supabase Auth melalui <code>updateUser()</code> tanpa mengubah role atau profil akun Anda.
            </p>
            <form id="recovery-update-form" novalidate>
              <div class="form-group">
                <label for="recovery-new-password" class="form-label">Password Baru</label>
                <input
                  id="recovery-new-password"
                  name="new_password"
                  type="password"
                  autocomplete="new-password"
                  class="form-input"
                  placeholder="Minimal 6 karakter"
                />
              </div>
              <div class="form-group">
                <label for="recovery-confirm-password" class="form-label">Konfirmasi Password Baru</label>
                <input
                  id="recovery-confirm-password"
                  name="confirm_password"
                  type="password"
                  autocomplete="new-password"
                  class="form-input"
                  placeholder="Ulangi password baru"
                />
              </div>
              <div class="auth-recovery-actions">
                <button type="submit" class="btn btn-primary" style="flex:1;">Simpan Password Baru</button>
                <button
                  type="button"
                  class="btn btn-secondary"
                  data-action="cancel-password-recovery"
                >
                  Batalkan
                </button>
              </div>
            </form>
          </section>
        </div>

        ${demoPanelHtml}
      </div>
    `;

    if (pendingAuthNotice && pendingAuthNotice.message) {
      const notice = pendingAuthNotice;
      pendingAuthNotice = null;
      renderAuthFeedback(notice.message, notice.variant || "info");
    }

    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
    const recoveryRequestForm = document.getElementById("recovery-request-form");
    const recoveryLinkPasteForm = document.getElementById("recovery-link-paste-form");
    const recoveryUpdateForm = document.getElementById("recovery-update-form");
    const tabList = document.querySelector(".tabs-nav[role='tablist']");
    if (tabList) {
      tabList.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        loginActiveTab = loginActiveTab === "login" ? "register" : "login";
        renderLoginPage(document.getElementById("main-content")).then(() => {
          document.getElementById(`tab-auth-${loginActiveTab}`)?.focus();
        });
      });
    }
    if (loginForm) {
      loginForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleLoginSubmit();
      });
    }
    if (registerForm) {
      registerForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleRegisterSubmit();
      });
    }
    if (recoveryRequestForm) {
      recoveryRequestForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleRecoveryRequestSubmit();
      });
    }
    if (recoveryLinkPasteForm) {
      recoveryLinkPasteForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleRecoveryLinkPasteSubmit();
      });
    }
    if (recoveryUpdateForm) {
      recoveryUpdateForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleRecoveryUpdateSubmit();
      });
    }
  }

  function renderAuthFeedback(message, variant = "warning") {
    const slot = document.getElementById("auth-feedback-slot");
    if (!slot) return;
    let bannerClass = "notice-banner-warning";
    if (variant === "danger") bannerClass = "notice-banner-danger";
    else if (variant === "success") bannerClass = "notice-banner-success";
    else if (variant === "info") bannerClass = "notice-banner-info";
    slot.innerHTML = `
      <div class="notice-banner ${bannerClass}" role="alert">
        <span>${window.TurnamenUI.escapeHtml(message)}</span>
      </div>
    `;
  }

  async function handleRecoveryRequestSubmit(triggerEl = null) {
    const emailEl = document.getElementById("recovery-email");
    const email = (emailEl?.value || "").trim();
    if (emailEl) emailEl.setAttribute("aria-invalid", email ? "false" : "true");

    if (!email) {
      window.TurnamenUI.showToast("Alamat email wajib diisi.", "warning");
      renderAuthFeedback("Masukkan alamat email akun untuk menerima tautan pemulihan.", "warning");
      return;
    }

    const submitBtn =
      triggerEl || document.querySelector("#recovery-request-form button[type='submit']");
    const redirectTo = getDesktopRecoveryRedirectUrl();
    await withSubmissionGuard("auth:recovery-request", submitBtn, "Mengirim Permintaan...", async () => {
      const res = await window.TurnamenAPI.requestPasswordRecovery(email, redirectTo);
      if (!res.success) {
        window.TurnamenUI.showToast(res.message, "danger");
        renderAuthFeedback(res.message, "danger");
        return;
      }

      const isMockRes = Boolean(res.data && res.data.mode === "mock");
      const infoMsg = isMockRes
        ? "Simulasi mode mock: tidak ada email nyata yang dikirimkan."
        : "Permintaan pemulihan dikirim. Periksa kotak masuk atau spam email Anda, lalu klik tautan pemulihan atau tempel URL redirect di bawah.";
      window.TurnamenUI.showToast(infoMsg, isMockRes ? "info" : "success");
      renderAuthFeedback(infoMsg, isMockRes ? "info" : "success");
    });
  }

  async function handleRecoveryLinkPasteSubmit() {
    const inputEl = document.getElementById("recovery-url-paste");
    const rawValue = (inputEl?.value || "").trim();
    if (inputEl) {
      inputEl.value = "";
      inputEl.setAttribute("aria-invalid", rawValue ? "false" : "true");
    }

    const parsed = parseSupabaseRecoveryUrl(rawValue);
    if (!parsed) {
      const msg =
        "Tautan tidak memuat parameter pemulihan password yang valid (type=recovery dengan token).";
      window.TurnamenUI.showToast(msg, "warning");
      renderAuthFeedback(msg, "warning");
      return;
    }
    if (parsed.errorMessage) {
      window.TurnamenUI.showToast(parsed.errorMessage, "danger");
      renderAuthFeedback(parsed.errorMessage, "danger");
      return;
    }

    pendingRecoverySession = {
      accessToken: parsed.accessToken || "",
      refreshToken: parsed.refreshToken || "",
      tokenHash: parsed.tokenHash || "",
    };
    loginActiveTab = "recovery-update";
    pendingAuthNotice = {
      message: "Tautan pemulihan valid terdeteksi. Silakan masukkan password baru Anda.",
      variant: "success",
    };
    await renderLoginPage(document.getElementById("main-content"));
    document.getElementById("recovery-new-password")?.focus();
  }

  async function handleRecoveryUpdateSubmit(triggerEl = null) {
    const newPassEl = document.getElementById("recovery-new-password");
    const confirmPassEl = document.getElementById("recovery-confirm-password");
    const newPassword = newPassEl?.value || "";
    const confirmPassword = confirmPassEl?.value || "";

    if (newPassEl) {
      newPassEl.setAttribute(
        "aria-invalid",
        newPassword && newPassword.length >= 6 ? "false" : "true"
      );
    }
    if (confirmPassEl) {
      confirmPassEl.setAttribute(
        "aria-invalid",
        confirmPassword && confirmPassword === newPassword ? "false" : "true"
      );
    }

    if (!pendingRecoverySession || (!pendingRecoverySession.accessToken && !pendingRecoverySession.tokenHash)) {
      const msg = "Sesi pemulihan password tidak ditemukan. Buka tautan dari email atau minta pemulihan baru.";
      window.TurnamenUI.showToast(msg, "danger");
      renderAuthFeedback(msg, "danger");
      return;
    }

    if (!newPassword.trim() || newPassword.length < 6) {
      const msg = "Password baru minimal terdiri dari 6 karakter.";
      window.TurnamenUI.showToast(msg, "warning");
      renderAuthFeedback(msg, "warning");
      return;
    }

    if (newPassword !== confirmPassword) {
      const msg = "Konfirmasi password baru tidak sesuai.";
      window.TurnamenUI.showToast(msg, "warning");
      renderAuthFeedback(msg, "warning");
      return;
    }

    const submitBtn =
      triggerEl || document.querySelector("#recovery-update-form button[type='submit']");
    await withSubmissionGuard("auth:recovery-update", submitBtn, "Menyimpan Password...", async () => {
      const res = await window.TurnamenAPI.updatePasswordWithRecoveryToken(
        pendingRecoverySession,
        newPassword
      );
      if (newPassEl) newPassEl.value = "";
      if (confirmPassEl) confirmPassEl.value = "";

      if (!res.success) {
        if (res.error && res.error.code === "UNAUTHORIZED") {
          pendingRecoverySession = null;
        }
        window.TurnamenUI.showToast(res.message, "danger");
        renderAuthFeedback(res.message, "danger");
        return;
      }

      pendingRecoverySession = null;
      loginActiveTab = "login";
      pendingAuthNotice = {
        message: "Password akun berhasil diperbarui melalui Supabase Auth. Silakan login menggunakan password baru Anda.",
        variant: "success",
      };
      window.TurnamenUI.showToast(
        "Password berhasil diperbarui. Silakan masuk dengan password baru.",
        "success"
      );
      await renderLoginPage(document.getElementById("main-content"));
      document.getElementById("login-email")?.focus();
    });
  }

  async function handleLoginSubmit(triggerEl = null) {
    const emailEl = document.getElementById("login-email");
    const passwordEl = document.getElementById("login-password");
    const email = (emailEl?.value || "").trim();
    const password = passwordEl?.value || "";

    if (emailEl) emailEl.setAttribute("aria-invalid", email ? "false" : "true");
    if (passwordEl) passwordEl.setAttribute("aria-invalid", password ? "false" : "true");

    if (!email || !password) {
      window.TurnamenUI.showToast("Email dan password wajib diisi.", "warning");
      renderAuthFeedback("Email dan password wajib diisi untuk masuk.", "warning");
      return;
    }

    const submitBtn = triggerEl || document.querySelector("#login-form button[type='submit']");
    await withSubmissionGuard("auth:login", submitBtn, "Memeriksa Akun...", async () => {
      const res = await window.TurnamenAPI.login(email, password);
      if (!res.success) {
        window.TurnamenUI.showToast(res.message, "danger");
        renderAuthFeedback(res.message, "danger");
        return;
      }

      const data = res.data || {};
      if (data.requires_email_confirmation === true || !data.token || !data.user) {
        updateUserTopbar(getCurrentUserSafe());
        const infoMsg =
          "Akun memerlukan konfirmasi email sebelum sesi dibuat. Periksa kotak masuk email Anda lalu login kembali.";
        window.TurnamenUI.showToast(infoMsg, "warning");
        renderAuthFeedback(infoMsg, "warning");
        if (passwordEl) passwordEl.value = "";
        return;
      }

      resetRoleScopedUiState();
      updateUserTopbar(data.user);
      window.TurnamenUI.showToast(
        `Selamat datang, ${data.user.full_name || data.user.username || data.user.email}.`,
        "success"
      );
      await navigateTo("dashboard");
    });
  }

  async function handleRegisterSubmit(triggerEl = null) {
    const payload = {
      full_name: (document.getElementById("reg-fullname")?.value || "").trim(),
      username: (document.getElementById("reg-username")?.value || "").trim(),
      role: document.getElementById("reg-role")?.value || "player",
      email: (document.getElementById("reg-email")?.value || "").trim(),
      password: document.getElementById("reg-password")?.value || "",
    };

    if (!payload.full_name || !payload.username || !payload.email || payload.password.length < 6) {
      window.TurnamenUI.showToast(
        "Lengkapi seluruh field pendaftaran (password minimal 6 karakter).",
        "warning"
      );
      renderAuthFeedback(
        "Nama lengkap, username, email valid, dan password minimal 6 karakter wajib diisi.",
        "warning"
      );
      return;
    }

    const submitBtn = triggerEl || document.querySelector("#register-form button[type='submit']");
    await withSubmissionGuard("auth:register", submitBtn, "Mendaftarkan...", async () => {
      const res = await window.TurnamenAPI.register(payload);
      if (!res.success) {
        window.TurnamenUI.showToast(res.message, "danger");
        renderAuthFeedback(res.message, "danger");
        return;
      }

      const data = res.data || {};
      if (data.requires_email_confirmation === true || !data.token || !data.user) {
        updateUserTopbar(getCurrentUserSafe());
        loginActiveTab = "login";
        await renderLoginPage(document.getElementById("main-content"));
        renderAuthFeedback(
          "Registrasi berhasil. Silakan konfirmasi email Anda terlebih dahulu sebelum masuk.",
          "warning"
        );
        window.TurnamenUI.showToast(
          "Registrasi berhasil. Konfirmasi email diperlukan sebelum login.",
          "info"
        );
        return;
      }

      resetRoleScopedUiState();
      updateUserTopbar(data.user);
      window.TurnamenUI.showToast(
        `Akun ${data.user.username || data.user.email} berhasil dibuat.`,
        "success"
      );
      await navigateTo("dashboard");
    });
  }

  async function handleLogout(triggerEl = null) {
    try {
      await withSubmissionGuard(
        "auth:logout",
        triggerEl,
        "Keluar...",
        async () => {
          await window.TurnamenAPI.logout();
          resetRoleScopedUiState();
          updateUserTopbar(getCurrentUserSafe());
          window.TurnamenUI.showToast(
            "Anda telah keluar dari sesi aktif dan beralih ke mode Tamu (Public Guest).",
            "info"
          );
          await navigateTo("login");
        },
        { skipRestoreHtml: true }
      );
    } finally {
      updateUserTopbar(getCurrentUserSafe());
    }
  }

  async function quickSwitchRole(roleName) {
    await applySimulatedRoleChange(roleName, "quick");
  }

  // =========================================================================
  // DELEGATED EVENT DISPATCHER
  // =========================================================================
  function bindDelegatedEvents() {
    const main = document.getElementById("main-content");
    const modal = document.getElementById("app-modal-backdrop");

    const handleActionEvent = (e) => {
      const target = e.target && e.target.closest("[data-action]");
      if (!target) return;
      const action = target.getAttribute("data-action");
      const id = target.getAttribute("data-id") || "";
      const tournamentId = target.getAttribute("data-tournament-id") || "";

      switch (action) {
        case "go-page": {
          const page = target.getAttribute("data-page") || "dashboard";
          navigateTo(page, tournamentId ? { tournamentId } : {});
          break;
        }
        case "browse-game-tournaments":
          tournamentFilterState.gameId = id;
          tournamentFilterState.status = "";
          navigateTo("tournament-list");
          break;
        case "retry-page":
          navigateTo(currentPage);
          break;
        case "retry-games":
          ensureGamesLoaded(true).then(() => navigateTo(currentPage));
          break;
        case "open-create-tournament":
          openCreateTournamentModal();
          break;
        case "submit-create-tournament":
          submitCreateTournament(target);
          break;
        case "open-edit-tournament":
          openEditTournamentModal(id);
          break;
        case "submit-edit-tournament":
          submitEditTournament(id, target);
          break;
        case "confirm-delete-tournament":
          confirmDeleteTournament(id);
          break;
        case "execute-delete-tournament":
          executeDeleteTournament(id, target);
          break;
        case "register-selected-team":
          registerSelectedTeam(id, target);
          break;
        case "verify-registration": {
          const nextStatus = target.getAttribute("data-status") || "approved";
          verifyRegistration(id, nextStatus, tournamentId, target);
          break;
        }
        case "open-create-team":
          openCreateTeamModal();
          break;
        case "submit-create-team":
          submitCreateTeam(target);
          break;
        case "open-team-detail":
          openTeamDetailModal(id);
          break;
        case "open-edit-team":
          openEditTeamModal(id);
          break;
        case "submit-edit-team":
          submitEditTeam(id, target);
          break;
        case "open-add-member":
          openAddMemberModal(id);
          break;
        case "submit-add-member":
          submitAddMember(id, target);
          break;
        case "submit-score":
          submitScore(id, tournamentId, target);
          break;
        case "open-override-score":
          openOverrideScoreModal({
            id,
            tournamentId,
            teamA: target.getAttribute("data-team-a") || "Team A",
            teamB: target.getAttribute("data-team-b") || "Team B",
            scoreA: Number(target.getAttribute("data-score-a") || 0),
            scoreB: Number(target.getAttribute("data-score-b") || 0),
            maxWin: Number(target.getAttribute("data-max") || 3),
          });
          break;
        case "submit-override-score":
          submitOverrideScore(id, tournamentId, target);
          break;
        case "confirm-regenerate-bracket":
          confirmRegenerateBracket(id);
          break;
        case "regenerate-bracket":
          regenerateBracket(id, target);
          break;
        case "open-announcement-modal":
          openAnnouncementModal(id);
          break;
        case "submit-announcement":
          submitAnnouncement(id, target);
          break;
        case "reset-tournament-filters":
          tournamentFilterState = { status: "", gameId: "", search: "" };
          navigateTo("tournament-list");
          break;
        case "reset-team-filters":
          teamFilterState = { gameId: "", search: "" };
          navigateTo("team-management");
          break;
        case "reset-match-filters":
          matchRoundFilter = "";
          matchStatusFilter = "";
          navigateTo("match-management");
          break;
        case "reset-announcement-filters":
          announcementPriorityFilter = "";
          navigateTo("announcements");
          break;
        case "switch-auth-tab": {
          const nextTab = target.getAttribute("data-tab") || "login";
          loginActiveTab = nextTab === "register" ? "register" : "login";
          renderLoginPage(document.getElementById("main-content")).then(() => {
            document.getElementById(`tab-auth-${loginActiveTab}`)?.focus();
          });
          break;
        }
        case "open-password-recovery": {
          loginActiveTab = "recovery-request";
          renderLoginPage(document.getElementById("main-content")).then(() => {
            document.getElementById("recovery-email")?.focus();
          });
          break;
        }
        case "cancel-password-recovery": {
          pendingRecoverySession = null;
          loginActiveTab = "login";
          renderLoginPage(document.getElementById("main-content")).then(() => {
            document.getElementById("login-email")?.focus();
          });
          break;
        }
        case "quick-switch-role": {
          const role = target.getAttribute("data-role") || "";
          quickSwitchRole(role);
          break;
        }
        case "logout":
          handleLogout(target);
          break;
        case "submit-update-profile":
          submitUpdateProfile(target);
          break;
        case "assign-user-role":
          submitAssignUserRole(id, target);
          break;
        case "open-create-game":
          openCreateGameModal();
          break;
        case "open-edit-game":
          openEditGameModal(id);
          break;
        case "submit-create-game":
          submitGameModal("", target);
          break;
        case "submit-edit-game":
          submitGameModal(id, target);
          break;
        case "trigger-game-artwork-picker": {
          const inputEl = document.getElementById(`artwork-file-input-${id}`);
          if (inputEl && typeof inputEl.click === "function") {
            inputEl.click();
          }
          break;
        }
        case "clear-game-artwork-preview":
          pendingArtworkDrafts.delete(id);
          artworkUploadState.delete(id);
          navigateTo("game-management");
          break;
        case "save-game-artwork":
          saveGameArtworkDraft(id, target);
          break;
        case "confirm-restore-game-artwork":
          openRestoreGameArtworkConfirm(id);
          break;
        case "submit-restore-game-artwork":
          restoreGameArtworkConfirmed(id, target);
          break;
        case "add-tournament-staff":
          submitAddTournamentStaff(id, target);
          break;
        case "remove-tournament-staff":
          submitRemoveTournamentStaff(tournamentId, id, target);
          break;
        default:
          break;
      }
    };

    const handleChangeEvent = (e) => {
      const target = e.target;
      if (!target) return;
      const action = target.getAttribute("data-action");
      if (action === "select-active-tournament") {
        if (target.value) {
          navigateTo(currentPage, { tournamentId: target.value });
        }
        return;
      }
      if (action === "game-artwork-file-input") {
        handleArtworkFileInputChange(target);
      }
    };

    if (main) {
      main.addEventListener("click", handleActionEvent);
      main.addEventListener("change", handleChangeEvent);
    }
    if (modal) {
      modal.addEventListener("click", handleActionEvent);
    }
  }

  window.TurnamenApp = {
    initApp,
    navigateTo,
    updateRuntimeIndicators,
    updateUserTopbar,
    filterTournaments(status) {
      tournamentFilterState.status = String(status || "");
      navigateTo("tournament-list");
    },
    openCreateTournamentModal,
    submitCreateTournament,
    openEditTournamentModal,
    submitEditTournament,
    registerSelectedTeam,
    verifyRegistration,
    openCreateTeamModal,
    submitCreateTeam,
    openTeamDetailModal,
    openEditTeamModal,
    submitEditTeam,
    openAddMemberModal,
    submitAddMember,
    submitScore,
    submitOverrideScore,
    regenerateBracket,
    openAnnouncementModal,
    submitAnnouncement,
    handleLoginSubmit,
    handleRegisterSubmit,
    handleRecoveryRequestSubmit,
    handleRecoveryLinkPasteSubmit,
    handleRecoveryUpdateSubmit,
    parseSupabaseRecoveryUrl,
    getDesktopRecoveryRedirectUrl,
    handleLogout,
    quickSwitchRole,
    submitUpdateProfile,
    submitAssignUserRole,
    openCreateGameModal,
    openEditGameModal,
    submitGameModal,
    handleArtworkFileInputChange,
    inspectAndPrepareArtworkFile,
    saveGameArtworkDraft,
    openRestoreGameArtworkConfirm,
    restoreGameArtworkConfirmed,
    submitAddTournamentStaff,
    submitRemoveTournamentStaff,
  };

  document.addEventListener("DOMContentLoaded", initApp);
})(window, document);
