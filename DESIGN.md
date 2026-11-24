# DESIGN.md: Sistem Desain Futuristic Arena Turnamen.in

> **Status Dokumen:** ACTIVE DESIGN SYSTEM (Branch `feature/fikri-ui-ux`)
> **Pemilik Desain:** Fikri (System Integration & Desktop UI/UX Redesign)
> **Dial Desain:** `ENERGY 2 / RHYTHM 2 / MOTION 1`

---

## 1. Arah Desain & Karakter Produk

- **Nama Aplikasi:** Turnamen.in
- **Identitas Visual:** **Futuristic Arena** (platform manajemen turnamen esports modern bernuansa arena kompetitif masa depan).
- **Target Platform:** Aplikasi desktop Windows 10/11 melalui Python Eel dan Chromium (`1024x768` hingga `1920x1080`, acuan utama `1366x820` dan `1440x900`).
- **Design Read:** Esports tournament operations desktop suite untuk organizer, panitia/wasit, kapten tim, dan pemain dalam gaya tactical-broadcast Futuristic Arena.
- **Prinsip Utama:**
  1. **Kejelasan Arena di Atas Dekorasi:** Data pertandingan, jadwal, status verifikasi, dan skor harus terbaca seketika tanpa gangguan glitch atau neon berlebihan.
  2. **Kontras Terukur (WCAG AA):** Seluruh pasangan teks diuji >= 4.5:1 dan seluruh batas kontrol interaktif/status diuji >= 3:1.
  3. **Disiplin Dose Cap:** Efek blur (`backdrop-filter`) dibatasi maksimal 2 elemen (`.topbar` dan `.modal-backdrop`). Efek glow aksen cyan dibatasi maksimal 2 fokus (aksi utama hover/focus dan sorotan pemenang/juara bracket).
  4. **Kejujuran Data & Mode:** Tidak ada metrik fiktif atau nilai fallback tersembunyi. Saat `APP_MODE=mock`, antarmuka menampilkan penanda simulasi yang tegas. Saat `APP_MODE=supabase`, fitur demo role disembunyikan dan kondisi `currentUser === null` ditangani sebagai tamu read-only.

---

## 2. Referensi UI UX Pro Max & Keputusan Desain (R-31)

Pencarian design system melalui UI UX Pro Max (`esports tournament dashboard futuristic arena`) menekankan:
- Navigasi keyboard yang konsisten dan urutan tab mengikuti alur visual.
- Ikon SVG konsisten (tanpa emoji dekoratif), `cursor: pointer` pada seluruh elemen interaktif, dan dukungan `prefers-reduced-motion`.
- Kontras teks >= 4.5:1 dan responsivitas lintas ukuran desktop hingga tablet (`768px`, `1024px`, `1366px`, `1440px`).

Alasan satu baris per keputusan utama:
- **Warna:** Dark navy (`#060A14` / `#0B1120` / `#10182B`) menekan silau saat operasional turnamen panjang; Electric Cyan (`#00E5FF`) menandai aksi utama dan status aktif; Futuristic Violet (`#8B5CF6` / `#C4B5FD`) membedakan aksen sekunder konteks turnamen tanpa menyaingi CTA utama.
- **Tipografi:** `Chakra Petch` / `Bahnschrift` pada judul dan display arena memberi karakter kompetitif tegas, `Plus Jakarta Sans` / `Segoe UI` menjaga keterbacaan tabel/form, dan `JetBrains Mono` / `Cascadia Mono` dengan `tabular-nums` meluruskan skor serta statistik secara vertikal.
- **Layout:** Shell desktop dengan sidebar tetap (menjadi drawer pada lebar <= 1024px) plus komposisi per halaman yang bervariasi sesuai fungsi (hero komando + KPI strip di Dashboard, filter toolbar + katalog di Daftar Turnamen, board bracket horizontal di Bracket, panel split di Login/Auth).
- **Spacing & Radius:** Skala spacing `4/8/12/16/20/24px` memisahkan konteks turnamen dari area aksi; radius terukur (`4px` badge/skor, `6px` input/tombol, `10px` kartu/panel, `12px` dialog) membedakan hirarki kontrol dari wadah data.
- **Ikonografi:** Inline SVG stroke geometric berketebalan `1.75px` menggantikan seluruh emoji agar konsisten di semua versi Windows dan Chromium.

---

## 3. Token Warna Futuristic Arena (Terverifikasi WCAG AA)

### A. Permukaan & Border
| Token CSS | Nilai Hex | Rasio Kontras & Kegunaan |
| :--- | :--- | :--- |
| `--bg-primary` | `#060A14` | Kanvas utama aplikasi |
| `--bg-secondary` | `#0B1120` | Latar sidebar dan panel sekunder |
| `--bg-surface` | `#10182B` | Kartu data, tabel, dan kotak pertandingan |
| `--bg-surface-elevated` | `#162038` | Panel terangkat, modal, dan baris header |
| `--bg-surface-hover` | `#1D2A48` | State hover tabel dan item navigasi |
| `--border-subtle` | `#233354` | Pemisah struktural kartu dan sel tabel |
| `--border-interactive` | `#5572A4` | Border input/tombol sekunder (>= 3.34:1 pada semua permukaan) |

### B. Teks & Aksen
| Token CSS | Nilai Hex | Rasio & Kegunaan |
| :--- | :--- | :--- |
| `--text-primary` | `#F1F5F9` | Judul, nama tim, skor (>= 16.14:1 pada surface) |
| `--text-secondary` | `#A8B8D0` | Label kolom, subjudul, deskripsi (>= 8.78:1 pada surface) |
| `--text-muted` | `#8B9FBD` | Metadata sekunder, timestamp (>= 6.00:1 pada elevated) |
| `--accent-primary` | `#00E5FF` | Electric Cyan untuk CTA utama (`#04101B` ink = 12.47:1) |
| `--accent-cyan-text` | `#67E8F9` | Teks sorotan cyan pada latar gelap (12.20:1 pada surface) |
| `--accent-violet` | `#6D28D9` | Aksen sekunder tombol/highlight violet (`#FFFFFF` = 7.10:1) |
| `--accent-violet-text` | `#C4B5FD` | Teks/label violet pada permukaan gelap (9.58:1 pada surface) |

### C. Warna Semantik Status
| Status | Token | Teks pada Surface | Rasio pada `#10182B` |
| :--- | :--- | :--- | :--- |
| Success / Approved / Completed | `--status-success` | `#34D399` | 9.20:1 |
| Warning / Ongoing / Pending | `--status-warning` | `#FBBF24` | 10.59:1 |
| Danger / Rejected / Disputed | `--status-danger` | `#FCA5A5` | 9.32:1 |
| Info / Scheduled / Open | `--status-info` | `#67E8F9` | 12.20:1 |

---

## 4. Standar Interaksi & Aksesibilitas

1. **Keyboard & Focus:** Seluruh kontrol dapat dicapai via `Tab`, diaktifkan via `Enter`/`Space`, memiliki `:focus-visible` `2px solid #00E5FF`, serta memiliki *skip link* ke `#main-content`.
2. **Modal Aksesibel:** Menggunakan `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, focus trap internal, penutupan via `Escape` atau klik backdrop, serta pemulihan fokus saat ditutup.
3. **Affordance & Reduced Motion:** Base layer menerapkan `cursor: pointer` pada seluruh kontrol aktif dan `cursor: not-allowed` pada elemen nonaktif. Seluruh transisi menghormati `@media (prefers-reduced-motion: reduce)`.
4. **State Data Lengkap:** Setiap view data menyediakan Loading State (`role="status"`), Empty State (penyebab + aksi lanjutan), dan Error State (`role="alert"` + tombol coba lagi).

---

## 5. Arsitektur Role-Based Esports Experience

Seluruh 5 role RBAC (`docs/contracts/role-permissions.md`) berbagi identitas visual **Futuristic Arena**, namun menerima struktur dashboard, navigasi, dan kontrol aksi sesuai hak akses masing-masing:

1. **Kelompok Competitive Experience (`player`, `team_captain`, dan tamu publik):**
   - **Player (`Competitive Arena`):** Banner turnamen unggulan, galeri poster cabang game (`/api/v1/games`), kartu penemuan turnamen dengan progres kuota, identitas tim pribadi serta match cards relevan, dan ringkasan klasemen. Tidak ada tombol administrasi atau menu pengelolaan skor.
   - **Team Captain (`Team Command`):** Hero identitas tim lengkap dengan emblem SVG geometris, pemilih tim milik kapten, grid roster anggota, status registrasi serta turnamen terbuka yang cocok dengan cabang game tim, dan jadwal/hasil pertandingan tim.
2. **Kelompok Management Experience (`organizer`, `committee`, `super_admin`):**
   - **Organizer (`Tournament Suite`):** Kontrol turnamen milik sendiri, metrik kuota & pending verification, antrean verifikasi peserta, dan akses cepat ke bracket serta audit log.
   - **Committee (`Match Operations`):** Antrean pengesahan skor cepat langsung dari dashboard operasional, antrean verifikasi peserta, dan publikasi pengumuman teknis tanpa kontrol pembuatan turnamen/tim.
   - **Super Admin (`System Control`):** Metrik sistem lintas organizer, kontrol penuh turnamen & tim, distribusi cabang game, telemetri runtime, dan jejak audit sistem.
3. **Navigasi Dinamis & Access Guard:**
   - Sidebar dirender ulang secara dinamis berdasarkan role aktif (`renderRoleNavigation`). Menu login hanya tampil saat belum masuk; tombol Keluar hanya tampil saat sesi aktif; halaman terlarang (seperti `match-management` untuk role non-staf atau `profile` untuk tamu) menampilkan Access Denied State yang aman ketika diakses langsung.

---

## 6. Sistem Aset Visual, Emblem Tim, & Bracket Terhubung

1. **Registry Artwork Game Lokal Siap-WebP (`desktop/web/assets/images/games/`):**
   - Seluruh artwork game dipetakan terpusat lewat `GAME_ARTWORK_REGISTRY` dan `resolveGameArtwork(game)` di `ui-components.js` sesuai `games.slug` dari `/api/v1/games` (`mobile-legends`, `valorant`, `ea-sports-fc`, dan fallback `default-arena`).
   - Setiap kartu poster game, banner utama, kartu partisipasi kapten, dan hero detail turnamen merender aset lokal berasio `16:9` dengan *contrast scrim* gelap dan fallback SVG inline tanpa hotlink eksternal. Mengganti `.svg` ke `.webp` hanya perlu memperbarui file lokal dan satu baris pada `GAME_ARTWORK_REGISTRY` tanpa mengubah logika bisnis.
2. **Sistem Emblem Tim Deterministik (`renderTeamEmblem`):**
   - Tag setiap tim di-hash secara deterministik ke salah satu dari 4 siluet perisai geometris dan 4 palet Futuristic Arena, sehingga identitas tim tetap konsisten di halaman Team Captain, Direktori Tim, Detail Turnamen, Match Management, Bracket, dan Klasemen.
3. **Visualisasi Bracket Terhubung SVG (`drawBracketConnectors`):**
   - Board Single Elimination merender lapisan `<svg class="bracket-connectors-svg">` di belakang kartu pertandingan yang menghitung jalur siku dari tengah sisi kanan match sumber menuju slot tujuan (`next_match_id` dan `next_slot` "A"/"B") serta menyalakan warna cyan untuk pertandingan yang telah selesai.
