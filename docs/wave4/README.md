# TURNAMEN.IN — WAVE 4A: SUPABASE CLOUD & DATABASE MIGRATION READ-ONLY AUDIT

**Tanggal Audit:** 2026-11-25  
**Target Proyek Supabase:** `turnamen-in` (`cfdsgxciodfkamskafwe`)  
**Repository & Branch Aktif:** `feature/fikri-ui-ux` (HEAD `e01cb4e`)  
**Status Audit:** Read-Only Audit (Tanpa Mutasi Kode, SQL, `.env`, atau Supabase Cloud)

---

## 1. Executive Summary

Audit **Wave 4A** dilakukan secara *read-only* untuk menilai kesiapan integrasi Supabase Cloud (`turnamen-in` / `cfdsgxciodfkamskafwe`) terhadap baseline kode **Wave 1–3.6** yang berada pada working tree branch `feature/fikri-ui-ux`.

**Keputusan Kesiapan Wave 4:** **`NOT READY — BLOCKERS FOUND`**

Terdapat **tiga blocker utama** yang mencegah dilakukannya penerapan migrasi langsung (*deployment*) ke Supabase Cloud pada tahap ini:

1. **Cloud Introspection Blocked (Kredensial / Akses CLI & DB Tidak Tersedia di Lingkungan Audit):**
   - File `.env` tidak ada di root repository, variabel lingkungan `SUPABASE_*` / `POSTGRES_*` / `DB_*` / `TURNAMEN_*` kosong, tidak ada `supabase` MCP server yang terpasang, dan `supabase projects list` (`supabase` CLI v`2.104.0`) mengembalikan:  
     `Access token not provided. Supply an access token by running supabase login or setting the SUPABASE_ACCESS_TOKEN environment variable.`
   - Karena itu, **skema aktual, RLS aktif, trigger auth, tabel, data existing, dan `supabase_migrations.schema_migrations` di Supabase Cloud belum dapat diinspeksi**. Audit tidak mengarang atau menebak kondisi Cloud.
2. **Critical Security Vulnerability `SUPA-001` Belum Ditutup dalam File Migrasi (`0005` Belum Ada):**
   - `supabase/migrations/0002_security_hardening.sql` (baris `169–214`) pada fungsi `handle_new_auth_user()` masih melakukan *auto-link* akun baru ke profil lama berdasarkan `LOWER(email)` ketika `auth_user_id IS NULL`.
   - `supabase/migrations/0002_security_hardening.sql` (baris `143`) pada `prevent_profile_privilege_escalation()` masih mengizinkan transisi `OLD.auth_user_id IS NULL -> NEW.auth_user_id = auth.uid()`.
   - `supabase/seed.sql` (baris `1–259`) menyisipkan 5 akun demo/seeded (`super_admin`, `organizer`, `committee`, dll.) dengan `auth_user_id` bernilai `NULL`. Jika skema `0002` + `seed.sql` aktif di Cloud sebelum `0005`, siapa pun yang melakukan pendaftaran publik dengan email seeded tersebut berisiko mengambil alih profil berhak istimewa (*privilege escalation / account hijacking*).
   - Rencana mitigasi sudah tersedia di `docs/wave4-supa001-auth-trigger-plan.md`, tetapi file migrasi `0005_supa001_auth_trigger_hardening.sql` belum dibuat dan belum diuji.
3. **Migrasi Wave 2.1–2.3 (`0003` & `0004`) Belum Tervalidasi pada PostgreSQL / Cloud Staging:**
   - Kode `APP_MODE=supabase` pada `backend/repositories/supabase/supabase_repository.py` kini bergantung penuh pada RPC `get_public_profile_summary`, `transition_tournament_status`, `register_team_atomic`, dan `submit_match_result_atomic` serta tabel `public.match_submission_requests` yang baru didefinisikan secara lokal di `0003` dan `0004`.
   - Kedua file migrasi tersebut masih berstatus *untracked* di Git dan belum diverifikasi terhadap state aktual database Cloud (termasuk risiko kegagalan akibat data legacy yang melanggar constraint baru atau perbedaan dengan `0001`/`0002` di Cloud).

---

## 2. Repository Baseline

Pemeriksaan baseline Git (`git branch --show-current`, `git status --short`, `git diff --stat`, `git log -n 5 --oneline`):

- **Branch Aktif:** `feature/fikri-ui-ux`
- **Commit Terakhir:** `e01cb4e` — `fix(ui-ux): guard organizer and committee actions when ownership or assignment is unverified`
- **Status Working Tree (Wave 1–3.6 belum di-commit/push/merge):**
  - **22 file modified** (`3177 insertions(+), 699 deletions(-)`):
    - Backend & Repository: `backend/api/routes/v1_routes.py`, `backend/modules/announcements/service.py`, `backend/modules/auth/permissions.py`, `backend/modules/auth/service.py`, `backend/modules/matches/bracket_engine.py`, `backend/modules/matches/service.py`, `backend/modules/reports/service.py`, `backend/modules/teams/service.py`, `backend/modules/tournaments/service.py`, `backend/repositories/interfaces/repository_protocol.py`, `backend/repositories/mock/mock_repository.py`, `backend/repositories/supabase/supabase_repository.py`.
    - Desktop / Frontend: `desktop/bridge/eel_bridge.py`, `desktop/web/assets/css/components.css`, `desktop/web/assets/js/components/ui-components.js`, `desktop/web/assets/js/core/api-client.js`, `desktop/web/assets/js/core/config.js`, `desktop/web/assets/js/pages/app-pages.js`, `desktop/web/index.html`.
    - Kontrak & Test: `docs/contracts/api-contract.md`, `docs/contracts/module-contract.md`, `tests/unit/test_reports_service.py`.
  - **16 entri untracked:**
    - Migrasi & Dokumentasi Wave 2–4: `supabase/migrations/0003_wave2_rls_compatibility.sql`, `supabase/migrations/0004_wave2_3_atomic_match_submission.sql`, `docs/wave4-supa001-auth-trigger-plan.md`.
    - Test Suite Wave 1–3.6 (12 file): `tests/integration/test_wave1_api_status_codes.py`, `tests/integration/test_wave2_api_access_and_visibility.py`, `tests/unit/test_wave1_auth_rules.py`, `tests/unit/test_wave1_match_rules.py`, `tests/unit/test_wave1_team_rules.py`, `tests/unit/test_wave1_tournament_rules.py`, `tests/unit/test_wave2_1_supabase_rls_remediation.py`, `tests/unit/test_wave2_2_security_edge_cases.py`, `tests/unit/test_wave2_3_atomic_match_submission.py`, `tests/unit/test_wave2_repository_and_services.py`, `tests/unit/test_wave3_6_interaction_hotfixes.py`, `tests/unit/test_wave3_frontend_role_integration.py`.
    - Direktori tambahan: `.agent/`.
- **Struktur `supabase/` Saat Ini:**
  - Tersedia: `supabase/migrations/0001_initial_schema.sql`, `0002_security_hardening.sql`, `0003_wave2_rls_compatibility.sql`, `0004_wave2_3_atomic_match_submission.sql`, dan `supabase/seed.sql`.
  - Tidak ada: `supabase/config.toml`, `supabase/schema.sql`, `supabase/.temp/`, dan `supabase/migrations/0005_*.sql`.
- **Guard Keamanan Client (`backend/infrastructure/supabase/client.py:105–151`):**
  - `validate_supabase_credentials()` memblokir `service_role`, prefix `sb_secret_*`, dan `sb_publishable_*` (karena `supabase==2.7.4` membutuhkan `anon` public JWT key berformat `eyJ...`).
  - `create_supabase_client()` beroperasi *stateless* (`persist_session=False`, `auto_refresh_token=False`) dengan JWT caller diteruskan per request via header `Authorization: Bearer <token>`.

---

## 3. Local Migration Inventory

| File | Ukuran / Baris | Status Git | Ruang Lingkup Utama | Catatan Idempotensi & Risiko Destruktif |
| :--- | :--- | :--- | :--- | :--- |
| `supabase/migrations/0001_initial_schema.sql` | 20.057 B / 398 baris | Tracked (di `HEAD`) | Ekstensi `pgcrypto`, fungsi `set_updated_at()`, 12 tabel inti (`profiles`, `games`, `tournaments`, `teams`, `team_members`, `tournament_staff`, `registrations`, `matches`, `match_results`, `payments`, `announcements`, `activity_logs`), 9 trigger `trg_*_updated_at`, `ENABLE ROW LEVEL SECURITY` semua tabel, dan policy read awal permisif + `current_user_role()`. | **Tidak idempoten** bila dijalankan ulang pada schema existing: `CREATE TABLE` tanpa `IF NOT EXISTS` pada beberapa objek? (`CREATE TABLE IF NOT EXISTS` dipakai, tetapi `CREATE TRIGGER` & `CREATE POLICY` di `0001` tidak memakai `DROP ... IF EXISTS`). **Kritis jika `0001` dijalankan tanpa `0002`:** policy `"Users read active profiles"` memakai `USING (is_active = true)` yang mengekspos seluruh profil aktif. |
| `supabase/migrations/0002_security_hardening.sql` | 31.669 B / 881 baris | Tracked (di `HEAD`) | Menambah `idx_profiles_auth_user_id` & FK `fk_profiles_auth_user_id -> auth.users(id)`, helper RLS (`current_profile_id()`, `current_user_role()`, `is_tournament_organizer()`, `is_tournament_committee()`, `is_team_captain()`), trigger anti-eskalasi `prevent_profile_privilege_escalation()`, trigger auth `on_auth_user_created` (`handle_new_auth_user()`), RPC `replace_tournament_matches(UUID, JSONB)`, serta mengganti policy RLS pada seluruh 12 tabel. | Menggunakan `DROP POLICY IF EXISTS` & `DROP TRIGGER IF EXISTS` sehingga relatif idempoten di atas `0001`. **Catatan destruktif terukur:** `replace_tournament_matches` mengeksekusi `DELETE FROM public.matches WHERE tournament_id = p_tournament_id` saat *re-generate* bracket (sudah dijaga agar menolak bila `status = 'completed'`, atau bila sudah ada skor/pemenang pada match non-bye). **Temuan keamanan:** mengandung bug `SUPA-001` (`LOWER(email)` auto-link) dan `SET search_path = public` (bukan `''`). |
| `supabase/migrations/0003_wave2_rls_compatibility.sql` | 15.464 B / 454 baris | **Untracked** (Wave 2.1–2.2) | Membuat schema `private` (`REVOKE ALL FROM PUBLIC, anon`), fungsi `private.transition_tournament_status`, `private.get_public_profile_summary`, `private.register_team_atomic` beserta wrapper `public.*` `SECURITY DEFINER SET search_path = ''`, serta unique index `uq_tournament_seed` pada `registrations(tournament_id, seed_number) WHERE seed_number IS NOT NULL`. | Idempoten (`CREATE SCHEMA IF NOT EXISTS`, `CREATE OR REPLACE FUNCTION`, `CREATE UNIQUE INDEX IF NOT EXISTS`, `REVOKE`/`GRANT` eksplisit). **Risiko migrasi data:** pembuatan `uq_tournament_seed` akan gagal jika Cloud sudah memiliki dua registrasi dengan `(tournament_id, seed_number)` kembar. |
| `supabase/migrations/0004_wave2_3_atomic_match_submission.sql` | 26.194 B / 743 baris | **Untracked** (Wave 2.3) | Membuat tabel `public.match_submission_requests` (`uq_match_submission_idempotency (match_id, actor_id, idempotency_key)` + RLS `SELECT` terbatas), helper `private.validate_tournament_bracket_integrity`, pembaruan `private.transition_tournament_status` (validasi integritas full DAG saat menuju `completed`), serta RPC atomik `private.submit_match_result_atomic` & wrapper `public.submit_match_result_atomic` (`FOR UPDATE` lock berurutan, cek SHA-256 request hash, upsert `match_results ON CONFLICT (match_id, game_number)`, update match & downstream bracket, transisi turnamen, insert `activity_logs` & ledger idempotensi dalam 1 transaksi). | Idempoten untuk definisi fungsi/tabel/policy (`IF NOT EXISTS`, `CREATE OR REPLACE`, `DROP POLICY IF EXISTS`). **Risiko runtime/data:** `submit_match_result_atomic` mengasumsikan `(match_id, game_number)` unik pada `match_results` (`0001` sudah mendeklarasikan `UNIQUE (match_id, game_number)`). Selain itu, `validate_tournament_bracket_integrity` akan menolak finalisasi (`completed`) pada turnamen lama bila data bracket di Cloud memiliki siklus, feeder duplikat, atau lebih dari satu Grand Final. |
| `supabase/seed.sql` | 17.281 B / 259 baris | Tracked (di `HEAD`) | Seed 5 profil (`super_admin`, `organizer`, `committee`, dan pengguna lainnya), game, tim, turnamen, registrasi, dan data awal menggunakan `ON CONFLICT (id) DO NOTHING`. | **Bahaya bila dijalankan di Cloud produksi:** seluruh 5 profil disisipkan **tanpa `auth_user_id`** (`NULL`), sehingga berinteraksi langsung dengan celah `SUPA-001` pada `0002` bila trigger belum diperbaiki. |

---

## 4. Supabase Cloud Schema Inventory

**STATUS: UNVERIFIED — CLOUD ACCESS BLOCKED (READ-ONLY)**

Kondisi aktual di lingkungan kerja saat audit dijalankan:
- `.env`: **tidak ditemukan** (`False`; hanya `.env.example` yang tersedia).
- Environment variables (`SUPABASE_*`, `POSTGRES_*`, `DB_*`, `TURNAMEN_*`): **tidak ada yang terpasang**.
- `supabase` CLI (`2.104.0` di `%APPDATA%\npm\supabase.cmd`): belum terautentikasi (`Access token not provided. Supply an access token by running supabase login or setting the SUPABASE_ACCESS_TOKEN environment variable.`).
- Direktori `~/.supabase/`: hanya berisi `traces/` dan `telemetry.json` (tanpa token/proyek tertaut).
- Database driver & MCP: tidak ada `supabase` MCP server terdaftar, dan paket Python `psycopg` / `psycopg2` tidak terpasang.

Oleh karena itu, daftar tabel aktual, kolom, tipe data, indeks, constraint, fungsi, trigger, RLS policy, dan isi data pada proyek Supabase Cloud `cfdsgxciodfkamskafwe` (`turnamen-in`) **belum dapat diobservasi**.

### Kueri Read-Only Wajib Saat Akses Cloud Sudah Diberikan
Setelah user menjalankan `supabase login` / memasok `SUPABASE_ACCESS_TOKEN` atau akses baca PostgreSQL read-only, jalankan inspeksi non-mutasi berikut:

```sql
-- 1. Inventaris tabel, RLS status, dan perkiraan row
SELECT n.nspname AS schema_name, c.relname AS table_name,
       c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS force_rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('public', 'private') AND c.relkind = 'r'
ORDER BY 1, 2;

-- 2. Inventaris kolom, constraint, dan indeks di public/private
SELECT table_schema, table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema IN ('public', 'private')
ORDER BY table_schema, table_name, ordinal_position;

SELECT conname, contype, conrelid::regclass AS table_name, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE connamespace IN ('public'::regnamespace, 'private'::regnamespace)
ORDER BY 3, 1;

-- 3. Inventaris fungsi & security mode (DEFINER vs INVOKER + search_path)
SELECT n.nspname, p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       p.prosecdef AS is_security_definer, p.proconfig
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname IN ('public', 'private')
ORDER BY 1, 2;

-- 4. Inventaris trigger (public + auth.users)
SELECT event_object_schema, event_object_table, trigger_name, action_timing, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_schema IN ('public', 'auth')
ORDER BY 1, 2, 3;

-- 5. Inventaris policy RLS aktif
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname IN ('public', 'private')
ORDER BY 1, 2, 3;

-- 6. Hak eksekusi RPC untuk anon / authenticated / PUBLIC
SELECT n.nspname, p.proname, r.rolname,
       has_function_privilege(r.oid, p.oid, 'EXECUTE') AS can_execute
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
CROSS JOIN (SELECT oid, rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')) r
WHERE n.nspname IN ('public', 'private')
ORDER BY 1, 2, 3;
```

---

## 5. RLS & Security Audit

Audit di bawah didasarkan pada kode SQL lokal (`0001`–`0004`), kontrak keamanan (`docs/contracts/role-permissions.md`, `docs/security.md`), dan perilaku backend (`supabase_repository.py`). Status penerapan di Cloud masih *unverified* hingga blocker Bagian 4 terbuka.

### Critical

1. **`SUPA-001` — Auto-Link Email pada `handle_new_auth_user()` (`0002_security_hardening.sql:169–214` & `line 143`):**
   - `handle_new_auth_user()` mencari baris di `public.profiles` dengan `LOWER(email) = LOWER(NEW.email) AND auth_user_id IS NULL` lalu langsung mengisi `auth_user_id = NEW.id`.
   - Bersamaan dengan `seed.sql` yang menyisipkan profil ber-role tinggi tanpa `auth_user_id`, penyerang yang mendaftar lewat public Auth dengan email target berpotensi mewarisi role `super_admin`, `organizer`, atau `committee`.
   - Lihat analisis rinci pada **Bagian 6**.

### High

2. **Eksposur PII `profiles` ke Seluruh `organizer` & `committee` via PostgREST (`0002_security_hardening.sql:411–417`):**
   - Policy `"Profiles select own or staff"` memberi izin `SELECT` pada **semua kolom dan semua baris `public.profiles`** jika `current_user_role() IN ('super_admin', 'organizer', 'committee')`.
   - Meskipun aplikasi Python kini memakai `get_public_profile_summary` (`0003`) untuk non-admin, pengguna mana pun dengan JWT `organizer` atau `committee` dapat memanggil PostgREST `GET /rest/v1/profiles` secara langsung menggunakan `SUPABASE_ANON_KEY` dan membaca `email` serta `phone` milik seluruh pengguna di sistem.
   - **Rekomendasi:** Batasi policy `SELECT` langsung pada `public.profiles` hanya untuk pemilik baris (`auth_user_id = auth.uid()`) dan `super_admin`, serta salurkan kebutuhan tampilan ringkas (`id, username, full_name, avatar_url`) untuk `organizer`/`committee`/`team_captain` melalui RPC aman atau view terbatasi kolom.

3. **Turnamen `draft` Terbuka di Policy `SELECT` Supabase (`0002_security_hardening.sql:461–466`):**
   - Policy `"Public read tournaments"` tetap memakai `FOR SELECT TO anon, authenticated USING (true)`.
   - Service Python (`backend/modules/tournaments/service.py`) menyembunyikan turnamen `draft` dari Guest, Player, dan Team Captain yang tidak berwenang, tetapi lewat Supabase Data API langsung (`anon`/`authenticated`), seluruh turnamen `draft` masih dapat dibaca publik.
   - **Rekomendasi:** Perketat `USING (status <> 'draft' OR current_user_role() = 'super_admin' OR is_tournament_organizer(id) OR is_tournament_committee(id))`.

4. **Potensi Pemalsuan Baris Audit di `activity_logs` via Direct Data API (`0002_security_hardening.sql:875–881`):**
   - Policy `"Activity logs insert authenticated"` mengizinkan setiap pengguna `authenticated` melakukan `INSERT` langsung ke `public.activity_logs` selama `actor_id = current_profile_id()` (atau `NULL`).
   - Karena itu, pengguna biasa bisa menyisipkan log palsu (`action` / `details` sembarangan) lewat PostgREST di luar transaksi bisnis yang sah.
   - **Rekomendasi:** Catat audit melalui jalur terkontrol server/RPC `SECURITY DEFINER` atau batasi `WITH CHECK` agar hanya role/aksi yang sah yang boleh menulis langsung.

5. **Dependensi Aplikasi Wave 2.1–2.3 terhadap Migrasi `0003` & `0004`:**
   - `SupabaseDataStoreRepository` memanggil `get_public_profile_summary`, `transition_tournament_status`, `register_team_atomic`, dan `submit_match_result_atomic`. Jika `0003`/`0004` belum diterapkan ke Cloud ketika kode aplikasi diaktifkan ke `APP_MODE=supabase`, fitur inti (tambah anggota tim oleh kapten, registrasi tim, generate bracket oleh committee, serta pengesahan skor) akan gagal total.

### Medium

6. **`SET search_path = public` pada Fungsi `0002` vs `SET search_path = ''` pada `0003`/`0004`:**
   - Fungsi helper di `0002` (`current_profile_id`, `current_user_role`, `is_tournament_organizer`, `is_tournament_committee`, `is_team_captain`, `prevent_profile_privilege_escalation`, `handle_new_auth_user`, `replace_tournament_matches`) menggunakan `SET search_path = public`, sedangkan standar hardening modern (`0003` & `0004`) sudah memakai `SET search_path = ''` dengan referensi skema penuh (`public.*`, `private.*`, `pg_catalog.*`).
   - **Rekomendasi:** Seragamkan seluruh fungsi `0002` ke `SET search_path = ''` pada hardening berikutnya.

7. **Tabel `payments` Ada di Skema (`0001` & `0002`), Belum Terintegrasi di Repository/API Aplikasi:**
   - `0002` mengizinkan `team_captain` membaca payment tim miliknya dan `super_admin` / organizer mengelola `payments`, namun `supabase_repository.py` belum membaca/menulis tabel `payments`. Perlu dipastikan pada Cloud apakah ada data `payments` yang sudah eksis atau masih kosong, serta apakah policy organizer perlu menyaring kepemilikan tim/turnamen secara konsisten.

8. **Ketidaksesuaian Minor pada Dokumentasi (`docs/database-schema.md` & `docs/wave4-supa001-auth-trigger-plan.md`):**
   - `docs/database-schema.md` hanya mendokumentasikan skema `0001` dan `0002`, belum mencakup `private` schema RPC (`0003`) dan tabel/RPC `match_submission_requests` / `submit_match_result_atomic` (`0004`).
   - `docs/wave4-supa001-auth-trigger-plan.md` baris `38` menyebut `0004_supa001_auth_trigger_hardening.sql` sementara baris `51` menyebut `0005_supa001_auth_trigger_hardening.sql`. Karena `0004` sudah dipakai oleh `0004_wave2_3_atomic_match_submission.sql`, migrasi SUPA-001 **harus diberi nomor `0005`**.

### Low

9. **Fungsi Utilitas `public.set_updated_at()` di `0001` Belum Mengunci `search_path`:**
   - `0001_initial_schema.sql:351–359` mendefinisikan `set_updated_at()` tanpa klausa `SET search_path`. Sebaiknya tambahkan `SET search_path = ''` pada fase hardening berikutnya.

### Matriks Ringkas Akses RLS Lokal (Setelah `0001`–`0004`)

| Role | `profiles` | `tournaments` | `teams` & `team_members` | `registrations` | `matches` & `match_results` | `announcements` | `activity_logs` | `match_submission_requests` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Guest (`anon`)** | Ditolak | `SELECT` semua *(catatan: `draft` masih terlihat)* | `SELECT` semua | Ditolak | `SELECT` semua | `SELECT` `is_published = true` | Ditolak | Ditolak |
| **Player (`authenticated`)** | `SELECT`/`UPDATE` diri sendiri *(tanpa ubah role/active)* | `SELECT` semua *(catatan: `draft` masih terlihat)* | `SELECT` semua | `SELECT` hanya milik tim yg di-kapteni (`0` utk player biasa) | `SELECT` semua | `SELECT` published | `SELECT` diri sendiri; `INSERT` diri sendiri | `SELECT` actor diri sendiri |
| **Team Captain** | `SELECT`/`UPDATE` diri; lookup anggota tim via `get_public_profile_summary` (`0003`) | `SELECT` semua *(catatan: `draft` masih terlihat)* | `INSERT`/`UPDATE` tim milik sendiri & `team_members` | `SELECT` tim sendiri; daftar via RPC `register_team_atomic` | `SELECT` semua | `SELECT` published | `SELECT`/`INSERT` diri sendiri | `SELECT` actor diri sendiri |
| **Organizer** | `SELECT` semua *(temuan High)*; `UPDATE` diri sendiri | `INSERT`/`UPDATE`/`DELETE` turnamen milik sendiri; transisi via `transition_tournament_status` | `SELECT` semua *(CRUD tim jika kapten sendiri)* | `SELECT`/`UPDATE`/`DELETE` pada turnamen miliknya | `UPDATE` / `replace_tournament_matches` / `submit_match_result_atomic` di turnamen miliknya | CRUD pada turnamen miliknya | `SELECT` semua | `SELECT` actor diri sendiri |
| **Committee** | `SELECT` semua *(temuan High)*; `UPDATE` diri sendiri | `SELECT`; hanya transisi `ongoing`/`completed` via RPC jika **assigned** di `tournament_staff` (`0003`/`0004`) | `SELECT` semua | `SELECT` semua (di turnamen terdaftar/akses RLS `0002`) | `submit_match_result_atomic` **hanya** pada turnamen tempatnya ditugaskan (`0004`) | `SELECT` semua (atau CRUD jika diizinkan app; RLS `0002` membatasi CRUD pengumuman ke admin/organizer pemilik) | `SELECT` diri/organizer (`0002`: admin & organizer dapat baca semua; committee hanya `actor_id = current_profile_id()`) | `SELECT` actor diri sendiri |
| **Super Admin** | Akses penuh | Akses penuh (`cancelled` dll.) | Akses penuh | Akses penuh | Akses penuh | Akses penuh | `SELECT`/`INSERT` penuh | `SELECT` penuh |

---

## 6. Auth Trigger / SUPA-001 Audit

Analisis terhadap implementasi lokal saat ini dibandingkan rancangan `docs/wave4-supa001-auth-trigger-plan.md`:

1. **Akar Masalah Saat Ini (`0002_security_hardening.sql`):**
   - `handle_new_auth_user()` (baris `169–214`):
     - Membaca metadata signup (`full_name`, `username`, `phone`), memaksa role signup publik ke `'player'` (`v_role := 'player'`), lalu **sebelum `INSERT`**, mengeksekusi:
       ```sql
       UPDATE public.profiles
       SET auth_user_id = NEW.id,
           phone = COALESCE(public.profiles.phone, v_phone)
       WHERE LOWER(email) = LOWER(NEW.email)
         AND auth_user_id IS NULL;
       ```
     - Jika ada profil ber-email sama dengan `auth_user_id IS NULL` (contohnya 5 profil dari `supabase/seed.sql`, atau profil pra-registrasi), akun Auth baru otomatis terhubung ke profil tersebut beserta seluruh **role**, **kepemilikan turnamen**, dan **tim** yang menempel pada profil itu.
   - `prevent_profile_privilege_escalation()` (baris `143`):
     - Mengandung celah pengecualian:
       ```sql
       IF NOT (OLD.auth_user_id IS NULL AND NEW.auth_user_id = auth.uid()) THEN ...
       ```
     - Mengizinkan non-admin menghubungkan profil tak bertuan kepada dirinya sendiri bila lolos policy `UPDATE`.
2. **Dampak Kombinasi dengan `supabase/seed.sql`:**
   - `supabase/seed.sql` menyisipkan profil bernomor UUID tetap tanpa `auth_user_id` (`auth_user_id = NULL`). Bila Cloud memuat `seed.sql` dan memakai `handle_new_auth_user()` versi `0002`, pendaftaran publik dengan email seeded (`admin@turnamen.in`, `organizer@turnamen.in`, `committee@turnamen.in`, dst.) dapat mengambil alih profil privileged.
3. **Kesesuaian Rancangan Perbaikan (`docs/wave4-supa001-auth-trigger-plan.md`):**
   - Menghapus blok `UPDATE public.profiles ... WHERE LOWER(email) = LOWER(NEW.email) AND auth_user_id IS NULL`.
   - Menambahkan unique index `uq_profiles_lower_email` pada `public.profiles (LOWER(email))` sehingga email ganda langsung ditolak secara deterministik.
   - Menghapus pengecualian `OLD.auth_user_id IS NULL` di `prevent_profile_privilege_escalation()`.
   - Menyediakan RPC `private.assign_user_role(UUID, VARCHAR)` + wrapper `public.assign_user_role` khusus `super_admin` untuk provisioning role sesudah akun Auth dibuat secara eksplisit lewat Supabase Auth Admin / CLI / Dashboard.
   - **Peringatan sebelum deployment `0005`:**
     - Nomor file harus **`supabase/migrations/0005_supa001_auth_trigger_hardening.sql`** (perbaiki catatan baris `38` di `docs/wave4-supa001-auth-trigger-plan.md` yang masih menyebut `0004`).
     - Wajib jalankan audit duplikat `LOWER(email)` dan orphan `auth_user_id IS NULL` di Cloud **sebelum** membuat `UNIQUE INDEX uq_profiles_lower_email`, jika tidak indeks unik akan gagal dibuat.

---

## 7. Local vs Cloud Comparison

| Komponen | Local Migration (`supabase/migrations/`) | Supabase Cloud (`cfdsgxciodfkamskafwe`) | Status | Risiko |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline Schema (`0001`)** | 12 tabel inti (`profiles` s/d `activity_logs`), `pgcrypto`, `set_updated_at()`, 9 trigger updated_at | **Tidak dapat diakses** (tanpa token/kredensial CLI/DB) | `UNVERIFIED (Cloud Access Blocked)` | **High** — Tidak diketahui apakah tabel Cloud dibuat manual, dari `0001`, atau memiliki kolom/constraint berbeda |
| **Security Hardening (`0002`)** | `auth_user_id` FK, helper RLS, anti-privilege trigger, `on_auth_user_created`, `replace_tournament_matches`, policy RLS semua tabel | **Tidak dapat diakses** | `UNVERIFIED (Cloud Access Blocked)` | **Critical** — Jika Cloud masih di `0001` tanpa `0002`, `profiles` terbuka untuk publik; jika sudah `0002`, celah `SUPA-001` aktif |
| **Wave 2.1–2.2 RLS Compatibility (`0003`)** | Schema `private`, RPC `transition_tournament_status`, `get_public_profile_summary`, `register_team_atomic`, index `uq_tournament_seed` | **Tidak dapat diakses** (file lokal *untracked*, komentar SQL menyatakan *not applied to Cloud yet*) | `UNVERIFIED / PENDING DEPLOYMENT` | **Critical** — `supabase_repository.py` bergantung pada 3 RPC ini; data seed kembar di Cloud dapat menggagalkan `uq_tournament_seed` |
| **Wave 2.3 Atomic Submission (`0004`)** | Tabel `match_submission_requests`, `private.validate_tournament_bracket_integrity`, upgrade `transition_tournament_status`, RPC `submit_match_result_atomic` | **Tidak dapat diakses** (file lokal *untracked*) | `UNVERIFIED / PENDING DEPLOYMENT` | **Critical** — `supabase_repository.py` bergantung pada RPC ini; bracket rusak di Cloud akan ditolak saat `completed` |
| **SUPA-001 Hardening (`0005`)** | **Belum ada file SQL** (baru berupa dokumen rancangan di `docs/wave4-supa001-auth-trigger-plan.md`) | **Tidak dapat diakses** | `MISSING LOCALLY & UNVERIFIED ON CLOUD` | **Critical** — Blokir deployment produksi sebelum `0005` dibuat dan diuji |
| **Seed / Akun Auth Demo (`seed.sql`)** | 5 profil tanpa `auth_user_id` + sample data | **Tidak dapat diakses** | `UNVERIFIED (Cloud Access Blocked)` | **Critical** — Berpotensi memicu takeover via `SUPA-001` jika ada profil `auth_user_id IS NULL` di Cloud |
| **Migration Ledger (`supabase_migrations`)** | Tidak ada `supabase/.temp/` atau `config.toml` di repo | **Tidak dapat diakses** | `UNVERIFIED (Cloud Access Blocked)` | **High** — Risiko bentrok histori jika Cloud sebelumnya diisi manual lewat SQL Editor tanpa CLI tracking |

---

## 8. Migration History Analysis

- Secara lokal, tidak terdapat `supabase/config.toml` maupun `supabase/.temp/` yang menautkan direktori lokal ke project ID `cfdsgxciodfkamskafwe`.
- Dari 4 file migrasi di `supabase/migrations/`:
  - `0001_initial_schema.sql` dan `0002_security_hardening.sql` sudah tercatat di Git (`HEAD`), namun **tidak ada bukti terverifikasi di repo** apakah `0001` dan `0002` diterapkan di Cloud melalui `supabase db push` (tercatat di `supabase_migrations.schema_migrations`) atau disalin manual via Supabase SQL Editor.
  - `0003_wave2_rls_compatibility.sql` dan `0004_wave2_3_atomic_match_submission.sql` masih berstatus *untracked* dan belum pernah diterapkan ke Cloud.
  - Penomoran migrasi lokal menggunakan `0001_...`, `0002_...`, `0003_...`, `0004_...` (4 digit sekuensial). Untuk konsistensi dengan Supabase CLI di kemudian hari atau mempertahankan konvensi saat ini, pemeriksaan tabel histori `supabase_migrations.schema_migrations` di Cloud wajib dilakukan lebih dulu.
- **Kueri wajib untuk menyinkronkan histori sebelum menjalankan migrasi:**
  ```sql
  SELECT version, name, statements
  FROM supabase_migrations.schema_migrations
  ORDER BY version;
  ```
  Jika tabel `supabase_migrations.schema_migrations` belum ada atau tidak mencantumkan `0001`/`0002` padahal objek `0001`/`0002` sudah ada di `public`, maka sebelum push CLI dijalankan perlu rekonsiliasi histori (mis. `supabase migration repair` secara sadar setelah backup dan inspeksi diff skema), **bukan** menjalankan ulang `0001` secara mentah karena trigger & policy di `0001` tidak memakai `IF NOT EXISTS`.

---

## 9. Data Integrity Risks

1. **Duplicate `seed_number` pada `registrations` (`0003`):**
   - `0003` membuat `CREATE UNIQUE INDEX uq_tournament_seed ON public.registrations(tournament_id, seed_number) WHERE seed_number IS NOT NULL`.
   - Jika Cloud sudah memiliki data registrasi legacy dengan `seed_number` ganda pada turnamen yang sama, pembuatan index akan gagal dan membatalkan migrasi `0003`.
2. **Bracket Legacy Rusak terhadap Validasi DAG Penuh (`0004`):**
   - `private.validate_tournament_bracket_integrity` (`0004`) memeriksa struktur penuh Single Elimination (`1` Grand Final, tanpa siklus, tanpa self-loop, tanpa feeder slot ganda, tanpa mundur round, tanpa match lintas turnamen).
   - Data pertandingan yang dibuat sebelum Wave 2.3 (atau lewat SQL Editor manual) berisiko ditolak saat `transition_tournament_status(..., 'completed')` atau `submit_match_result_atomic(...)`.
3. **Orphan `auth_user_id IS NULL` & Duplicate `LOWER(email)` pada `profiles` (`0002` -> `0005`):**
   - Jika di Cloud ada dua profil dengan casing email berbeda (mis. `User@ex.com` dan `user@ex.com`), indeks unik `uq_profiles_lower_email` di `0005` akan gagal.
   - Profil `auth_user_id IS NULL` (seperti hasil `seed.sql`) tetap tidak dapat dipakai login sampai dipetakan ke akun `auth.users` yang sah dan validasi data diselesaikan.
4. **Duplikat `(match_id, game_number)` pada `match_results` (`0004`):**
   - `submit_match_result_atomic` mengandalkan `ON CONFLICT (match_id, game_number) DO UPDATE`. Jika di Cloud skema awal dibuat tanpa constraint `UNIQUE (match_id, game_number)` dari `0001`, PostgreSQL akan menolak statement `ON CONFLICT` saat runtime (`42P10`).
5. **Konsistensi Kolom `winner_team_id` / `next_match_id` pada `matches`:**
   - Saat menerapkan `0003`/`0004`, pastikan tipe data kolom (`UUID`, `TIMESTAMPTZ`, `INTEGER`, `VARCHAR`) di Cloud identik 100% dengan `0001` agar PL/pgSQL `SELECT ... INTO` dan `RETURNING row_to_json(...)` tidak error tipe saat runtime.

---

## 10. Recommended Migration Order

Jangan jalankan migrasi apa pun ke produksi sebelum langkah berurutan berikut dilalui:

1. **Tahap 0 — Buka Akses & Read-Only Snapshot Cloud:**
   - Autentikasi Supabase CLI (`supabase login` / `SUPABASE_ACCESS_TOKEN`) dan tautkan atau ambil read-only inspection dari project `cfdsgxciodfkamskafwe`.
   - Jalankan seluruh kueri **Bagian 4**, **Bagian 8**, dan **Bagian 11**.
   - Ambil *database dump* / verifikasi backup & PITR (Point-in-Time Recovery) aktif di dashboard Supabase.
2. **Tahap 1 — Rekonsiliasi Baseline (`0001` & `0002`):**
   - Bandingkan diff skema aktual Cloud terhadap `0001` + `0002`.
   - Jika Cloud masih berada di `0001` (atau ada penyimpangan DDL manual), selaraskan lebih dulu ke baseline `0002` di staging/branch sebelum melangkah ke `0003`.
   - Rekonsiliasi catatan `supabase_migrations.schema_migrations` bila perlu.
3. **Tahap 2 — Pembuatan & Uji Migrasi `0005` (`SUPA-001`) di Lokal / Staging Terisolasi:**
   - Implementasikan `supabase/migrations/0005_supa001_auth_trigger_hardening.sql` sesuai `docs/wave4-supa001-auth-trigger-plan.md` (+ pertimbangkan pengetatan `profiles` select policy, `draft` tournament select policy, `activity_logs` insert policy, dan `SET search_path = ''` pada fungsi `0002`).
4. **Tahap 3 — Penerapan Berurutan pada Staging / Supabase Branch Terpisah:**
   - Jalankan secara berurutan dalam transaksi / CLI tracking:
     1. `0003_wave2_rls_compatibility.sql`
     2. `0004_wave2_3_atomic_match_submission.sql`
     3. `0005_supa001_auth_trigger_hardening.sql`
   - Jalankan verifikasi integrasi `APP_MODE=supabase` untuk 6 role (`Guest`, `Player`, `Team Captain`, `Organizer`, `Committee` assigned/unassigned, `Super Admin`).
5. **Tahap 4 — Provisioning Akun Auth Valid (Pengganti Profil Orphan `seed.sql`):**
   - Tautkan/buat user pada `auth.users` via Admin API / Dashboard lalu sambungkan ke profil yang valid; pastikan tidak ada lagi akun privileged dengan `auth_user_id IS NULL`.
6. **Tahap 5 — Staged Production Deployment (Wave 4B/4C):**
   - Baru lakukan penerapan ke Cloud utama setelah Tahap 0–4 lulus 100%.

---

## 11. Required Pre-deployment Checks

Jalankan seluruh pemeriksaan read-only berikut pada target Cloud **sebelum** mengeksekusi migrasi `0003`, `0004`, maupun `0005`:

```sql
-- Check 1: Deteksi email duplikat case-insensitive (blocker index uq_profiles_lower_email di 0005)
SELECT LOWER(email) AS normalized_email, COUNT(*) AS cnt, ARRAY_AGG(id) AS profile_ids
FROM public.profiles
GROUP BY LOWER(email)
HAVING COUNT(*) > 1;

-- Check 2: Deteksi profil orphan auth_user_id IS NULL (risiko SUPA-001 & seed.sql)
SELECT id, username, email, role, is_active, created_at
FROM public.profiles
WHERE auth_user_id IS NULL
ORDER BY created_at;

-- Check 3: Deteksi seed_number ganda per turnamen (blocker uq_tournament_seed di 0003)
SELECT tournament_id, seed_number, COUNT(*) AS cnt, ARRAY_AGG(id) AS registration_ids
FROM public.registrations
WHERE seed_number IS NOT NULL
GROUP BY tournament_id, seed_number
HAVING COUNT(*) > 1;

-- Check 4: Deteksi duplikat (match_id, game_number) pada match_results (blocker upsert 0004)
SELECT match_id, game_number, COUNT(*) AS cnt, ARRAY_AGG(id) AS result_ids
FROM public.match_results
GROUP BY match_id, game_number
HAVING COUNT(*) > 1;

-- Check 5: Verifikasi keberadaan UNIQUE constraint (match_id, game_number) pada match_results
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.match_results'::regclass AND contype IN ('u', 'p');

-- Check 6: Deteksi turnamen ongoing/completed yang jumlah Grand Final-nya != 1 atau ada next_match lintas turnamen
SELECT m.tournament_id,
       COUNT(*) FILTER (WHERE m.next_match_id IS NULL) AS root_count,
       COUNT(*) FILTER (WHERE nm.id IS NOT NULL AND nm.tournament_id <> m.tournament_id) AS cross_tournament_links
FROM public.matches m
LEFT JOIN public.matches nm ON nm.id = m.next_match_id
GROUP BY m.tournament_id
HAVING COUNT(*) FILTER (WHERE m.next_match_id IS NULL) <> 1
    OR COUNT(*) FILTER (WHERE nm.id IS NOT NULL AND nm.tournament_id <> m.tournament_id) > 0;

-- Check 7: Periksa definisi trigger handle_new_auth_user yang sedang aktif di Cloud
SELECT pg_get_functiondef(p.oid)
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname = 'handle_new_auth_user';
```

---

## 12. Recommended Rollback / Recovery Strategy

1. **Snapshot & Backup Wajib Sebelum Mutasi:**
   - Buat *logical backup* (`supabase db dump` / `pg_dump` schema + data) serta pastikan snapshot/PITR Supabase tersedia tepat sebelum menerapkan setiap gelombang migrasi.
2. **Eksekusi Transaksional & Staging-First:**
   - Uji seluruh migrasi lebih dahulu di *Supabase Branch* atau proyek staging agar kegagalan constraint terdeteksi sebelum menyentuh `cfdsgxciodfkamskafwe`.
   - Jangan jalankan beberapa migrasi sekaligus tanpa checkpoint verifikasi di antara `0003`, `0004`, dan `0005`.
3. **Prinsip Rollback — Hindari `DROP` Data Bisnis Secara Buta:**
   - Untuk **`0003` (`private` RPC & index):** aman melakukan rollback level objek bila diperlukan (`DROP FUNCTION IF EXISTS public.transition_tournament_status(UUID, VARCHAR);`, `public.get_public_profile_summary(UUID, UUID)`, `public.register_team_atomic(UUID, UUID, TEXT)`, `DROP INDEX IF EXISTS public.uq_tournament_seed;`), dengan konsekuensi `supabase_repository.py` Wave 2.1–2.3 tidak dapat beroperasi dan kode aplikasi harus tetap di `APP_MODE=mock` atau versi kompatibel.
   - Untuk **`0004` (`match_submission_requests` & `submit_match_result_atomic`):** jangan langsung men-`DROP` tabel `match_submission_requests` jika sudah ada request produksi; gunakan *forward-fix migration* atau `REVOKE EXECUTE` sementara pada fungsi wrapper `public.submit_match_result_atomic` sambil memulihkan transaksi dari backup jika diperlukan.
   - Untuk **`0005` (`SUPA-001`):** **jangan pernah melakukan rollback ke fungsi `handle_new_auth_user()` versi `0002`** karena akan membuka kembali celah *email account hijack*. Bila ada error pada `0005`, lakukan *forward-fix* sambil menonaktifkan signup publik sementara di Supabase Auth Settings hingga fungsi diperbaiki.

---

## 13. Wave 4 Readiness Decision

**Status Akhir:** **`NOT READY — BLOCKERS FOUND`**

**Alasan Penetapan Status:**
1. **Cloud Schema & State Unverified:** Tidak ada token/kredensial akses ke Supabase Cloud (`cfdsgxciodfkamskafwe`), sehingga status aktual tabel, RLS, trigger, data existing, dan `schema_migrations` tidak dapat diverifikasi.
2. **Security Blocker (`SUPA-001`):** `0002_security_hardening.sql` masih mengandung celah *auto-link* `LOWER(email)` pada profil `auth_user_id IS NULL`, dan migrasi penutupnya (`0005_supa001_auth_trigger_hardening.sql`) belum dibuat.
3. **Unverified Pending Migrations (`0003` & `0004`):** Kedua migrasi krusial Wave 2.1–2.3 masih *untracked*, belum pernah divalidasi pada database PostgreSQL/Cloud staging, dan berpotensi gagal bila ada data legacy Cloud yang melanggar constraint baru (`uq_tournament_seed`, integritas DAG bracket).

**Syarat Masuk Wave 4B (Next Gate):**
1. Pengguna menyediakan akses baca yang sah ke Supabase Cloud `cfdsgxciodfkamskafwe` (mis. `supabase login` / `SUPABASE_ACCESS_TOKEN` atau kredensial read-only / `.env` lokal sesuai aturan keamanan).
2. Inspeksi Bagian 4, 8, dan 11 selesai dijalankan secara read-only dan tabel Perbandingan Local vs Cloud terisi fakta aktual Cloud.
3. File `supabase/migrations/0005_supa001_auth_trigger_hardening.sql` selesai disiapkan dan diuji sebelum push.
