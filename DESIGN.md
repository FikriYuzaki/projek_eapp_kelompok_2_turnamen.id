# DESIGN.md — Arahan Visual Awal Turnamen.in (DRAFT)

> **Status Dokumen:** DRAFT AWAL — Menunggu Tinjauan dan Persetujuan **Ferlita** (*Project Coordinator & UI/UX Designer*).  
> **Catatan Penting:** Dokumen ini memberikan fondasi awal agar pengembangan paralel dapat berjalan. Palet warna, tipografi, dan tata letak final **belum dikunci** dan berada di bawah wewenang Ferlita. Skill kualitas seperti `antislop-ui` dan `frontend-design` berfungsi sebagai filter kualitas dan keterbacaan, bukan pengganti keputusan desain koordinator.

---

## 1. Karakter & Identitas Produk

- **Nama Aplikasi:** Turnamen.in
- **Target Platform:** Desktop Application (Windows 10/11, resolusi acuan awal `1366×820` hingga `1920×1080`)
- **Tema Utama:** *Modern Dark Esports Management Dashboard*
- **Kesan Visual:** Profesional, taktis, bersih, terstruktur, dan berfokus pada kejelasan data kompetisi (jadwal, skor, status registrasi, serta bagan pertandingan / *bracket*).
- **Prinsip Utama:**
  1. **Kejelasan di Atas Dekorasi:** Panitia dan kapten tim membutuhkan informasi status turnamen, pertandingan berikutnya, dan skor secara instan tanpa gangguan elemen visual berlebihan (*no neon visual clutter*).
  2. **Konsistensi Status:** Setiap status turnamen, pendaftaran, pembayaran, dan pertandingan wajib memiliki penanda teks dan warna (*status badge*) yang konsisten di seluruh halaman.
  3. **Transparansi Mode Data:** Ketika aplikasi berjalan dalam `APP_MODE=mock`, antarmuka wajib menampilkan indikator yang jelas bahwa data yang sedang dilihat adalah data simulasi lokal.

---

## 2. Draft Token Visual (Dapat Disesuaikan oleh Ferlita)

Nilai variabel CSS di `desktop/web/assets/css/variables.css` disiapkan sebagai titik awal yang mudah diubah oleh Ferlita:

### A. Warna Permukaan (Dark Slate Theme)
| Token CSS | Nilai Awal (Draft) | Kegunaan |
| :--- | :--- | :--- |
| `--bg-primary` | `#0b0f17` | Latar belakang utama jendela aplikasi |
| `--bg-secondary` | `#111827` | Latar sidebar, topbar, dan panel sekunder |
| `--bg-surface` | `#161f30` | Kartu (*card*), kontainer tabel, dan kotak pertandingan |
| `--bg-surface-hover` | `#1e293b` | State *hover* pada baris tabel dan navigasi |
| `--border-subtle` | `#26334d` | Garis pemisah kartu, tabel, dan konektor bracket |

### B. Warna Teks & Aksen
| Token CSS | Nilai Awal (Draft) | Kegunaan |
| :--- | :--- | :--- |
| `--text-primary` | `#f8fafc` | Judul, nama tim, skor utama |
| `--text-secondary` | `#94a3b8` | Label kolom, metadata jadwal, subjudul |
| `--text-muted` | `#64748b` | Teks bantuan, placeholder, waktu lampau |
| `--accent-primary` | `#3b82f6` | Aksi utama, fokus aktif, sorotan navigasi |
| `--accent-secondary` | `#06b6d4` | Aksen sekunder untuk sorotan turnamen aktif |

### C. Warna Semantik Status
| Status | Token CSS | Nilai Awal | Contoh Penggunaan |
| :--- | :--- | :--- | :--- |
| **Success / Completed / Approved** | `--status-success` | `#10b981` | Pertandingan selesai, registrasi disetujui, pembayaran lunas |
| **Warning / Ongoing / Pending** | `--status-warning` | `#f59e0b` | Menunggu verifikasi panitia, pertandingan sedang berjalan, mode mock |
| **Danger / Disputed / Rejected** | `--status-danger` | `#ef4444` | Pendaftaran ditolak, sengketa skor, kesalahan validasi |
| **Info / Scheduled / Draft** | `--status-info` | `#6366f1` | Pertandingan terjadwal, turnamen dalam tahap persiapan |

---

## 3. Tipografi (Draft)

- **Font Utama (UI & Data):** `'Segoe UI', Inter, system-ui, -apple-system, sans-serif` — dioptimalkan untuk keterbacaan di Windows 10/11 tanpa bergantung pada koneksi internet.
- **Font Angka / Skor / Kode (`monospace`):** `'Cascadia Mono', 'Consolas', monospace` — wajib menggunakan `font-variant-numeric: tabular-nums` pada skor pertandingan, waktu jadwal, dan tabel klasemen agar angka sejajar secara vertikal.
- **Skala Ukuran Teks:**
  - Judul Halaman: `1.5rem` (24px), `font-weight: 700`
  - Judul Bagian / Kartu: `1.125rem` (18px), `font-weight: 600`
  - Teks Utama / Tabel: `0.875rem` (14px), `font-weight: 400`
  - Badge / Label Kecil: `0.75rem` (12px), `font-weight: 600`

---

## 4. Tata Letak Desktop (App Shell)

1. **Sidebar Kiri Tetap (`250px`):**
   - Logo & identitas **Turnamen.in**.
   - Daftar menu utama: Dashboard, Daftar Turnamen, Detail Turnamen, Manajemen Tim, Manajemen Pertandingan, Bracket, Pengumuman, Laporan, Profil Pengguna, dan Pintu Masuk (Login).
   - Indikator status koneksi API lokal (`Flask API Connected` / `Offline`).
2. **Topbar (`64px`):**
   - Judul halaman aktif & ringkasan konteks turnamen yang sedang dipilih.
   - Badge mode aplikasi (`MOCK MODE` atau `SUPABASE ONLINE`).
   - Pemilih peran simulasi (*Role Switcher* khusus mode mock untuk menguji tampilan per role) dan informasi profil aktif.
3. **Area Konten Utama (`flex: 1`, scrollable):**
   - Padding proporsional (`24px`), grid ringkasan metrik di bagian atas, diikuti filter/pencarian dan konten utama (tabel, daftar kartu, atau visualisasi bracket).

---

## 5. Komponen Dasar yang Tersedia di Starter

1. **Sidebar & Topbar Navigation**
2. **Summary Metric Cards** (jumlah turnamen aktif, tim terdaftar, pertandingan selesai, total hadiah)
3. **Data Tables** dengan kolom terstruktur, pencarian instan, dan filter status
4. **Single Elimination Bracket View** (Quarter Final → Semi Final → Final untuk 8 tim)
5. **Modal / Dialog** untuk detail dan form input terfokus
6. **Forms** dengan validasi input yang jelas
7. **Status Badges** (`draft`, `open_registration`, `ongoing`, `completed`, `pending`, `approved`, `rejected`, `scheduled`, ` bye`)
8. **Toast Notifications** untuk umpan balik aksi pengguna
9. **State Standar:** *Loading State*, *Empty State*, *Error State*, dan *Success State*.

---

## 6. Panduan Tinjauan untuk Ferlita

Ferlita dapat memperbarui dokumen ini serta file CSS di `desktop/web/assets/css/` dengan langkah berikut:
1. Tinjau variabel warna dan tipografi di `desktop/web/assets/css/variables.css`.
2. Periksa struktur komponen di `desktop/web/assets/css/components.css` dan halaman di `desktop/web/pages/`.
3. Pastikan setiap tombol yang fiturnya masih berupa *blueprint* atau *placeholder* menampilkan keterangan status yang jujur (bukan tombol mati tanpa umpan balik).
4. Setelah palet dan komponen disepakati bersama tim, ubah status dokumen ini dari `DRAFT` menjadi `APPROVED`.
