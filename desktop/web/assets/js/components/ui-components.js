/**
 * Turnamen.in: Reusable Futuristic Arena UI Components (`window.TurnamenUI`)
 * Owner: Fikri (System Integration & Desktop UI/UX)
 * Provides SVG icons, badges, loading/empty/error states, accessible modal, and toasts.
 */
(function (window, document) {
  "use strict";

  const STATUS_MAP = {
    ongoing: { label: "LIVE | Sedang Berlangsung", cls: "badge-warning", live: true },
    open_registration: { label: "Pendaftaran Dibuka", cls: "badge-info", live: false },
    registration_closed: { label: "Pendaftaran Ditutup", cls: "badge-neutral", live: false },
    completed: { label: "Selesai", cls: "badge-success", live: false },
    draft: { label: "Draft", cls: "badge-neutral", live: false },
    cancelled: { label: "Dibatalkan", cls: "badge-danger", live: false },
    approved: { label: "Disetujui", cls: "badge-success", live: false },
    pending: { label: "Menunggu Verifikasi", cls: "badge-warning", live: false },
    rejected: { label: "Ditolak", cls: "badge-danger", live: false },
    withdrawn: { label: "Mengundurkan Diri", cls: "badge-neutral", live: false },
    scheduled: { label: "Terjadwal", cls: "badge-info", live: false },
    bye: { label: "BYE (Lolos Otomatis)", cls: "badge-neutral", live: false },
    disputed: { label: "Sengketa Skor", cls: "badge-danger", live: false },
    urgent: { label: "Mendesak", cls: "badge-danger", live: false },
    important: { label: "Penting", cls: "badge-warning", live: false },
    normal: { label: "Info", cls: "badge-info", live: false },
  };

  const ROLE_MAP = {
    super_admin: { label: "Super Admin", cls: "badge-violet" },
    organizer: { label: "Tournament Organizer", cls: "badge-info" },
    committee: { label: "Committee / Panitia", cls: "badge-warning" },
    team_captain: { label: "Team Captain", cls: "badge-success" },
    player: { label: "Player", cls: "badge-neutral" },
  };

  const ICON_PATHS = {
    trophy:
      '<path d="M6 4h12v5a6 6 0 0 1-12 0V4z"/><path d="M6 6H3v2a3 3 0 0 0 3 3M18 6h3v2a3 3 0 0 1-3 3M12 15v5M8 20h8"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
    shield: '<path d="M12 3l7 3v5c0 4.5-3 8.4-7 10-4-1.6-7-5.5-7-10V6l7-3z"/>',
    users:
      '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    bracket: '<path d="M3 6h5v4H3M3 14h5v4H3M8 8h4v8H8M12 12h5M17 9h4v6h-4z"/>',
    alert:
      '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    empty:
      '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 15h6"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    pin: '<path d="M12 17v5M9 3h6l-1 6 3 3v2H7v-2l3-3-1-6z"/>',
    refresh:
      '<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>',
    check: '<path d="M20 6L9 17l-5-5"/>',
    close: '<path d="M18 6L6 18M6 6l12 12"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
    dashboard:
      '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    detail:
      '<path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/>',
    swords: '<path d="M4 20l6-6M14 4l6 6-8 8-6-6 8-8zM15 9l-6 6"/>',
    megaphone:
      '<path d="M3 11l14-5v12L3 13v-2zM17 8a4 4 0 0 1 0 8M7 14l1.5 5H11l-1.2-4.5"/>',
    chart: '<path d="M4 20h16M7 16v-5M12 16V7M17 16v-8"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5"/>',
    login:
      '<path d="M10 17l5-5-5-5M15 12H3M14 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5"/>',
  };

  let modalCleanup = null;
  let lastFocusedBeforeModal = null;

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function icon(name, size = 16, className = "") {
    const paths = ICON_PATHS[name] || ICON_PATHS.info;
    const clsAttr = className ? ` class="${escapeHtml(className)}"` : "";
    return `<svg${clsAttr} width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
  }

  function formatRupiah(amount) {
    const num = Number(amount || 0);
    if (!Number.isFinite(num) || num <= 0) return "Gratis";
    return "Rp " + num.toLocaleString("id-ID");
  }

  function formatDateTime(isoStr) {
    if (!isoStr) return "-";
    const parsed = new Date(isoStr);
    if (Number.isNaN(parsed.getTime())) {
      return String(isoStr).slice(0, 19).replace("T", " ");
    }
    return parsed.toLocaleString("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatDateOnly(isoStr) {
    if (!isoStr) return "-";
    const parsed = new Date(isoStr);
    if (Number.isNaN(parsed.getTime())) {
      return String(isoStr).slice(0, 10);
    }
    return parsed.toLocaleDateString("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function renderStatusBadge(status) {
    const key = String(status || "").toLowerCase();
    const info = STATUS_MAP[key] || {
      label: escapeHtml(status || "-"),
      cls: "badge-neutral",
      live: false,
    };
    const dot = info.live ? `<span class="badge-live-dot" aria-hidden="true"></span>` : "";
    return `<span class="badge ${info.cls}">${dot}${info.label}</span>`;
  }

  function renderRoleBadge(role) {
    if (!role) {
      return `<span class="badge badge-neutral">Tamu (Belum Masuk)</span>`;
    }
    const key = String(role).toLowerCase();
    const info = ROLE_MAP[key] || { label: escapeHtml(role), cls: "badge-neutral" };
    return `<span class="badge ${info.cls}">${info.label}</span>`;
  }

  function renderLoadingState(
    message = "Memuat data arena...",
    detail = "Mengambil data terbaru dari server API lokal."
  ) {
    return `
      <div class="state-box" role="status" aria-live="polite">
        <div class="state-icon">
          <span class="arena-spinner" aria-hidden="true"></span>
        </div>
        <h3>${escapeHtml(message)}</h3>
        <p>${escapeHtml(detail)}</p>
      </div>
    `;
  }

  function renderEmptyState(
    title = "Belum Ada Data",
    subtitle = "Data untuk bagian ini masih kosong.",
    actionHtml = ""
  ) {
    return `
      <div class="state-box">
        <div class="state-icon">${icon("empty", 20)}</div>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(subtitle)}</p>
        ${actionHtml ? `<div class="state-actions">${actionHtml}</div>` : ""}
      </div>
    `;
  }

  function renderErrorState(message = "Gagal memuat data", retryCallbackOrAction = "") {
    let retryAttr = "";
    if (typeof retryCallbackOrAction === "string" && retryCallbackOrAction.trim()) {
      const trimmed = retryCallbackOrAction.trim();
      if (trimmed.includes("(")) {
        retryAttr = `onclick="${escapeHtml(trimmed)}"`;
      } else {
        retryAttr = `data-action="${escapeHtml(trimmed)}"`;
      }
    }
    return `
      <div class="state-box state-box-error" role="alert">
        <div class="state-icon">${icon("alert", 20)}</div>
        <h3>Gagal Memuat Data</h3>
        <p>${escapeHtml(message)}</p>
        ${
          retryAttr
            ? `<div class="state-actions"><button type="button" class="btn btn-secondary btn-sm" ${retryAttr}>${icon("refresh", 14)}<span>Coba Lagi</span></button></div>`
            : ""
        }
      </div>
    `;
  }

  function renderAuthNotice(
    title = "Akses Terbatas",
    message = "Masuk terlebih dahulu untuk mengakses aksi akun pada bagian ini.",
    ctaLabel = "Buka Halaman Login"
  ) {
    return `
      <div class="notice-banner" role="region" aria-label="${escapeHtml(title)}">
        <div>
          <strong>${escapeHtml(title)}:</strong>
          <span>${escapeHtml(message)}</span>
        </div>
        <button type="button" class="btn btn-primary btn-sm" data-action="go-page" data-page="login">
          ${escapeHtml(ctaLabel)}
        </button>
      </div>
    `;
  }

  function renderAccessDeniedState(
    title = "Akses Ditolak",
    message = "Role akun Anda tidak memiliki izin untuk membuka halaman ini.",
    actionHtml = ""
  ) {
    return `
      <div class="state-box state-box-denied" role="alert">
        <div class="state-icon">${icon("lock", 20)}</div>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(message)}</p>
        ${actionHtml ? `<div class="state-actions">${actionHtml}</div>` : ""}
      </div>
    `;
  }

  const GAME_ARTWORK_REGISTRY = {
    "mobile-legends": {
      slug: "mobile-legends",
      src: "assets/images/games/mobile-legends.svg",
      webpSrc: "assets/images/games/mobile-legends.webp",
      primary: "#00E5FF",
      secondary: "#8B5CF6",
      code: "MOBA 5V5",
      accentShape:
        '<polygon points="160,18 214,64 194,116 126,116 106,64" fill="none" stroke="#00E5FF" stroke-width="2"/><polygon points="160,34 196,66 182,102 138,102 124,66" fill="rgba(0,229,255,0.14)" stroke="#8B5CF6" stroke-width="1.5"/>',
    },
    valorant: {
      slug: "valorant",
      src: "assets/images/games/valorant.svg",
      webpSrc: "assets/images/games/valorant.webp",
      primary: "#38EEFF",
      secondary: "#A78BFA",
      code: "TACTICAL FPS",
      accentShape:
        '<path d="M116 30L160 112L204 30" fill="none" stroke="#00E5FF" stroke-width="2.5"/><path d="M134 42L160 90L186 42" fill="none" stroke="#8B5CF6" stroke-width="1.5"/><circle cx="160" cy="34" r="4" fill="#00E5FF"/>',
    },
    "ea-sports-fc": {
      slug: "ea-sports-fc",
      src: "assets/images/games/ea-sports-fc.svg",
      webpSrc: "assets/images/games/ea-sports-fc.webp",
      primary: "#34D399",
      secondary: "#00E5FF",
      code: "SPORTS 1V1",
      accentShape:
        '<circle cx="160" cy="70" r="38" fill="rgba(0,229,255,0.08)" stroke="#00E5FF" stroke-width="2"/><circle cx="160" cy="70" r="20" fill="none" stroke="#8B5CF6" stroke-width="1.5"/><path d="M90 70H230" stroke="#233354" stroke-width="1.5"/>',
    },
    "default-arena": {
      slug: "default-arena",
      src: "assets/images/games/default-arena.svg",
      webpSrc: "assets/images/games/default-arena.webp",
      primary: "#00E5FF",
      secondary: "#8B5CF6",
      code: "ESPORTS ARENA",
      accentShape:
        '<rect x="122" y="30" width="76" height="76" rx="10" fill="rgba(0,229,255,0.08)" stroke="#00E5FF" stroke-width="2"/><path d="M138 68h44M160 46v44" stroke="#8B5CF6" stroke-width="2"/>',
    },
  };

  function resolveGameArtwork(game) {
    const rawSlug =
      game && typeof game === "object"
        ? String(game.slug || game.game_id || game.name || game.game_name || "")
        : String(game || "");
    const normalized = rawSlug.trim().toLowerCase();

    if (normalized && GAME_ARTWORK_REGISTRY[normalized]) {
      return GAME_ARTWORK_REGISTRY[normalized];
    }
    if (normalized.includes("mobile-legends") || normalized.includes("mobile legends") || normalized.includes("mlbb")) {
      return GAME_ARTWORK_REGISTRY["mobile-legends"];
    }
    if (normalized.includes("valorant")) {
      return GAME_ARTWORK_REGISTRY.valorant;
    }
    if (normalized.includes("ea-sports-fc") || normalized.includes("fc 25") || normalized.includes("fc25")) {
      return GAME_ARTWORK_REGISTRY["ea-sports-fc"];
    }
    return GAME_ARTWORK_REGISTRY["default-arena"];
  }

  function getGamePalette(gameSlugOrName) {
    return resolveGameArtwork(gameSlugOrName);
  }

  function renderGameArtwork(game, labelOverride = "", options = {}) {
    const gameName = (game && (game.name || game.game_name)) || "Esports";
    const asset = resolveGameArtwork(game);
    const label = labelOverride || asset.code;
    const loadingAttr = options && options.eager ? "eager" : "lazy";
    const hideLabels = Boolean(options && options.hideLabels);

    return `
      <div class="artwork-media">
        <img
          class="artwork-img"
          src="${escapeHtml(asset.src)}"
          alt="Artwork ${escapeHtml(gameName)}"
          width="960"
          height="540"
          loading="${loadingAttr}"
          decoding="async"
          onerror="this.style.display='none'; if (this.nextElementSibling) { this.nextElementSibling.classList.add('is-visible'); }"
        />
        <svg class="artwork-fallback-svg" viewBox="0 0 320 160" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ilustrasi game ${escapeHtml(gameName)}">
          <rect width="320" height="160" fill="#0B1120"/>
          <path d="M0 132L72 132L96 108L320 108" stroke="#1D2A48" stroke-width="1.5"/>
          <path d="M0 28L210 28L232 50L320 50" stroke="#1D2A48" stroke-width="1.5"/>
          ${asset.accentShape}
        </svg>
        <div class="artwork-scrim" aria-hidden="true"></div>
        ${
          hideLabels
            ? ""
            : `
          <span class="artwork-kicker-tag">${escapeHtml(label)}</span>
          <span class="artwork-caption">${escapeHtml(gameName)}</span>
        `
        }
      </div>
    `;
  }

  function renderGameChip(gameName, gameSlug = "") {
    const asset = resolveGameArtwork(gameSlug || gameName);
    return `<span class="game-chip"><span class="game-chip-dot" style="background-color:${asset.primary};" aria-hidden="true"></span><span>${escapeHtml(gameName || "Esports")}</span></span>`;
  }

  function hashIdentifier(text) {
    let hash = 0;
    const str = String(text || "");
    for (let i = 0; i < str.length; i += 1) {
      hash = (hash * 31 + str.charCodeAt(i)) >>> 0;
    }
    return hash;
  }

  const TEAM_EMBLEM_PALETTES = [
    { stroke: "#00E5FF", innerStroke: "#8B5CF6", bg: "#0D162C", innerBg: "#132042" },
    { stroke: "#38EEFF", innerStroke: "#34D399", bg: "#0C1829", innerBg: "#12263C" },
    { stroke: "#A78BFA", innerStroke: "#00E5FF", bg: "#12132B", innerBg: "#1B1E45" },
    { stroke: "#FBBF24", innerStroke: "#00E5FF", bg: "#141628", innerBg: "#1E243E" },
  ];

  function renderTeamEmblem(tagOrTeam, size = 44) {
    const rawTag =
      tagOrTeam && typeof tagOrTeam === "object"
        ? tagOrTeam.tag || tagOrTeam.team_tag || tagOrTeam.name || "TM"
        : tagOrTeam || "TM";
    const cleanTag = String(rawTag).trim().toUpperCase().slice(0, 4) || "TM";
    const hash = hashIdentifier(cleanTag);
    const pal = TEAM_EMBLEM_PALETTES[hash % TEAM_EMBLEM_PALETTES.length];
    const shapeIdx = hash % 4;
    const fontSize = cleanTag.length >= 4 ? 10 : 11.5;

    let shapePaths = "";
    if (shapeIdx === 0) {
      shapePaths = `
        <path d="M24 3L41 9.5V22.5C41 33.2 33.8 41.6 24 45C14.2 41.6 7 33.2 7 22.5V9.5L24 3Z" fill="${pal.bg}" stroke="${pal.stroke}" stroke-width="2"/>
        <path d="M24 7.5L36.8 12.2V22C36.8 30 31.3 36.4 24 39.4C16.7 36.4 11.2 30 11.2 22V12.2L24 7.5Z" fill="${pal.innerBg}" stroke="${pal.innerStroke}" stroke-width="1.1"/>
      `;
    } else if (shapeIdx === 1) {
      shapePaths = `
        <polygon points="24,3 42,13.5 42,34.5 24,45 6,34.5 6,13.5" fill="${pal.bg}" stroke="${pal.stroke}" stroke-width="2"/>
        <polygon points="24,8 37.5,15.8 37.5,32.2 24,40 10.5,32.2 10.5,15.8" fill="${pal.innerBg}" stroke="${pal.innerStroke}" stroke-width="1.1"/>
      `;
    } else if (shapeIdx === 2) {
      shapePaths = `
        <path d="M6 10L18 6L24 3L30 6L42 10L39 27L24 45L9 27L6 10Z" fill="${pal.bg}" stroke="${pal.stroke}" stroke-width="2"/>
        <path d="M11.5 13.5L24 8.5L36.5 13.5L34.5 25.5L24 38.5L13.5 25.5L11.5 13.5Z" fill="${pal.innerBg}" stroke="${pal.innerStroke}" stroke-width="1.1"/>
      `;
    } else {
      shapePaths = `
        <polygon points="24,3 44,20 35,43 13,43 4,20" fill="${pal.bg}" stroke="${pal.stroke}" stroke-width="2"/>
        <polygon points="24,8.5 39,21 31.8,38.5 16.2,38.5 9,21" fill="${pal.innerBg}" stroke="${pal.innerStroke}" stroke-width="1.1"/>
      `;
    }

    return `
      <span class="team-emblem" style="width:${size}px; height:${size}px;" aria-hidden="true">
        <svg width="${size}" height="${size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          ${shapePaths}
          <text x="24" y="28" text-anchor="middle" fill="#F1F5F9" font-family="monospace" font-size="${fontSize}" font-weight="700" letter-spacing="0.03em">${escapeHtml(cleanTag)}</text>
        </svg>
      </span>
    `;
  }

  function renderPlayerAvatar(nickname, role = "starter", size = 38) {
    const clean = String(nickname || "PL").trim();
    const parts = clean.split(/[\s_-]+/).filter(Boolean);
    const initials =
      parts.length >= 2
        ? (parts[0][0] + parts[1][0]).toUpperCase()
        : clean.slice(0, 2).toUpperCase() || "PL";
    const roleKey = String(role || "starter").toLowerCase();
    const borderClass =
      roleKey === "captain"
        ? "is-captain"
        : roleKey === "coach"
          ? "is-coach"
          : roleKey === "substitute"
            ? "is-sub"
            : "is-starter";

    return `
      <span class="player-avatar ${borderClass}" style="width:${size}px; height:${size}px;" aria-hidden="true">
        <span>${escapeHtml(initials)}</span>
      </span>
    `;
  }

  function renderProgressBar(percent, ariaLabel = "Progres") {
    const clamped = Math.max(0, Math.min(100, Number(percent || 0)));
    return `
      <div class="progress-track" role="progressbar" aria-label="${escapeHtml(ariaLabel)}" aria-valuenow="${clamped}" aria-valuemin="0" aria-valuemax="100">
        <div class="progress-fill" style="width:${clamped}%;"></div>
      </div>
    `;
  }

  function renderMatchCard(match, options = {}) {
    const highlightTeamIds = new Set(options.highlightTeamIds || []);
    const winA = match.winner_team_id && match.winner_team_id === match.team_a_id;
    const winB = match.winner_team_id && match.winner_team_id === match.team_b_id;
    const involvesOwnTeam =
      highlightTeamIds.has(match.team_a_id) || highlightTeamIds.has(match.team_b_id);

    const teamABadge = match.team_a_id
      ? renderTeamEmblem(match.team_a_tag, 24)
      : `<span class="badge badge-neutral tabular-nums">TBD</span>`;
    const teamBBadge = match.team_b_id
      ? renderTeamEmblem(match.team_b_tag, 24)
      : `<span class="badge badge-neutral tabular-nums">TBD</span>`;

    return `
      <article class="match-card ${involvesOwnTeam ? "is-highlighted" : ""}">
        <div class="match-card-header">
          <span class="tabular-nums"><strong>${escapeHtml(match.round_name || "Match")}</strong> #${match.match_number} (Bo${match.best_of || 3})</span>
          ${renderStatusBadge(match.status)}
        </div>
        <div class="match-card-teams">
          <div class="match-card-team ${winA ? "is-winner" : ""}">
            <div class="match-card-team-name">
              ${teamABadge}
              <span>${escapeHtml(match.team_a_name || "TBD")}</span>
            </div>
            <span class="match-card-score">${match.score_a ?? 0}</span>
          </div>
          <div class="match-card-team ${winB ? "is-winner" : ""}">
            <div class="match-card-team-name">
              ${teamBBadge}
              <span>${escapeHtml(match.team_b_name || "TBD")}</span>
            </div>
            <span class="match-card-score">${match.score_b ?? 0}</span>
          </div>
        </div>
      </article>
    `;
  }

  function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      container.setAttribute("aria-live", "polite");
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.setAttribute("role", type === "danger" ? "alert" : "status");

    const textSpan = document.createElement("span");
    textSpan.textContent = String(message || "");

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "toast-close";
    closeBtn.setAttribute("aria-label", "Tutup notifikasi");
    closeBtn.innerHTML = icon("close", 14);
    closeBtn.addEventListener("click", () => toast.remove());

    toast.appendChild(textSpan);
    toast.appendChild(closeBtn);
    container.appendChild(toast);

    setTimeout(() => {
      if (toast.isConnected) {
        toast.remove();
      }
    }, 4200);
  }

  function getModalFocusableElements(backdrop) {
    return Array.from(
      backdrop.querySelectorAll(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      )
    );
  }

  function closeModal() {
    const backdrop = document.getElementById("app-modal-backdrop");
    if (!backdrop) return;

    if (typeof modalCleanup === "function") {
      modalCleanup();
      modalCleanup = null;
    }

    backdrop.classList.add("hidden");
    backdrop.setAttribute("aria-hidden", "true");

    if (lastFocusedBeforeModal && typeof lastFocusedBeforeModal.focus === "function") {
      try {
        lastFocusedBeforeModal.focus();
      } catch (_err) {
        // Ignore focus restoration error if origin node was detached.
      }
    }
    lastFocusedBeforeModal = null;
  }

  function openModal({ title, bodyHtml, footerHtml = "" }) {
    const backdrop = document.getElementById("app-modal-backdrop");
    if (!backdrop) return;

    if (typeof modalCleanup === "function") {
      modalCleanup();
      modalCleanup = null;
    }

    if (document.activeElement && !backdrop.contains(document.activeElement)) {
      lastFocusedBeforeModal = document.activeElement;
    }

    const titleEl = document.getElementById("app-modal-title");
    const bodyEl = document.getElementById("app-modal-body");
    const footerEl = document.getElementById("app-modal-footer");
    const closeHeaderBtn = document.getElementById("app-modal-close-btn");

    if (titleEl) titleEl.textContent = title || "Dialog";
    if (bodyEl) bodyEl.innerHTML = bodyHtml || "";
    if (footerEl) {
      footerEl.innerHTML =
        footerHtml ||
        `<button type="button" class="btn btn-secondary" data-modal-close="true">Tutup</button>`;
    }

    backdrop.classList.remove("hidden");
    backdrop.setAttribute("aria-hidden", "false");

    const onKeydown = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeModal();
        return;
      }
      if (e.key === "Tab") {
        const focusable = getModalFocusableElements(backdrop);
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    const onBackdropClick = (e) => {
      if (e.target === backdrop) {
        closeModal();
        return;
      }
      if (e.target && e.target.closest("[data-modal-close='true']")) {
        closeModal();
      }
    };

    const onCloseBtnClick = () => closeModal();

    document.addEventListener("keydown", onKeydown);
    backdrop.addEventListener("click", onBackdropClick);
    if (closeHeaderBtn) {
      closeHeaderBtn.addEventListener("click", onCloseBtnClick);
    }

    modalCleanup = () => {
      document.removeEventListener("keydown", onKeydown);
      backdrop.removeEventListener("click", onBackdropClick);
      if (closeHeaderBtn) {
        closeHeaderBtn.removeEventListener("click", onCloseBtnClick);
      }
    };

    const focusable = getModalFocusableElements(backdrop);
    if (focusable.length > 0) {
      const preferred =
        backdrop.querySelector("#app-modal-body input, #app-modal-body select, #app-modal-body textarea") ||
        focusable[0];
      preferred.focus();
    }
  }

  window.TurnamenUI = {
    escapeHtml,
    icon,
    formatRupiah,
    formatDateTime,
    formatDateOnly,
    renderStatusBadge,
    renderRoleBadge,
    renderLoadingState,
    renderEmptyState,
    renderErrorState,
    renderAuthNotice,
    renderAccessDeniedState,
    resolveGameArtwork,
    renderGameArtwork,
    renderGameChip,
    renderTeamEmblem,
    renderPlayerAvatar,
    renderProgressBar,
    renderMatchCard,
    showToast,
    openModal,
    closeModal,
  };
})(window, document);
