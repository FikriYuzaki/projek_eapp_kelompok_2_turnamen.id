# Wave 6.11: Laporan Perbaikan CSS Layout Overflow & Double Scrollbar

**Tanggal:** 28 November 2026
**Branch Repository:** `feature/fikri-ui-ux`
**Cakupan Perubahan:** Hanya stylesheet frontend (`variables.css`, `layout.css`, `components.css`)
**Status Keseluruhan:** **PASS** (Terverifikasi di `1366x820`, `1920x1080`, dan `1024x768` pada seluruh 10 halaman + `pytest` `304 passed`)

---

## 1. Ringkasan Root Cause

Pada pengujian interaktif Native Desktop Supabase, container utama (`.app-shell`) dan `.sidebar` berhenti sekitar pertengahan tinggi jendela ketika dokumen tergulir, menyisakan ruang kosong berwarna `#060a14` (`--bg-primary`) di bagian bawah serta memunculkan dua scrollbar vertikal berdampingan.

Root cause yang teridentifikasi dan dibuktikan hingga tingkat piksel:

1. **Kebocoran *containing block* elemen `position: absolute` ke `<body>` / `<html>`:**
   - [layout.css](file:///C:/Turnamen.in/desktop/web/assets/css/layout.css) menetapkan `position: static` pada `.app-shell`, `.main-workspace`, dan `.content-area`.
   - Elemen aksesibilitas tersembunyi `.sr-only` ([variables.css](file:///C:/Turnamen.in/desktop/web/assets/css/variables.css)) dan `.artwork-file-input-sr` ([components.css](file:///C:/Turnamen.in/desktop/web/assets/css/components.css)) memakai `position: absolute` tanpa `top`/`left` dan tanpa ancestor `position: relative` lokal, sehingga `offsetParent` mereka melompat ke `<body>` pada posisi vertikal flow konten (`top: 1053px..1322px` di Dashboard Super Admin dan `top: 1094px..1095px` di Manajemen Game).
2. **Root `html, body` tidak mengunci overflow dan rantai tinggi flex memakai `100vh`:**
   - [variables.css](file:///C:/Turnamen.in/desktop/web/assets/css/variables.css) menetapkan `html, body { height: 100%; }` tanpa `overflow: hidden;`, sehingga elemen `.sr-only` / `.artwork-file-input-sr` di bawah fold memanjangkan `html.scrollHeight` menjadi `1322px` (Dashboard) dan `1095px` (Manajemen Game) di luar `.app-shell` (`820px`).
   - Akibatnya muncul scrollbar vertikal luar milik viewport `html` (lebar `15px`, mengurangi `html.clientWidth` dari `1366px` menjadi `1351px`) di samping scrollbar dalam milik `.content-area` (`overflow-y: auto`, lebar `15px`). Saat viewport tergulir (`window.scrollY > 0`), `.app-shell` dan `.sidebar` bergeser ke atas dan menampakkan latar `#060a14` di bagian bawah jendela.

---

## 2. Perubahan CSS yang Diterapkan

Tidak ada perubahan pada API, JavaScript, HTML, Python, database, Storage, Auth, maupun `.env`. Hanya 3 file CSS yang diperbarui:

1. **[desktop/web/assets/css/variables.css](file:///C:/Turnamen.in/desktop/web/assets/css/variables.css#L81-L161)**
   - `html, body`: menambahkan `overflow: hidden;` untuk mencegah munculnya scrollbar dokumen luar.
   - `.sr-only`: menambahkan `clip-path: inset(50%);` mendampingi `clip: rect(0, 0, 0, 0);`.

2. **[desktop/web/assets/css/layout.css](file:///C:/Turnamen.in/desktop/web/assets/css/layout.css#L6-L260)**
   - `.app-shell`: menambahkan `position: relative;` sebagai *containing block* root dan mengubah `min-height: 100vh; height: 100vh;` menjadi `height: 100%; min-height: 100%;`.
   - `.sidebar`: menambahkan `height: 100%; min-height: 0; overflow: hidden;` agar sidebar selalu penuh setinggi viewport dan `.sidebar-footer` tetap menempel di bawah.
   - `.sidebar-nav`: menambahkan `min-height: 0;` pada item flex sehingga hanya daftar navigasi yang menggulir jika item melebihi tinggi jendela.
   - `.main-workspace`: mengganti `height: 100vh;` dengan `min-height: 0; height: 100%; overflow: hidden;`.
   - `.content-area`: menambahkan `position: relative;` dan `min-height: 0;` agar seluruh elemen `position: absolute` di dalamnya tetap terkungkung di container konten dan tidak pernah membocorkan `html.scrollHeight`.

3. **[desktop/web/assets/css/components.css](file:///C:/Turnamen.in/desktop/web/assets/css/components.css#L2255-L2282)**
   - `.artwork-manager-actions`: menambahkan `position: relative;` sebagai *containing block* lokal grup aksi kartu poster.
   - `.artwork-file-input-sr`: menambahkan `top: 0; left: 0;` dan `clip-path: inset(50%);` agar input file tersembunyi tetap berada pada koordinat lokal `(0, 0)` di dalam `.artwork-manager-actions`.

---

## 3. Perbandingan Pengukuran Sebelum vs Sesudah Perbaikan

| Skenario Uji (Super Admin) | Metrik | Sebelum Perbaikan | Sesudah Perbaikan | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Dashboard (`1366x820`)** | `html.scrollHeight` / `html.clientWidth` | `1322px` / `1351px` (`-15px` scrollbar luar) | `820px` / `1366px` | **PASS** |
| | `window.scrollY` saat uji `window.scrollTo(0, 502)` | `502.4px` (shell terpotong ke `318px`, `502px` hitam) | `0px` (tidak bergulir) | **PASS** |
| | Scrollbar vertikal aktif | 2 (`html` + `.content-area`) | 1 (`.content-area` saja) | **PASS** |
| | Ukuran screenshot penuh (`fullPage: true`) | `1351x1286` | `1366x820` | **PASS** |
| **Manajemen Game (`1366x820`)** | `html.scrollHeight` / `html.clientWidth` | `1095px` / `1351px` | `820px` / `1366px` | **PASS** |
| | `offsetParent` `.artwork-file-input-sr` | `BODY` (`top: 1094px`) | `.artwork-manager-actions` (lokal) | **PASS** |
| | Ukuran screenshot penuh (`fullPage: true`) | `1351x1095` | `1366x820` | **PASS** |
| **Dashboard (`1920x1080`)** | `html.scrollHeight` / `html.clientWidth` | `1158px` / `1905px` | `1080px` / `1920px` | **PASS** |
| | Ukuran screenshot penuh (`fullPage: true`) | Tidak diukur sebelum | `1920x1080` | **PASS** |
| **Manajemen Game (`1024x768`)** | `html.scrollHeight` / `html.clientWidth` | `2382px` (pada tangkapan `1009x2382`) | `768px` / `1024px` | **PASS** |

---

## 4. Hasil Regression Test Lintas Viewport & Halaman

Seluruh pengukuran dijalankan di Playwright Chromium dengan peran `Super Admin` setelah perubahan CSS terakhir. Pada setiap halaman, skrip menguji `window.scrollTo(0, 500)`, memeriksa elemen `position: absolute` (HTML `HTMLElement`), memeriksa daftar scroll container aktif, dan menguji `main.scrollTop = 200` ketika konten melebihi tinggi container.

### A. Viewport `1366 x 820`

| Halaman | `html.scrollHeight` (`clientW`) | `window.scrollY` | `.app-shell` / `.sidebar` / Footer Bottom | `.content-area` (`clientH` -> `scrollH`, scroll test) | Elemen Bocor ke `body`/`html` | Status |
| :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| Dashboard Super Admin | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `1496` (`scrollTop` OK) | `0` | **PASS** |
| Manajemen Game | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `1095` (`scrollTop` OK) | `0` | **PASS** |
| Tournament List | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `756` (fit tanpa scrollbar) | `0` | **PASS** |
| Tournament Detail | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `1478` (`scrollTop` OK) | `0` | **PASS** |
| Team Management | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `1155` (`scrollTop` OK) | `0` | **PASS** |
| Match Management | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `806` (`scrollTop` OK) | `0` | **PASS** |
| Bracket | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `977` (`scrollTop` OK) | `0` | **PASS** |
| Announcements | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `756` (fit tanpa scrollbar) | `0` | **PASS** |
| Reports | `820px` (`1366`) | `0` | `820` / `820` / `820` | `756` -> `1153` (`scrollTop` OK) | `0` | **PASS** |
| Profile | `820px` (`1366`) | `0` | `820` / `820` / `820` | `726` -> `726` (fit tanpa scrollbar) | `0` | **PASS** |

### B. Viewport `1920 x 1080`

| Halaman | `html.scrollHeight` (`clientW`) | `window.scrollY` | `.app-shell` / `.sidebar` / Footer Bottom | `.content-area` (`clientH` -> `scrollH`, scroll test) | Elemen Bocor ke `body`/`html` | Status |
| :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| Dashboard Super Admin | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1355` (`scrollTop` OK) | `0` | **PASS** |
| Manajemen Game | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1016` (fit) | `0` | **PASS** |
| Tournament List | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1016` (fit) | `0` | **PASS** |
| Tournament Detail | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1309` (`scrollTop` OK) | `0` | **PASS** |
| Team Management | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1016` (fit) | `0` | **PASS** |
| Match Management | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1016` (fit) | `0` | **PASS** |
| Bracket | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1016` (fit) | `0` | **PASS** |
| Announcements | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1016` (fit) | `0` | **PASS** |
| Reports | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1153` (`scrollTop` OK) | `0` | **PASS** |
| Profile | `1080px` (`1920`) | `0` | `1080` / `1080` / `1080` | `1016` -> `1016` (fit) | `0` | **PASS** |

### C. Viewport `1024 x 768` (Breakpoint Drawer `<= 1024px`)

| Halaman | `html.scrollHeight` (`clientW`) | `window.scrollY` | `.app-shell` / `.sidebar` / Footer Bottom | `.content-area` (`clientH` -> `scrollH`, scroll test) | Elemen Bocor ke `body`/`html` | Status |
| :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| Dashboard Super Admin | `768px` (`1024`) | `0` | `768` / `768` / `768` | `674` -> `1865` (`scrollTop` OK) | `0` | **PASS** |
| Manajemen Game | `768px` (`1024`) | `0` | `768` / `768` / `768` | `704` -> `2316` (`scrollTop` OK) | `0` | **PASS** |
| Tournament List | `768px` (`1024`) | `0` | `768` / `768` / `768` | `704` -> `704` (fit) | `0` | **PASS** |
| Tournament Detail | `768px` (`1024`) | `0` | `768` / `768` / `768` | `674` -> `1664` (`scrollTop` OK) | `0` | **PASS** |
| Team Management | `768px` (`1024`) | `0` | `768` / `768` / `768` | `674` -> `1159` (`scrollTop` OK) | `0` | **PASS** |
| Match Management | `768px` (`1024`) | `0` | `768` / `768` / `768` | `674` -> `901` (`scrollTop` OK) | `0` | **PASS** |
| Bracket | `768px` (`1024`) | `0` | `768` / `768` / `768` | `704` -> `965` (`scrollTop` OK) | `0` | **PASS** |
| Announcements | `768px` (`1024`) | `0` | `768` / `768` / `768` | `674` -> `674` (fit) | `0` | **PASS** |
| Reports | `768px` (`1024`) | `0` | `768` / `768` / `768` | `674` -> `1267` (`scrollTop` OK) | `0` | **PASS** |
| Profile | `768px` (`1024`) | `0` | `768` / `768` / `768` | `674` -> `674` (fit) | `0` | **PASS** |

---

## 5. Hasil Regression Fungsional Tambahan

| Komponen / Alur Uji | Hasil Terukur | Status |
| :--- | :--- | :-: |
| **Modal (`+ Tambah Game`)** | Terbuka (`hidden` dihapus), tertutup via tombol tutup (`#app-modal-close-btn`) maupun tombol `Escape`. Setelah ditutup, `document.body.style.overflow = ""` dan computed `overflow` kembali ke `hidden`; `html.scrollHeight = 820`, `window.scrollY = 0`. | **PASS** |
| **Dropdown Role & Filter** | `#topbar-role-switcher` berhasil berganti ke `garuda_eo (organizer)` lalu kembali ke `superadmin (super_admin)`; dropdown filter status turnamen (`#filter-tournament-status`) berubah dan kembali tanpa error. | **PASS** |
| **Navigasi & Sidebar Drawer (`1024x768`)** | Seluruh 10 menu navigasi berpindah halaman mulus. Drawer responsif (`#sidebar-toggle-btn` -> `.sidebar.is-open`) memiliki tinggi `768px`, footer bottom `768px`, `.sidebar-nav` `661px`, dan menutup normal via `#sidebar-close-btn`. | **PASS** |
| **Preview Poster Valid & Batalkan** | Memilih PNG `640x360` merender `.artwork-manager-preview-img`, mengaktifkan tombol `Simpan Poster` (`disabled = false`), menjaga `html.scrollHeight = 820`, dan tombol `Batalkan Preview` (`[data-action="clear-game-artwork-preview"]`) membersihkan preview. | **PASS** |
| **Penolakan File Tidak Didukung** | Memilih file SVG tersamar `.png` menampilkan pesan validasi error (`Format SVG, HTML, atau executable tidak diperbolehkan. Gunakan JPEG, PNG, atau WebP.`), tombol `Simpan Poster` tetap `disabled`, dan `html.scrollHeight = 820`. | **PASS** |
| **Aksesibilitas Input File** | Ketiga `.artwork-file-input-sr` memiliki `aria-label`, `tabIndex: 0`, dan `offsetParent: "artwork-manager-actions"` (dimensi `1x1` pada koordinat lokal tombol aksi, tidak membocorkan tinggi halaman). | **PASS** |
| **Console Error Check** | Hanya 1 error yang diharapkan pada mode `--api-only` (`/eel.js` `404`), 0 JavaScript runtime error lain. | **PASS** |

---

## 6. Bukti Screenshot & Verifikasi Otomatis

- **Screenshot `1366x820` Dashboard Super Admin (`fullPage: true`, dimensi terverifikasi `1366x820`):**
  [w611_fix_dashboard_1366x820.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_fix_dashboard_1366x820.png)
- **Screenshot `1366x820` Manajemen Game (`fullPage: true`, dimensi terverifikasi `1366x820`):**
  [w611_fix_game_mgmt_1366x820.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_fix_game_mgmt_1366x820.png)
- **Screenshot `1920x1080` Dashboard Super Admin (`fullPage: true`, dimensi terverifikasi `1920x1080`):**
  [w611_fix_dashboard_1920x1080.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_fix_dashboard_1920x1080.png)
- **Screenshot `1024x768` Manajemen Game (`fullPage: true`, dimensi terverifikasi `1024x768`):**
  [w611_fix_game_mgmt_1024x768.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_fix_game_mgmt_1024x768.png)
- **Suite Pengujian Python (`.\.venv\Scripts\pytest.exe -q`):** `304 passed, 4 warnings in 72.94s`.
- **Kebersihan Diff & Lingkungan:** `git diff --check` keluar dengan kode `0`, `.env` tidak ada (`False`), seluruh perubahan sebelumnya dipertahankan tanpa operasi commit/push/merge/reset/checkout.
