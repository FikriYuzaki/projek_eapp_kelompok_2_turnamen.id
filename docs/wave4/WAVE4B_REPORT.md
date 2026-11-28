# TURNAMEN.IN - WAVE 4B: LOCAL POSTGRESQL VALIDATION & SUPA-001 REMEDIATION REPORT

**Tanggal Laporan:** 2026-11-26  
**Branch Aktif:** `feature/fikri-ui-ux`  
**Keputusan Wave 4B (Validasi Lokal PostgreSQL 18.6):** **PASS (Lokal Terisolasi)**  
**Status Penerapan Cloud Production:** **BELUM DITERAPKAN (Dilarang pada Wave 4B)**  
**Status Kompatibilitas PostgreSQL 17.11:** **BELUM TERBUKTI DI RUNTIME PG 17 (Diuji pada PostgreSQL 18.6)**

---

## 1. Ringkasan Eksekutif

Wave 4B menyelesaikan audit menyeluruh terhadap migrasi `0001`–`0004`, implementasi serta penyempurnaan migrasi `supabase/migrations/0005_supa001_auth_trigger_hardening.sql` untuk menutup kerentanan **SUPA-001**, serta eksekusi uji integrasi dan keamanan langsung pada instance **PostgreSQL 18.6** lokal yang benar-benar terisolasi.

Hasil verifikasi akhir:
- **Seluruh 257 test `pytest` lulus (`257 passed, 1 warning`)**: terdiri atas 250 test baseline Wave 1–3.6 ditambah 7 test integrasi/keamanan PostgreSQL 18.6 di [`tests/integration/test_wave4b_postgres_migrations_and_security.py`](../../tests/integration/test_wave4b_postgres_migrations_and_security.py).
- **Smoke check aplikasi (`python run.py --check`) lulus** dalam `APP_MODE=mock` (`health_ok: true`, `repository_ok: true`).
- **Pengujian nyata pada PostgreSQL 18.6 berhasil menangkap 2 bug PL/pgSQL nyata** pada rancangan awal `0005` (`pg_catalog.session_user` dan akses `v_actor.id` pada variabel `RECORD` yang belum terisi saat pemanggilan `service_role`/`postgres`), serta 1 bug hang pipe `pg_ctl start` pada Windows di test harness. Seluruhnya telah diperbaiki dan diverifikasi ulang.
- **Tidak ada perubahan pada Supabase Cloud, cluster PostgreSQL utama pengguna, maupun dependency manifest (`requirements.txt`).**

---

## 2. Pengungkapan Versi PostgreSQL & Batasan Lingkungan

| Komponen | Lingkungan Uji Lokal Wave 4B | Target Supabase Cloud (`turnamen-in`) |
| :--- | :--- | :--- |
| **PostgreSQL Version** | **PostgreSQL 18.6** (`x86_64-windows`, msvc-19.44.35228, 64-bit) | **PostgreSQL 17.11** (inspeksi read-only 2026-11-25) |
| **Isolasi Cluster** | Ephemeral `initdb` + `pg_ctl` di `%TEMP%\turnamen_wave4b_pg_*`, port acak bebas, bind ketat `127.0.0.1`, dibersihkan otomatis (`0` direktori tersisa) | Project `cfdsgxciodfkamskafwe`, `ACTIVE_HEALTHY` (tidak disentuh pada Wave 4B) |
| **Auth / Gateway** | Simulasi lokal schema `auth` (`auth.users`, `auth.uid()`, `auth.role()`) + role `anon`, `authenticated`, `service_role`, `authenticator` + GUC JWT | Supabase GoTrue + PostgREST gateway |
| **Driver Uji** | `psycopg 3.3.9` + `psycopg-binary 3.3.9` (sudah terpasang di `.venv`, tanpa mengubah `requirements.txt`) | Supabase Python SDK `2.7.4` / PostgREST |

**Pernyataan Wajib Perbedaan Versi:**
1. Seluruh migrasi `0001`–`0005` telah **diuji runtime secara langsung pada PostgreSQL 18.6**.
2. **Kompatibilitas penuh terhadap PostgreSQL 17.11 belum terbukti melalui runtime test langsung pada PostgreSQL 17**, karena PostgreSQL 17 belum terpasang di mesin uji dan Docker tidak tersedia.
3. **Pemeriksaan Kompatibilitas SQL Statis terhadap PostgreSQL 17:** Seluruh konstruk SQL pada `0001`–`0005` (`CREATE EXTENSION pgcrypto`, `gen_random_uuid()`, `pg_catalog.sha256()`, `WITH RECURSIVE`, `ON CONFLICT (match_id, game_number) DO UPDATE`, `CREATE UNIQUE INDEX ... ON (LOWER(email))`, `SECURITY DEFINER SET search_path = ''`, dan `FOR UPDATE`) adalah fitur standar PostgreSQL 13–17. Tidak terdapat sintaks khusus PostgreSQL 18 (seperti `uuidv7()`, `RETURNING OLD/NEW`, atau virtual generated columns). Meski demikian, uji coba staging pada PostgreSQL 17 tetap wajib dilakukan sebelum deployment produksi.

---

## 3. Audit Migrasi `0001`–`0004` (Read-Only terhadap `0001` & `0002`)

Migrasi `0001` dan `0002` tidak diubah secara langsung. Hasil audit dependensi, constraint, trigger, RLS, dan RPC adalah sebagai berikut:

| File Migrasi | Objek Utama | Temuan Audit & Implikasi |
| :--- | :--- | :--- |
| [`0001_initial_schema.sql`](../../supabase/migrations/0001_initial_schema.sql) | `pgcrypto`, `set_updated_at()`, 12 tabel inti, 9 trigger `updated_at`, `ENABLE ROW LEVEL SECURITY` di 12 tabel, `current_user_role()`, policy read awal + `Users read active profiles` | 1. `set_updated_at()` belum menetapkan `search_path` (diselesaikan di `0005`).<br>2. `CREATE TRIGGER` & `CREATE POLICY` tidak memakai `DROP ... IF EXISTS`, sehingga `0001` tidak idempoten jika dijalankan ulang mentah di Cloud.<br>3. Policy `"Users read active profiles"` membuka seluruh kolom `profiles` ke `public` (`anon` + `authenticated`).<br>4. Constraint `uq_tournament_seed UNIQUE (tournament_id, seed_number)` sudah dibuat langsung oleh `0001` baris 184 (menjelaskan mengapa index tersebut sudah ditemukan di Cloud). |
| [`0002_security_hardening.sql`](../../supabase/migrations/0002_security_hardening.sql) | `idx_profiles_auth_user_id`, FK `fk_profiles_auth_user_id -> auth.users(id)`, helper RLS, `prevent_profile_privilege_escalation()`, `handle_new_auth_user()`, trigger `on_auth_user_created`, `replace_tournament_matches()`, policy RLS 12 tabel | 1. **Celah SUPA-001:** `handle_new_auth_user()` melakukan `UPDATE public.profiles ... WHERE LOWER(email) = LOWER(NEW.email) AND auth_user_id IS NULL`.<br>2. **Celah Self-Claim:** `prevent_profile_privilege_escalation()` baris 143 mengizinkan transisi `OLD.auth_user_id IS NULL -> NEW.auth_user_id = auth.uid()`.<br>3. **Over-Exposure PII:** Policy `"Profiles select own or staff"` mengizinkan `organizer` dan `committee` membaca seluruh kolom `public.profiles` (`email`, `phone`).<br>4. Fungsi helper di `0002` memakai `SET search_path = public` (bukan `''`), `REVOKE`/`GRANT` belum seragam, dan `v_phone` bertipe `VARCHAR(40)` sedangkan kolom tabel `VARCHAR(30)`. |
| [`0003_wave2_rls_compatibility.sql`](../../supabase/migrations/0003_wave2_rls_compatibility.sql) | Schema `private`, RPC `transition_tournament_status`, `get_public_profile_summary`, `register_team_atomic` beserta wrapper `public.*` | Idempoten dan konsisten menggunakan `SECURITY DEFINER SET search_path = ''` pada `private.*` serta `SECURITY INVOKER SET search_path = ''` pada wrapper `public.*`. Bergantung pada tabel/kolom `0001` dan helper RLS. |
| [`0004_wave2_3_atomic_match_submission.sql`](../../supabase/migrations/0004_wave2_3_atomic_match_submission.sql) | Tabel `match_submission_requests`, `private.validate_tournament_bracket_integrity`, upgrade `private.transition_tournament_status`, RPC `submit_match_result_atomic` | Menggunakan `pg_catalog.sha256()`, `WITH RECURSIVE`, dan penguncian berurutan (`tournaments FOR UPDATE` lalu `matches ORDER BY id FOR UPDATE`) untuk mencegah deadlock. Catatan penting: hasil JSON mengembalikan key `tournament_status` (bukan nested object `tournament.status`). |

---

## 4. Analisis Alur Aplikasi & Perbaikan SUPA-001 pada `0005`

### A. Analisis Alur Registrasi & Login Aplikasi (`backend/modules/auth/service.py`)

1. **Self-Registration (`AuthService.register` / `_register_supabase`):**
   - Klien hanya diizinkan memilih `role` dalam `SELF_REGISTRABLE_ROLES` (`player` atau `team_captain`).
   - Backend memanggil `auth.sign_up(...)` dengan `user_metadata` (`username`, `full_name`, `role`, `phone` opsional).
   - Pada PostgreSQL, trigger `on_auth_user_created` (`public.handle_new_auth_user()`) berjalan `AFTER INSERT ON auth.users`:
     - Jika email sudah ada di `public.profiles` (termasuk profil seeded dengan `auth_user_id IS NULL`), trigger mengangkat `ERRCODE = '23505'` sehingga transaksi `auth.users` ikut ter-rollback penuh (tidak ada akun auth yatim dan tidak ada auto-link).
     - Jika `raw_user_meta_data->>'role'` berisi role privileged (`super_admin`, `organizer`, `committee`) atau nilai tak dikenal, trigger mengabaikannya dan memaksa role baru menjadi `'player'`. Hanya `'player'` dan `'team_captain'` yang diizinkan pada self-signup.
     - Jika konfirmasi email tidak aktif (`access_token` tersedia), `_register_supabase` langsung membaca profil berdasarkan `auth_user_id` (melalui RLS `"Profiles select own or admin"`) tanpa pernah mencari berdasarkan email.
2. **Login (`AuthService.login` / `_login_supabase`):**
   - Autentikasi didelegasikan ke Supabase GoTrue (`sign_in_with_password`).
   - Profil dicari eksklusif melalui `get_profile_by_auth_user_id(auth_user_id)`. Jika akun Auth belum ditautkan ke profil melalui mekanisme tepercaya, login ditolak dengan `PROFILE_NOT_PROVISIONED_MESSAGE`.
   - Keputusan otorisasi di seluruh backend (`permissions.py`, `tournaments`, `teams`, `matches`, `announcements`, `reports`) dan RLS PostgreSQL bersumber penuh dari `public.profiles.role`, bukan `raw_user_meta_data`.

### B. Pemenuhan 9 Persyaratan Keamanan di [`0005_supa001_auth_trigger_hardening.sql`](../../supabase/migrations/0005_supa001_auth_trigger_hardening.sql)

1. **Menghapus auto-link profil berdasarkan email:** Blok `UPDATE public.profiles ... WHERE LOWER(email) = LOWER(NEW.email) AND auth_user_id IS NULL` dihapus total dari `public.handle_new_auth_user()`.
2. **Melindungi profil seeded dari pengambilalihan:** `handle_new_auth_user()` menolak `id = NEW.id OR pg_catalog.lower(email) = v_clean_email` dengan `ERRCODE = '23505'`, diperkuat oleh `UNIQUE INDEX uq_profiles_lower_email ON public.profiles (LOWER(email))`.
3. **Mencegah pengaitan `auth_user_id` ke profil orang lain:** `public.prevent_profile_privilege_escalation()` menghapus pengecualian `OLD.auth_user_id IS NULL`, menolak seluruh modifikasi langsung `auth_user_id`, `role`, `is_active`, `email`, dan `username` oleh non-`super_admin` (`ERRCODE = '42501'`), serta memeriksa `request.jwt.claim.role` maupun `request.jwt.claims` JSON.
4. **Mencegah eskalasi role oleh pengguna biasa:** Signup publik hanya dapat menginisialisasi `'player'` atau `'team_captain'`; promosi ke `committee`, `organizer`, atau `super_admin` hanya melalui `public.assign_user_role(UUID, VARCHAR)` yang memvalidasi `auth.uid()` milik `super_admin` aktif.
5. **Tidak menjadikan `raw_user_meta_data` sumber otorisasi role:** Seluruh helper RLS (`current_user_role`, `is_tournament_organizer`, `is_tournament_committee`, `is_team_captain`), trigger, dan RPC membaca otorisasi dari `public.profiles` berdasarkan `auth.uid()`.
6. **Mekanisme linking tepercaya dan tervalidasi:** `private.link_profile_auth_user(p_profile_id, p_auth_user_id)` (beserta wrapper `public.link_profile_auth_user`) hanya dapat dijalankan oleh `super_admin` aktif, `service_role`, atau `postgres`/`supabase_admin`, serta memverifikasi profil target belum tertaut ke akun lain, akun `auth.users` ada, `email_confirmed_at IS NOT NULL`, dan email cocok case-insensitive. Aktivitas tercatat ke `public.activity_logs` (`PROFILE_AUTH_LINKED`).
7. **Alur pendaftaran pengguna baru tetap aman:** User baru (`player` atau `team_captain`) dengan email belum terdaftar otomatis mendapatkan baris `public.profiles` aktif (`id = NEW.id, auth_user_id = NEW.id`).
8. **Mempertahankan profil yang sudah tertaut sah:** `handle_new_auth_user()` melakukan early return idempoten jika `auth_user_id = NEW.id` sudah ada, dan `link_profile_auth_user()` idempoten untuk pasangan yang sama serta menolak overwrite pasangan berbeda (`ERRCODE = 'P0009'`).
9. **Hardening `SECURITY DEFINER` dan `search_path`:** Seluruh fungsi pada `private.*` dan `public.*` (`set_updated_at`, `current_profile_id`, `current_user_role`, `is_tournament_organizer`, `is_tournament_committee`, `is_team_captain`, `replace_tournament_matches`, `prevent_profile_privilege_escalation`, `handle_new_auth_user`, `link_profile_auth_user`, `assign_user_role`) kini mengunci `SET search_path = ''` dengan referensi schema eksplisit serta `REVOKE`/`GRANT EXECUTE` ketat. Policy `"Users read active profiles"` dan `"Profiles select own or staff"` diganti dengan `"Profiles select own or admin"`.

### C. Bug Nyata yang Ditemukan & Diperbaiki Saat Uji PostgreSQL 18.6

1. **`pg_catalog.session_user` di `private.link_profile_auth_user()`:** PostgreSQL menolak `pg_catalog.session_user` dengan `42P01: missing FROM-clause entry for table "pg_catalog"` karena `session_user` adalah keyword SQL niladic. Diperbaiki menjadi `session_user`.
2. **Akses `v_actor.id` saat `v_auth_uid IS NULL` di `private.link_profile_auth_user()`:** Saat dipanggil sebagai `postgres` atau `service_role` tanpa `auth.uid()`, `v_actor RECORD` belum pernah diisi sehingga `COALESCE(v_actor.id, v_profile.id)` memicu `55000: record "v_actor" is not assigned yet`. Diperbaiki dengan variabel terpisah `v_actor_id UUID := NULL`.
3. **Urutan validasi `link_profile_auth_user()`:** Pemeriksaan `v_profile.auth_user_id IS NOT NULL` dipindahkan sebelum pengecekan email agar percobaan overwrite profil yang sudah tertaut selalu mengembalikan `P0009` secara konsisten.

---

## 5. Ringkasan Pengujian Terpisah per Kategori

### A. PostgreSQL Native Tests (PostgreSQL 18.6 Lokal)
- Eksekusi bersih `0001` -> `0005` pada 2 database baru terpisah (`turnamen_wave4b_fresh`, `turnamen_wave4b_fresh_2`) plus eksekusi `supabase/seed.sql`.
- Verifikasi RLS aktif (`relrowsecurity = true`) pada seluruh 13 tabel `public` (`12` tabel inti + `match_submission_requests`).
- Verifikasi index `uq_tournament_seed` dan `uq_profiles_lower_email`, atribut `prosecdef`, `proconfig` (`search_path=""`), hak `EXECUTE` untuk `anon`/`authenticated`/`service_role`, serta trigger `on_auth_user_created` dan `trg_prevent_profile_privilege_escalation`.
- Verifikasi konkurensi nyata (`ThreadPoolExecutor`) pada `register_team_atomic` (4 kapten paralel berebut kuota 2 -> tepat 2 sukses, 2 ditolak `P0009`, seed `[1, 2]`) dan `submit_match_result_atomic` (3 request paralel dengan `idempotency_key` sama -> tidak ada duplikasi `match_results`, replay mengembalikan `idempotent_replay = true`).

### B. Supabase Auth Simulation Tests (Lokal via Schema `auth` + Role `authenticator`)
- Simulasi `auth.users`, `auth.uid()`, `auth.role()`, dan session `SET LOCAL ROLE anon | authenticated | service_role` dengan GUC JWT (`request.jwt.claim.sub`, `request.jwt.claim.role`, `request.jwt.claims`).
- Uji anti-hijack SUPA-001 untuk `admin@turnamen.in`, `ADMIN@TURNAMEN.IN`, `organizer@turnamen.in`, `committee@turnamen.in`: insert ke `auth.users` ditolak (`UniqueViolation`), baris `auth.users` di-rollback, dan `profiles.auth_user_id` tetap `NULL`.
- Uji downgrade role `raw_user_meta_data` (`super_admin`, `organizer`, `committee`, `ADMIN` -> `'player'`), sementara `team_captain` dan `player` tetap aktif.
- Uji duplicate case-insensitive email dan duplicate username -> rollback `auth.users` bersih.
- Uji user `auth.users` tanpa profil (`orphan`) -> `current_profile_id()` dan `current_user_role()` bernilai `NULL`, 0 baris terbaca dari `profiles`.
- Uji akses `anon` (`games` terbaca, `profiles`/`payments`/`tournament_staff`/`activity_logs`/`match_submission_requests` kosong) dan proteksi PII `profiles` bagi `organizer` yang telah dipromosikan.

### C. RPC Integration Tests (PostgreSQL 18.6)
- Seluruh 7 RPC diuji terhadap session `anon`, `authenticated`, dan `service_role`:
  - `public.get_public_profile_summary` (pemilik tim dapat melihat 4 kolom non-PII; kapten lain & `anon` ditolak `42501`).
  - `public.register_team_atomic` (kapasitas & seed atomik).
  - `public.replace_tournament_matches` (atomic replace bracket).
  - `public.transition_tournament_status` (committee ditugaskan vs committee tidak ditugaskan vs larangan `cancelled`).
  - `public.submit_match_result_atomic` (idempotensi paralel, penolakan tampered payload `P0009`, dan `force_override` pada Grand Final).
  - `public.link_profile_auth_user` (penolakan unconfirmed email, email mismatch, non-admin, overwrite profil tertaut `P0009`; sukses via `super_admin` dan `service_role`; verifikasi profil seeded dengan `id != auth_user_id` tetap bekerja normal di RLS dan RPC).
  - `public.assign_user_role` (penolakan non-admin & target belum tertaut `P0009`; sukses oleh `super_admin` dan tercatat di `activity_logs`).

### D. Pengujian Supabase Cloud yang Belum Dilakukan
Pengujian berikut **TIDAK** dijalankan pada Wave 4B dan masih menjadi prasyarat sebelum rilis produksi:
1. Uji end-to-end Supabase GoTrue Auth (signup, email confirmation, refresh token, JWT signing/verification nyata).
2. Uji HTTP gateway PostgREST Supabase Cloud dan perilaku `SUPABASE_ANON_KEY` terhadap API `supabase_repository.py`.
3. Eksekusi langsung `0001`–`0005` pada engine **PostgreSQL 17.11** (staging branch/project terpisah).
4. Verifikasi pasca-migrasi terhadap 59 baris data aktual di project Cloud `cfdsgxciodfkamskafwe`.

**Ringkasan Eksekusi Command Terakhir:**
- `.\.venv\Scripts\python.exe -m pytest -v` -> **`257 passed, 1 warning in 39.89s`** (exit code `0`).
- `.\.venv\Scripts\python.exe run.py --check` -> **`health_ok: true`, `repository_ok: true`** (exit code `0`).

---

## 6. Production Reconciliation Plan (Baseline Cloud Terverifikasi 2026-11-25)

Berdasarkan temuan read-only project `turnamen-in` (`cfdsgxciodfkamskafwe`, PostgreSQL 17.11, inspeksi ChatGPT 2026-11-25):

### Kondisi Baseline Cloud Saat Ini
- **Tabel & RLS:** 12 tabel `public` ada (total 59 baris), seluruhnya `RLS enabled`, `FORCE ROW LEVEL SECURITY` tidak aktif.
- **Data Profil & Drift:** Seluruh 5 profil memiliki `auth_user_id = NULL`; tidak ada duplikasi email case-insensitive; tidak ada benturan `seed_number` pada `registrations`; index `uq_tournament_seed` sudah tersedia di Cloud (berasal dari constraint `0001`, bukan `0003`).
- **Migration History:** Tabel `supabase_migrations.schema_migrations` belum ditemukan / kosong (menunjukkan skema awal kemungkinan dibuat manual lewat SQL Editor, bukan `supabase db push`).
- **Celah Kritis di Cloud Saat Ini:**
  - 4 tabel (`activity_logs`, `payments`, `registrations`, `tournament_staff`) berstatus RLS aktif **tanpa policy aktif** (seluruh akses non-owner/PostgREST untuk tabel tersebut saat ini tertutup total).
  - Policy `"Users read active profiles"` masih aktif pada `public.profiles` untuk role `public`, membuka seluruh kolom `profiles` (`email`, `phone`, `role`) ke `anon` dan `authenticated`.
  - Tidak ada trigger pada `auth.users`; `handle_new_auth_user()`, `prevent_profile_privilege_escalation()`, schema `private`, `match_submission_requests`, dan seluruh RPC Wave 2.1–2.3 belum tersedia di Cloud; `set_updated_at()` belum mengunci `search_path`.

### Urutan Rekonsiliasi Produksi yang Direkomendasikan (Untuk Wave Berikutnya / Setelah Persetujuan)
1. **Ambil Backup & Verifikasi Ulang Pre-Check:** Aktifkan/pastikan snapshot & PITR di Supabase Dashboard, ambil logical dump, dan ulangi query cek duplikat email, `seed_number`, `match_results (match_id, game_number)`, serta struktur bracket `matches`.
2. **Jangan Jalankan Ulang `0001` Mentah:** Karena 12 tabel dan `uq_tournament_seed` sudah ada serta `0001` tidak memakai `DROP TRIGGER/POLICY IF EXISTS`, rekonsiliasi baseline dilakukan dengan menandai/menyinkronkan baseline `0001` dan menerapkan hardening `0002` pada **staging/branch PostgreSQL 17** terlebih dahulu (terutama mengganti policy `0001` termasuk menghapus `"Users read active profiles"` dan mengisi policy 4 tabel yang kosong).
3. **Terapkan Berurutan `0003` -> `0004` -> `0005` di Staging PG 17:** Verifikasi seluruh object (`private.*`, `match_submission_requests`, `uq_profiles_lower_email`, `on_auth_user_created`, `prevent_profile_privilege_escalation`, `link_profile_auth_user`, `assign_user_role`) serta uji alur aplikasi `APP_MODE=supabase` terhadap GoTrue + PostgREST.
4. **Selesaikan 5 Profil `auth_user_id = NULL` Sebelum Membuka Signup Publik:**
   - Untuk setiap akun demo/operasional yang dipertahankan di Cloud (`super_admin`, `organizer`, `committee`, dll.), buat/undang akun Auth terkonfirmasi lewat Supabase Admin API (`auth.admin.createUser` dengan `email_confirm: true` tanpa role privileged di metadata), lalu tautkan lewat `public.link_profile_auth_user(profile_id, auth_user_id)` dengan `service_role`.
   - Untuk akun demo yang tidak dipakai di produksi, nonaktifkan atau hapus sebelum produksi dibuka.
5. **Terapkan ke Cloud Production & Verifikasi Pasca-Deploy:** Jalankan `0002` (reconciled) -> `0003` -> `0004` -> `0005`, sinkronkan `supabase_migrations.schema_migrations`, dan jalankan audit read-only ulang untuk memastikan tidak ada lagi policy `"Users read active profiles"`, seluruh 13 tabel memiliki policy yang tepat, dan `on_auth_user_created` aktif pada `auth.users`.
