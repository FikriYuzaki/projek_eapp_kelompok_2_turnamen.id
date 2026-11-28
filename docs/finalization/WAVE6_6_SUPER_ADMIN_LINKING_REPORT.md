# TURNAMEN.IN: WAVE 6.6 SUPER ADMIN LINKING & SECURITY ADVISORS REPORT

- **Tanggal Laporan:** 2026-11-26
- **Project Ref:** `cfdsgxciodfkamskafwe` (`turnamen-in`, Region `ap-south-1`, PostgreSQL `17.11`)
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Status Akhir Wave 6.6:** **`SUPER ADMIN LINKED: READY FOR CONTROLLED RUNTIME LOGIN TEST`** *(Public Signup tetap `DISABLED`; Security Advisors memerlukan review lanjutan sebelum perubahan grants/fungsi apa pun.)*

---

## 1. Hasil Aktual Linking Super Admin

Pengaitan akun `super_admin` telah dieksekusi secara eksplisit pada Supabase Cloud melalui fungsi `private.link_profile_auth_user(p_profile_id uuid, p_auth_user_id uuid)` setelah seluruh audit pra-linking pada Wave 6.6 lulus:

| Pemeriksaan | Hasil Aktual Cloud | Target | Status |
| :--- | :--- | :--- | :---: |
| **Metode Linking** | `private.link_profile_auth_user('11111111-1111-4111-8111-111111111101'::uuid, 'abc811ac-a57a-4d63-8c90-92280e4962c4'::uuid)` | Eksplisit via `0005` RPC | **PASS** |
| **Keterkaitan Profil `super_admin`** | Profil `super_admin` (`11111111-1111-4111-8111-111111111101`) terhubung ke Auth user (`abc811ac-a57a-4d63-8c90-92280e4962c4`) | Tertaut 1:1 | **PASS** |
| **Status & Role Profil** | `role = 'super_admin'`, tetap aktif (`is_active = true`) | Aktif & tidak berubah | **PASS** |
| **Total Profil (`public.profiles`)** | **`5` baris** (`1` tertaut, `4` akun demo lainnya tetap unlinked) | Tetap `5` | **PASS** |
| **Total Auth Users (`auth.users`)** | **`1` baris** (terverifikasi email) | Tetap `1` | **PASS** |
| **Audit Trail (`public.activity_logs`)** | **`1` catatan audit `PROFILE_AUTH_LINKED`** berhasil dibuat | Tercatat otomatis | **PASS** |
| **Status Public Signup** | **Tetap `DISABLED`** | `DISABLED` | **PASS** |

---

## 2. Ringkasan Audit Infrastruktur Pra-Linking (Dari `wave66_audit_result.json`)

- **`role_table_grants`:** `12` tabel domain inti memakai default privilege Data API yang dibatasi oleh RLS aktif (`13` tabel `relrowsecurity = true`, `43` policy); `public.match_submission_requests` mencabut semua hak dari `PUBLIC` & `anon` dan hanya mengizinkan `SELECT` terbatas untuk `authenticated`.
- **Foreign Key:** `fk_profiles_auth_user_id` aktif (`FOREIGN KEY (auth_user_id) REFERENCES auth.users(id) ON DELETE SET NULL`).
- **Auth Trigger `0005` (`on_auth_user_created` / `handle_new_auth_user`):** `SET search_path TO ''`, penolakan email existing `SQLSTATE 23505` aktif, dan auto-link berdasarkan email nonaktif (`has_autolink_update = false`).

---

## 3. Hasil Security Advisors & Penilaian Teknis

Pemeriksaan **Supabase Dashboard -> Advisors -> Security Advisor** pada project `cfdsgxciodfkamskafwe` pasca-linking melaporkan temuan berikut:

| Kategori Temuan Security Advisors | Jumlah / Status | Penilaian & Tindak Lanjut |
| :--- | :---: | :--- |
| **`anon` `SECURITY DEFINER`** | **`2` temuan** | **Perlu review, JANGAN langsung ubah grants atau fungsi.** Pada arsitektur `0001`-`0006`, tepat `2` fungsi `SECURITY DEFINER` memiliki `anon_exec = true`: `public.current_user_role()` (dipakai evaluasi policy RLS) dan `public.list_tournament_announcements(UUID)` (proyeksi non-PII untuk halaman turnamen publik yang menyembunyikan turnamen `draft`). Mencabut hak `anon` secara langsung akan memutus policy RLS atau tampilan pengumuman publik bagi Guest. |
| **`authenticated` `SECURITY DEFINER`** | **`6` temuan** | **Perlu review, JANGAN langsung ubah grants atau fungsi.** Aplikasi secara sengaja memakai `SECURITY DEFINER` dengan `SET search_path = ''` agar helper RLS (`current_profile_id`, `is_tournament_organizer`, `is_tournament_committee`, `is_team_captain`) serta RPC `private.*` terproteksi (`transition_tournament_status`, `get_public_profile_summary`, `register_team_atomic`, `submit_match_result_atomic`, `link_profile_auth_user`, `assign_user_role`, `list_committee_candidates`, `list_tournament_staff`) tetap dapat menembus RLS `profiles`/`matches`/`registrations` secara terkendali tanpa membuka tabel `profiles` secara langsung. Setiap item perlu ditinjau per fungsi bersama detail Advisor sebelum memutuskan apakah ada penyesuaian. |
| **Leaked Password Protection** | **`disabled`** | Pengaturan GoTrue Auth di Supabase Dashboard (tergantung konfigurasi/paket project). Perlu ditinjau dan dipertimbangkan pengaktifannya sebelum Public Signup dibuka kembali. |

**Kesimpulan Advisor:** Tidak boleh langsung mencabut `EXECUTE` atau menghapus `SECURITY DEFINER` secara massal. Temuan ini tidak memblokir pengujian login read-only `super_admin` pada tahap berikutnya selama Public Signup tetap `DISABLED`.

---

## 4. Rencana Pengujian Login Desktop Turnamen.in (`APP_MODE=supabase`)

> **Batasan Keamanan:** Pengujian belum dijalankan pada tahap ini. Jangan membuat/mengubah file `.env` atau menjalankan pengujian yang membuat/mengubah data produksi tanpa persetujuan eksplisit. Jangan pernah memakai `sb_secret_*` atau `service_role` key pada konfigurasi desktop.

### Langkah 1: Siapkan Konfigurasi Ephemeral / Lokal (Saat Disetujui)
Sesuai [config.py](file:///C:/Turnamen.in/backend/core/config.py) dan [client.py](file:///C:/Turnamen.in/backend/infrastructure/supabase/client.py), aplikasi mendukung variabel berikut (prioritaskan `SUPABASE_PUBLISHABLE_KEY`):
```powershell
# Opsi aman di sesi PowerShell sementara (tidak menulis file .env ke disk):
$env:APP_MODE = "supabase"
$env:SECRET_KEY = "<string-acak-lokal-minimal-32-karakter>"
$env:SUPABASE_URL = "https://cfdsgxciodfkamskafwe.supabase.co"
$env:SUPABASE_PUBLISHABLE_KEY = "<salin-sb_publishable_...-dari-Dashboard-Project-Settings-API>"
# Catatan: jika memakai legacy key, gunakan SUPABASE_ANON_KEY (eyJ...) saja, bukan keduanya dengan nilai berbeda.
```

### Langkah 2: Smoke Check Non-Mutatif (`run.py --check`)
```powershell
.\.venv\Scripts\python.exe run.py --check --mode supabase
```
- **Ekspektasi:** `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`, tanpa menyentuh atau menulis data produksi dan tanpa mencetak secret ke log.

### Langkah 3: Uji Login Desktop Read-Only (`super_admin`)
```powershell
.\.venv\Scripts\python.exe run.py
```
1. Masuk pada layar login memakai kredensial akun Auth `super_admin` yang sudah ditautkan (`abc811ac-a57a-4d63-8c90-92280e4962c4`).
2. Verifikasi **read-only** tanpa membuat data baru:
   - Login berhasil (`POST /api/v1/auth/login` -> `200`, profil aktif dengan `role = super_admin`).
   - Sesi aktif terbaca (`GET /api/v1/auth/me`).
   - Data kompetisi awal (`3` game, `2` turnamen, `8` tim, bracket, dan `2` pengumuman) tampil normal melalui RLS + RPC `0006`.
   - Daftar profil/admin terbaca oleh `super_admin` sesuai `"Profiles select own or admin"`.
   - Uji logout (`POST /api/v1/auth/logout`) dan pastikan akses tanpa token ke endpoint terproteksi ditolak (`401`).
3. **Larangan selama uji awal:** Jangan membuat turnamen/tim/registrasi/user uji baru di produksi, jangan aktifkan Public Signup, dan bersihkan variabel environment sementara setelah selesai (`Remove-Item Env:APP_MODE, Env:SECRET_KEY, Env:SUPABASE_URL, Env:SUPABASE_PUBLISHABLE_KEY -ErrorAction SilentlyContinue`).

---

## 5. Hasil Aktual Wave 6.7 Tahap 1: Smoke Check Supabase (`PASS`)

- **Waktu Eksekusi:** `2026-11-26T15:13:11Z` UTC (`22:13:11` WIB)
- **Sumber Bukti Utama:** `wave67_stage1_smoke_result.json` (`exit_code: 0`, `passed: true`, `error_message: null`)
- **Perintah Teruji:** `.\.venv\Scripts\python.exe run.py --check --mode supabase` (via skrip sementara di luar repository dengan variabel environment proses sementara)

| Item Verifikasi Smoke Check | Hasil Aktual | Status |
| :--- | :--- | :---: |
| **Mode Aplikasi (`APP_MODE`)** | `supabase` (`is_simulation: false`, `supabase_configured: true`) | **PASS** |
| **Status API Health (`health_ok`)** | `true` (`GET /api/v1/health` -> `200`) | **PASS** |
| **Status Repository (`repository_ok`)** | `true` | **PASS** |
| **Jumlah Game (`games_count`)** | `3` (`GET /api/v1/games` -> `200`, baca langsung ke Supabase Cloud) | **PASS** |
| **Jumlah Turnamen (`tournaments_count`)** | `2` (`GET /api/v1/tournaments` -> `200`, baca langsung ke Supabase Cloud) | **PASS** |
| **Keamanan & Non-Mutasi** | Ketiga request `GET` berhasil tanpa `INSERT`, `UPDATE`, `DELETE`, `login`, `logout`, maupun mutasi data produksi; `secret_key` dan `supabase_publishable_key` ter-redaksi (`***REDACTED***`), `.env` tidak dibuat, dan environment sementara sudah dibersihkan di blok `finally` | **PASS** |
| **Status Tahap Selanjutnya** | **Smoke Check PASS.** Tahap 2 (uji login & desktop UI) belum dijalankan dan menunggu persetujuan eksplisit; Public Signup tetap `DISABLED`. | **HOLD** |
