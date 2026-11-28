# Wave 6.8: Laporan Investigasi & Optimasi Performa Dashboard (`Target < 3 Detik`)

- **Tanggal:** 2026-11-27
- **Target Sistem:** Aplikasi Desktop Python Eel + Flask REST API (`/api/v1`) + Supabase PostgreSQL (`APP_MODE=supabase` & `APP_MODE=mock`)
- **Konteks Masalah:** Setelah login Super Admin berhasil di `APP_MODE=supabase`, halaman Dashboard gagal memuat data dengan pesan: *"Permintaan melalui Python Eel bridge melebihi batas waktu tunggu. Proses di sisi Python mungkin masih berjalan."*

---

## 1. Ringkasan Eksekutif & Akar Masalah (Tahap 1: Investigasi)

Investigasi terukur pada frontend (`app-pages.js`, `api-client.js`, `eel-bridge.js`), Python Eel bridge (`eel_bridge.py`), service backend (`auth/service.py`, `reports/service.py`), dan adapter Supabase (`supabase_repository.py`) menemukan **6 akar bottleneck yang saling bertumpuk**:

1. **Serialisasi Request Akibat Blocking Socket di Event Loop `gevent` (`eel_bridge.py`):**
   - `eel` menjalankan callback `@eel.expose` melalui `gevent.spawn` dengan `gevent.monkey.is_module_patched("socket") == False`.
   - `forward_api_request()` memakai `requests.Session.request()` berbasis blocking socket standar tanpa threadpool offload. Akibatnya, seluruh panggilan `Promise.all(...)` dari UI tereksekusi **secara berurutan (serial)** pada satu OS thread `gevent`, sementara seluruh timer timeout JS `8000ms` (`BRIDGE_CALL_TIMEOUT_MS`) berjalan bersamaan sejak `t=0`.
2. **Pembuatan Client & Koneksi TLS Baru Per Query (`supabase_repository.py`):**
   - `_get_client()` memanggil `self._client_factory(...)` (`create_supabase_client()`) pada setiap pemanggilan query JWT tanpa reuse per token. Pada beban Dashboard awal (`before`), tercatat **`65` instansiasi client baru** dalam satu kali buka Dashboard.
3. **N+1 Query pada `list_tournaments()` dan `list_teams()` (`supabase_repository.py`):**
   - `list_tournaments()` memanggil `_enrich_tournament()` per turnamen yang mengeksekusi `list_registrations_by_tournament()` (masing-masing query ke `registrations` + seluruh `teams`).
   - `list_teams()` memanggil `_enrich_team()` per tim yang mengeksekusi `list_team_members(team_id)` berulang kali (`1` query tambahan per tim).
4. **Duplikasi Skala Besar pada `GET /api/v1/tournaments/<id>/reports` (`reports/service.py`):**
   - `get_tournament_report()` mengambil `tournament`, `registrations`, `matches`, dan `announcements`, lalu memanggil `get_tournament_standings()`, yang **mengulang kembali** query `tournament`, `registrations`, `matches`, serta memanggil `list_teams()` (memicu N+1 `team_members` lagi) hanya untuk mengambil `name` dan `tag` yang sebenarnya sudah ada di `registrations`.
   - Pada benchmark terukur (`before`), endpoint `/reports` sendirian memicu **`30` remote HTTP call** (`24` client baru).
5. **Verifikasi JWT GoTrue Berulang (`auth_get_user`) Per Endpoint (`auth/service.py`):**
   - Setiap request terautentikasi memanggil `auth.get_user(jwt)` ke Supabase GoTrue Auth serta query `profiles`. Satu kali muat Dashboard Super Admin memicu **`7` kali** `auth.get_user` dan **`8` kali** query `profiles`.
6. **Waterfall 4 Tahap & Request Tidak Terpakai di Frontend (`app-pages.js`):**
   - `renderDashboard()` + `renderSuperAdminDashboard()` mengirim **`9` HTTP request** dalam **`4` waterfall berurutan**: `GET /games` -> `[tournaments, teams]` -> `[matches, announcements, reports, registrations]` -> `[users, games?include_inactive=true]`.
   - Padahal `renderSuperAdminDashboard()` tidak memakai `matches`, `announcements`, maupun `registrations`, dan sudah cukup mengambil `GET /games?include_inactive=true` satu kali bersama `tournaments`, `teams`, dan `users`.

---

## 2. Pengukuran Sebelum vs Sesudah Optimasi

### A. Benchmark Query Count & Client Creation per Endpoint (Mode `APP_MODE=supabase` dengan Mock Query Counter, Data Seed: 3 Game, 2 Turnamen, 6 Tim, 5 Profil, 7 Match, 4 Registrasi, 3 Pengumuman)

| Endpoint | Remote Calls (`BEFORE`) | New Clients (`BEFORE`) | Remote Calls (`AFTER`) | New Clients (`AFTER`) | Perubahan |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `GET /api/v1/games` | 3 | 3 | *Dihapus (digabung ke query admin)* | 0 | Duplikasi dihilangkan untuk `super_admin` |
| `GET /api/v1/games?include_inactive=true` | 3 | 3 | **3** (`1 auth`, `1 profiles`, `1 games`) | **1** | Dipindah ke Wave 1 paralel |
| `GET /api/v1/tournaments` | 8 | 6 | **4** (`1 profiles`, `1 tournaments`, `1 games`, `1 registrations`) | **0** (reuse) | Eliminasi N+1 & query `teams` berulang |
| `GET /api/v1/teams` | 10 | 10 | **3** (`1 teams`, `1 games`, `1 team_members` batch) | **0** (reuse) | Eliminasi N+1 `team_members` |
| `GET /api/v1/users` | 3 | 3 | **2** (`2 profiles`) | **0** (reuse) | Dipindah ke Wave 1 paralel, reuse auth |
| `GET /api/v1/tournaments/<id>/matches` | 6 | 4 | *Tidak dipanggil di Dashboard `super_admin`* | 0 | Hanya dipanggil role yang menampilkan match |
| `GET /api/v1/tournaments/<id>/announcements` | 7 | 6 | *Tidak dipanggil di Dashboard `super_admin`* | 0 | Hanya dipanggil role yang menampilkan pengumuman |
| `GET /api/v1/tournaments/<id>/registrations` | 8 | 6 | *Tidak dipanggil di Dashboard `super_admin`* | 0 | Hanya dipanggil `organizer` & `committee` |
| `GET /api/v1/tournaments/<id>/reports` | 30 | 24 | **10** (`1 profiles`, `1 tournaments`, `1 games`, `2 regs`, `2 teams`, `1 matches`, `1 rpc`, `1 activity_logs` limit 10) | **0** (reuse) | Hilangkan double-scan standings & N+1 `list_teams()` |
| **TOTAL 1x Load Dashboard Super Admin** | **78 remote calls** | **65 client baru** | **22 remote calls** | **1 client JWT (+1 init)** | **-71.8% remote calls, -98.5% client churn** |

Catatan tambahan:
- Apabila pengguna baru saja melewati `POST /api/v1/auth/login` (<= 5 detik sebelumnya), cache identitas terverifikasi mengisi `auth.get_user` saat login sehingga jumlah `auth.get_user` saat redirect awal ke Dashboard dapat turun dari `7` menjadi **`0`**.
- Pada jalur konfirmasi keamanan (`test_online_login_inactive_user_and_jwt_propagation`), query `public.profiles` tetap dijalankan langsung pada DB sehingga status `is_active` dan `role` selalu real-time dan tidak pernah stale.

### B. Pengukuran Durasi Eksekusi Lokal (`APP_MODE=mock` & Simulasi Concurrency Eel)

1. **Flask `test_client()` per endpoint (`APP_MODE=mock`, kondisi localhost offline):**
   - `GET /api/v1/games`: `4.45 ms`
   - `GET /api/v1/games?include_inactive=true`: `0.53 ms`
   - `GET /api/v1/tournaments`: `0.45 ms`
   - `GET /api/v1/teams`: `0.51 ms`
   - `GET /api/v1/users`: `0.35 ms`
   - `GET /api/v1/tournaments/.../matches`: `0.54 ms`
   - `GET /api/v1/tournaments/.../announcements`: `0.40 ms`
   - `GET /api/v1/tournaments/.../reports`: `0.93 ms`
   - `GET /api/v1/tournaments/.../registrations`: `0.52 ms`
2. **Simulasi Konkurensi Eel Bridge (`test_eel_bridge_parallel_gevent_threadpool_prevents_serialization`):**
   - 4 request paralel melalui `gevent.spawn(eel_bridge.eel_api_request, ...)` dengan simulasi latency blocking I/O masing-masing `250 ms` selesai dalam **`< 0.65 detik`** (serial sebelum perbaikan memerlukan `>= 1.00 detik`).
3. **End-to-End Python Eel Bridge -> Flask REST API (`APP_MODE=mock`, 2 Wave Paralel):**
   - Wave 1 paralel (`games?include_inactive=true`, `tournaments`, `teams`, `users`): **`66.12 ms`**
   - Wave 2 (`tournaments/<id>/reports`): **`3.85 ms`**
   - Total waktu persiapan data Dashboard melalui Eel Bridge: **`69.99 ms`** (`0.07 detik`).

---

## 3. Ringkasan Perubahan Kode (Tahap 2: Optimasi)

1. **[desktop/bridge/eel_bridge.py](file:///C:/Turnamen.in/desktop/bridge/eel_bridge.py):**
   - Menambahkan `_run_without_blocking_gevent()` pada `eel_check_api_health()` dan `eel_api_request()` agar blocking `requests.Session` dijalankan di `gevent.get_hub().threadpool` saat berjalan di dalam greenlet `eel` yang belum di-monkey-patch.
2. **[backend/repositories/supabase/supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py):**
   - Menambahkan cache client terisolasi per token (`_token_clients`, batas 32 entri, TTL 300 detik, dihapus saat `auth_sign_out` atau error `auth_get_user`) di `_get_client()` serta dipakai bersama di `auth_get_user()`.
   - Mengubah `list_tournaments()` menggunakan batch query `registrations` (`select("tournament_id,status")`, `.in_("tournament_id", ...)` bila didukung client) tanpa scan `teams`.
   - Mengubah `_enrich_tournament()` agar hanya mengambil `select("status")` dari `registrations`.
   - Mengubah `list_teams()` menggunakan 1 batch query `team_members` (`is_active=True`) alih-alih query N+1 per tim.
   - Membatasi lookup `teams` pada `list_registrations_by_tournament()` dan `list_matches_by_tournament()` hanya pada ID tim terkait, serta langsung return `[]` jika 0 baris.
   - Menambahkan parameter `limit` opsional pada `list_activity_logs()`.
3. **[backend/modules/auth/service.py](file:///C:/Turnamen.in/backend/modules/auth/service.py) & [backend/api/routes/v1_routes.py](file:///C:/Turnamen.in/backend/api/routes/v1_routes.py):**
   - Menambahkan cache identitas JWT terverifikasi berumur pendek (`TOKEN_CACHE_TTL_SECONDS = 5.0`, dibatasi `exp` JWT, diinvalidasi saat `logout`, `complete_password_recovery`, `update_profile`, dan `assign_role`) tanpa meng-cache status `is_active`/`role` di `profiles`.
   - Menambahkan request-level actor memoization di `flask.g` (`_resolve_current_actor()`).
4. **[backend/modules/reports/service.py](file:///C:/Turnamen.in/backend/modules/reports/service.py):**
   - Mengekstrak `_compute_standings(regs, matches)` sehingga `get_tournament_report()` memakai ulang data `regs` dan `matches` yang sudah diambil, menggunakan `team_name`/`team_tag` yang sudah tersedia tanpa memanggil `list_teams()` N+1, dan membatasi `list_activity_logs(..., limit=10)`.
5. **[desktop/web/assets/js/pages/app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js):**
   - Mengoptimalkan `renderDashboard()` agar menjalankan Wave 1 paralel sesuai role (`super_admin` langsung memuat `[games?include_inactive=true, tournaments, teams, users]` secara paralel tanpa duplikasi `GET /games`), dan Wave 2 hanya memuat sub-resource turnamen aktif yang benar-benar dirender oleh role aktif (`reports` saja untuk `super_admin`).
   - Memperbaiki `renderSuperAdminDashboard()` untuk memanfaatkan data `preloadedUsersRes` dan `preloadedAllGamesRes` serta menangani kegagalan per bagian (misalnya kegagalan `reports`) tanpa mengosongkan seluruh Dashboard.
6. **Regresi & Benchmark Otomatis:**
   - Menambahkan [tests/unit/test_wave6_8_dashboard_performance.py](file:///C:/Turnamen.in/tests/unit/test_wave6_8_dashboard_performance.py).

---

## 4. Hasil Verifikasi Suite Pengujian & Kondisi Environment

- **Unit & Integrasi Baru Wave 6.8:** `tests/unit/test_wave6_8_dashboard_performance.py` -> **4 passed in 0.93s**
- **Seluruh Suite `pytest`:** **291 passed, 4 warnings in 54.18s** (0 failed, 0 skipped)
- **Smoke Check `APP_MODE=mock` (`run.py --check`):** `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`
- **Kebersihan Diff (`git diff --check`):** keluar dengan kode `0`
- **Status Secret & Database:** `DOTENV_EXISTS=False`; tidak ada kredensial/token di log; tidak ada perubahan data produksi, migrasi SQL, kebijakan RLS, maupun status Public Signup (tetap `DISABLED`).

### Catatan Pengujian Langsung pada Supabase Cloud (`APP_MODE=supabase`)

Pengukuran angka query (`78 -> 22` calls) dan perbaikan threadpool Eel sudah diverifikasi secara otomatis pada lingkungan uji lokal, sedangkan pengukuran wall-clock langsung terhadap instance Supabase Cloud (`https://cfdsgxciodfkamskafwe.supabase.co`) **belum dijalankan dari sesi agent** karena `SUPABASE_PUBLISHABLE_KEY` dan kredensial login Super Admin tidak disimpan di workspace/environment.

Skrip pengukur non-PII siap pakai telah disiapkan di folder scratch (`verify_wave68_cloud.ps1` / `run_wave68_cloud_bench.py`) apabila pengguna ingin memverifikasi langsung durasi end-to-end Cloud pada jaringan lokal setelah optimasi ini.
