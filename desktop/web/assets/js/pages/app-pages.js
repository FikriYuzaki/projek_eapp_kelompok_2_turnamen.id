/**
 * Turnamen.in: Futuristic Arena Desktop Pages Controller (`window.TurnamenApp`)
 * Owner: Fikri (System Integration & Desktop UI/UX)
 * Connects all 10 screens to `window.TurnamenAPI` across Mock and Supabase modes.
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

  const ROLE_CAPABILITIES = {
    super_admin: [
      "Akses penuh manajemen pengguna, turnamen, tim, bracket, skor, pengumuman, dan laporan.",
    ],
    organizer: [
      "Membuat turnamen baru serta mengubah atau menghapus turnamen milik sendiri.",
      "Memverifikasi pendaftaran tim, menyusun bracket, mengesahkan skor, dan menerbitkan pengumuman.",
    ],
    committee: [
      "Memverifikasi pendaftaran peserta pada turnamen yang ditugaskan.",
      "Menyusun bracket, menginput/mengesahkan skor pertandingan, dan mempublikasikan pengumuman.",
    ],
    team_captain: [
      "Membuat tim baru, memperbarui profil tim milik sendiri, dan menambah anggota roster.",
      "Mendaftarkan tim milik sendiri ke turnamen yang membuka pendaftaran.",
    ],
    player: [
      "Melihat daftar turnamen, detail peserta, tim, jadwal pertandingan, bracket, pengumuman, dan klasemen.",
      "Mengakses halaman profil pribadi (akses read-only pada operasional turnamen).",
    ],
  };

  let currentPage = "dashboard";
  let navigationSeq = 0;
  let loginActiveTab = "login";
  let tournamentFilterState = { status: "", gameId: "", search: "" };
  let teamFilterState = { gameId: "", search: "" };
  let matchRoundFilter = "";
  let announcementPriorityFilter = "";

  const gamesState = { items: [], loaded: false, error: null };
  let cachedTournaments = [];

  // =========================================================================
  // AUTH, MODE & RBAC HELPERS (UX-ONLY; BACKEND IS SOLE SECURITY AUTHORITY)
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

  function isStaffRole(role) {
    return role === "super_admin" || role === "organizer" || role === "committee";
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
  // INITIALIZATION & GLOBAL SHELL BINDINGS
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

  function bindSidebarNavigation() {
    const navButtons = document.querySelectorAll(".nav-item[data-page]");
    navButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-page");
        closeMobileSidebar();
        navigateTo(target);
      });
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

    if (closeBtn) {
      closeBtn.addEventListener("click", closeMobileSidebar);
    }
    if (backdrop) {
      backdrop.addEventListener("click", closeMobileSidebar);
    }
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
      navigateTo(currentPage);
    });
  }

  function bindTopbarAuthButton() {
    const btn = document.getElementById("topbar-auth-action");
    if (!btn) return;
    btn.addEventListener("click", () => {
      const user = getCurrentUserSafe();
      if (user) {
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
      authBtn.textContent = user ? "Keluar" : "Masuk";
    }
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

  // =========================================================================
  // NAVIGATION WITH RACE-CONDITION GUARD
  // =========================================================================
  async function navigateTo(pageName, options = {}) {
    const seq = ++navigationSeq;
    const targetPage = PAGE_TITLES[pageName] ? pageName : "dashboard";

    if (options && options.tournamentId && window.TurnamenConfig) {
      window.TurnamenConfig.setSelectedTournamentId(options.tournamentId);
    }

    currentPage = targetPage;

    document.querySelectorAll(".nav-item[data-page]").forEach((btn) => {
      const isCurrent = btn.getAttribute("data-page") === targetPage;
      btn.classList.toggle("active", isCurrent);
      if (isCurrent) {
        btn.setAttribute("aria-current", "page");
      } else {
        btn.removeAttribute("aria-current");
      }
    });

    const titleEl = document.getElementById("topbar-page-title");
    if (titleEl) {
      titleEl.textContent = PAGE_TITLES[targetPage] || "Turnamen.in";
    }

    updateUserTopbar(getCurrentUserSafe());

    const container = document.getElementById("main-content");
    if (!container) return;
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
  // 1. DASHBOARD PAGE
  // =========================================================================
  async function renderDashboard(container, isStale) {
    const [tourRes, teamsRes] = await Promise.all([
      window.TurnamenAPI.getTournaments(),
      window.TurnamenAPI.getTeams(),
    ]);
    if (isStale()) return;

    if (!tourRes.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(
        tourRes.message,
        "retry-page"
      );
      return;
    }

    const tournaments = Array.isArray(tourRes.data) ? tourRes.data : [];
    const teamsOk = Boolean(teamsRes.success && Array.isArray(teamsRes.data));
    const teams = teamsOk ? teamsRes.data : [];
    const ctx = await resolveActiveTournamentContext(tournaments);
    if (isStale()) return;

    let report = null;
    let reportError = null;
    if (ctx.active) {
      const reportRes = await window.TurnamenAPI.getTournamentReport(ctx.active.id);
      if (isStale()) return;
      if (reportRes.success && reportRes.data) {
        report = reportRes.data;
      } else {
        reportError = reportRes.message || "Ringkasan laporan belum tersedia.";
      }
    }

    const summary = report && report.summary ? report.summary : null;
    const activeTitle = ctx.active ? ctx.active.title : "Belum Ada Turnamen Aktif";
    const approvedDisplay = summary
      ? `${summary.approved_teams} / ${summary.max_teams}`
      : ctx.active
        ? `${ctx.active.approved_teams_count || 0} / ${ctx.active.max_teams || 0}`
        : "0";
    const matchProgressDisplay = summary
      ? `${summary.completed_matches} / ${summary.total_matches}`
      : "0 / 0";
    const matchRateText = summary
      ? `Penyelesaian ${summary.completion_percentage}%`
      : "Belum ada pertandingan dijadwalkan";
    const prizeDisplay = ctx.active
      ? window.TurnamenUI.formatRupiah(
          summary && summary.prize_pool !== undefined ? summary.prize_pool : ctx.active.prize_pool
        )
      : "-";

    const heroHtml = ctx.active
      ? `
        <section class="arena-hero" aria-label="Sorotan Turnamen Aktif">
          <div class="arena-hero-main">
            <span class="arena-hero-kicker">Turnamen Aktif Terpilih</span>
            <h2 class="arena-hero-title">${window.TurnamenUI.escapeHtml(activeTitle)}</h2>
            <div class="arena-hero-meta">
              ${window.TurnamenUI.renderStatusBadge(ctx.active.status)}
              <span>Game: <strong>${window.TurnamenUI.escapeHtml(ctx.active.game_name)}</strong></span>
              <span>Format: <strong class="tabular-nums">Single Elimination Bo${ctx.active.best_of}</strong></span>
              <span>Mulai: <strong class="tabular-nums">${window.TurnamenUI.formatDateOnly(ctx.active.start_date)}</strong></span>
            </div>
          </div>
          <div class="page-actions">
            <button type="button" class="btn btn-secondary" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">
              ${window.TurnamenUI.icon("bracket", 15)}
              <span>Buka Bracket</span>
            </button>
            <button type="button" class="btn btn-primary" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">
              <span>Detail &amp; Peserta</span>
            </button>
          </div>
        </section>
      `
      : `
        <section class="arena-hero" aria-label="Status Arena">
          <div class="arena-hero-main">
            <span class="arena-hero-kicker">Arena Siap Digunakan</span>
            <h2 class="arena-hero-title">Belum Ada Turnamen Terdaftar</h2>
            <p class="card-subtitle">Buat turnamen pertama atau sinkronkan data dari server untuk memulai kompetisi.</p>
          </div>
          ${
            canPerform("tournament:create")
              ? `<button type="button" class="btn btn-primary" data-action="open-create-tournament">${window.TurnamenUI.icon("plus", 15)}<span>Buat Turnamen Baru</span></button>`
              : `<button type="button" class="btn btn-secondary" data-action="go-page" data-page="tournament-list">Lihat Katalog Turnamen</button>`
          }
        </section>
      `;

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      ${heroHtml}
      ${
        reportError
          ? `<div class="notice-banner notice-banner-warning" role="alert"><span>${window.TurnamenUI.escapeHtml(reportError)}</span></div>`
          : ""
      }

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Total Turnamen</div>
          <div class="metric-value">${tournaments.length}</div>
          <div class="metric-note">Data aktual dari server API</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Tim Terdaftar</div>
          <div class="metric-value">${teamsOk ? teams.length : "-"}</div>
          <div class="metric-note">${teamsOk ? `Terverifikasi pada turnamen aktif: ${approvedDisplay}` : "Gagal memuat data tim"}</div>
        </div>
        <div class="metric-card metric-card-accent">
          <div class="metric-label">Progres Pertandingan</div>
          <div class="metric-value">${matchProgressDisplay}</div>
          <div class="metric-note">${matchRateText}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Hadiah Turnamen Aktif</div>
          <div class="metric-value">${prizeDisplay}</div>
          <div class="metric-note">${window.TurnamenUI.escapeHtml(ctx.active ? ctx.active.venue || "Online" : "Belum ada turnamen")}</div>
        </div>
      </div>

      <div class="workspace-split">
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Daftar Turnamen</h3>
              <p class="card-subtitle">Pilih turnamen untuk meninjau peserta atau membuka bracket.</p>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-list">Lihat Semua</button>
          </div>
          ${
            tournaments.length === 0
              ? window.TurnamenUI.renderEmptyState(
                  "Belum Ada Turnamen",
                  "Belum ada turnamen yang tersimpan pada sistem."
                )
              : `
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Turnamen</th>
                    <th>Game</th>
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
                        <div class="table-subtext">${window.TurnamenUI.escapeHtml(t.venue || "Online")}</div>
                      </td>
                      <td>${window.TurnamenUI.escapeHtml(t.game_name)}</td>
                      <td class="tabular-nums">${t.approved_teams_count || 0} / ${t.max_teams}</td>
                      <td>${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                      <td>
                        <div class="row-actions">
                          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="tournament-detail" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Detail</button>
                          <button type="button" class="btn btn-ghost btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Bracket</button>
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

        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Jejak Audit Aktivitas</h3>
              <p class="card-subtitle">${window.TurnamenUI.escapeHtml(activeTitle)}</p>
            </div>
            <span class="badge badge-violet">Audit Log</span>
          </div>
          ${
            report && Array.isArray(report.recent_activity) && report.recent_activity.length > 0
              ? `
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
                  ${report.recent_activity
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
                  "Aktivitas terbaru turnamen akan tercatat di sini setelah ada aksi operasional."
                )
          }
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 2. TOURNAMENT LIST PAGE
  // =========================================================================
  async function renderTournamentList(container, isStale) {
    await ensureGamesLoaded(false);
    if (isStale()) return;

    const apiFilters = {};
    if (tournamentFilterState.status) apiFilters.status = tournamentFilterState.status;
    if (tournamentFilterState.gameId) apiFilters.game_id = tournamentFilterState.gameId;

    const res = await window.TurnamenAPI.getTournaments(apiFilters);
    if (isStale()) return;

    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message, "retry-page");
      return;
    }

    const rawList = Array.isArray(res.data) ? res.data : [];
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
          <h2>Katalog &amp; Manajemen Turnamen</h2>
          <p>Kelola seluruh turnamen lintas cabang game esports dengan status dan kuota peserta aktual.</p>
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

      <div class="card" id="tournament-list-results">
        ${renderTournamentListTable(list, rawList.length, canCreate)}
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
          resultsEl.innerHTML = renderTournamentListTable(filtered, rawList.length, canCreate);
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

  function renderTournamentListTable(list, rawTotal, canCreate) {
    if (list.length === 0) {
      return window.TurnamenUI.renderEmptyState(
        "Tidak Ada Turnamen Ditemukan",
        rawTotal === 0
          ? "Belum ada turnamen tersedia. Buat turnamen baru atau ubah filter pencarian."
          : "Tidak ada turnamen yang cocok dengan kata kunci pencarian saat ini.",
        canCreate
          ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-tournament">Buat Turnamen Pertama</button>`
          : ""
      );
    }

    return `
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
                  <td>${window.TurnamenUI.escapeHtml(t.game_name)}</td>
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
    const canVerify = canPerform("registration:verify", { tournament: t });
    const canRegister =
      canPerform("registration:create") &&
      (t.status === "open_registration" || t.status === "draft");
    const eligibleTeams = canRegister ? getEligibleTeamsForRegistration(teams, t, regs) : [];

    container.innerHTML = `
      ${renderTournamentContextBar(
        ctx.list,
        t,
        `<button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="bracket" data-tournament-id="${window.TurnamenUI.escapeHtml(t.id)}">Buka Bracket</button>`
      )}

      <div class="page-header">
        <div class="page-header-copy">
          <h2>${window.TurnamenUI.escapeHtml(t.title)}</h2>
          <p>${window.TurnamenUI.escapeHtml(t.description || "Tidak ada deskripsi tambahan untuk turnamen ini.")}</p>
        </div>
        ${
          canPerform("tournament:edit", { tournament: t })
            ? `<button type="button" class="btn btn-secondary btn-sm" data-action="open-edit-tournament" data-id="${window.TurnamenUI.escapeHtml(t.id)}">${window.TurnamenUI.icon("edit", 14)}<span>Edit Info Turnamen</span></button>`
            : ""
        }
      </div>

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
          ${
            canRegister
              ? `
            <div class="row-actions">
              <label for="reg-team-select" class="sr-only">Pilih tim untuk didaftarkan</label>
              <select id="reg-team-select" class="form-select form-select-compact" ${eligibleTeams.length === 0 ? "disabled" : ""}>
                ${
                  eligibleTeams.length > 0
                    ? eligibleTeams
                        .map(
                          (tm) =>
                            `<option value="${window.TurnamenUI.escapeHtml(tm.id)}">${window.TurnamenUI.escapeHtml(tm.name)} [${window.TurnamenUI.escapeHtml(tm.tag)}]</option>`
                        )
                        .join("")
                    : `<option value="">Tidak ada tim yang memenuhi syarat</option>`
                }
              </select>
              <button
                type="button"
                class="btn btn-primary btn-sm"
                data-action="register-selected-team"
                data-id="${window.TurnamenUI.escapeHtml(t.id)}"
                ${eligibleTeams.length === 0 ? "disabled" : ""}
              >
                ${window.TurnamenUI.icon("plus", 14)}
                <span>Daftarkan Tim</span>
              </button>
            </div>
          `
              : ""
          }
        </div>

        ${
          regs.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Belum Ada Tim Terdaftar",
                "Belum ada tim yang mengirimkan pendaftaran untuk turnamen ini."
              )
            : `
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Seed</th>
                  <th>Nama Tim</th>
                  <th>Tag</th>
                  <th>Catatan Verifikasi</th>
                  <th>Status</th>
                  ${canVerify ? "<th>Aksi Panitia</th>" : ""}
                </tr>
              </thead>
              <tbody>
                ${regs
                  .map(
                    (r) => `
                  <tr>
                    <td class="tabular-nums">#${r.seed_number || "-"}</td>
                    <td><strong>${window.TurnamenUI.escapeHtml(r.team_name)}</strong></td>
                    <td class="tabular-nums"><span class="badge badge-neutral">${window.TurnamenUI.escapeHtml(r.team_tag)}</span></td>
                    <td>${window.TurnamenUI.escapeHtml(r.notes || "-")}</td>
                    <td>${window.TurnamenUI.renderStatusBadge(r.status)}</td>
                    ${
                      canVerify
                        ? `
                      <td>
                        <div class="row-actions">
                          <button type="button" class="btn btn-success btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="approved">Setujui</button>
                          <button type="button" class="btn btn-danger btn-sm" data-action="verify-registration" data-id="${window.TurnamenUI.escapeHtml(r.id)}" data-status="rejected">Tolak</button>
                        </div>
                      </td>
                    `
                        : ""
                    }
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
    await navigateTo("tournament-detail");
  }

  // =========================================================================
  // 4. TEAM MANAGEMENT PAGE
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

    const canCreateTeam = canPerform("team:create");
    const gameOptions = gamesState.items
      .map(
        (g) =>
          `<option value="${window.TurnamenUI.escapeHtml(g.id)}" ${teamFilterState.gameId === g.id ? "selected" : ""}>${window.TurnamenUI.escapeHtml(g.name)}</option>`
      )
      .join("");

    container.innerHTML = `
      ${renderGamesErrorNotice()}
      <div class="page-header">
        <div class="page-header-copy">
          <h2>Manajemen Tim &amp; Roster Pemain</h2>
          <p>Kelola data tim esports, tag resmi, region, serta daftar anggota beserta ID in-game.</p>
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

      <div class="card" id="team-list-results">
        ${renderTeamManagementTable(teams, canCreateTeam)}
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
          resultsEl.innerHTML = renderTeamManagementTable(filtered, canCreateTeam);
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

  function renderTeamManagementTable(teams, canCreateTeam) {
    if (teams.length === 0) {
      return window.TurnamenUI.renderEmptyState(
        "Belum Ada Tim Ditemukan",
        "Belum ada tim yang sesuai dengan filter saat ini.",
        canCreateTeam
          ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-create-team">Buat Tim Baru</button>`
          : ""
      );
    }

    return `
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
                  <td><strong>${window.TurnamenUI.escapeHtml(tm.name)}</strong></td>
                  <td>${window.TurnamenUI.escapeHtml(tm.game_name)}</td>
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
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Tim berhasil dibuat.", "success");
    await navigateTo("team-management");
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
    await navigateTo("team-management");
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
    await navigateTo("team-management");
  }

  // =========================================================================
  // 5. MATCH MANAGEMENT & SCORE SUBMISSION PAGE
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
                      <td>${window.TurnamenUI.escapeHtml(m.team_a_name || "TBD")}</td>
                      <td class="tabular-nums"><strong>${m.score_a} - ${m.score_b}</strong></td>
                      <td>${window.TurnamenUI.escapeHtml(m.team_b_name || "TBD")}</td>
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
      notes: "Disahkan melalui Match Management Desktop",
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
    const hasExistingBracket = rounds.length > 0;

    container.innerHTML = `
      ${renderTournamentContextBar(
        ctx.list,
        ctx.active,
        `
          <button type="button" class="btn btn-secondary btn-sm" data-action="go-page" data-page="match-management" data-tournament-id="${window.TurnamenUI.escapeHtml(ctx.active.id)}">Kelola Skor</button>
          ${
            canGenerate
              ? `<button type="button" class="btn btn-primary btn-sm" data-action="${hasExistingBracket ? "confirm-regenerate-bracket" : "regenerate-bracket"}" data-id="${window.TurnamenUI.escapeHtml(data.tournament_id || ctx.active.id)}">${hasExistingBracket ? "Reset / Generate Ulang Bracket" : "Generate Bracket"}</button>`
              : ""
          }
        `
      )}

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
                      <article class="bracket-match-card ${isCompleted ? "is-completed" : ""}">
                        <div class="bracket-match-meta">
                          <span class="tabular-nums">Match #${m.match_number} (Bo${m.best_of})</span>
                          ${window.TurnamenUI.renderStatusBadge(m.status)}
                        </div>
                        <div class="bracket-team-row ${winA ? "winner" : ""} ${byeA ? "bye" : ""}">
                          <span>${window.TurnamenUI.escapeHtml(m.team_a_name || "TBD")}</span>
                          <span class="bracket-score">${m.score_a}</span>
                        </div>
                        <div class="bracket-team-row ${winB ? "winner" : ""} ${byeB ? "bye" : ""}">
                          <span>${window.TurnamenUI.escapeHtml(m.team_b_name || "TBD")}</span>
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
        `
        }
      </div>
    `;
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
              <article class="announcement-card ${a.is_pinned ? "is-pinned" : ""}">
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
    await navigateTo("announcements");
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
          <div class="metric-note">${s.completed_matches ?? 0} dari ${s.total_matches ?? 0} pertandingan selesai</div>
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
                    <td class="tabular-nums"><strong>#${row.rank}</strong></td>
                    <td class="tabular-nums"><span class="badge badge-neutral">${window.TurnamenUI.escapeHtml(row.team_tag)}</span></td>
                    <td><strong>${window.TurnamenUI.escapeHtml(row.team_name)}</strong></td>
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
