/**
 * Turnamen.in — Desktop Pages Controller (`window.TurnamenApp`)
 * Owner: Ferlita (Project Coordinator & UI/UX Designer)
 * Implements all 10 initial screens connected to `window.TurnamenAPI` in Mock/Supabase modes.
 */
(function (window, document) {
  "use strict";

  const PAGE_TITLES = {
    dashboard: "Dashboard Utama",
    "tournament-list": "Daftar Turnamen",
    "tournament-detail": "Detail & Peserta Turnamen",
    "team-management": "Manajemen Tim & Pemain",
    "match-management": "Manajemen Pertandingan & Skor",
    bracket: "Single Elimination Bracket",
    announcements: "Pengumuman Kompetisi",
    reports: "Laporan & Klasemen Turnamen",
    profile: "Profil Pengguna & Status Sistem",
    login: "Masuk & Simulasi Role",
  };

  let currentPage = "dashboard";
  let cachedGames = [];
  let cachedTournaments = [];

  async function initApp() {
    bindSidebarNavigation();
    bindRoleSwitcher();

    const healthRes = await window.TurnamenAPI.getHealth();
    updateRuntimeIndicators(healthRes);

    const gamesRes = await window.TurnamenAPI.getGames();
    if (gamesRes.success && Array.isArray(gamesRes.data)) {
      cachedGames = gamesRes.data;
    }

    await navigateTo("dashboard");
  }

  function bindSidebarNavigation() {
    const navButtons = document.querySelectorAll(".nav-item[data-page]");
    navButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-page");
        navigateTo(target);
      });
    });
  }

  function bindRoleSwitcher() {
    const switcher = document.getElementById("topbar-role-switcher");
    if (!switcher) return;
    switcher.addEventListener("change", (e) => {
      const user = window.TurnamenAPI.setSimulatedRole(e.target.value);
      updateUserTopbar(user);
      window.TurnamenUI.showToast(
        `Peran simulasi diubah ke: ${user.full_name} (${user.role})`,
        "info"
      );
      navigateTo(currentPage);
    });
  }

  function updateRuntimeIndicators(healthRes) {
    const modeBadge = document.getElementById("app-mode-badge");
    const apiStatusEl = document.getElementById("sidebar-api-status");

    if (healthRes && healthRes.success && healthRes.data) {
      window.TurnamenConfig.setRuntimeInfo(healthRes.data);
      const isMock = healthRes.data.is_simulation;
      if (modeBadge) {
        modeBadge.className = isMock ? "badge badge-warning" : "badge badge-success";
        modeBadge.textContent = isMock
          ? "MOCK MODE (DATA SIMULASI LOKAL)"
          : "SUPABASE ONLINE MODE";
      }
      if (apiStatusEl) {
        apiStatusEl.innerHTML = `<span style="color:#34d399;">●</span> Flask API Aktif (${healthRes.data.app_mode})`;
      }
    } else if (apiStatusEl) {
      apiStatusEl.innerHTML = `<span style="color:#f87171;">●</span> Flask API Tidak Terhubung`;
    }

    updateUserTopbar(window.TurnamenConfig.getState().currentUser);
  }

  function updateUserTopbar(user) {
    const label = document.getElementById("topbar-active-user");
    const switcher = document.getElementById("topbar-role-switcher");
    if (label && user) {
      label.textContent = `${user.username} (${user.role})`;
    }
    if (switcher && user) {
      switcher.value = user.role;
    }
  }

  async function navigateTo(pageName, options = {}) {
    if (options.tournamentId) {
      window.TurnamenConfig.setSelectedTournamentId(options.tournamentId);
    }
    currentPage = pageName;

    document.querySelectorAll(".nav-item[data-page]").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-page") === pageName);
    });

    const titleEl = document.getElementById("topbar-page-title");
    if (titleEl) {
      titleEl.textContent = PAGE_TITLES[pageName] || "Turnamen.in";
    }

    const container = document.getElementById("main-content");
    if (!container) return;
    container.innerHTML = window.TurnamenUI.renderLoadingState();

    switch (pageName) {
      case "dashboard":
        await renderDashboard(container);
        break;
      case "tournament-list":
        await renderTournamentList(container);
        break;
      case "tournament-detail":
        await renderTournamentDetail(container);
        break;
      case "team-management":
        await renderTeamManagement(container);
        break;
      case "match-management":
        await renderMatchManagement(container);
        break;
      case "bracket":
        await renderBracketPage(container);
        break;
      case "announcements":
        await renderAnnouncementsPage(container);
        break;
      case "reports":
        await renderReportsPage(container);
        break;
      case "profile":
        await renderProfilePage(container);
        break;
      case "login":
        await renderLoginPage(container);
        break;
      default:
        await renderDashboard(container);
    }
  }

  // =========================================================================
  // 1. DASHBOARD PAGE
  // =========================================================================
  async function renderDashboard(container) {
    const state = window.TurnamenConfig.getState();
    const [tourRes, teamsRes, reportRes] = await Promise.all([
      window.TurnamenAPI.getTournaments(),
      window.TurnamenAPI.getTeams(),
      window.TurnamenAPI.getTournamentReport(state.selectedTournamentId),
    ]);

    if (!tourRes.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(
        tourRes.message,
        "TurnamenApp.navigateTo('dashboard')"
      );
      return;
    }

    cachedTournaments = tourRes.data || [];
    const teams = teamsRes.data || [];
    const report = reportRes.success ? reportRes.data : null;
    const summary = report ? report.summary : {};

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Ringkasan Operasional Turnamen</h2>
          <p>Pantau turnamen aktif, progres bracket Single Elimination, dan pengumuman terbaru.</p>
        </div>
        <div style="display:flex; gap:10px;">
          <button class="btn btn-secondary" onclick="TurnamenApp.navigateTo('bracket')">Lihat Bracket 8 Tim</button>
          <button class="btn btn-primary" onclick="TurnamenApp.navigateTo('tournament-list')">Kelola Turnamen</button>
        </div>
      </div>

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Total Turnamen</div>
          <div class="metric-value">${cachedTournaments.length}</div>
          <div class="metric-note">Mendukung multi-game & multi-turnamen</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Tim Terdaftar</div>
          <div class="metric-value">${teams.length}</div>
          <div class="metric-note">${summary.approved_teams || 8} tim terverifikasi di bracket utama</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Progres Pertandingan</div>
          <div class="metric-value">${summary.completed_matches || 0} / ${summary.total_matches || 0}</div>
          <div class="metric-note">Penyelesaian ${summary.completion_percentage || 0}%</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Hadiah Utama</div>
          <div class="metric-value">${window.TurnamenUI.formatRupiah(summary.prize_pool || 10000000)}</div>
          <div class="metric-note">Nusantara Campus Cup 2026</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Daftar Turnamen Aktif</h3>
            <button class="btn btn-secondary btn-sm" onclick="TurnamenApp.navigateTo('tournament-list')">Lihat Semua</button>
          </div>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Nama Turnamen</th>
                  <th>Game</th>
                  <th>Peserta</th>
                  <th>Status</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                ${cachedTournaments
                  .map(
                    (t) => `
                  <tr>
                    <td><strong>${window.TurnamenUI.escapeHtml(t.title)}</strong></td>
                    <td>${window.TurnamenUI.escapeHtml(t.game_name)}</td>
                    <td class="tabular-nums">${t.approved_teams_count}/${t.max_teams}</td>
                    <td>${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                    <td>
                      <button class="btn btn-secondary btn-sm" onclick="TurnamenApp.navigateTo('tournament-detail', {tournamentId: '${t.id}'})">Detail</button>
                    </td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Log Aktivitas & Audit Terbaru</h3>
            <span class="badge badge-info">Audit Trail</span>
          </div>
          ${
            report && report.recent_activity && report.recent_activity.length
              ? `<div class="table-container">
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
                          <td class="tabular-nums">${window.TurnamenUI.escapeHtml(String(log.created_at).slice(0, 19).replace("T", " "))}</td>
                        </tr>
                      `
                        )
                        .join("")}
                    </tbody>
                  </table>
                </div>`
              : window.TurnamenUI.renderEmptyState("Belum Ada Aktivitas")
          }
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 2. TOURNAMENT LIST PAGE
  // =========================================================================
  async function renderTournamentList(container, filterStatus = "") {
    const res = await window.TurnamenAPI.getTournaments(
      filterStatus ? { status: filterStatus } : {}
    );
    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message);
      return;
    }
    const list = res.data || [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Manajemen Daftar Turnamen</h2>
          <p>Kelola seluruh turnamen lintas cabang game e-sport.</p>
        </div>
        <button class="btn btn-primary" onclick="TurnamenApp.openCreateTournamentModal()">+ Buat Turnamen Baru</button>
      </div>

      <div class="filter-bar">
        <select id="filter-tournament-status" class="form-select" onchange="TurnamenApp.filterTournaments(this.value)">
          <option value="" ${filterStatus === "" ? "selected" : ""}>Semua Status</option>
          <option value="ongoing" ${filterStatus === "ongoing" ? "selected" : ""}>Sedang Berlangsung (Ongoing)</option>
          <option value="open_registration" ${filterStatus === "open_registration" ? "selected" : ""}>Pendaftaran Dibuka</option>
          <option value="draft" ${filterStatus === "draft" ? "selected" : ""}>Draft</option>
          <option value="completed" ${filterStatus === "completed" ? "selected" : ""}>Selesai</option>
        </select>
      </div>

      <div class="card">
        ${
          list.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Tidak Ada Turnamen Ditemukan",
                "Belum ada turnamen yang sesuai dengan filter status tersebut."
              )
            : `
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
                  .map(
                    (t) => `
                  <tr>
                    <td>
                      <strong>${window.TurnamenUI.escapeHtml(t.title)}</strong>
                      <div style="font-size:11.5px; color:var(--text-muted);">${window.TurnamenUI.escapeHtml(t.venue)}</div>
                    </td>
                    <td>${window.TurnamenUI.escapeHtml(t.game_name)}</td>
                    <td class="tabular-nums">Single Elim (Bo${t.best_of})</td>
                    <td class="tabular-nums">${t.approved_teams_count} / ${t.max_teams} Tim</td>
                    <td class="tabular-nums">${window.TurnamenUI.formatRupiah(t.prize_pool)}</td>
                    <td>${window.TurnamenUI.renderStatusBadge(t.status)}</td>
                    <td style="display:flex; gap:6px;">
                      <button class="btn btn-secondary btn-sm" onclick="TurnamenApp.navigateTo('tournament-detail', {tournamentId: '${t.id}'})">Peserta</button>
                      <button class="btn btn-primary btn-sm" onclick="TurnamenApp.navigateTo('bracket', {tournamentId: '${t.id}'})">Bracket</button>
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

  function openCreateTournamentModal() {
    const gameOptions = cachedGames
      .map(
        (g) => `<option value="${g.id}">${window.TurnamenUI.escapeHtml(g.name)}</option>`
      )
      .join("");

    window.TurnamenUI.openModal({
      title: "Buat Turnamen E-Sport Baru",
      bodyHtml: `
        <div class="form-group">
          <label class="form-label">Judul Turnamen</label>
          <input id="new-tour-title" class="form-input" placeholder="Contoh: Piala Kampus Nasional 2026" />
        </div>
        <div class="form-group">
          <label class="form-label">Cabang Game</label>
          <select id="new-tour-game" class="form-select">${gameOptions}</select>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label class="form-label">Kuota Tim (Max Teams)</label>
            <select id="new-tour-max-teams" class="form-select">
              <option value="4">4 Tim</option>
              <option value="8" selected>8 Tim</option>
              <option value="16">16 Tim</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Format Seri (Best Of)</label>
            <select id="new-tour-bo" class="form-select">
              <option value="1">Best of 1 (Bo1)</option>
              <option value="3" selected>Best of 3 (Bo3)</option>
              <option value="5">Best of 5 (Bo5)</option>
            </select>
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label class="form-label">Biaya Registrasi (Rp)</label>
            <input id="new-tour-fee" type="number" class="form-input tabular-nums" value="50000" />
          </div>
          <div class="form-group">
            <label class="form-label">Total Hadiah (Rp)</label>
            <input id="new-tour-prize" type="number" class="form-input tabular-nums" value="5000000" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Tanggal Mulai</label>
          <input id="new-tour-start" type="date" class="form-input tabular-nums" value="2026-12-01" />
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary" onclick="TurnamenUI.closeModal()">Batal</button>
        <button class="btn btn-primary" onclick="TurnamenApp.submitCreateTournament()">Simpan Turnamen</button>
      `,
    });
  }

  async function submitCreateTournament() {
    const payload = {
      title: document.getElementById("new-tour-title")?.value || "",
      game_id: document.getElementById("new-tour-game")?.value || "",
      max_teams: Number(document.getElementById("new-tour-max-teams")?.value || 8),
      best_of: Number(document.getElementById("new-tour-bo")?.value || 3),
      registration_fee: Number(document.getElementById("new-tour-fee")?.value || 0),
      prize_pool: Number(document.getElementById("new-tour-prize")?.value || 0),
      start_date: `${document.getElementById("new-tour-start")?.value || "2026-12-01"}T10:00:00+07:00`,
      status: "open_registration",
    };

    const res = await window.TurnamenAPI.createTournament(payload);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Turnamen baru berhasil dibuat!", "success");
    await navigateTo("tournament-list");
  }

  // =========================================================================
  // 3. TOURNAMENT DETAIL & REGISTRATIONS PAGE
  // =========================================================================
  async function renderTournamentDetail(container) {
    const tid = window.TurnamenConfig.getState().selectedTournamentId;
    const [tourRes, regsRes, teamsRes] = await Promise.all([
      window.TurnamenAPI.getTournamentById(tid),
      window.TurnamenAPI.getTournamentRegistrations(tid),
      window.TurnamenAPI.getTeams(),
    ]);

    if (!tourRes.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(tourRes.message);
      return;
    }

    const t = tourRes.data;
    const regs = regsRes.data || [];
    const teams = teamsRes.data || [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>${window.TurnamenUI.escapeHtml(t.title)}</h2>
          <p>${window.TurnamenUI.escapeHtml(t.description)}</p>
        </div>
        <div style="display:flex; gap:8px;">
          ${window.TurnamenUI.renderStatusBadge(t.status)}
          <button class="btn btn-primary btn-sm" onclick="TurnamenApp.navigateTo('bracket', {tournamentId: '${t.id}'})">Buka Bracket</button>
        </div>
      </div>

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Cabang Game</div>
          <div class="metric-value" style="font-size:17px;">${window.TurnamenUI.escapeHtml(t.game_name)}</div>
          <div class="metric-note">Format Bo${t.best_of}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Peserta Terverifikasi</div>
          <div class="metric-value">${t.approved_teams_count} / ${t.max_teams}</div>
          <div class="metric-note">Total Pendaftar: ${t.registered_teams_count}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Biaya Pendaftaran</div>
          <div class="metric-value" style="font-size:18px;">${window.TurnamenUI.formatRupiah(t.registration_fee)}</div>
          <div class="metric-note">Venue: ${window.TurnamenUI.escapeHtml(t.venue)}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Prize Pool</div>
          <div class="metric-value" style="font-size:18px;">${window.TurnamenUI.formatRupiah(t.prize_pool)}</div>
          <div class="metric-note">Single Elimination</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Daftar Tim Peserta & Verifikasi Registrasi</h3>
          <div style="display:flex; gap:8px;">
            <select id="reg-team-select" class="form-select">
              ${teams.map((tm) => `<option value="${tm.id}">${window.TurnamenUI.escapeHtml(tm.name)} [${tm.tag}]</option>`).join("")}
            </select>
            <button class="btn btn-secondary btn-sm" onclick="TurnamenApp.registerSelectedTeam('${t.id}')">+ Daftarkan Tim</button>
          </div>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Seed</th>
                <th>Nama Tim</th>
                <th>Tag</th>
                <th>Catatan Verifikasi</th>
                <th>Status</th>
                <th>Aksi Panitia</th>
              </tr>
            </thead>
            <tbody>
              ${regs
                .map(
                  (r) => `
                <tr>
                  <td class="tabular-nums">#${r.seed_number || "-"}</td>
                  <td><strong>${window.TurnamenUI.escapeHtml(r.team_name)}</strong></td>
                  <td class="tabular-nums">${window.TurnamenUI.escapeHtml(r.team_tag)}</td>
                  <td>${window.TurnamenUI.escapeHtml(r.notes || "-")}</td>
                  <td>${window.TurnamenUI.renderStatusBadge(r.status)}</td>
                  <td style="display:flex; gap:6px;">
                    <button class="btn btn-success btn-sm" onclick="TurnamenApp.verifyRegistration('${r.id}', 'approved')">Setujui</button>
                    <button class="btn btn-danger btn-sm" onclick="TurnamenApp.verifyRegistration('${r.id}', 'rejected')">Tolak</button>
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  async function registerSelectedTeam(tournamentId) {
    const teamId = document.getElementById("reg-team-select")?.value;
    if (!teamId) return;
    const res = await window.TurnamenAPI.registerTeamToTournament(tournamentId, {
      team_id: teamId,
      notes: "Pendaftaran via Dashboard",
    });
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.showToast("Tim berhasil didaftarkan!", "success");
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
    window.TurnamenUI.showToast(`Status pendaftaran diubah ke ${newStatus}`, "success");
    await navigateTo("tournament-detail");
  }

  // =========================================================================
  // 4. TEAM MANAGEMENT PAGE
  // =========================================================================
  async function renderTeamManagement(container) {
    const res = await window.TurnamenAPI.getTeams();
    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message);
      return;
    }
    const teams = res.data || [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Manajemen Tim & Roster Pemain</h2>
          <p>Kelola data tim e-sport, kapten tim, dan ID in-game anggota.</p>
        </div>
        <button class="btn btn-primary" onclick="TurnamenApp.openCreateTeamModal()">+ Buat Tim Baru</button>
      </div>

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
              </tr>
            </thead>
            <tbody>
              ${teams
                .map(
                  (tm) => `
                <tr>
                  <td class="tabular-nums"><span class="badge badge-info">${window.TurnamenUI.escapeHtml(tm.tag)}</span></td>
                  <td><strong>${window.TurnamenUI.escapeHtml(tm.name)}</strong></td>
                  <td>${window.TurnamenUI.escapeHtml(tm.game_name)}</td>
                  <td>${window.TurnamenUI.escapeHtml(tm.region)}</td>
                  <td class="tabular-nums">${tm.member_count} Pemain</td>
                  <td>
                    ${(tm.members || [])
                      .map(
                        (m) =>
                          `<span class="badge badge-neutral" style="margin-right:4px;">${window.TurnamenUI.escapeHtml(m.nickname)} (${window.TurnamenUI.escapeHtml(m.ingame_id)})</span>`
                      )
                      .join("")}
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  function openCreateTeamModal() {
    const gameOptions = cachedGames
      .map((g) => `<option value="${g.id}">${window.TurnamenUI.escapeHtml(g.name)}</option>`)
      .join("");
    window.TurnamenUI.openModal({
      title: "Registrasi Tim E-Sport Baru",
      bodyHtml: `
        <div class="form-group">
          <label class="form-label">Nama Tim</label>
          <input id="new-team-name" class="form-input" placeholder="Contoh: Krakatau Esports" />
        </div>
        <div class="grid-2" style="margin-bottom:0;">
          <div class="form-group">
            <label class="form-label">Tag Tim (2-6 Huruf)</label>
            <input id="new-team-tag" class="form-input tabular-nums" placeholder="KRK" maxlength="6" />
          </div>
          <div class="form-group">
            <label class="form-label">Kota / Region</label>
            <input id="new-team-region" class="form-input" value="Jakarta" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Cabang Game</label>
          <select id="new-team-game" class="form-select">${gameOptions}</select>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary" onclick="TurnamenUI.closeModal()">Batal</button>
        <button class="btn btn-primary" onclick="TurnamenApp.submitCreateTeam()">Simpan Tim</button>
      `,
    });
  }

  async function submitCreateTeam() {
    const payload = {
      name: document.getElementById("new-team-name")?.value || "",
      tag: document.getElementById("new-team-tag")?.value || "",
      region: document.getElementById("new-team-region")?.value || "Indonesia",
      game_id: document.getElementById("new-team-game")?.value || "",
    };
    const res = await window.TurnamenAPI.createTeam(payload);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Tim berhasil dibuat!", "success");
    await navigateTo("team-management");
  }

  // =========================================================================
  // 5. MATCH MANAGEMENT & SCORE SUBMISSION PAGE
  // =========================================================================
  async function renderMatchManagement(container) {
    const tid = window.TurnamenConfig.getState().selectedTournamentId;
    const res = await window.TurnamenAPI.getTournamentMatches(tid);
    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message);
      return;
    }

    const data = res.data;
    const matches = data.matches || [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Manajemen Pertandingan & Pengesahan Skor</h2>
          <p>Turnamen Aktif: <strong>${window.TurnamenUI.escapeHtml(data.tournament_title)}</strong> (Format Best of ${data.best_of})</p>
        </div>
        <button class="btn btn-secondary" onclick="TurnamenApp.navigateTo('bracket')">Lihat Bagan Bracket</button>
      </div>

      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Babak</th>
                <th>Match #</th>
                <th>Team A</th>
                <th>Skor</th>
                <th>Team B</th>
                <th>Pemenang</th>
                <th>Status</th>
                <th>Input / Sahkan Skor (Bo${data.best_of})</th>
              </tr>
            </thead>
            <tbody>
              ${matches
                .map(
                  (m) => `
                <tr>
                  <td><strong>${window.TurnamenUI.escapeHtml(m.round_name)}</strong></td>
                  <td class="tabular-nums">#${m.match_number}</td>
                  <td>${window.TurnamenUI.escapeHtml(m.team_a_name)}</td>
                  <td class="tabular-nums"><strong>${m.score_a} - ${m.score_b}</strong></td>
                  <td>${window.TurnamenUI.escapeHtml(m.team_b_name)}</td>
                  <td>${m.winner_team_name ? `<span class="badge badge-success">${window.TurnamenUI.escapeHtml(m.winner_team_name)}</span>` : "-"}</td>
                  <td>${window.TurnamenUI.renderStatusBadge(m.status)}</td>
                  <td>
                    ${
                      m.team_a_id && m.team_b_id && m.status !== "completed"
                        ? `
                      <div style="display:flex; align-items:center; gap:6px;">
                        <input id="score-a-${m.id}" type="number" min="0" max="4" value="${m.score_a}" class="form-input tabular-nums" style="width:54px; padding:4px 6px;" />
                        <span>:</span>
                        <input id="score-b-${m.id}" type="number" min="0" max="4" value="${m.score_b}" class="form-input tabular-nums" style="width:54px; padding:4px 6px;" />
                        <button class="btn btn-primary btn-sm" onclick="TurnamenApp.submitScore('${m.id}')">Sahkan</button>
                      </div>
                    `
                        : `<span style="font-size:12px; color:var(--text-muted);">${
                            m.status === "completed"
                              ? "Terkunci (Audited)"
                              : "Menunggu Lawan"
                          }</span>`
                    }
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  async function submitScore(matchId) {
    const scoreA = Number(document.getElementById(`score-a-${matchId}`)?.value || 0);
    const scoreB = Number(document.getElementById(`score-b-${matchId}`)?.value || 0);

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
      "Skor disahkan! Pemenang otomatis maju ke babak berikutnya.",
      "success"
    );
    await navigateTo("match-management");
  }

  // =========================================================================
  // 6. BRACKET VISUALIZATION PAGE (SINGLE ELIMINATION)
  // =========================================================================
  async function renderBracketPage(container) {
    const tid = window.TurnamenConfig.getState().selectedTournamentId;
    const res = await window.TurnamenAPI.getTournamentMatches(tid);
    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message);
      return;
    }

    const data = res.data;
    const rounds = data.rounds || [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Single Elimination Bracket — ${window.TurnamenUI.escapeHtml(data.tournament_title)}</h2>
          <p>Pemenang setiap babak otomatis mengisi slot pertandingan berikutnya setelah skor disahkan.</p>
        </div>
        <div style="display:flex; gap:10px;">
          <button class="btn btn-secondary" onclick="TurnamenApp.navigateTo('match-management')">Kelola Skor</button>
          <button class="btn btn-primary" onclick="TurnamenApp.regenerateBracket('${data.tournament_id}')">Reset / Generate Ulang Bracket</button>
        </div>
      </div>

      <div class="card">
        ${
          rounds.length === 0
            ? window.TurnamenUI.renderEmptyState(
                "Bracket Belum Dibuat",
                "Klik tombol Generate Bracket untuk menyusun jadwal Single Elimination dari tim yang telah disetujui."
              )
            : `
          <div class="bracket-board">
            ${rounds
              .map(
                (round) => `
              <div class="bracket-round">
                <div class="bracket-round-header">
                  <span>${window.TurnamenUI.escapeHtml(round.round_name)}</span>
                  <span class="tabular-nums">${round.matches.length} Match</span>
                </div>
                <div class="bracket-matches-col">
                  ${round.matches
                    .map(
                      (m) => `
                    <div class="bracket-match-card">
                      <div class="bracket-match-meta">
                        <span class="tabular-nums">Match #${m.match_number} (Bo${m.best_of})</span>
                        <span>${window.TurnamenUI.escapeHtml(m.status.toUpperCase())}</span>
                      </div>
                      <div class="bracket-team-row ${m.winner_team_id && m.winner_team_id === m.team_a_id ? "winner" : ""}">
                        <span>${window.TurnamenUI.escapeHtml(m.team_a_name)}</span>
                        <span class="bracket-score">${m.score_a}</span>
                      </div>
                      <div class="bracket-team-row ${m.winner_team_id && m.winner_team_id === m.team_b_id ? "winner" : ""}">
                        <span>${window.TurnamenUI.escapeHtml(m.team_b_name)}</span>
                        <span class="bracket-score">${m.score_b}</span>
                      </div>
                    </div>
                  `
                    )
                    .join("")}
                </div>
              </div>
            `
              )
              .join("")}
          </div>
        `
        }
      </div>
    `;
  }

  async function regenerateBracket(tournamentId) {
    const res = await window.TurnamenAPI.generateBracket(tournamentId);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.showToast("Bracket Single Elimination berhasil disusun!", "success");
    await navigateTo("bracket");
  }

  // =========================================================================
  // 7. ANNOUNCEMENTS PAGE
  // =========================================================================
  async function renderAnnouncementsPage(container) {
    const tid = window.TurnamenConfig.getState().selectedTournamentId;
    const res = await window.TurnamenAPI.getAnnouncements(tid);
    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message);
      return;
    }
    const items = res.data || [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Papan Pengumuman Turnamen</h2>
          <p>Informasi teknis, pembaruan jadwal, dan instruksi check-in dari panitia.</p>
        </div>
        <button class="btn btn-primary" onclick="TurnamenApp.openAnnouncementModal('${tid}')">+ Buat Pengumuman</button>
      </div>

      <div style="display:flex; flex-direction:column; gap:14px;">
        ${
          items.length === 0
            ? window.TurnamenUI.renderEmptyState("Belum Ada Pengumuman")
            : items
                .map(
                  (a) => `
              <div class="card">
                <div class="card-header">
                  <div style="display:flex; align-items:center; gap:10px;">
                    ${a.is_pinned ? `<span class="badge badge-warning">📌 Disematkan</span>` : ""}
                    ${window.TurnamenUI.renderStatusBadge(a.priority)}
                    <h3 class="card-title">${window.TurnamenUI.escapeHtml(a.title)}</h3>
                  </div>
                  <span style="font-size:12px; color:var(--text-muted);" class="tabular-nums">
                    Oleh ${window.TurnamenUI.escapeHtml(a.author_name || "Panitia")}
                  </span>
                </div>
                <p style="margin:0; color:var(--text-secondary);">${window.TurnamenUI.escapeHtml(a.content)}</p>
              </div>
            `
                )
                .join("")
        }
      </div>
    `;
  }

  function openAnnouncementModal(tournamentId) {
    window.TurnamenUI.openModal({
      title: "Publikasikan Pengumuman Resmi",
      bodyHtml: `
        <div class="form-group">
          <label class="form-label">Judul Pengumuman</label>
          <input id="ann-title" class="form-input" placeholder="Contoh: Perubahan Jadwal Semi Final" />
        </div>
        <div class="form-group">
          <label class="form-label">Prioritas</label>
          <select id="ann-priority" class="form-select">
            <option value="normal">Normal</option>
            <option value="important" selected>Penting (Important)</option>
            <option value="urgent">Mendesak (Urgent)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Isi Pengumuman</label>
          <textarea id="ann-content" rows="4" class="form-textarea" placeholder="Tulis instruksi lengkap untuk peserta..."></textarea>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary" onclick="TurnamenUI.closeModal()">Batal</button>
        <button class="btn btn-primary" onclick="TurnamenApp.submitAnnouncement('${tournamentId}')">Publikasikan</button>
      `,
    });
  }

  async function submitAnnouncement(tournamentId) {
    const payload = {
      title: document.getElementById("ann-title")?.value || "",
      priority: document.getElementById("ann-priority")?.value || "normal",
      content: document.getElementById("ann-content")?.value || "",
      is_pinned: false,
    };
    const res = await window.TurnamenAPI.createAnnouncement(tournamentId, payload);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    window.TurnamenUI.closeModal();
    window.TurnamenUI.showToast("Pengumuman berhasil dipublikasikan!", "success");
    await navigateTo("announcements");
  }

  // =========================================================================
  // 8. REPORTS & STANDINGS PAGE
  // =========================================================================
  async function renderReportsPage(container) {
    const tid = window.TurnamenConfig.getState().selectedTournamentId;
    const res = await window.TurnamenAPI.getTournamentReport(tid);
    if (!res.success) {
      container.innerHTML = window.TurnamenUI.renderErrorState(res.message);
      return;
    }

    const report = res.data;
    const s = report.summary;
    const standings = report.standings || [];

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Laporan & Klasemen — ${window.TurnamenUI.escapeHtml(report.tournament.title)}</h2>
          <p>Statistik penyelesaian pertandingan dan rekor menang-kalah seluruh tim peserta.</p>
        </div>
      </div>

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-label">Tingkat Penyelesaian</div>
          <div class="metric-value">${s.completion_percentage}%</div>
          <div class="metric-note">${s.completed_matches} dari ${s.total_matches} pertandingan selesai</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Tim Terverifikasi</div>
          <div class="metric-value">${s.approved_teams} / ${s.max_teams}</div>
          <div class="metric-note">Menunggu verifikasi: ${s.pending_registrations}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Pertandingan Tersisa</div>
          <div class="metric-value">${s.scheduled_matches}</div>
          <div class="metric-note">Menunggu hasil pertandingan</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Juara Turnamen</div>
          <div class="metric-value" style="font-size:16px;">${window.TurnamenUI.escapeHtml(s.champion_team || "Belum Ditentukan")}</div>
          <div class="metric-note">Menunggu Grand Final selesai</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Tabel Klasemen & Statistik Tim (Standings)</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Peringkat</th>
                <th>Tag</th>
                <th>Nama Tim</th>
                <th>Main</th>
                <th>Menang (Match)</th>
                <th>Kalah (Match)</th>
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
                  <td class="tabular-nums" style="color:#34d399; font-weight:700;">${row.matches_won}</td>
                  <td class="tabular-nums" style="color:#f87171;">${row.matches_lost}</td>
                  <td class="tabular-nums">${row.games_won} - ${row.games_lost}</td>
                  <td>${window.TurnamenUI.escapeHtml(row.highest_round_name)}</td>
                  <td><span class="badge badge-info">${window.TurnamenUI.escapeHtml(row.placement_label)}</span></td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 9. USER PROFILE & SYSTEM DIAGNOSTICS PAGE
  // =========================================================================
  async function renderProfilePage(container) {
    const state = window.TurnamenConfig.getState();
    const user = state.currentUser;

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Profil Pengguna & Diagnostik Lingkungan</h2>
          <p>Informasi akun aktif, role RBAC, dan konfigurasi koneksi aplikasi.</p>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Identitas Akun Aktif</h3>
            <span class="badge badge-info">${window.TurnamenUI.escapeHtml(user.role)}</span>
          </div>
          <div class="form-group">
            <label class="form-label">Nama Lengkap</label>
            <input class="form-input" value="${window.TurnamenUI.escapeHtml(user.full_name)}" readonly />
          </div>
          <div class="form-group">
            <label class="form-label">Username</label>
            <input class="form-input tabular-nums" value="${window.TurnamenUI.escapeHtml(user.username)}" readonly />
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input class="form-input tabular-nums" value="${window.TurnamenUI.escapeHtml(user.email)}" readonly />
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Status Runtime & Konfigurasi</h3>
          </div>
          <p style="color:var(--text-secondary); margin-top:0;">
            Mode Operasi Saat Ini: <strong>${state.appMode.toUpperCase()}</strong>
            (${state.isSimulation ? "Menggunakan MockDataStoreRepository lokal tanpa kredensial cloud" : "Terhubung ke Supabase"})
          </p>
          <p style="color:var(--text-secondary);">
            Endpoint REST API Lokal: <code class="tabular-nums">${window.TurnamenUI.escapeHtml(state.apiBaseUrl)}</code>
          </p>
          <button class="btn btn-secondary" onclick="TurnamenApp.navigateTo('login')">Ganti Akun / Login Ulang</button>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 10. LOGIN & ROLE SIMULATION PAGE
  // =========================================================================
  async function renderLoginPage(container) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <h2>Masuk ke Turnamen.in</h2>
          <p>Gunakan form login atau pilih salah satu dari 5 akun role demo (password demo: <code>turnamen123</code>).</p>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Login dengan Email & Password</h3>
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input id="login-email" class="form-input" value="organizer@turnamen.in" />
          </div>
          <div class="form-group">
            <label class="form-label">Password</label>
            <input id="login-password" type="password" class="form-input" value="turnamen123" />
          </div>
          <button class="btn btn-primary" onclick="TurnamenApp.handleLoginSubmit()">Masuk Sekarang</button>
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Pilih Cepat Akun Demo (Mock Mode)</h3>
            <span class="badge badge-warning">5 Role RBAC</span>
          </div>
          <p style="color:var(--text-secondary); margin-top:0;">
            Klik salah satu role di bawah ini untuk langsung menguji hak akses di seluruh halaman:
          </p>
          <div style="display:flex; flex-direction:column; gap:8px;">
            <button class="btn btn-secondary" onclick="TurnamenApp.quickSwitchRole('super_admin')">1. Super Admin (admin@turnamen.in)</button>
            <button class="btn btn-secondary" onclick="TurnamenApp.quickSwitchRole('organizer')">2. Tournament Organizer (organizer@turnamen.in)</button>
            <button class="btn btn-secondary" onclick="TurnamenApp.quickSwitchRole('committee')">3. Committee / Panitia (committee@turnamen.in)</button>
            <button class="btn btn-secondary" onclick="TurnamenApp.quickSwitchRole('team_captain')">4. Team Captain (captain@turnamen.in)</button>
            <button class="btn btn-secondary" onclick="TurnamenApp.quickSwitchRole('player')">5. Player (player@turnamen.in)</button>
          </div>
        </div>
      </div>
    `;
  }

  async function handleLoginSubmit() {
    const email = document.getElementById("login-email")?.value || "";
    const password = document.getElementById("login-password")?.value || "";
    const res = await window.TurnamenAPI.login(email, password);
    if (!res.success) {
      window.TurnamenUI.showToast(res.message, "danger");
      return;
    }
    updateUserTopbar(res.data.user);
    window.TurnamenUI.showToast(`Selamat datang, ${res.data.user.full_name}!`, "success");
    await navigateTo("dashboard");
  }

  async function quickSwitchRole(roleName) {
    const user = window.TurnamenAPI.setSimulatedRole(roleName);
    updateUserTopbar(user);
    window.TurnamenUI.showToast(`Beralih ke akun demo: ${user.full_name}`, "success");
    await navigateTo("dashboard");
  }

  window.TurnamenApp = {
    initApp,
    navigateTo,
    filterTournaments(status) {
      const container = document.getElementById("main-content");
      if (container) renderTournamentList(container, status);
    },
    openCreateTournamentModal,
    submitCreateTournament,
    registerSelectedTeam,
    verifyRegistration,
    openCreateTeamModal,
    submitCreateTeam,
    submitScore,
    regenerateBracket,
    openAnnouncementModal,
    submitAnnouncement,
    handleLoginSubmit,
    quickSwitchRole,
  };

  document.addEventListener("DOMContentLoaded", initApp);
})(window, document);
