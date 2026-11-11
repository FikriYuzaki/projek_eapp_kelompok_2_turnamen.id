---
name: turnamen-frontend-ui
description: Panduan desain UI/UX, komponen dashboard desktop dark-theme, aksesibilitas, dan integrasi API client untuk Ferlita pada aplikasi Turnamen.in.
---

# Turnamen.in — Frontend & Desktop UI (`turnamen-frontend-ui`)

Skill ini ditujukan bagi **Ferlita (Project Coordinator & UI/UX Designer)** untuk merancang dan mengembangkan antarmuka desktop Turnamen.in.

## 1. Scope
Mencakup perancangan design system (`DESIGN.md`), styling CSS3 (`desktop/web/assets/css/`), halaman HTML (`desktop/web/index.html` dan `desktop/web/pages/`), komponen UI reusable (`desktop/web/assets/js/components/`), serta skrip interaksi halaman (`desktop/web/assets/js/pages/`).

## 2. Responsibilities
- Menetapkan dan memelihara arahan visual aplikasi di `DESIGN.md`.
- Membangun halaman utama: Login, Dashboard, Tournament List, Tournament Detail, Team Management, Match Management, Bracket, Announcements, Reports, dan User Profile.
- Menyediakan state visual yang lengkap pada setiap tampilan data: *Loading State*, *Empty State*, *Error State*, dan *Success State*.
- Memastikan seluruh angka skor, jadwal, dan klasemen menggunakan `font-variant-numeric: tabular-nums` agar mudah dipindai oleh panitia.

## 3. Architecture Rules
- Gunakan **HTML5, CSS3, dan Vanilla JavaScript (ES6+)** tanpa framework frontend berat.
- Seluruh pengambilan atau pengiriman data dari UI wajib melewati `window.TurnamenAPI` (`desktop/web/assets/js/core/api-client.js`) yang dikelola bersama Fikri.
- Jangan menaruh query database, secret key, atau validasi otorisasi akhir di sisi frontend. Menyembunyikan tombol di UI hanyalah bantuan UX, bukan pengaman sistem.
- Tampilkan banner atau badge indikator yang jelas saat aplikasi berjalan dalam `APP_MODE=mock`.
- Jangan membuat tombol aktif yang tidak berfungsi; jika fitur masih tahap blueprint, tampilkan keterangan status placeholder atau toast informatif yang jujur.

## 4. Allowed Directories
- `DESIGN.md`
- `desktop/web/index.html`
- `desktop/web/pages/`
- `desktop/web/assets/css/`
- `desktop/web/assets/images/`
- `desktop/web/assets/js/components/`
- `desktop/web/assets/js/pages/`

## 5. Prohibited Changes
- Dilarang mengubah `desktop/launcher/`, `desktop/bridge/`, atau `desktop/web/assets/js/core/` tanpa berkoordinasi dengan Fikri.
- Dilarang mengubah kode Python di `backend/` atau skema SQL di `supabase/`.

## 6. Required Dependencies
- Browser berbasis Chromium (Chrome / Microsoft Edge pada Windows 10/11) yang dijalankan oleh Python Eel.
- Kontrak data dari `docs/contracts/frontend-contract.md` dan `docs/contracts/api-contract.md`.

## 7. Development Workflow
1. Tinjau dan perbarui token desain di `DESIGN.md` serta `desktop/web/assets/css/variables.css`.
2. Jalankan aplikasi melalui `python run.py` (dalam `APP_MODE=mock`) untuk memeriksa halaman secara langsung.
3. Gunakan komponen di `desktop/web/assets/js/components/` untuk merender kartu, tabel, badge status, modal, dan notifikasi toast.
4. Uji kontras warna, navigasi keyboard (`:focus-visible`), serta tampilan data simulasi 8 tim pada halaman Bracket.

## 8. Testing Requirements
- Verifikasi visual dan fungsional seluruh 10 bagian/halaman dalam mode mock.
- Pastikan perpindahan navigasi sidebar, filter tabel, simulasi login/role, dan visualisasi bracket 8 tim berjalan tanpa error di *DevTools Console*.

## 9. Acceptance Criteria
- Tema gelap (*dark esports dashboard*) tampil bersih, rapi, dan konsisten di resolusi desktop (`1366×820` ke atas).
- Semua komponen dasar (Sidebar, Topbar, Cards, Tables, Modal, Forms, Search/Filter, Badges, Toast, State Loading/Empty/Error) tersedia dan berfungsi.
- Tidak ada tombol palsu yang diam saja ketika diklik.

## 10. Integration Contracts
- Mengonsumsi method pada `window.TurnamenAPI` sesuai `docs/contracts/frontend-contract.md`.
- Mematuhi format payload dan status code yang dijelaskan pada `docs/contracts/api-contract.md`.
