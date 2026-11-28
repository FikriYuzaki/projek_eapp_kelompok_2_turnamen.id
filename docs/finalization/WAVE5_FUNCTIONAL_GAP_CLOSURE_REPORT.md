# Laporan Wave 5: Functional Gap Closure & Application Stabilization

- **Tanggal Selesai:** 2026-11-26
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Status Pengujian Akhir:** **`263 passed, 1 warning in 47.34s`** (tanpa error, pada Python 3.12.10 + PostgreSQL 18.6 lokal)

---

## 1. Bug yang Diperbaiki

1. **Koreksi Baseline Supabase Cloud pada [APP_READINESS_REPORT.md](file:///C:/Turnamen.in/docs/finalization/APP_READINESS_REPORT.md):**
   - Memperbarui kondisi project `turnamen-in` (`cfdsgxciodfkamskafwe`) sesuai hasil inspeksi read-only via koneksi Supabase ChatGPT pada `2026-11-26` (bukan akses langsung Antigravity):
     - `12` public tables, `12` tabel ber-RLS enabled, total `9` RLS policies aktif, `uq_tournament_seed` tersedia, `migration history` kosong, `5` profiles dengan `auth_user_id = NULL`, serta `4` tabel yang belum memiliki policy (`activity_logs`, `payments`, `registrations`, `tournament_staff`).
2. **Tournament Status Transition Integrity ([service.py](file:///C:/Turnamen.in/backend/modules/tournaments/service.py)):**
   - Memperbaiki `TournamentService.update_tournament()` agar seluruh perubahan `status` wajib melewati `self._repo.transition_tournament_status()` (dan tidak pernah dikirim ke `update_tournament()`).
   - Validasi field biasa (`title`, `venue`, `date_range`, `max_teams`, `best_of`, dll.) dilakukan terlebih dahulu; perubahan status dieksekusi sebelum pembaruan field biasa sehingga kegagalan aturan state machine atau integritas bracket (misalnya `ongoing` ke `completed` sebelum Grand Final selesai) gagal konsisten (`409 CONFLICT`) tanpa meninggalkan perubahan parsial.
   - Pengubahan field biasa tanpa `status` tidak mengganggu status turnamen yang sedang berjalan.
3. **Announcement Author Name Protection & Projection ([0006_wave5_functional_rpc.sql](file:///C:/Turnamen.in/supabase/migrations/0006_wave5_functional_rpc.sql), [supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py), [announcements/service.py](file:///C:/Turnamen.in/backend/modules/announcements/service.py)):**
   - Menghapus query langsung `client.table("profiles").select("id,full_name")` dari `SupabaseDataStoreRepository.list_announcements_by_tournament()` yang terblokir RLS `0005` (`"Profiles select own or admin"`).
   - Menambahkan RPC `public.list_tournament_announcements(p_tournament_id UUID)` (`SECURITY DEFINER`, `SET search_path = ''`, tanpa parameter lookup profil acak) yang mengembalikan kolom pengumuman plus `author_name` (`COALESCE(NULLIF(btrim(p.full_name), ''), 'Panitia')`) tanpa membuka `SELECT` pada `public.profiles` dan tanpa mengembalikan `email`, `phone`, `auth_user_id`, atau PII lainnya.
   - Pengumuman pada turnamen berstatus `draft` dibatasi hanya untuk `super_admin`, `organizer` pemilik, atau `committee` yang ditugaskan (`[]` bagi `anon` / `player`), baik pada PostgreSQL RPC `0006` maupun `AnnouncementService.list_announcements()`.
4. **Authentication Session Persistence pada Windows Desktop App ([config.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/config.js), [api-client.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/api-client.js), [app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js)):**
   - **Kepemilikan Session:** Backend (`AuthService._sessions` di Mock Mode dan Supabase GoTrue Auth di Supabase Mode) adalah pemilik kebenaran sesi; frontend hanya menyimpan handle bearer token + identitas tersanitasi di `window.sessionStorage` (`turnamen.auth_session.v1`).
   - **Mengapa `window.sessionStorage`:** Eel (`eel==0.17.0`) berjalan di atas Chromium `--app` tanpa keychain/storage terenkripsi bawaan. `sessionStorage` mempertahankan sesi login maupun role simulasi saat window di-reload (`F5`), sekaligus otomatis dibersihkan saat window aplikasi ditutup, tanpa menyimpan password, `service_role` key, `refresh_token` plaintext di file konfigurasi, maupun token buatan sendiri.
   - **Penanganan Expiry & Pencabutan:** `config.js` memeriksa klaim `exp` pada JWT sebelum memulihkan sesi; `initApp()` melakukan revalidasi ke backend via `GET /api/v1/auth/me` saat reload; respons `401 UNAUTHORIZED` otomatis membersihkan sesi lokal; dan `handleLogout()` / `enterGuestMode()` memanggil `POST /api/v1/auth/logout` lalu menghapus key sesi dari `sessionStorage`.

---

## 2. Fitur PARTIAL yang Diselesaikan

| Fitur | UI (`app-pages.js`) | API Client (`api-client.js`) | Flask API (`v1_routes.py`) | Service & Repository | Database (`0002`–`0006`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Edit Profile** | Form edit `full_name`, `phone`, `avatar_url` di `renderProfilePage` + tombol `Simpan Profil` | `updateProfile()` (`PATCH /auth/me`) | `PATCH /api/v1/auth/me` | `AuthService.update_profile()` | `0002` `"Profiles update own"` + trigger anti-eskalasi `role` |
| **CRUD Games** | Tombol `Tambah Game`, ikon edit per game, & modal create/edit/nonaktifkan di Dashboard Super Admin | `createGame()`, `updateGame()`, `getGames({ includeInactive })` | `POST /api/v1/games`, `PATCH /api/v1/games/<id>`, `GET /api/v1/games?include_inactive=true` | `TournamentService.create_game()`, `update_game()` (`game:manage`), Mock & Supabase Repo | `0002` `"Super admin manage games"` |
| **Tournament Staff** | Panel `Penugasan Panitia (Committee)` di `renderTournamentDetail` (daftar staf, dropdown kandidat, tombol tugaskan & cabut) | `getCommitteeCandidates()`, `getTournamentStaff()`, `addTournamentStaff()`, `removeTournamentStaff()` | `GET /api/v1/staff/candidates`, `GET/POST /api/v1/tournaments/<id>/staff`, `DELETE /api/v1/tournaments/<id>/staff/<user_id>` | `TournamentService.*_tournament_staff()`, Mock & Supabase Repo | `0002` RLS `tournament_staff` + `0006` `list_committee_candidates()` & `list_tournament_staff()` |
| **Assign User Role** | Tabel `Manajemen Pengguna & Penetapan Role` pada Dashboard Super Admin | `getUsers()`, `assignUserRole()` | `GET /api/v1/users`, `PATCH /api/v1/users/<id>/role` | `AuthService.list_users()`, `assign_role()` -> `assign_user_role()` | `0005` `assign_user_role` RPC + `"Profiles select own or admin"` |
| **Super Admin Bootstrap** | Badge status `Tertaut Auth` / `Belum Tertaut` di tabel admin | Didokumentasikan pada laporan kesiapan & Wave 5 | Login standar via `POST /api/v1/auth/login` setelah linking | `AuthService._login_supabase()` | `0005` `public.link_profile_auth_user()` untuk tautan `super_admin` pertama via `postgres`/`service_role` |

---

## 3. Fitur yang Masih Belum Tersedia (Opsional Post-MVP)

- **Modul Pembayaran (`payments`):**
  - Hasil pemeriksaan seluruh kontrak ([api-contract.md](file:///C:/Turnamen.in/docs/contracts/api-contract.md), [module-contract.md](file:///C:/Turnamen.in/docs/contracts/module-contract.md), [frontend-contract.md](file:///C:/Turnamen.in/docs/contracts/frontend-contract.md)), `backend/`, dan `desktop/`: tabel `payments` hanya disiapkan di skema SQL (`0001`/`0002`) dan seed data (`mock_data.py`/`seed.sql`), **tanpa** endpoint API, method repository, service, maupun UI yang direncanakan.
  - Dengan demikian `payments` berstatus **fitur opsional pasca-MVP**, tidak menggunakan payment gateway eksternal, dan **bukan penghambat demonstrasi aplikasi**.

---

## 4. File yang Diubah dan Ditambah pada Wave 5

- **Database Migration Baru (`0001`–`0005` dipertahankan utuh):**
  - [0006_wave5_functional_rpc.sql](file:///C:/Turnamen.in/supabase/migrations/0006_wave5_functional_rpc.sql)
- **Backend & Repositories:**
  - [repository_protocol.py](file:///C:/Turnamen.in/backend/repositories/interfaces/repository_protocol.py)
  - [mock_repository.py](file:///C:/Turnamen.in/backend/repositories/mock/mock_repository.py)
  - [supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py)
  - [service.py](file:///C:/Turnamen.in/backend/modules/auth/service.py) (`AuthService`)
  - [service.py](file:///C:/Turnamen.in/backend/modules/tournaments/service.py) (`TournamentService`)
  - [service.py](file:///C:/Turnamen.in/backend/modules/announcements/service.py) (`AnnouncementService`)
  - [v1_routes.py](file:///C:/Turnamen.in/backend/api/routes/v1_routes.py)
- **Frontend Desktop:**
  - [config.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/config.js)
  - [api-client.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/api-client.js)
  - [app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js)
- **Tests & Documentation:**
  - [test_wave1_tournament_rules.py](file:///C:/Turnamen.in/tests/unit/test_wave1_tournament_rules.py)
  - [test_wave4b_postgres_migrations_and_security.py](file:///C:/Turnamen.in/tests/integration/test_wave4b_postgres_migrations_and_security.py)
  - [test_wave5_functional_gap_closure.py](file:///C:/Turnamen.in/tests/unit/test_wave5_functional_gap_closure.py)
  - [APP_READINESS_REPORT.md](file:///C:/Turnamen.in/docs/finalization/APP_READINESS_REPORT.md)
  - [WAVE5_FUNCTIONAL_GAP_CLOSURE_REPORT.md](file:///C:/Turnamen.in/docs/finalization/WAVE5_FUNCTIONAL_GAP_CLOSURE_REPORT.md)

---

## 5. Hasil Pengujian & Quality Gate

| Pengujian / Pemeriksaan | Hasil | Detail Terbaru |
| :--- | :--- | :--- |
| Full `pytest -v` | **PASS (`263 passed`)** | `263 passed, 1 warning in 47.34s` (termasuk unit test Wave 1–5, API integration tests, Node VM UI/session tests, dan 8 PostgreSQL 18.6 integration tests mencakup migration `0001` sampai `0006`). |
| CLI Smoke Check (`run.py --check`) | **PASS** | `app_mode: "mock"`, `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`. |
| JS Syntax Check (`node --check`) | **PASS (5/5)** | `config.js`, `eel-bridge.js`, `api-client.js`, `ui-components.js`, `app-pages.js` lulus bersih. |
| Wave 5 Eel Mock Loopback E2E | **PASS** | Diuji end-to-end melalui `BackgroundFlaskServer` + `eel_bridge.forward_api_request`: login semua role uji (`admin`, `organizer`, `captain`, `player`), `PATCH /auth/me`, `GET /users`, `POST/PATCH /games`, `POST /tournaments`, `GET /staff/candidates`, `POST /tournaments/<id>/staff`, buat 2 tim, daftar + approve, generate bracket, submit skor, cek `reports` (`champion: Wave5 Alpha`), `POST /announcements`, dan `POST /auth/logout`. |
| Git Hygiene (`git diff --check`) | **PASS** | Exit code `0`, branch tetap `feature/fikri-ui-ux`, tidak ada commit/push/merge maupun perubahan ke Cloud. |

---

## 6. Keseimbangan Mock & Supabase Parity

- Seluruh interface baru (`assign_user_role`, `list_games(include_inactive)`, `create_game`, `update_game`, `list_tournament_staff`, `list_committee_candidates`, `add_tournament_staff`, `remove_tournament_staff`, serta `list_announcements_by_tournament`) memiliki kontrak method identik pada `DataStoreRepositoryProtocol`, `MockDataStoreRepository`, dan `SupabaseDataStoreRepository`.
- Validasi domain dan pemeriksaan role RBAC berjalan konsisten di layer `Service` dan diperkuat di layer PostgreSQL melalui RLS (`0002`, `0005`) serta RPC (`0003`, `0004`, `0005`, `0006`).

---

## 7. Batasan Supabase Cloud Saat Ini

1. **Lingkungan Cloud Belum Dimigrasi:** Berdasarkan inspeksi read-only koneksi Supabase ChatGPT (`2026-11-26`), `turnamen-in` (`cfdsgxciodfkamskafwe`) belum memiliki riwayat migrasi `0002` sampai `0006` maupun RPC yang diandalkan aplikasi dalam `APP_MODE=supabase`, dan 4 tabel privat (`activity_logs`, `payments`, `registrations`, `tournament_staff`) masih belum ber-policy.
2. **Wave 4C GoTrue/PostgREST Integration:** Pengujian nyata terhadap GoTrue + PostgREST lokal tetap **BLOCKED** karena tidak ada container runtime (`Docker` / `Podman` / `Rancher Desktop`), sehingga **tidak diklaim PASS terhadap Supabase Cloud**.
3. **Konfigurasi `.env`:** File `.env` lokal tidak dibuat oleh audit ini; untuk beralih ke mode Supabase dibutuhkan `.env` berisi `APP_MODE=supabase`, `SUPABASE_URL`, dan legacy public `SUPABASE_ANON_KEY` (`eyJ...`) setelah Cloud menerapkan `0002` sampai `0006` dan bootstrap `super_admin` melalui `public.link_profile_auth_user(...)`.

---

## 8. Penilaian Kesiapan Demonstrasi

- **Demonstrasi Offline / Desktop Lokal (`APP_MODE=mock`):** **SIAP PENUH (READY)**. Seluruh alur utama dan fitur yang sebelumnya berstatus `PARTIAL` (edit profil, manajemen game `super_admin`, penugasan panitia turnamen, penetapan role pengguna, persistensi session di browser desktop saat reload, dan state machine turnamen) kini berfungsi end-to-end dengan stabilitas penuh (`263 passed`).
- **Demonstrasi Online (`APP_MODE=supabase`):** **SIAP SECARA KODE & SKEMA LOKAL (`0001`–`0006`), MENUNGGU DEPLOY MIGRASI CLOUD & `.env`**. Setelah `0002` sampai `0006` diterapkan ke database target serta akun `super_admin` ditautkan dengan `link_profile_auth_user`, backend dan frontend siap terhubung ke Supabase Auth & PostgreSQL.
