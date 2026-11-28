# Laporan Kesiapan Aplikasi Turnamen.in (Final Application Readiness Audit)

- **Tanggal Audit:** 2026-11-26
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Status Akhir Kesiapan:** **READY WITH LIMITATIONS**
  - **Mock Mode (Demo Lokal / Simulasi):** **READY** (Desktop Flask API + Eel bridge + frontend berjalan stabil, 257 test lulus, E2E loopback flow lulus).
  - **Supabase Online Mode (Cloud Production):** **NOT READY / BLOCKED** (belum ada `.env` lokal, dan Supabase Cloud berdasarkan inspeksi koneksi Supabase ChatGPT read-only pada 2026-11-26 belum menerapkan migration `0002` sampai `0005` serta masih memiliki 5 profil seeded dengan `auth_user_id = NULL` dan kerentanan SUPA-001).

---

## 1. Ringkasan Eksekutif

Aplikasi **Turnamen.in** telah melewati pengujian logika inti, kontrak API Flask (`/api/v1`), frontend Vanilla HTML/CSS/JS, serta kompatibilitas database migration `0001` sampai `0005` secara lokal pada **PostgreSQL 18.6** dan **PostgreSQL 17.11** (`257 passed`). Alur utama penyelenggaraan turnamen Single Elimination (login, buat turnamen, buat tim & tambah anggota, daftar peserta, verifikasi panitia, generate bracket + BYE, input skor & force override, pengumuman, hingga laporan & klasemen) berfungsi end-to-end dalam `APP_MODE=mock`.

Namun, aplikasi belum siap dijalankan dalam `APP_MODE=supabase` terhadap project Cloud saat ini karena tiga penghambat utama:
1. Konfigurasi lingkungan (`.env`) belum tersedia di workspace sehingga runtime otomatis fallback ke `mock`.
2. Database Supabase Cloud (`cfdsgxciodfkamskafwe`) berdasarkan pemeriksaan read-only via koneksi Supabase ChatGPT pada `2026-11-26` (bukan akses langsung Antigravity ke Cloud) menunjukkan: 12 public tables seluruhnya memiliki RLS enabled dengan total 9 RLS policies aktif, `migration history` kosong (migration `0002` sampai `0005` serta seluruh RPC Wave 2.1 sampai 4B belum diterapkan), 4 tabel (`activity_logs`, `payments`, `registrations`, `tournament_staff`) belum memiliki policy, `uq_tournament_seed` sudah tersedia, dan seluruh 5 profil memiliki `auth_user_id = NULL`.
3. Pengujian integrasi nyata terhadap GoTrue Auth + PostgREST (`Wave 4C`) masih **BLOCKED** karena tidak ada container runtime (`Docker` / `Podman` / `Rancher Desktop`) pada mesin lokal.

Selain itu, terdapat celah fungsional di lapisan aplikasi yang perlu diketahui sebelum demonstrasi: manajemen `payments`, CRUD cabang `games`, UI/API edit profil (`PATCH /api/v1/auth/me`), UI/API penugasan `tournament_staff`, serta UI/API role assignment (`assign_user_role`) belum tersedia di REST API dan antarmuka frontend.

---

## 2. Kondisi Lingkungan & Verifikasi yang Dijalankan

Seluruh pemeriksaan dilakukan secara read-only terhadap kode dan runtime lokal tanpa mengubah migration `0001` sampai `0005` dan tanpa menyentuh Supabase Cloud:

| Pemeriksaan | Hasil | Detail Observasi |
| :--- | :--- | :--- |
| Git Branch & Status | PASS | Branch aktif `feature/fikri-ui-ux`, `git diff --check` exit code `0`. |
| Keberadaan `.env` | `False` | File `C:\Turnamen.in\.env` tidak ditemukan di workspace. |
| Smoke Check CLI (`run.py --check`) | PASS (Mock) | `app_mode: "mock"`, `is_simulation: true`, `supabase_configured: false`, `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`. |
| Validasi JS Syntax (`node --check`) | PASS (5/5) | `config.js`, `eel-bridge.js`, `api-client.js`, `ui-components.js`, `app-pages.js` lulus tanpa syntax error (`node` v24.15.0). |
| Full Test Suite (`pytest -v`) | PASS (257/257) | `257 passed, 1 warning in 44.59s` (mencakup unit test, integrasi API, frontend contract, serta 7 PG integration test pada PG 18.6; sebelumnya juga `257 passed in 44.04s` pada PG 17.11). |
| Mock Mode Loopback E2E Smoke | PASS | Server Flask `127.0.0.1` + `eel_bridge.forward_api_request` menguji `/health` -> login organizer & captain -> `POST /tournaments` -> `POST /teams` (x2) -> `POST /registrations` (x2) -> approve (x2) -> `POST /bracket/generate` -> `PATCH /matches/<id>/result` -> `GET /reports` -> `POST /announcements` -> `POST /auth/logout`, seluruhnya HTTP `200`/`201` dengan status akhir `completed`. |
| Guard Konfigurasi `APP_MODE=supabase` | VERIFIED | Memanggil `load_config({'app_mode': 'supabase'})` tanpa kredensial melempar `ValueError: APP_MODE=supabase membutuhkan SUPABASE_URL dan SUPABASE_ANON_KEY pada file .env.` |

---

## 3. Audit Kesiapan Supabase Mode (`APP_MODE=mock` vs `APP_MODE=supabase`)

### Mengapa Saat Ini `app_mode: mock` dan `supabase_configured: false`
1. Pada [config.py](file:///C:/Turnamen.in/backend/core/config.py#L22-L24) dan [config.py](file:///C:/Turnamen.in/backend/core/config.py#L175-L188), `load_config()` hanya memuat `.env` jika `ENV_PATH.exists()` bernilai benar (`C:\Turnamen.in\.env`). Karena `.env` belum ada dan environment variable OS `APP_MODE`, `SUPABASE_URL`, serta `SUPABASE_ANON_KEY` tidak diset, `APP_MODE` memakai nilai bawaan `"mock"`.
2. Pada [config.py](file:///C:/Turnamen.in/backend/core/config.py#L168), `to_safe_dict()` menghitung `"supabase_configured": bool(self.supabase_url and self.supabase_anon_key)`, sehingga nilainya `false`.

### Audit Rantai Inisialisasi & Auth Supabase Mode
- **Validasi Kredensial ([client.py](file:///C:/Turnamen.in/backend/infrastructure/supabase/client.py#L135-L145)):**
  - `validate_supabase_credentials()` menolak key berjenis `service_role`, `sb_secret_*`, dan `sb_publishable_*`.
  - Karena library `supabase==2.7.4` menggunakan format JWT legacy, proyek wajib memakai legacy public `anon` JWT key (awalan `eyJ...`), bukan publishable key baru berformat `sb_publishable_*`.
- **Per-Request Client Isolation ([client.py](file:///C:/Turnamen.in/backend/infrastructure/supabase/client.py)):**
  - `create_supabase_client()` menonaktifkan sesi global (`persist_session=False`) dan mengikat token bearer per request menggunakan `ContextVar` serta `flask.g`, sehingga aman terhadap kebocoran sesi antar pengguna pada Flask threaded server.
- **Repository Parity ([supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py)):**
  - Operasi RPC kritis (`get_public_profile_summary`, `transition_tournament_status`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`) sudah dipetakan di adapter Supabase.
  - Kekurangan yang teridentifikasi pada adapter & service dirinci pada Bagian 5.

---

## 4. Matriks Kesiapan 19 Fitur Utama

Status dinilai untuk kedua mode: **Mock** (`APP_MODE=mock`) dan **Supabase** (`APP_MODE=supabase` terhadap kondisi Cloud baseline saat ini vs jika `0002` sampai `0005` + `.env` sudah terpasang).

| No | Fitur Utama | Frontend | Flask API | Repository / DB | Mock Mode | Supabase Mode (Saat Ini) | Catatan / Gap Teknis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Login & Logout | `renderLoginPage`, topbar auth | `POST /auth/login`, `POST /auth/logout` | GoTrue Auth / Mock Token | **READY** | **BLOCKED** | Butuh `.env`; token disimpan di RAM JS (`config.js`), hilang saat reload window. |
| 2 | Registrasi Akun Baru | `renderLoginPage` tab daftar | `POST /auth/register` | `0005` `handle_new_auth_user` | **READY** | **BLOCKED** | Cloud belum menerapkan `0005` (SUPA-001). Role self-register dibatasi `player` dan `team_captain`. |
| 3 | Profile & Manajemen User | `renderProfilePage` (read-only) | `GET /auth/me` (tidak ada PATCH profile / role route) | `AuthService.update_profile` & `assign_role` ada tapi tidak diekspos | **PARTIAL** | **BLOCKED** | Tidak ada endpoint `PATCH /auth/me` maupun UI edit profil atau manajemen user/role oleh admin. |
| 4 | Role Switcher & Mode Guest | Topbar role switcher & guest view | `X-Mock-Role` (hanya `mock`) | Mock session / Anon RLS | **READY** | **PARTIAL** | Guest di Supabase Mode butuh kebijakan RLS `0002` sampai `0005` agar data publik aman tanpa bocor `profiles`. |
| 5 | Dashboard Player | `renderPlayerDashboard` | `/tournaments`, `/teams`, `/matches`, `/announcements` | Read-only player view | **READY** | **BLOCKED** | Di Cloud baseline, `Users read active profiles` terbuka untuk umum. |
| 6 | Dashboard Team Captain | `renderCaptainDashboard` | `/teams`, `/registrations`, `/tournaments` | Captain ownership RLS (`0002`) | **READY** | **BLOCKED** | Cloud belum memiliki `0002` sampai `0005`. |
| 7 | Dashboard Organizer | `renderOrganizerDashboard` | CRUD turnamen, registrasi, bracket, reports | Organizer ownership RLS (`0002`) | **READY** | **BLOCKED** | Di Supabase Mode, `PATCH /tournaments/<id>` masih update status langsung tanpa `transition_tournament_status` RPC. |
| 8 | Dashboard Committee | `renderCommitteeDashboard` | `/registrations`, `/matches`, `/reports` | `is_staff_assigned`, `tournament_staff` | **READY** | **BLOCKED** | Tabel `tournament_staff` di Cloud belum memiliki policy RLS (bagian dari 4 tabel tanpa policy pada inspeksi 2026-11-26) dan belum ada UI penugasan staff. |
| 9 | Dashboard Super Admin | `renderSuperAdminDashboard` | Global `/tournaments`, `/teams`, `/games`, `/reports` | Full admin RLS (`0002`/`0005`) | **PARTIAL** | **BLOCKED** | UI Super Admin tidak memiliki panel manajemen user/role maupun manajemen cabang game. |
| 10 | Katalog & Manajemen Game | `renderGamePosterGallery` | `GET /games`, `GET /games/<id>` | `list_games`, `get_game_by_id` | **PARTIAL** | **BLOCKED** | Read-only catalog berjalan baik; Create/Update/Delete game belum ada di Protocol, Repository, API, maupun UI. |
| 11 | CRUD & Status Turnamen | Daftar, detail, modal create/edit/delete | `GET/POST /tournaments`, `GET/PATCH/DELETE /tournaments/<id>` | `transition_tournament_status` RPC + CRUD | **READY** | **BLOCKED** | `update_tournament` belum melewati `transition_tournament_status` saat `status` diubah lewat Edit Modal. |
| 12 | Penugasan Panitia (`tournament_staff`) | Badge `Ditugaskan` / `Lihat Saja` | Tidak ada route write staff | `is_staff_assigned` read-only | **PARTIAL** | **BLOCKED** | Tidak ada API/UI untuk menugaskan atau mencabut panitia; di Mock Mode bergantung pada 2 row seed. |
| 13 | Manajemen Tim & Anggota Roster | `renderTeamManagement` & modal | `GET/POST /teams`, `PATCH /teams/<id>`, `POST /teams/<id>/members` | `get_public_profile_summary` RPC | **READY** | **BLOCKED** | Penambahan member pakai `user_id` mengandalkan RPC `get_public_profile_summary` (`0003`/`0005`) yang belum ada di Cloud. |
| 14 | Pendaftaran Tim ke Turnamen | Modal daftar pada detail turnamen | `POST /tournaments/<id>/registrations` | `register_team_atomic` RPC (`0002`/`0005`) | **READY** | **BLOCKED** | Cloud belum punya `register_team_atomic` dan tabel `registrations` termasuk dalam 4 tabel tanpa policy pada inspeksi 2026-11-26. |
| 15 | Verifikasi Peserta Turnamen | Panel verifikasi organizer/panitia | `PATCH /registrations/<id>/status` | `update_registration` + RLS (`0002`/`0003`) | **READY** | **BLOCKED** | Tabel `registrations` di Cloud belum memiliki policy RLS pada inspeksi 2026-11-26. |
| 16 | Pembayaran (`payments`) | Hanya teks `Biaya Daftar` | Tidak ada route `/payments` | Tabel `payments` ada di DB + 1 row seed Mock | **NOT IMPLEMENTED** | **BLOCKED** | Belum ada method di `DataStoreRepositoryProtocol`, Service, API, maupun UI; `payments` termasuk dalam 4 tabel tanpa policy pada inspeksi 2026-11-26. |
| 17 | Bracket Generation & Visualisasi | `renderBracketPage` + pohon SVG/card | `POST /tournaments/<id>/bracket/generate` | `replace_tournament_matches` RPC (`0003`) | **READY** | **BLOCKED** | Single Elimination + BYE berjalan penuh; Cloud belum punya `replace_tournament_matches`. |
| 18 | Input Skor & Force Override | Inline form + modal override | `GET /matches`, `PATCH /matches/<id>/result` | `submit_match_result_atomic` RPC (`0004`) | **READY** | **BLOCKED** | Idempotency-Key & lock atomik terverifikasi pada PG 17.11/18.6; Cloud belum punya RPC `0004`. |
| 19 | Pengumuman, Laporan & Standings | `renderAnnouncementsPage`, `renderReportsPage` | `/announcements`, `/reports`, `/standings` | Query `announcements`, `matches`, `activity_logs` | **READY** | **BLOCKED** | Di `supabase_repository.py:937`, query `profiles` untuk `author_name` pada `announcements` terfilter RLS `0005` sehingga fallback ke `"Panitia"`. |

---

## 5. Bug Kritis & Celah Integrasi yang Ditemukan

1. **[CRITICAL - Supabase Runtime & Security] Cloud Baseline Belum Sinkron dengan Migration `0002` sampai `0005`:**
   - Hasil inspeksi read-only via koneksi Supabase ChatGPT pada `2026-11-26` (project `turnamen-in`, ID `cfdsgxciodfkamskafwe`; bukan akses langsung Antigravity ke Cloud) mencatat: 12 public tables memiliki RLS enabled dengan total 9 RLS policies, migration history kosong, `uq_tournament_seed` sudah tersedia, 5 profil memiliki `auth_user_id = NULL`, dan terdapat 4 tabel tanpa policy (`activity_logs`, `payments`, `registrations`, `tournament_staff`).
   - Migration `0002`, `0003`, `0004`, dan `0005` serta seluruh RPC utama (`get_public_profile_summary`, `transition_tournament_status`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`, `assign_user_role`, `link_profile_auth_user`) belum tercatat pada migration history Cloud.
   - Policy publik `Users read active profiles` pada `profiles` masih berisiko terhadap eksposur data profil dan kerentanan `SUPA-001` sebelum `0005` diterapkan.
2. **[CRITICAL - Supabase Mode] Degradasi `author_name` Pengumuman karena RLS `0005` ([supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py#L937)):**
   - `list_announcements()` melakukan query langsung `client.table("profiles").select("id,full_name").execute()`.
   - Dengan RLS `"Profiles select own or admin"` dari `0005`, `anon`, `player`, `team_captain`, `organizer`, dan `committee` hanya menerima baris profil miliknya sendiri (atau kosong untuk `anon`). Akibatnya, `author_name` pengumuman yang dibuat orang lain akan jatuh ke fallback `"Panitia"` alih-alih menampilkan nama pembuat sebenarnya. Seharusnya nama author diselesaikan melalui fungsi/view aman (misalnya `get_public_profile_summary`) atau kolom denormalisasi terkontrol.
3. **[HIGH - Supabase Mode] Transisi Status lewat Edit Turnamen Melewati Validasi RPC ([service.py](file:///C:/Turnamen.in/backend/modules/tournaments/service.py#L328-L377)):**
   - `TournamentService.update_tournament()` ketika menerima field `status` hanya memanggil `self._repo.update_tournament(tournament["id"], updates)` (`UPDATE tournaments`) dan tidak memanggil `self._repo.transition_tournament_status(...)`.
   - Di Supabase Mode, jika organizer mengubah `status` ke `completed` lewat `PATCH /api/v1/tournaments/<id>`, RLS `"Organizer or admin update tournaments"` tetap mengizinkannya tanpa mengecek `validate_tournament_bracket_integrity` sebagaimana dikawal oleh RPC `transition_tournament_status`.
4. **[MEDIUM - UX & Demo Reliability] Sesi Auth Disimpan di Memori JS ([config.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/config.js#L126-L134)):**
   - `state.token` dan `state.currentUser` tidak disimpan di `sessionStorage`. Pada `APP_MODE=supabase`, me-reload jendela desktop (F5) memutus sesi login dan memaksa user masuk ulang. Pada `APP_MODE=mock`, reload akan me-reset akun ke default `organizer`. Selain itu, penyimpanan data di Mock Mode murni berada di RAM sehingga setiap turnamen atau skor baru akan kembali ke seed awal saat aplikasi Python dimulai ulang.
5. **[MEDIUM - Gap Kontrak & Endpoint] Method Service Tidak Diekspos ke API & Frontend:**
   - `AuthService.update_profile()` (`backend/modules/auth/service.py:401`) dan `AuthService.assign_role()` (`backend/modules/auth/service.py:461`) sudah tersedia di layer service, tetapi tidak didaftarkan di `backend/api/routes/v1_routes.py`. Selain itu `assign_role()` memanggil `update_profile` alih-alih `assign_user_role` RPC pada migration `0005`.
   - `renderProfilePage` (`app-pages.js:5004-5018`) hanya menampilkan field `readonly` tanpa form simpan.

---

## 6. Perbandingan Database Lokal (`0001` sampai `0005`) vs Cloud Baseline

| Komponen | Database Lokal Teruji (PG 17.11 & 18.6) | Cloud Baseline (Inspeksi ChatGPT Read-Only 2026-11-26) | Dampak ke Aplikasi |
| :--- | :--- | :--- | :--- |
| Migration `0001` | Terpasang | Skema dasar 12 tabel aktif (`uq_tournament_seed` tersedia), namun `migration history` kosong | Skema tabel dasar kompatibel, tetapi riwayat migrasi Cloud belum tercatat. |
| Migration `0002` (Security & Hardening) | Terpasang | **Belum ada** (total 9 RLS policies di Cloud; `activity_logs`, `payments`, `registrations`, `tournament_staff` tanpa policy) | Tanpa `0002`, 4 tabel privat belum memiliki policy RLS dan `register_team_atomic` & `transition_tournament_status` tidak tersedia. |
| Migration `0003` (RLS Compatibility & Bracket RPC) | Terpasang | **Belum ada** | `replace_tournament_matches` dan `get_public_profile_summary` gagal dipanggil di Supabase Mode. |
| Migration `0004` (Atomic Match Submission) | Terpasang | **Belum ada** | `submit_match_result_atomic` dan idempotency table tidak tersedia di Cloud. |
| Migration `0005` (SUPA-001 Hardening) | Terpasang | **Belum ada** | Public signup berpotensi terblokir atau menimpa profil seeded jika skema lama dipakai; role assignment & profile linking aman belum aktif. |
| Profil Seeded (`supabase/seed.sql`) | Diuji ter-link & terisolasi | 5 profil dengan `auth_user_id = NULL` | Di `0005`, akun demo baru pada email yang sama ditolak (`AUTH_TRIGGER_CONFLICT`) sampai dihubungkan secara eksplisit. |

### Alur Bootstrap `super_admin` Pertama di Supabase Mode (`0005`)
Karena migration `0005` melarang auto-link berdasarkan email maupun penetapan role via `raw_user_meta_data`:
1. Buat user nyata di Supabase Auth Dashboard (misalnya akun admin atau organizer).
2. Karena `profiles` awal tidak otomatis terhubung ke profil seeded (`auth_user_id = NULL`), tautkan profil `super_admin` pertama menggunakan eksekusi tervalidasi di SQL Editor Supabase (hak istimewa database/postgres) atau `service_role` dengan memanggil:
   `SELECT public.link_profile_auth_user(<profile_id_super_admin>, <auth_user_id_nyata>);`
3. Setelah `super_admin` pertama aktif dan memiliki sesi Auth nyata, pengaitan akun panitia/organizer lain atau promosi role berikutnya dilakukan melalui RPC:
   - `public.link_profile_auth_user(p_profile_id, p_auth_user_id)`
   - `public.assign_user_role(p_target_profile_id, p_new_role)`
4. Alternatifnya, untuk user baru tanpa memakai profil seeded, buat akun via Sign Up (role default `player`), lalu promosikan oleh `postgres`/`service_role`/`super_admin` melalui `public.assign_user_role`.

---

## 7. Penilaian Kesiapan Demonstrasi

| Skenario Demonstrasi | Kelayakan | Penjelasan |
| :--- | :--- | :--- |
| **Demo Offline Desktop (Mock Mode)** | **LAYAK (READY)** | Jalankan `python run.py` tanpa `.env`. Mendukung switch langsung antar 6 role (Guest, Player, Team Captain, Organizer, Committee, Super Admin), CRUD turnamen, registrasi & verifikasi tim, generate bracket Single Elimination + BYE, pengesahan skor & force override, pengumuman, serta laporan/klasemen. Batasan: data kembali ke seed awal bila aplikasi ditutup/restart; fitur Payments & CRUD Game belum tersedia. |
| **Demo Online Cloud (Supabase Mode)** | **TIDAK LAYAK (NOT READY)** | Belum ada `.env` valid, Cloud belum menjalankan `0002` sampai `0005`, integrasi nyata GoTrue/PostgREST (Wave 4C) belum dapat diuji lokal tanpa Docker/Podman, dan masih ada bug `list_announcements` + `update_tournament` pada adapter Supabase. |

---

## 8. Urutan Rekomendasi Perbaikan Sebelum Rilis / Demo Online

1. **[P0 - Database Cloud]** Terapkan migration `0002`, `0003`, `0004`, dan `0005` ke database target sesuai prosedur perubahan skema yang disetujui tim, lalu verifikasi daftar tabel, policy, trigger, dan 7 fungsi RPC.
2. **[P0 - Bootstrap Akun Cloud]** Buat user Supabase Auth untuk `super_admin` dan akun demo resmi, lalu hubungkan ke profil target menggunakan `public.link_profile_auth_user(...)` (atau bersihkan profil seeded yang tidak terpakai bila memakai signup bersih).
3. **[P0 - Konfigurasi Runtime]** Sediakan `.env` lokal dari `.env.example` dengan `APP_MODE=supabase`, `SUPABASE_URL`, dan legacy `SUPABASE_ANON_KEY` (`eyJ...`), tanpa pernah mem-commit `.env` atau memakai `service_role` di aplikasi.
4. **[P1 - Integrasi Kode Backend]**
   - Perbaiki `SupabaseDataStoreRepository.list_announcements()` ([supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py#L937)) agar tidak membaca tabel `profiles` secara mentah setelah `0005` (gunakan `get_public_profile_summary` atau fallback yang aman).
   - Arahkan perubahan status di `TournamentService.update_tournament()` ([service.py](file:///C:/Turnamen.in/backend/modules/tournaments/service.py#L328-L377)) melalui `transition_tournament_status` RPC.
   - Hubungkan `AuthService.assign_role()` dengan RPC `assign_user_role` dan putuskan apakah route `PATCH /api/v1/auth/me` serta manajemen role perlu dibuka pada kontrak API.
5. **[P1 - Verifikasi GoTrue & PostgREST Nyata]** Jalankan ulang pengujian Wave 4C pada lingkungan dengan container runtime aktif (`Docker` / `Podman` / `Rancher Desktop`) atau staging project Supabase terpisah.
6. **[P2 - Kelengkapan Fitur Opsional]** Implementasikan modul `payments`, penugasan `tournament_staff`, dan CRUD `games` bila masuk dalam ruang lingkup penilaian akhir produk.
