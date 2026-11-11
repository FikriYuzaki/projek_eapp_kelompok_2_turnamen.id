/**
 * Turnamen.in — Reusable UI Components (`window.TurnamenUI`)
 * Owner: Ferlita (Project Coordinator & UI/UX Designer)
 * Provides badges, loading/empty/error states, modals, and toast notifications.
 */
(function (window, document) {
  "use strict";

  const STATUS_MAP = {
    ongoing: { label: "Sedang Berlangsung", cls: "badge-warning" },
    open_registration: { label: "Pendaftaran Dibuka", cls: "badge-info" },
    registration_closed: { label: "Pendaftaran Ditutup", cls: "badge-neutral" },
    completed: { label: "Selesai", cls: "badge-success" },
    draft: { label: "Draft", cls: "badge-neutral" },
    cancelled: { label: "Dibatalkan", cls: "badge-danger" },
    approved: { label: "Disetujui", cls: "badge-success" },
    pending: { label: "Menunggu Verifikasi", cls: "badge-warning" },
    rejected: { label: "Ditolak", cls: "badge-danger" },
    withdrawn: { label: "Mengundurkan Diri", cls: "badge-neutral" },
    scheduled: { label: "Terjadwal", cls: "badge-info" },
    bye: { label: "BYE (Lolos Otomatis)", cls: "badge-neutral" },
    disputed: { label: "Sengketa Skor", cls: "badge-danger" },
    urgent: { label: "Mendesak", cls: "badge-danger" },
    important: { label: "Penting", cls: "badge-warning" },
    normal: { label: "Info", cls: "badge-info" },
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatRupiah(amount) {
    const num = Number(amount || 0);
    if (num === 0) return "Gratis";
    return "Rp " + num.toLocaleString("id-ID");
  }

  function renderStatusBadge(status) {
    const key = String(status || "").toLowerCase();
    const info = STATUS_MAP[key] || { label: escapeHtml(status || "-"), cls: "badge-neutral" };
    return `<span class="badge ${info.cls}">${info.label}</span>`;
  }

  function renderLoadingState(message = "Memuat data turnamen...") {
    return `
      <div class="state-box">
        <h3>⏳ ${escapeHtml(message)}</h3>
        <p>Mohon tunggu sebentar, sedang mengambil data dari server lokal.</p>
      </div>
    `;
  }

  function renderEmptyState(title = "Belum Ada Data", subtitle = "Data untuk bagian ini masih kosong.", actionHtml = "") {
    return `
      <div class="state-box">
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(subtitle)}</p>
        ${actionHtml ? `<div style="margin-top:12px;">${actionHtml}</div>` : ""}
      </div>
    `;
  }

  function renderErrorState(message = "Gagal memuat data", retryFnName = "") {
    return `
      <div class="state-box" style="border-color: var(--status-danger);">
        <h3 style="color: #f87171;">⚠️ Terjadi Kesalahan</h3>
        <p>${escapeHtml(message)}</p>
        ${
          retryFnName
            ? `<button class="btn btn-secondary btn-sm" style="margin-top:10px;" onclick="${retryFnName}">Coba Lagi</button>`
            : ""
        }
      </div>
    `;
  }

  function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3600);
  }

  function openModal({ title, bodyHtml, footerHtml = "" }) {
    const backdrop = document.getElementById("app-modal-backdrop");
    if (!backdrop) return;
    document.getElementById("app-modal-title").textContent = title || "Detail";
    document.getElementById("app-modal-body").innerHTML = bodyHtml || "";
    document.getElementById("app-modal-footer").innerHTML =
      footerHtml ||
      `<button class="btn btn-secondary" onclick="TurnamenUI.closeModal()">Tutup</button>`;
    backdrop.classList.remove("hidden");
  }

  function closeModal() {
    const backdrop = document.getElementById("app-modal-backdrop");
    if (backdrop) {
      backdrop.classList.add("hidden");
    }
  }

  window.TurnamenUI = {
    escapeHtml,
    formatRupiah,
    renderStatusBadge,
    renderLoadingState,
    renderEmptyState,
    renderErrorState,
    showToast,
    openModal,
    closeModal,
  };
})(window, document);
