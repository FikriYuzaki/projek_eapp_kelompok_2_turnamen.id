/**
 * Turnamen.in: Reusable Futuristic Arena UI Components (`window.TurnamenUI`)
 * Owner: Fikri (System Integration & Desktop UI/UX)
 * Provides SVG icons, badges, loading/empty/error states, accessible modal, and toasts.
 */
(function (window, document) {
  "use strict";

  const STATUS_MAP = {
    ongoing: { label: "Sedang Berlangsung", cls: "badge-warning", live: true },
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
    showToast,
    openModal,
    closeModal,
  };
})(window, document);
