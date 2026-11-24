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
  let selectedCaptainTeamId = "";
  let tournamentFilterState = { status: "", gameId: "", search: "" };
  let teamFilterState = { gameId: "", search: "" };
  let matchRoundFilter = "";
  let announcementPriorityFilter = "";

  const gamesState = { items: [], loaded: false, error: null };
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
    window.requestAnimationFrame(() => {
      const stageEl = document.getElementById("bracket-stage");
      if (stageEl) drawBracketConnectors(stageEl);
    });
    if (!bracketResizeListenerBound) {
      bracketResizeListenerBound = true;
      window.addEventListener("resize", () => {
        if (bracketResizeTimer) window.clearTimeout(bracketResizeTimer);
        bracketResizeTimer = window.setTimeout(() => {
          const stageEl = document.getElementById("bracket-stage");
          if (stageEl) drawBracketConnectors(stageEl);
        }, 90);
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
        if (role === "super_admin" || role === "committee") return true;
        if (role === "organizer") {
          return !context.tournament || context.tournament.organizer_id === user.id;
        }
        return false;
      default:
        return false;
    }
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
  async function initApp() {
    bindSidebarNavigation();
    bindResponsiveSidebar();
    bindRoleSwitcher();
    bindTopbarAuthButton();
    bindDelegatedEvents();

    const healthRes = await window.TurnamenAPI.getHealth();
    updateRuntimeIndicators(healthRes);

    await ensureGamesLoaded(true);
    await navigateTo("dashboard");
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

  function bindRoleSwitcher() {
    const switcher = document.getElementById("topbar-role-switcher");
    if (!switcher) return;
    switcher.addEventListener("change", (e) => {
      if (!isMockMode()) {
        window.TurnamenUI.showToast(
          "Simulasi role hanya tersedia pada APP_MODE=mock.",
          "warning"
        );
        updateRuntimeIndicators(null);
        return;
      }
      const user = window.TurnamenAPI.setSimulatedRole(e.target.value);
      updateUserTopbar(user);
      if (!user) {
        window.TurnamenUI.showToast("Gagal mengubah peran simulasi.", "warning");
        return;
      }
      window.TurnamenUI.showToast(
        `Peran simulasi diubah ke: ${user.full_name} (${user.role})`,
        "info"
      );
      navigateTo("dashboard");
    });
  }

  function bindTopbarAuthButton() {
    const btn = document.getElementById("topbar-auth-action");
    if (!btn) return;
    btn.addEventListener("click", () => {
      if (getCurrentUserSafe()) {
        handleLogout();
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

    if (switcher && user && user.role && isMock) {
      switcher.value = user.role;
    }

    if (authBtn) {
      authBtn.hidden = !user;
      authBtn.textContent = "Keluar";
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
      return { error: null, list: [], active: null };
    }

    const selectedId = getRuntimeState().selectedTournamentId;
    let active = list.find((t) => t.id === selectedId);
    if (!active) {
      active = list.find((t) => t.status === "ongoing") || list[0];
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
      container.innerHTML = window.TurnamenUI.renderAccessDeniedState(
        access.title,
        access.message,
        access.actionHtml
      );
      return;
    }

    container.innerHTML = window.TurnamenUI.renderLoadingState(
      `Memuat ${PAGE_TITLES[targetPage] || "halaman"}...`
    );

    const isStale = () => seq !== navigationSeq;

    switch (targetPage) {
      case "dashboard":
        await renderDashboard(container, isStale);
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
        await renderDashboard(container, isStale);
    }
  }

  // =========================================================================
  // 1. ROLE-BASED DASHBOARD DISPATCHER & 5+ ROLE VIEWS
  // =========================================================================
  async function renderDashboard(container, isStale) {
    await ensureGamesLoaded(false);
    if (isStale()) return;

    const [tourRes, teamsRes] = await Promise.all([
      window.TurnamenAPI.getTournaments(),
      window.TurnamenAPI.getTeams(),
    ]);
    if (isStale()) return;

    if (!tourRes.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(tourRes.message, "retry-page");
      return;
    }

    const tournaments = Array.isArray(tourRes.data) ? tourRes.data : [];
    const teamsOk = Boolean(teamsRes.success && Array.isArray(teamsRes.data));
    const teams = teamsOk ? teamsRes.data : [];
    const ctx = await resolveActiveTournamentContext(tournaments);
    if (isStale()) return;

    let activeMatches = [];
    let activeAnnouncements = [];
    let activeReport = null;
    let activeRegs = [];

    if (ctx.active) {
      const [matchRes, annRes, reportRes, regRes] = await Promise.all([
        window.TurnamenAPI.getTournamentMatches(ctx.active.id),
        window.TurnamenAPI.getAnnouncements(ctx.active.id),
        window.TurnamenAPI.getTournamentReport(ctx.active.id),
        window.TurnamenAPI.getTournamentRegistrations(ctx.active.id),
      ]);
      if (isStale()) return;
      if (matchRes.success && matchRes.data && Array.isArray(matchRes.data.matches)) {
        activeMatches = matchRes.data.matches;
      }
      if (annRes.success && Array.isArray(annRes.data)) {
        activeAnnouncements = [...annRes.data].sort(
          (a, b) => Number(Boolean(b.is_pinned)) - Number(Boolean(a.is_pinned))
        );
      }
      if (reportRes.success && reportRes.data) {
        activeReport = reportRes.data;
      }
      if (regRes.success && Array.isArray(regRes.data)) {
        activeRegs = regRes.data;
      }
    }

    const roleKey = getActiveRoleKey();
    const sharedData = {
      tournaments,
      teams,
      teamsOk,
      ctx,
      activeMatches,
      activeAnnouncements,
      activeReport,
      activeRegs,
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
      case "super_admin":
        renderSuperAdminDashboard(container, sharedData);
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
          .map((g, idx) => {
            const tourCount = tournaments.filter((t) => t.game_id === g.id).length;
            return `
            <article class="game-poster-card">
              <div class="game-poster-art">${window.TurnamenUI.renderGameArtwork(g, "", { eager: idx < 2 })}</div>
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
              (t.status === "open_registration" || t.status === "draft") &&
              teams.some((tm) => ownedTeamIds.includes(tm.id) && tm.game_id === t.game_id);

            return `
            <article class="tournament-card">
              <div class="tournament-card-art">
                ${window.TurnamenUI.renderGameArtwork(game, `BO${t.best_of || 3} SINGLE ELIM`)}
                <div class="tournament-card-overlay-badge">
                  ${window.TurnamenUI.renderStatusBadge(t.status)}
                </div>
              </div>
              <div class="tournament-card-body">
                <h3 class="tournament-card-title">${window.TurnamenUI.escapeHtml(t.title)}</h3>
                <div class="tournament-card-meta">
                  <span>Hadiah: <strong class="tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</strong></span>
                  <span>Venue: <strong>${window.TurnamenUI.escapeHtml(t.venue || "Online")}</strong></span>
                  <span>Mulai: <strong class="tabular-nums">${window.TurnamenUI.formatDateOnly(t.start_date)}</strong></span>
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
            ${window.TurnamenUI.renderGameArtwork(featuredGame, `HADIAH ${window.TurnamenUI.formatRupiah(featured.prize_pool)}`, { eager: true })}
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
      if (
        (tournament.status === "open_registration" || tournament.status === "draft") &&
        eligible.length > 0
      ) {
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
                ${window.TurnamenUI.renderGameChip(activeTeam.game_name)}
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
                    ${window.TurnamenUI.renderGameArtwork(tGame, tournament.game_name)}
                    <div class="tournament-card-overlay-badge">
                      ${window.TurnamenUI.renderStatusBadge(reg.status)}
                    </div>
                  </div>
                  <div class="participation-card-body">
                    <div class="participation-card-head">
                      ${window.TurnamenUI.renderTeamEmblem(reg.team_tag, 38)}
                      <div>
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
    const { tournaments, ctx, activeReport, activeRegs, activeAnnouncements } = data;
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

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Kontrol Turnamen &amp; Operasional Organizer</h2>
          <p>Kelola turnamen milik Anda, verifikasi peserta, susun bracket, dan pantau pengesahan skor.</p>
        </div>
        <div class="page-actions">
          ${
            ctx.active
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
                  <th>Turnamen</th>
                  <th>Game</th>
                  <th>Kuota Terisi</th>
                  <th>Prize Pool</th>
                  <th>Status</th>
                  <th>Aksi Pengelolaan</th>
                </tr>
              </thead>
              <tbody>
                ${myTournaments
                  .map((t) => {
                    const max = Number(t.max_teams || 0);
                    const app = Number(t.approved_teams_count || 0);
                    const pct = max > 0 ? Math.round((app / max) * 100) : 0;
                    const canDelete = t.status !== "ongoing" && t.status !== "completed";
                    return `
                    <tr>
                      <td>
                        <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>
                        <div class="table-subtext">${window.TurnamenUI.escapeHtml(t.venue || "Online")} | Bo${t.best_of}</div>
                      </td>
                      <td>${window.TurnamenUI.renderGameChip(t.game_name)}</td>
                      <td style="min-width:140px;">
                        <div class="tabular-nums" style="font-size:12px; margin-bottom:4px;">${app} / ${max} Tim</div>
                        ${window.TurnamenUI.renderProgressBar(pct, `Kuota ${t.title}`)}
                      </td>
                      <td class="tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</td>
                      <td>${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                      <td>
                        <div class="row-actions">
                          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Peserta</button>
                          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="match-management" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Skor</button>
                          <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Bracket</button>
                          <button type="button" class="btn btn-ghost btn-sm" data-action="open-edit-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}" aria-label="Edit ${window.TurnamenUI.escapeHtml(t.title)}">${window.TurnamenUI.icon("edit", 14)}</button>
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
              ctx.active
                ? `<button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Kelola Peserta</button>`
                : ""
            }
          </div>
          ${
            pendingActiveRegs.length > 0
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
                          <button type="button" class="btn btn-success btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="approved">Setujui</button>
                          <button type="button" class="btn btn-danger btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="rejected">Tolak</button>
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
    const { ctx, activeMatches, activeRegs, activeAnnouncements, activeReport } = data;
    const playableMatches = activeMatches.filter(
      (m) => m.team_a_id && m.team_b_id && m.status !== "completed"
    );
    const completedMatches = activeMatches.filter((m) => m.status === "completed");
    const pendingRegs = activeRegs.filter((r) => r.status === "pending");

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      ${renderTournamentContextBar(
        ctx.list,
        ctx.active,
        ctx.active
          ? `
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Bracket</button>
          <button type="button" class="btn btn-primary btn-sm" data-action="open-announcement-modal" data-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">+ Buat Pengumuman</button>
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

      <div class="grid-4">
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Match Siap Disahkan</div>
          <div class="metric-value">${playableMatches.length}</div>
          <div class="metric-note">Menunggu hasil skor pertandingan</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Match Terkunci</div>
          <div class="metric-value">${completedMatches.length}</div>
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
                      <td>
                        <div class="score-inline-form">
                          <label for="score-a-${window.TurnamenUI.escapeHtml(m.id)}" class="sr-only">Skor ${window.TurnamenUI.escapeHtml(m.team_a_name)}</label>
                          <input id="score-a-${window.TurnamenUI.escapeHtml(m.id)}" type="number" min="0" max="${maxWin}" value="${m.score_a}" class="form-input tabular-nums score-inline-input" />
                          <span aria-hidden="true">:</span>
                          <label for="score-b-${window.TurnamenUI.escapeHtml(m.id)}" class="sr-only">Skor ${window.TurnamenUI.escapeHtml(m.team_b_name)}</label>
                          <input id="score-b-${window.TurnamenUI.escapeHtml(m.id)}" type="number" min="0" max="${maxWin}" value="${m.score_b}" class="form-input tabular-nums score-inline-input" />
                          <button type="button" class="btn btn-primary btn-sm" data-action="submit-score" data-id="${window.TurnamenUI.escapeHtml(m.id)}">Sahkan</button>
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
            <h3 class="card-title">Antrean Verifikasi Peserta</h3>
            <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail">Panel Peserta</button>
          </div>
          ${
            pendingRegs.length > 0
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
                          <button type="button" class="btn btn-success btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="approved">Setujui</button>
                          <button type="button" class="btn btn-danger btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="rejected">Tolak</button>
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
  function renderSuperAdminDashboard(container, data) {
    const { tournaments, teams, teamsOk, ctx, activeReport } = data;
    const state = getRuntimeState();
    const ongoingCount = tournaments.filter((t) => t.status === "ongoing").length;
    const openCount = tournaments.filter((t) => t.status === "open_registration").length;
    const totalRosterPlayers = teams.reduce(
      (sum, tm) => sum + Number(tm.member_count ?? (tm.members ? tm.members.length : 0)),
      0
    );
    const summary = activeReport && activeReport.summary ? activeReport.summary : null;

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Administrasi Sistem Turnamen.in</h2>
          <p>Kontrol penuh lintas organizer, katalog game, tim esports, dan audit operasional.</p>
        </div>
        <div class="page-actions">
          <button type="button" class="btn btn-secondary" data-action="open-create-team">${window.TurnamenUI.icon("plus", 14)}<span>Buat Tim</span></button>
          <button type="button" class="btn btn-primary" data-action="open-create-tournament">${window.TurnamenUI.icon("plus", 14)}<span>Buat Turnamen</span></button>
        </div>
      </div>

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Total Turnamen Sistem</div>
          <div class="metric-value">${tournaments.length}</div>
          <div class="metric-note">${ongoingCount} berlangsung, ${openCount} buka pendaftaran</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Cabang Game Aktif</div>
          <div class="metric-value">${gamesState.items.length}</div>
          <div class="metric-note">Terdaftar pada katalog sistem</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Tim &amp; Pemain</div>
          <div class="metric-value">${teamsOk ? teams.length : "-"}</div>
          <div class="metric-note">${teamsOk ? `${totalRosterPlayers} total pemain pada roster` : "Data tim gagal dimuat"}</div>
        </div>
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Progres Turnamen Aktif</div>
          <div class="metric-value">${summary ? `${summary.completed_matches} / ${summary.total_matches}` : "0 / 0"}</div>
          <div class="metric-note">${summary ? `${summary.completion_percentage}% selesai` : "Belum ada pertandingan"}</div>
        </div>
      </div>

      <div class="workspace-split">
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Kontrol Seluruh Turnamen</h3>
              <p class="card-subtitle">Akses administrasi penuh untuk mengubah, mengaudit, atau memantau bracket.</p>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-list">Kelola Lengkap</button>
          </div>
          ${
            tournaments.length === 0
              ? window.TurnamenUI.renderEmptyState("Belum Ada Turnamen", "Sistem belum memiliki data turnamen.")
              : `
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Turnamen</th>
                    <th>Peserta</th>
                    <th>Status</th>
                    <th>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  ${tournaments
                    .map(
                      (t) => `
                    <tr>
                      <td>
                        <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>
                        <div class="table-subtext">${window.TurnamenUI.escapeHtml(t.game_name)} | ${window.TurnamenUI.escapeHtml(t.venue || "Online")}</div>
                      </td>
                      <td class="tabular-nums">${t.approved_teams_count || 0} / ${t.max_teams}</td>
                      <td>${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                      <td>
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

        <div class="stack-md">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Distribusi Cabang Game</h3>
              <span class="badge badge-info">Catalog</span>
            </div>
            ${
              gamesState.items.length > 0
                ? `
              <div class="kv-list">
                ${gamesState.items
                  .map((g) => {
                    const gTours = tournaments.filter((t) => t.game_id === g.id).length;
                    const gTeams = teams.filter((tm) => tm.game_id === g.id).length;
                    return `
                    <div class="kv-item">
                      <span class="kv-label">${window.TurnamenUI.renderGameChip(g.name, g.slug)}</span>
                      <span class="kv-value tabular-nums">${gTours} Turnamen | ${gTeams} Tim</span>
                    </div>
                  `;
                  })
                  .join("")}
              </div>
            `
                : window.TurnamenUI.renderEmptyState("Game Kosong", "Belum ada cabang game aktif.")
            }
          </div>

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
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Jejak Audit Aktivitas Sistem (${window.TurnamenUI.escapeHtml(ctx.active ? ctx.active.title : "Turnamen Aktif")})</h3>
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="reports">Laporan Lengkap</button>
        </div>
        ${
          activeReport && Array.isArray(activeReport.recent_activity) && activeReport.recent_activity.length > 0
            ? `
          <div class="table-container">
            <table class="data-table">
              <thead><tr><th>Aksi</th><th>Entitas</th><th>Waktu</th></tr></thead>
              <tbody>
                ${activeReport.recent_activity
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
            : window.TurnamenUI.renderEmptyState("Belum Ada Aktivitas", "Belum ada log audit pada turnamen aktif.")
        }
      </div>
    `;
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
          ${window.TurnamenUI.renderGameArtwork(featuredGame, "PUBLIC ARENA", { eager: true })}
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
    await ensureGamesLoaded(false);
    if (isStale()) return;

    const apiFilters = {};
    if (tournamentFilterState.status) apiFilters.status = tournamentFilterState.status;
    if (tournamentFilterState.gameId) apiFilters.game_id = tournamentFilterState.gameId;

    const [res, teamsRes] = await Promise.all([
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
    if (list.length === 0) {
      return `
        <div class="card">
          ${window.TurnamenUI.renderEmptyState(
            "Tidak Ada Turnamen Ditemukan",
            rawTotal === 0
              ? "Belum ada turnamen tersedia. Buat turnamen baru atau ubah filter pencarian."
              : "Tidak ada turnamen yang cocok dengan kata kunci pencarian saat ini.",
            canCreate
              ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-tournament">Buat Turnamen Pertama</button>`
              : ""
          )}
        </div>
      `;
    }

    if (competitiveView) {
      return renderTournamentDiscoveryCards(list, gamesById, { ownedTeamIds, teams });
    }

    return `
      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Judul Turnamen</th>
                <th>Game</th>
                <th>Format</th>
                <th>Kuota Tim</th>
                <th>Total Hadiah</th>
                <th>Status</th>
                <th>Aksi</th>
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
                  return `
                  <tr>
                    <td>
                      <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>
                      <div class="table-subtext">${window.TurnamenUI.escapeHtml(t.venue || "Online")} | ${window.TurnamenUI.formatDateOnly(t.start_date)}</div>
                    </td>
                    <td>${window.TurnamenUI.renderGameChip(t.game_name)}</td>
                    <td class="tabular-nums">Single Elim (Bo${t.best_of})</td>
                    <td class="tabular-nums">${t.approved_teams_count || 0} / ${t.max_teams} Tim</td>
                    <td class="tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</td>
                    <td>${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                    <td>
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
    const games = await ensureGamesLoaded(false);
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

  async function submitCreateTournament() {
    const payload = {
      title: (document.getElementById("new-tour-title")?.value || "").trim(),
      game_id: document.getElementById("new-tour-game")?.value || "",
      max_teams: Number(document.getElementById("new-tour-max-teams")?.value || 8),
      best_of: Number(document.getElementById("new-tour-bo")?.value || 3),
      registration_fee: Number(document.getElementById("new-tour-fee")?.value || 0),
      prize_pool: Number(document.getElementById("new-tour-prize")?.value || 0),
      venue: (document.getElementById("new-tour-venue")?.value || "Online").trim(),
      start_date: `${document.getElementById("new-tour-start")?.value || "2026-12-01"}T10:00:00+07:00`,
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
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Turnamen baru berhasil dibuat.", "success");
    await navigateTo("tournament-list");
  }

  async function openEditTournamentModal(tournamentId) {
    const res = await window.TurnamenAPI.getTournamentById(tournamentId);
    if (!res.success || !res.data) {
      window.TurnamenUI.showToast(res.message || "Gagal memuat detail turnamen.", "danger");
      return;
    }
    const t = res.data;
    if (!canPerform("tournament:edit", { tournament: t })) {
      window.TurnamenUI.showToast("Anda tidak memiliki izin mengubah turnamen ini.", "danger");
      return;
    }

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
            <select id="edit-tour-status" class="form-select">
              <option value="draft" ${t.status === "draft" ? "selected" : ""}>Draft</option>
              <option value="open_registration" ${t.status === "open_registration" ? "selected" : ""}>Pendaftaran Dibuka</option>
              <option value="registration_closed" ${t.status === "registration_closed" ? "selected" : ""}>Pendaftaran Ditutup</option>
              <option value="ongoing" ${t.status === "ongoing" ? "selected" : ""}>Sedang Berlangsung</option>
              <option value="completed" ${t.status === "completed" ? "selected" : ""}>Selesai</option>
              <option value="cancelled" ${t.status === "cancelled" ? "selected" : ""}>Dibatalkan</option>
            </select>
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

  async function submitEditTournament(tournamentId) {
    const payload = {
      title: (document.getElementById("edit-tour-title")?.value || "").trim(),
      status: document.getElementById("edit-tour-status")?.value || "open_registration",
      venue: (document.getElementById("edit-tour-venue")?.value || "Online").trim(),
      max_teams: Number(document.getElementById("edit-tour-max-teams")?.value || 8),
      prize_pool: Number(document.getElementById("edit-tour-prize")?.value || 0),
      description: (document.getElementById("edit-tour-desc")?.value || "").trim(),
    };
    const res = await window.TurnamenAPI.updateTournament(tournamentId, payload);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Data turnamen berhasil diperbarui.", "success");
    await navigateTo(currentPage);
  }

  function confirmDeleteTournament(tournamentId) {
    window.TurnamenUI.openModal({
      title: "Konfirmasi Hapus Turnamen",
      bodyHtml: `
        <p style="margin:0; color:var(--text-secondary);">
          Apakah Anda yakin ingin menghapus turnamen ini? Turnamen berstatus <code>ongoing</code> atau <code>completed</code> tidak dapat dihapus oleh sistem.
        </p>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-danger" data-action="execute-delete-tournament" data-id="${window.TurnamenUI.escapeHtml(tournamentId)}">Hapus Turnamen</button>
      `,
    });
  }

  async function executeDeleteTournament(tournamentId) {
    const res = await window.TurnamenAPI.deleteTournament(tournamentId);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Turnamen berhasil dihapus.", "success");
    await navigateTo("tournament-list");
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
    const gamesById = buildGameLookup();
    const heroGame = gamesById[t.game_id] || { name: t.game_name, slug: t.game_name };
    const teamsById = {};
    teams.forEach((tm) => {
      teamsById[tm.id] = tm;
    });
    const canVerify = canPerform("registration:verify", { tournament: t });
    const canRegister =
      canPerform("registration:create") &&
      (t.status === "open_registration" || t.status === "draft");
    const eligibleTeams = canRegister ? getEligibleTeamsForRegistration(teams, t, regs) : [];

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
          ${window.TurnamenUI.renderGameArtwork(heroGame, "", { eager: true, hideLabels: true })}
        </div>
        <div class="tournament-detail-hero-scrim" aria-hidden="true"></div>
        <div class="tournament-detail-hero-content">
          <div>
            <div class="tournament-detail-hero-badges">
              ${window.TurnamenUI.renderGameChip(t.game_name, heroGame.slug)}
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
          <div class="metric-note">Total Pendaftar: ${t.registered_teams_count || regs.length}</div>
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
            <h3 class="card-title">Daftar Tim Peserta &amp; Verifikasi Registrasi</h3>
            <p class="card-subtitle">Registrasi tim berstatus disetujui akan masuk ke bagan bracket.</p>
          </div>
          ${registrationControlHtml}
        </div>

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
                    canVerify || r.notes
                      ? `
                    <div class="participant-card-foot">
                      <span class="table-subtext">${window.TurnamenUI.escapeHtml(r.notes || "Terverifikasi")}</span>
                      ${
                        canVerify
                          ? `
                        <div class="row-actions">
                          <button type="button" class="btn btn-success btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="approved">Setujui</button>
                          <button type="button" class="btn btn-danger btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="rejected">Tolak</button>
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
    `;
  }

  async function registerSelectedTeam(tournamentId) {
    const teamId = document.getElementById("reg-team-select")?.value;
    if (!teamId) {
      window.TurnamenUI.showToast("Pilih tim yang valid terlebih dahulu.", "warning");
      return;
    }
    const res = await window.TurnamenAPI.registerTeamToTournament(tournamentId, {
      team_id: teamId,
      notes: "Pendaftaran via Desktop UI",
    });
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.showToast("Tim berhasil didaftarkan.", "success");
    await navigateTo("tournament-detail");
  }

  async function verifyRegistration(registrationId, newStatus) {
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

  // =========================================================================
  // 4. TEAM MANAGEMENT PAGE (ADAPTIVE PER ROLE)
  // =========================================================================
  async function renderTeamManagement(container, isStale) {
    await ensureGamesLoaded(false);
    if (isStale()) return;

    const res = await window.TurnamenAPI.getTeams(
      teamFilterState.gameId ? { game_id: teamFilterState.gameId } : {}
    );
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
    if (teams.length === 0) {
      return `
        <div class="card">
          ${window.TurnamenUI.renderEmptyState(
            "Belum Ada Tim Ditemukan",
            "Belum ada tim yang sesuai dengan filter saat ini.",
            canCreateTeam
              ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-team">Buat Tim Baru</button>`
              : ""
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
                    <td>${window.TurnamenUI.renderGameChip(tm.game_name)}</td>
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
    const games = await ensureGamesLoaded(false);
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

  async function submitCreateTeam() {
    const payload = {
      name: (document.getElementById("new-team-name")?.value || "").trim(),
      tag: (document.getElementById("new-team-tag")?.value || "").trim(),
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
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Tim berhasil dibuat.", "success");
    await navigateTo(currentPage);
  }

  async function openTeamDetailModal(teamId) {
    const res = await window.TurnamenAPI.getTeamById(teamId);
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
    const res = await window.TurnamenAPI.getTeamById(teamId);
    if (!res.success || !res.data) {
      window.TurnamenUI.showToast(res.message || "Gagal memuat data tim.", "danger");
      return;
    }
    const tm = res.data;
    if (!canPerform("team:manage", { team: tm })) {
      window.TurnamenUI.showToast("Anda tidak memiliki izin mengubah tim ini.", "danger");
      return;
    }

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

  async function submitEditTeam(teamId) {
    const payload = {
      name: (document.getElementById("edit-team-name")?.value || "").trim(),
      tag: (document.getElementById("edit-team-tag")?.value || "").trim(),
      region: (document.getElementById("edit-team-region")?.value || "").trim(),
    };
    const res = await window.TurnamenAPI.updateTeam(teamId, payload);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Data tim berhasil diperbarui.", "success");
    await navigateTo(currentPage);
  }

  function openAddMemberModal(teamId) {
    window.TurnamenUI.openModal({
      title: "Tambah Anggota Roster Tim",
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
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="submit-add-member" data-id="${window.TurnamenUI.escapeHtml(teamId)}">Tambahkan Anggota</button>
      `,
    });
  }

  async function submitAddMember(teamId) {
    const payload = {
      nickname: (document.getElementById("member-nickname")?.value || "").trim(),
      ingame_id: (document.getElementById("member-ingame-id")?.value || "").trim(),
      member_role: document.getElementById("member-role")?.value || "starter",
    };
    const res = await window.TurnamenAPI.addTeamMember(teamId, payload);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Anggota tim berhasil ditambahkan.", "success");
    await navigateTo(currentPage);
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
    const matches = matchRoundFilter
      ? allMatches.filter((m) => m.round_name === matchRoundFilter)
      : allMatches;

    const canManageMatches = canPerform("match:submit_result", { tournament: ctx.active });
    const completedCount = allMatches.filter((m) => m.status === "completed").length;
    const readyCount = allMatches.filter(
      (m) => m.team_a_id && m.team_b_id && m.status !== "completed"
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

      <div class="grid-3">
        <div class="metric-card">
          <div class="metric-label">Total Match Bracket</div>
          <div class="metric-value">${allMatches.length}</div>
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
        roundNames.length > 0
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
        </div>
      `
          : ""
      }

      <div class="card">
        ${
          matches.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Belum Ada Pertandingan",
                "Bracket turnamen ini belum dibuat. Generate bracket untuk menghasilkan jadwal pertandingan.",
                `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Buka Halaman Bracket</button>`
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
                    const isReady = Boolean(m.team_a_id && m.team_b_id && m.status !== "completed");
                    let actionCell = `<span class="table-subtext">Menunggu Lawan</span>`;
                    if (m.status === "completed") {
                      actionCell = canManageMatches
                        ? `<button type="button" class="btn btn-ghost btn-sm" data-action="open-override-score" data-id="${window.TurnamenUI.escapeHtml(m.id)}" data-team-a="${window.TurnamenUI.escapeHtml(m.team_a_name)}" data-team-b="${window.TurnamenUI.escapeHtml(m.team_b_name)}" data-score-a="${m.score_a}" data-score-b="${m.score_b}" data-max="${maxWin}">Koreksi Audit</button>`
                        : `<span class="table-subtext">Terkunci (Audited)</span>`;
                    } else if (m.status === "bye") {
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
                          <button type="button" class="btn btn-primary btn-sm" data-action="submit-score" data-id="${window.TurnamenUI.escapeHtml(m.id)}">Sahkan</button>
                        </div>
                      `
                        : `<span class="table-subtext">Siap Bertanding</span>`;
                    }

                    return `
                    <tr>
                      <td><strong>${window.TurnamenUI.escapeHtml(m.round_name)}</strong></td>
                      <td class="tabular-nums">#${m.match_number}</td>
                      <td>
                        <div class="team-cell-inline">
                          ${m.team_a_id ? window.TurnamenUI.renderTeamEmblem(m.team_a_tag, 22) : ""}
                          <span>${window.TurnamenUI.escapeHtml(m.team_a_name || "TBD")}</span>
                        </div>
                      </td>
                      <td class="tabular-nums"><strong>${m.score_a} - ${m.score_b}</strong></td>
                      <td>
                        <div class="team-cell-inline">
                          ${m.team_b_id ? window.TurnamenUI.renderTeamEmblem(m.team_b_tag, 22) : ""}
                          <span>${window.TurnamenUI.escapeHtml(m.team_b_name || "TBD")}</span>
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
    if (roundSelect) {
      roundSelect.addEventListener("change", (e) => {
        matchRoundFilter = e.target.value;
        navigateTo("match-management");
      });
    }
  }

  async function submitScore(matchId) {
    const scoreA = Number(document.getElementById(`score-a-${matchId}`)?.value ?? 0);
    const scoreB = Number(document.getElementById(`score-b-${matchId}`)?.value ?? 0);

    const res = await window.TurnamenAPI.submitMatchResult(matchId, {
      score_a: scoreA,
      score_b: scoreB,
      notes: "Disahkan melalui panel operasional desktop",
    });

    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }

    window.TurnamenUI.showToast(
      "Skor disahkan. Pemenang otomatis maju ke babak berikutnya.",
      "success"
    );
    await navigateTo(currentPage);
  }

  function openOverrideScoreModal(matchData) {
    window.TurnamenUI.openModal({
      title: "Koreksi Audit Skor Pertandingan",
      bodyHtml: `
        <p style="margin-top:0; color:var(--text-secondary);">
          Pertandingan ini sudah berstatus selesai. Koreksi skor akan dicatat pada log audit dengan <code>force_override: true</code>.
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
        <button type="button" class="btn btn-danger" data-action="submit-override-score" data-id="${window.TurnamenUI.escapeHtml(matchData.id)}">Sahkan Koreksi</button>
      `,
    });
  }

  async function submitOverrideScore(matchId) {
    const scoreA = Number(document.getElementById("override-score-a")?.value ?? 0);
    const scoreB = Number(document.getElementById("override-score-b")?.value ?? 0);
    const notes = (document.getElementById("override-notes")?.value || "").trim();

    if (notes.length < 4) {
      window.TurnamenUI.showToast(
        "Catatan alasan koreksi wajib diisi (minimal 4 karakter).",
        "warning"
      );
      return;
    }

    const res = await window.TurnamenAPI.submitMatchResult(matchId, {
      score_a: scoreA,
      score_b: scoreB,
      notes,
      force_override: true,
    });
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Koreksi audit skor berhasil disimpan.", "success");
    await navigateTo(currentPage);
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
                          const winA = m.winner_team_id && m.winner_team_id === m.team_a_id;
                          const winB = m.winner_team_id && m.winner_team_id === m.team_b_id;
                          const byeA = !m.team_a_id;
                          const byeB = !m.team_b_id;
                          return `
                          <article
                            class="bracket-match-card ${isCompleted ? "is-completed" : ""}"
                            data-match-id="${window.TurnamenUI.escapeHtml(m.id)}"
                            data-next-match-id="${window.TurnamenUI.escapeHtml(m.next_match_id || "")}"
                            data-next-slot="${window.TurnamenUI.escapeHtml(m.next_slot || "")}"
                            data-completed="${isCompleted ? "true" : "false"}"
                          >
                            <div class="bracket-match-meta">
                              <span class="tabular-nums">Match #${m.match_number} (Bo${m.best_of})</span>
                              ${window.TurnamenUI.renderStatusBadge(m.status)}
                            </div>
                            <div class="bracket-team-row ${winA ? "winner" : ""} ${byeA ? "bye" : ""}" data-slot="A">
                              <span class="bracket-team-identity">
                                ${m.team_a_id ? window.TurnamenUI.renderTeamEmblem(m.team_a_tag, 22) : ""}
                                <span class="bracket-team-name">${window.TurnamenUI.escapeHtml(m.team_a_name || "TBD")}</span>
                              </span>
                              <span class="bracket-score">${m.score_a}</span>
                            </div>
                            <div class="bracket-team-row ${winB ? "winner" : ""} ${byeB ? "bye" : ""}" data-slot="B">
                              <span class="bracket-team-identity">
                                ${m.team_b_id ? window.TurnamenUI.renderTeamEmblem(m.team_b_tag, 22) : ""}
                                <span class="bracket-team-name">${window.TurnamenUI.escapeHtml(m.team_b_name || "TBD")}</span>
                              </span>
                              <span class="bracket-score">${m.score_b}</span>
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

  function confirmRegenerateBracket(tournamentId) {
    window.TurnamenUI.openModal({
      title: "Konfirmasi Reset Bracket",
      bodyHtml: `
        <p style="margin:0; color:var(--text-secondary);">
          Bracket untuk turnamen ini sudah tersedia. Membuat ulang bracket akan mengganti jadwal pertandingan yang ada berdasarkan daftar tim berstatus <code>approved</code>.
        </p>
      `,
      footerHtml: `
        <button type="button" class="btn btn-secondary" data-modal-close="true">Batal</button>
        <button type="button" class="btn btn-primary" data-action="regenerate-bracket" data-id="${window.TurnamenUI.escapeHtml(tournamentId)}">Lanjutkan Generate Ulang</button>
      `,
    });
  }

  async function regenerateBracket(tournamentId) {
    const res = await window.TurnamenAPI.generateBracket(tournamentId);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Bracket Single Elimination berhasil disusun.", "success");
    await navigateTo("bracket");
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
    allItems.sort((a, b) => Number(Boolean(b.is_pinned)) - Number(Boolean(a.is_pinned)));
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
                "Belum ada pengumuman yang sesuai dengan filter pada turnamen ini."
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
                    Oleh ${window.TurnamenUI.escapeHtml(a.author_name || "Panitia")} | ${window.TurnamenUI.formatDateTime(a.created_at)}
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

  function openAnnouncementModal(tournamentId) {
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
        <button type="button" class="btn btn-primary" data-action="submit-announcement" data-id="${window.TurnamenUI.escapeHtml(tournamentId)}">Publikasikan</button>
      `,
    });
  }

  async function submitAnnouncement(tournamentId) {
    const payload = {
      title: (document.getElementById("ann-title")?.value || "").trim(),
      priority: document.getElementById("ann-priority")?.value || "normal",
      content: (document.getElementById("ann-content")?.value || "").trim(),
      is_pinned: Boolean(document.getElementById("ann-pinned")?.checked),
    };
    const res = await window.TurnamenAPI.createAnnouncement(tournamentId, payload);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Pengumuman berhasil dipublikasikan.", "success");
    await navigateTo(currentPage);
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

    container.innerHTML = `
      ${renderTournamentContextBar(ctx.list, ctx.active)}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>Laporan &amp; Klasemen: ${window.TurnamenUI.escapeHtml(report.tournament?.title || ctx.active.title)}</h2>
          <p>Statistik penyelesaian pertandingan dan rekor menang-kalah seluruh tim peserta.</p>
        </div>
      </div>

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
          <div class="metric-note">Menunggu verifikasi: ${s.pending_registrations ?? 0}</div>
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
              <input id="profile-fullname" class="form-input" value="${window.TurnamenUI.escapeHtml(user.full_name || "-")}" readonly />
            </div>
            <div class="form-group">
              <label for="profile-username" class="form-label">Username</label>
              <input id="profile-username" class="form-input tabular-nums" value="${window.TurnamenUI.escapeHtml(user.username || "-")}" readonly />
            </div>
            <div class="form-group">
              <label for="profile-email" class="form-label">Email</label>
              <input id="profile-email" class="form-input tabular-nums" value="${window.TurnamenUI.escapeHtml(user.email || "-")}" readonly />
            </div>
            <div class="row-actions">
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
        </div>

        ${demoPanelHtml}
      </div>
    `;

    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
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
  }

  function renderAuthFeedback(message, variant = "warning") {
    const slot = document.getElementById("auth-feedback-slot");
    if (!slot) return;
    slot.innerHTML = `
      <div class="notice-banner ${variant === "danger" ? "notice-banner-danger" : "notice-banner-warning"}" role="alert">
        <span>${window.TurnamenUI.escapeHtml(message)}</span>
      </div>
    `;
  }

  async function handleLoginSubmit() {
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

    updateUserTopbar(data.user);
    window.TurnamenUI.showToast(
      `Selamat datang, ${data.user.full_name || data.user.username || data.user.email}.`,
      "success"
    );
    await navigateTo("dashboard");
  }

  async function handleRegisterSubmit() {
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

    updateUserTopbar(data.user);
    window.TurnamenUI.showToast(
      `Akun ${data.user.username || data.user.email} berhasil dibuat.`,
      "success"
    );
    await navigateTo("dashboard");
  }

  async function handleLogout() {
    await window.TurnamenAPI.logout();
    updateUserTopbar(getCurrentUserSafe());
    window.TurnamenUI.showToast("Anda telah keluar dari sesi aktif.", "info");
    await navigateTo("login");
  }

  async function quickSwitchRole(roleName) {
    if (!isMockMode()) {
      window.TurnamenUI.showToast(
        "Pemilihan akun demo tidak tersedia pada APP_MODE=supabase.",
        "warning"
      );
      return;
    }
    const user = window.TurnamenAPI.setSimulatedRole(roleName);
    updateUserTopbar(user);
    if (!user) {
      window.TurnamenUI.showToast("Role simulasi tidak tersedia.", "warning");
      return;
    }
    window.TurnamenUI.showToast(`Beralih ke akun demo: ${user.full_name}`, "success");
    await navigateTo("dashboard");
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

      switch (action) {
        case "go-page": {
          const page = target.getAttribute("data-page") || "dashboard";
          const tournamentId = target.getAttribute("data-tournament-id") || "";
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
          submitCreateTournament();
          break;
        case "open-edit-tournament":
          openEditTournamentModal(id);
          break;
        case "submit-edit-tournament":
          submitEditTournament(id);
          break;
        case "confirm-delete-tournament":
          confirmDeleteTournament(id);
          break;
        case "execute-delete-tournament":
          executeDeleteTournament(id);
          break;
        case "register-selected-team":
          registerSelectedTeam(id);
          break;
        case "verify-registration": {
          const nextStatus = target.getAttribute("data-status") || "approved";
          verifyRegistration(id, nextStatus);
          break;
        }
        case "open-create-team":
          openCreateTeamModal();
          break;
        case "submit-create-team":
          submitCreateTeam();
          break;
        case "open-team-detail":
          openTeamDetailModal(id);
          break;
        case "open-edit-team":
          openEditTeamModal(id);
          break;
        case "submit-edit-team":
          submitEditTeam(id);
          break;
        case "open-add-member":
          openAddMemberModal(id);
          break;
        case "submit-add-member":
          submitAddMember(id);
          break;
        case "submit-score":
          submitScore(id);
          break;
        case "open-override-score":
          openOverrideScoreModal({
            id,
            teamA: target.getAttribute("data-team-a") || "Team A",
            teamB: target.getAttribute("data-team-b") || "Team B",
            scoreA: Number(target.getAttribute("data-score-a") || 0),
            scoreB: Number(target.getAttribute("data-score-b") || 0),
            maxWin: Number(target.getAttribute("data-max") || 3),
          });
          break;
        case "submit-override-score":
          submitOverrideScore(id);
          break;
        case "confirm-regenerate-bracket":
          confirmRegenerateBracket(id);
          break;
        case "regenerate-bracket":
          regenerateBracket(id);
          break;
        case "open-announcement-modal":
          openAnnouncementModal(id);
          break;
        case "submit-announcement":
          submitAnnouncement(id);
          break;
        case "switch-auth-tab": {
          const nextTab = target.getAttribute("data-tab") || "login";
          loginActiveTab = nextTab === "register" ? "register" : "login";
          renderLoginPage(document.getElementById("main-content")).then(() => {
            document.getElementById(`tab-auth-${loginActiveTab}`)?.focus();
          });
          break;
        }
        case "quick-switch-role": {
          const role = target.getAttribute("data-role") || "";
          quickSwitchRole(role);
          break;
        }
        case "logout":
          handleLogout();
          break;
        default:
          break;
      }
    };

    const handleChangeEvent = (e) => {
      const target = e.target;
      if (!target || target.getAttribute("data-action") !== "select-active-tournament") {
        return;
      }
      if (target.value) {
        navigateTo(currentPage, { tournamentId: target.value });
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
    handleLogout,
    quickSwitchRole,
  };

  document.addEventListener("DOMContentLoaded", initApp);
})(window, document);
