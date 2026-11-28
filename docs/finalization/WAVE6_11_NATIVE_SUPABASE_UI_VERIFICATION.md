# Wave 6.11: Laporan Verifikasi Native Desktop UI (APP_MODE=supabase)

**Tanggal:** 28 November 2026
**Branch Repository:** `feature/fikri-ui-ux`
**Mode Target:** `APP_MODE=supabase` via Python Eel native (`python run.py`, tanpa `--api-only`)
**Sifat Pengujian:** READ-ONLY (tanpa upload, replace, restore, perubahan database/Storage, atau pembuatan `.env`)
**Status Keseluruhan:** **PASS (Verifikasi Pengguna Tanpa Kendala; Arsip Screenshot Tidak Tersedia / NOT TESTED)**

> **Ringkasan Eksekusi Pengguna:** Launcher native Python Eel (`wave611_native_supabase_ui.ps1`) telah dijalankan oleh pengguna pada `28 November 2026` pukul `13:47:57` s/d `13:49:41` WIB **sesudah perbaikan CSS layout overflow & double scrollbar selesai**. Pengguna mengonfirmasi seluruh pemeriksaan berjalan lancar tanpa kendala, dan metadata sesi mencatat penutupan aplikasi bersih (`app_exit_code: 0`) serta pembersihan seluruh environment variable sementara (`env_vars_cleaned: true`). Arsip screenshot dan ekspor log DevTools tidak disimpan pada folder screenshot, sehingga butir arsip dicatat secara jujur sebagai **NOT TESTED**.

---

## 1. Identifikasi Konfigurasi `run.py` & Environment Variable Wajib (`PASS` - Audit Statis)

Berdasarkan pemeriksaan langsung terhadap [`run.py`](file:///C:/Turnamen.in/run.py), [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L200-L384), dan [`desktop/launcher/app_launcher.py`](file:///C:/Turnamen.in/desktop/launcher/app_launcher.py#L374-L481), berikut kebutuhan konfigurasi untuk menjalankan aplikasi native Python Eel dalam mode `supabase`:

| Variabel Environment | Status | Nilai / Aturan pada Pengujian Read-Only | Sumber Penegakan |
| :--- | :--- | :--- | :--- |
| `APP_MODE` | **Wajib** | `supabase` | [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L239-L299) |
| `SUPABASE_URL` | **Wajib** | `https://cfdsgxciodfkamskafwe.supabase.co` | [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L294-L299) |
| `SUPABASE_PUBLISHABLE_KEY` | **Wajib** | Diinput tersembunyi oleh pengguna saat runtime (`sb_publishable_...`), atau legacy anon key via `SUPABASE_ANON_KEY` (`eyJ...`, tidak boleh bertentangan dan dilarang `sb_secret_*` / `service_role`) | [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L291-L299) |
| `SECRET_KEY` | **Wajib** | Token acak lokal ephemeral (>= 32 karakter) di memori proses | [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L283-L289) |
| `API_HOST` / `API_PORT` | Opsional (Default aman) | `127.0.0.1` / `5000` | [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L351-L352) |
| `EEL_HOST` / `EEL_PORT` | Opsional (Default aman) | `127.0.0.1` / `8080` | [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L355-L356) |
| `EEL_BROWSER_MODE` | Opsional (Default aman) | `chrome` (`C:\Program Files\Google\Chrome\Application\chrome.exe` terdeteksi tersedia) | [`desktop/launcher/app_launcher.py`](file:///C:/Turnamen.in/desktop/launcher/app_launcher.py#L353-L443) |
| `EEL_START_PAGE`, ukuran window | Opsional (Default aman) | `index.html`, `1366x820` | [`backend/core/config.py`](file:///C:/Turnamen.in/backend/core/config.py#L358-L360) |

Catatan keamanan:
- File `.env` tidak ada sebelum maupun sesudah eksekusi (`dotenv_exists_before: false`, `dotenv_exists_after: false`).
- [`load_config()`](file:///C:/Turnamen.in/backend/core/config.py#L338-L384) membaca langsung environment variable proses sementara tanpa menulis file `.env`.

---

## 2. Kesiapan Launcher PowerShell Sementara & Fixture Lokal (`PASS`)

- **Launcher PowerShell:** `%LOCALAPPDATA%\TurnamenBackups\wave611_native_supabase_ui.ps1`
- **File Uji Preview Lokal (Read-Only):**
  - `%LOCALAPPDATA%\TurnamenBackups\native_ui_test_files\valid_preview_640x360.png` (`1,484` byte, PNG `640x360` valid untuk preview tanpa klik `Simpan Poster`)
  - `%LOCALAPPDATA%\TurnamenBackups\native_ui_test_files\invalid_disguised_svg.png` (`71` byte, file SVG bertipe ekstensi `.png` untuk uji penolakan format tidak valid tanpa upload)
- **Direktori Screenshot:** `%LOCALAPPDATA%\TurnamenBackups\native_ui_screenshots\`
- **Metadata Sesi (Non-Secret):** `%LOCALAPPDATA%\TurnamenBackups\wave611_native_ui_session.json`

---

## 3. Matriks Verifikasi Native Desktop UI (`APP_MODE=supabase`, Read-Only, Pasca CSS Fix)

| No | Item Verifikasi | Status | Bukti Aktual / Catatan |
| :-: | :--- | :---: | :--- |
| 1 | Pre-check `run.py --check` & peluncuran native Python Eel (`python run.py`) | **PASS** | `wave611_native_ui_session.json`: `precheck_exit_code: 0` (`health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`, `app_mode: "supabase"`, `supabase_configured: true`, `error: null`), `launcher_mode: "native_python_eel"`, `key_type: "publishable"`. |
| 2 | Login Super Admin (input langsung oleh pengguna) | **PASS** | Dikonfirmasi langsung oleh pengguna berjalan normal tanpa kendala. |
| 3 | Halaman Dashboard Super Admin & Layout Desktop (Sidebar penuh, footer di dasar, tanpa ruang hitam, tanpa scrollbar ganda) | **PASS** | Dikonfirmasi langsung oleh pengguna pada pengujian pasca-perbaikan CSS (`13:47:57` s/d `13:49:41` WIB) tanpa kendala. |
| 4 | Halaman Manajemen Game | **PASS** | Dikonfirmasi langsung oleh pengguna tampil normal tanpa kendala. |
| 5 | Ketiga artwork resmi dari Supabase (`Mobile Legends: Bang Bang`, `VALORANT`, `EA Sports FC 25`) | **PASS** | Ketiga game katalog aktual terkonfirmasi pada pre-check (`games_count: 3`) dan diverifikasi tampil normal oleh pengguna pada jendela native. |
| 6 | Navigasi antar halaman | **PASS** | Dikonfirmasi langsung oleh pengguna berjalan normal tanpa kendala. |
| 7 | Preview file lokal valid (`valid_preview_640x360.png`, lalu `Batalkan Preview`) | **PASS** | Dikonfirmasi langsung oleh pengguna berjalan normal tanpa klik `Simpan Poster`. |
| 8 | Validasi penolakan file tidak didukung (`invalid_disguised_svg.png`) | **PASS** | Dikonfirmasi langsung oleh pengguna penolakan berjalan normal tanpa upload. |
| 9 | Console JavaScript & error API | **PASS** *(Konfirmasi Pengguna)* | Pengguna mengonfirmasi tidak ada kendala error JS/API; catatan: tidak ada file ekspor log DevTools yang diarsipkan. |
| 10 | Penutupan normal jendela desktop, pembersihan env var sementara, `.env` tetap tidak ada, dan nol mutasi Cloud | **PASS** | `wave611_native_ui_session.json`: `app_exit_code: 0`, `env_vars_cleaned: true`, `remaining_temp_vars: []`, `dotenv_exists_before: false`, `dotenv_exists_after: false`. |
| 11 | Arsip screenshot sesi Native Desktop UI | **NOT TESTED** | Direktori `%LOCALAPPDATA%\TurnamenBackups\native_ui_screenshots\` terverifikasi kosong (`[]`); tidak ada file screenshot yang disimpan untuk diarsipkan. |
| 12 | Mutasi live UI (upload/replace/restore poster) & akun non-admin live pada Eel native | **NOT TESTED** | Sengaja tidak dijalankan pada sesi read-only ini. Siklus upload/replace/restore sudah teruji terpisah via live Cloud API Wave 6.11 (`7/7 PASS`), sedangkan uji akun non-admin live ditangguhkan karena hanya ada `1` Auth user dan `Public Signup = DISABLED`. |

---

## 4. Bukti Metadata Sesi & Status Arsip

- **Metadata Sesi Aktual (`%LOCALAPPDATA%\TurnamenBackups\wave611_native_ui_session.json`):**
  - `started_at`: `2026-11-28T13:47:57.0162035+07:00`
  - `ended_at`: `2026-11-28T13:49:41.4839090+07:00` (`~104.5` detik)
  - `launcher_mode`: `native_python_eel`
  - `app_mode`: `supabase`
  - `supabase_url`: `https://cfdsgxciodfkamskafwe.supabase.co`
  - `key_type`: `publishable`
  - `precheck_exit_code`: `0` (`health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`, `supabase_configured: true`)
  - `app_exit_code`: `0`
  - `dotenv_exists_before`: `false` / `dotenv_exists_after`: `false`
  - `env_vars_cleaned`: `true` (`remaining_temp_vars: []`)
- **Screenshot Native Desktop UI (`%LOCALAPPDATA%\TurnamenBackups\native_ui_screenshots\`):** **NOT TESTED** (tidak ada file gambar tersimpan; tidak ada bukti screenshot yang diklaim atau dibuat-buat).

---

## 5. Kesimpulan

Tahap **P0 Native Desktop Supabase UI Verification (`APP_MODE=supabase`, Read-Only)** telah dijalankan secara penuh di desktop lokal oleh pengguna setelah perbaikan CSS overflow dan selesai **tanpa kendala**, dengan pembersihan environment variable sementara yang terverifikasi oleh launcher (`app_exit_code: 0`, `env_vars_cleaned: true`, `dotenv_exists_after: false`). Satu-satunya celah dokumentasi hanyalah absennya arsip screenshot (`NOT TESTED`), sementara seluruh fungsi aplikasi untuk akun `super_admin` terkonfirmasi siap sebelum tim melangkah ke daftar pekerjaan P1.
