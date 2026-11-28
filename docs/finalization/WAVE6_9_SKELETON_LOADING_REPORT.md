# Wave 6.9: Laporan Dashboard Loading Experience & Skeleton Shimmer

- **Tanggal:** 2026-11-27
- **Target Sistem:** Desktop UI Turnamen.in (`desktop/web/assets/css/components.css`, `desktop/web/assets/js/components/ui-components.js`, `desktop/web/assets/js/pages/app-pages.js`) beserta seluruh optimasi Wave 6.8 pada Python Eel bridge & backend API.
- **Tujuan:** Menghadirkan loading experience instan dengan skeleton shimmer bertema navy/cyan, progressive section loading, preservasi data saat refresh, aksesibilitas penuh, responsivitas `1366x820` & `1024x768`, serta mempertahankan waktu muat di bawah target 3 detik.

---

## 1. Desain Skeleton Shimmer & Aksesibilitas

### A. Animasi & Token Visual (`desktop/web/assets/css/components.css`)
- Menggunakan animasi CSS murni (`@keyframes arena-shimmer`, `1.65s ease-in-out infinite`, zero animasi JavaScript berat) dengan palet **Futuristic Arena**:
  - Background navy gelap `#121d33` dengan border halus `rgba(35, 51, 84, 0.55)`.
  - Gradient shimmer cyan/turquoise halus (`rgba(0, 229, 255, 0.08)` -> `rgba(56, 238, 255, 0.16)` -> `rgba(0, 229, 255, 0.06)`).
  - `pointer-events: none` dan `user-select: none` agar placeholder tidak pernah menghalangi interaksi saat konten siap.
- **Aksesibilitas & Motion:**
  - Setiap kontainer skeleton menandai `role="status"`, `aria-busy="true"`, dan label status informatif; atribut `aria-busy` diubah kembali ke `"false"` pada blok `finally` di `navigateTo()` saat selesai atau gagal.
  - `@media (prefers-reduced-motion: reduce)` menonaktifkan `animation` pada `.arena-skeleton` (`animation: none; background-image: none; background-color: #16233b;`).
- **Responsivitas (`1366x820` & `1024x768`):**
  - Skeleton memakai `.grid-4`, `.grid-2`, `.workspace-split` (dari `layout.css`) serta aturan `@media (max-width: 1024px)` pada `.skeleton-table-row` dan `.skeleton-chart-bars` agar dimensi tetap menyerupai konten asli tanpa layout shift di resolusi desktop `1366x820` maupun `1024x768`.

### B. Komponen Reusable (`desktop/web/assets/js/components/ui-components.js`)
Seluruh komponen skeleton diekspor melalui `window.TurnamenUI`:
1. `renderStatCardsSkeleton(count)`: kartu metrik Dashboard.
2. `renderTournamentCardsSkeleton(count)`: kartu turnamen (banner media, badge status, judul, progress bar, aksi).
3. `renderTableSkeleton({ rows, columns, title })`: tabel data (turnamen, pengguna, jejak audit).
4. `renderListSkeleton({ rows, title, withAvatar })`: daftar tim, anggota, dan katalog game.
5. `renderAnnouncementCardsSkeleton(count)`: kartu pengumuman kompetisi.
6. `renderReportChartSkeleton()`: kombinasi ringkasan statistik + grafik batang (`skeleton-chart-bars`) + tabel klasemen.
7. `renderDashboardSkeleton(roleKey)`: kerangka tata letak awal Dashboard sesuai role (`super_admin` dan role kompetitif/manajerial lain).
8. `renderRefreshBanner(label)`: indikator ringan di bagian atas halaman saat menyegarkan ulang data yang sudah ada di cache snapshot.

---

## 2. Progressive Loading, Optimasi Tambahan & Preservasi Data

1. **Progressive Section Loading Dashboard Super Admin ([app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js)):**
   - `renderSuperAdminProgressive()` langsung memasang kerangka Dashboard dengan slot independen (`#sa-metrics-slot`, `#sa-tournaments-slot`, `#sa-games-slot`, `#sa-users-slot`, `#sa-audit-slot`).
   - Seluruh 4 endpoint Wave 1 (`getGames({ includeInactive: true })`, `getTournaments()`, `getTeams()`, `getUsers()`) tetap berjalan paralel tanpa menunggu satu sama lain (mempertahankan seluruh optimasi backend & Eel Wave 6.8).
   - Setiap kartu **langsung mengganti skeleton-nya segera setelah endpoint masing-masing selesai**, tanpa menunggu endpoint lain yang lebih lambat.
   - Begitu `getTournaments()` selesai, `getTournamentReport(ctx.active.id)` (Wave 2) **langsung dijalankan tanpa menunggu `getTeams()` maupun `getUsers()` selesai**, mengurangi critical path menunggu antar wave.
   - Kegagalan pada satu bagian (misalnya `reports` gagal atau lambat) hanya menampilkan `renderErrorState` pada bagian tersebut, sementara Turnamen, Game, Tim, dan Pengguna tetap tampil utuh.
2. **Preservasi Data Lama saat Refresh (`uiPageSnapshots`):**
   - `uiPageSnapshots` menyimpan snapshot HTML valid berdasarkan `(role, userId, page, filter/tournamentId)` di memori aplikasi dan dibersihkan otomatis saat `resetRoleScopedUiState()` (`logout`/`login`).
   - Saat pengguna menyegarkan halaman yang sudah pernah dimuat tanpa mengubah filter/turnamen, data sebelumnya dipertahankan bersama banner `.skeleton-refresh-bar` hingga data terbaru tiba (menghindari kedipan skeleton yang tidak perlu).
3. **Paralelisasi Halaman Sekunder:**
   - `renderTournamentList()` dan `renderTeamManagement()` kini menjalankan `ensureGamesLoaded(false)` secara paralel di `Promise.all(...)` bersama request utama turnamen/tim, menghilangkan waterfall sekuensial ketika `gamesState.loaded` masih `false`.
4. **Tanpa Delay Artifisial:** Tidak ada `setTimeout` penahan shimmer; seluruh skeleton langsung hilang segera setelah data atau error state diterima.

---

## 3. Hasil Pengujian & Benchmark Aktual

### A. Hasil Pengujian Otomatis (`pytest`)
- `tests/unit/test_wave6_9_skeleton_loading.py`: **3 passed**
  - Validasi CSS shimmer, `prefers-reduced-motion`, `pointer-events: none`, dan aturan responsif `1024px` / `1240px`.
  - Validasi Node VM seluruh 7 helper skeleton `TurnamenUI`, progressive rendering (slot turnamen & pengguna tampil saat `reports` masih pending, kemudian skeleton audit hilang & `aria-busy="false"` saat selesai), stale-snapshot preservation saat refresh, kegagalan parsial Dashboard, serta kondisi loaded / empty / error pada `tournament-list`, `team-management`, `announcements`, dan `reports` (memastikan nol `data-skeleton="true"` tersisa).
  - Benchmark API `APP_MODE=mock` `< 3.0s`.
- Gabungan `tests/unit/test_wave6_9_skeleton_loading.py` + `tests/unit/test_wave6_8_dashboard_performance.py`: **7 passed in 1.44s**.
- Seluruh suite `pytest -q`: **294 passed, 4 warnings in 53.89s** (0 failed, 0 skipped).
- Smoke check `.\.venv\Scripts\python.exe run.py --check`: `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`.
- `git diff --check`: keluar dengan kode `0`; `DOTENV_EXISTS=False`.

### B. Benchmark Perbandingan `APP_MODE=mock` vs `APP_MODE=supabase`

| Lingkungan & Skenario | Kondisi Pengukuran | Wave 6.8 (Sebelum Skeleton Progressive) | Wave 6.9 (Sesudah Progressive + Paralelisasi) | Status Target (< 3 Detik) |
| :--- | :--- | :--- | :--- | :--- |
| **`APP_MODE=mock` (Eel Bridge + Flask Lokal)** | 127.0.0.1 offline, 2 wave paralel (`wave1`: 4 endpoint + `wave2`: `reports`) | `wave1 = 66.12 ms`, `report = 3.85 ms`, **Total = `69.99 ms`** | `wave1 = 46.86 ms`, `report = 3.38 ms`, **Total = `50.23 ms`** (`announcements = 2.89 ms`) | **PASS (`0.05 detik`)** |
| **`APP_MODE=supabase` (Query Counter Benchmark)** | Simulasi seed data tanpa network key Cloud | `78` -> `22` remote calls; `65` -> `1` client baru | Tetap `22` remote calls (`1` client baru), plus Wave 2 overlap dengan Wave 1 tersisa & section tampil progresif tanpa menunggu bagian lain | Arsitektur siap `< 3s` |
| **`APP_MODE=supabase` (Live Cloud Wall-Clock)** | Koneksi nyata ke `cfdsgxciodfkamskafwe.supabase.co` | Belum dijalankan di sesi agent (tanpa `SUPABASE_PUBLISHABLE_KEY` / login aktif) | Belum dijalankan di sesi agent; pengguna dapat mengukur langsung via `scratch/verify_wave68_cloud.ps1` | Menunggu pengukuran live di desktop pengguna |

---

## 4. Kepatuhan Batasan

- Tidak ada perubahan skema database PostgreSQL, Auth, kebijakan RLS, maupun file di `supabase/migrations/`.
- Tidak ada operasi CRUD produksi; Public Signup tetap `DISABLED`.
- Seluruh optimasi Wave 6.8 tetap aktif dan terverifikasi pada test regresi.
- Tidak ada perubahan branch Git, commit, push, maupun merge, dan tidak ada `.env` atau kredensial tersimpan di repository/log.
