# TURNAMEN.IN — WAVE 6.2: SUPABASE CLOUD MIGRATION DEPLOYMENT RUNBOOK

- **Tanggal Runbook:** 2026-11-26
- **Repository:** `FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Target Supabase Project:** `turnamen-in` (`cfdsgxciodfkamskafwe`, PostgreSQL `17.11`)
- **Supabase CLI Teruji:** `2.104.0`
- **Status:** **`READY FOR APPROVAL`** *(Eksekusi Cloud **BELUM** dijalankan; menunggu persetujuan terpisah dari pemilik project. Stage 1 Read-Only Equivalence Gate **wajib lulus 100%** sebelum `0001` boleh ditandai `applied`.)*

---

## 1. Pre-Deployment Checklist

Pastikan seluruh prasyarat berikut terpenuhi sebelum jendela pemeliharaan (*maintenance window*) dimulai:

- [ ] **Persetujuan Pemilik Project:** Persetujuan eksplisit diberikan untuk mengeksekusi migrasi pada project `cfdsgxciodfkamskafwe`.
- [ ] **Integritas Repository Lokal:** Branch `feature/fikri-ui-ux`, migration [0001_initial_schema.sql](file:///C:/Turnamen.in/supabase/migrations/0001_initial_schema.sql) s/d [0006_wave5_functional_rpc.sql](file:///C:/Turnamen.in/supabase/migrations/0006_wave5_functional_rpc.sql) tidak dimodifikasi, dan `pytest` lulus (`281 passed`).
- [ ] **Kredensial Operator (Lokal / Ephemeral, Tidak Di-commit):**
  - `SUPABASE_ACCESS_TOKEN` atau sesi `supabase login` aktif untuk project `cfdsgxciodfkamskafwe`.
  - Password database Postgres Cloud atau koneksi pooler/direct SSL yang valid.
  - Supabase CLI terpasang (`supabase --version` >= `2.104.0`) dan `psql` / `pg_dump` PostgreSQL 17.x tersedia.
- [ ] **Jendela Pemeliharaan & Blokir Signup Publik:** Pengumuman downtime singkat telah disiapkan dan operator memiliki akses **Supabase Dashboard -> Authentication -> Providers / Sign In Settings** untuk menonaktifkan public signup sementara.
- [ ] **Backup Verified:** Backup penuh Cloud (Dashboard + dump logis `pg_dump`) tersedia sebelum satu pun perintah mutasi dijalankan.
- [ ] **Larangan Eksekusi `seed.sql`:** Dikonfirmasi bahwa [seed.sql](file:///C:/Turnamen.in/supabase/seed.sql) **TIDAK** boleh dijalankan ulang di Cloud (`--include-seed` dilarang).

---

## 2. Filename & Version Compatibility Verification (`0001`–`0006`)

Pengujian empiris dijalankan secara terisolasi pada **PostgreSQL 17.11** (binary EnterpriseDB SHA-256 terverifikasi) menggunakan **Supabase CLI `2.104.0`** dan salinan temporary `0001`–`0006` (file asli di `supabase/migrations/` tidak diubah):

| Pengujian CLI `2.104.0` (PG 17.11 Lokal Terisolasi) | Perintah | Hasil Observasi |
| :--- | :--- | :--- |
| Daftar migrasi dengan prefix `0001`–`0006` | `supabase migration list --workdir <tmp> --db-url <pg17>` | **PASS (`rc=0`)**: Menampilkan 6 versi `0001` s/d `0006` secara berurutan pada kolom `Local`. |
| Repair `0001` saat tabel histori belum ada | `supabase migration repair --status applied 0001 --yes --workdir <tmp> --db-url <pg17>` | **PASS (`rc=0`)**: Output `Repaired migration history: [0001] => applied`. |
| Dry-run push setelah repair `0001` | `supabase db push --dry-run --workdir <tmp> --db-url <pg17>` | **PASS (`rc=0`)**: Mendeteksi tepat 5 migrasi pending (`0002` s/d `0006`), tidak mengulang `0001`. |
| Push berurutan `0002`–`0006` | `supabase db push --yes --workdir <tmp> --db-url <pg17>` | **PASS (`rc=0`)**: Menerapkan `0002 -> 0003 -> 0004 -> 0005 -> 0006` bersih, 13 tabel `public` aktif, `schema_migrations` terisi 6 baris (`0001`–`0006`). |

### Alternatif Pemetaan Timestamp (Hanya Jika CLI Diupgrade ke Versi yang Menolak Prefix 4-Digit)

Supabase CLI `2.104.0` **menerima** `0001`–`0006` secara native sehingga **tidak perlu mengganti nama file asli**. Apabila di masa mendatang digunakan versi CLI lain yang mewajibkan 14-digit timestamp `YYYYMMDDHHMMSS`, salin `supabase/migrations/` ke direktori kerja sementara dengan pemetaan 1:1 berikut (isi SQL dan urutan tetap identik 100%, tanpa duplikasi):

- `0001_initial_schema.sql` -> `20261111000001_initial_schema.sql`
- `0002_security_hardening.sql` -> `20261119000002_security_hardening.sql`
- `0003_wave2_rls_compatibility.sql` -> `20261125000003_wave2_rls_compatibility.sql`
- `0004_wave2_3_atomic_match_submission.sql` -> `20261125000004_wave2_3_atomic_match_submission.sql`
- `0005_supa001_auth_trigger_hardening.sql` -> `20261126000005_supa001_auth_trigger_hardening.sql`
- `0006_wave5_functional_rpc.sql` -> `20261126000006_wave5_functional_rpc.sql`

*(Juga terverifikasi lulus `rc=0` pada PostgreSQL 17.11 + CLI `2.104.0`.)*

---

## 3. Migration History Initialization (`supabase_migrations.schema_migrations`)

Kondisi aktual Cloud `cfdsgxciodfkamskafwe` (inspeksi 2026-11-26): `migration history` kosong (`supabase_migrations.schema_migrations` belum tersedia).

Berdasarkan pengujian empiris pada PostgreSQL 17.11 dengan Supabase CLI `2.104.0`:
1. Sebelum `migration repair`, `SELECT to_regclass('supabase_migrations.schema_migrations')` mengembalikan `NULL`.
2. Menjalankan `supabase migration repair --status applied 0001` **secara otomatis membuat** schema `supabase_migrations` dan tabel `supabase_migrations.schema_migrations` dengan kolom:
   - `version text`
   - `statements text[]`
   - `name text`
   lalu menyisipkan baris `('0001', 'initial_schema')`.
3. **Peringatan Mutlak:** Meskipun `migration repair` berhasil membuat tabel histori secara otomatis pada PG `17.11` + CLI `2.104.0`, perintah `migration repair --status applied 0001` **DILARANG** dijalankan pada Cloud sebelum **Stage 1 Baseline Equivalence Verification (Bagian 4)** membuktikan bahwa seluruh objek di Cloud benar-benar ekuivalen dengan [0001_initial_schema.sql](file:///C:/Turnamen.in/supabase/migrations/0001_initial_schema.sql).

---

## 4. Baseline `0001` + `seed.sql` Verification

### A. Inventaris Eksak `0001_initial_schema.sql` + `seed.sql` pada PostgreSQL 17.11 Lokal

| Kategori Objek | Jumlah di Lokal PG 17.11 (`0001` + `seed.sql`) | Status Cloud (Inspeksi 2026-11-26) | Status Ekuivalensi Saat Ini |
| :--- | :--- | :--- | :--- |
| **Tabel & Kolom (`public`)** | `12` tabel (`142` total kolom: `profiles`: 11, `games`: 14, `tournaments`: 22, `teams`: 10, `team_members`: 10, `tournament_staff`: 5, `registrations`: 11, `matches`: 18, `match_results`: 11, `payments`: 12, `announcements`: 10, `activity_logs`: 8) | `12` tabel publik | **Parsial** (jumlah tabel cocok; tipe/default/nullability 142 kolom belum diinspeksi kolom-per-kolom) |
| **Primary Key (`p`)** | `12` PK (`<table>_pkey`) | Belum dirinci per constraint | **Belum Terbukti** |
| **Foreign Key (`f`)** | `27` FK lintas tabel `public` (`ON DELETE RESTRICT/CASCADE/SET NULL`) | Belum dirinci | **Belum Terbukti** |
| **Check Constraints (`c`)** | `30` CHECK constraints (termasuk `chk_tournament_dates`, `chk_different_teams`, `chk_winner_valid`, rentang role/status) | Belum dirinci | **Belum Terbukti** |
| **Unique Constraints (`u`)** | `14` UNIQUE constraints (termasuk `uq_tournament_seed`, `uq_tournament_team_registration`, `uq_tournament_round_match`, `uq_match_game_number`, `uq_team_member_ingame`, `uq_tournament_staff_assignment`) | `uq_tournament_seed` terkonfirmasi aktif | **Parsial** (13 constraint lain belum diinspeksi langsung) |
| **Indexes (`pg_indexes`)** | `53` indexes pada schema `public` (PK + UNIQUE + `idx_*`) | Belum dirinci | **Belum Terbukti** |
| **Functions (`public`)** | `2` fungsi aplikasi (`set_updated_at()`, `current_user_role()`) + `36` fungsi ekstensi `pgcrypto` | `set_updated_at()` & `current_user_role()` dilaporkan ada | **Parsial** (definisi `prosrc` & atribut security perlu dicek) |
| **Triggers** | `9` trigger `trg_*_updated_at` (`BEFORE UPDATE`) pada 9 tabel | Belum dirinci | **Belum Terbukti** |
| **RLS & Policies** | `12` tabel `relrowsecurity = true`; `9` policies (`Public read *` x7, `"Users read active profiles"`, `"Super admin full access profiles"`); `4` tabel tanpa policy (`activity_logs`, `payments`, `registrations`, `tournament_staff`) | **Cocok**: `12` RLS enabled, `9` policies, `4` tabel tanpa policy | **Terkonfirmasi Jumlah/Pola** (definisi `qual` perlu dicek ulang) |
| **Grants** | Default Supabase platform grants untuk `anon` / `authenticated` / `service_role` di Cloud (pada `0001` tidak ada `REVOKE/GRANT` custom) | Default Supabase Data API | **Perlu Cek Stage 1** |
| **Seeded Records** | `59` baris total (`profiles`: 5 dengan `auth_user_id = NULL`, `games`: 3, `tournaments`: 2, `tournament_staff`: 2, `teams`: 8, `team_members`: 16, `registrations`: 8, `matches`: 7, `match_results`: 3, `payments`: 1, `announcements`: 2, `activity_logs`: 2) | `5` profil dengan `auth_user_id = NULL`, `0` akun `auth.users` | **Parsial** (54 baris di 11 tabel lain + cek duplikat `LOWER(email)` belum diinspeksi langsung) |

### B. Stage 1 Read-Only Baseline Equivalence Query (Wajib Lulus Sebelum `repair 0001`)

Jalankan kueri **read-only** berikut di Supabase SQL Editor (atau `psql` read-only) pada project `cfdsgxciodfkamskafwe`:

```sql
-- 1. Tabel, RLS, dan jumlah kolom (target: 12 tabel, semua rls_enabled=true, total 142 kolom)
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled,
       COUNT(a.attname) AS column_count
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
WHERE n.nspname = 'public' AND c.relkind = 'r'
GROUP BY c.relname, c.relrowsecurity
ORDER BY c.relname;

-- 2. Daftar kolom rinci (bandingkan terhadap 0001_initial_schema.sql)
SELECT table_name, ordinal_position, column_name, data_type, udt_name,
       character_maximum_length, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 3. Semua 83 constraints (12 p, 27 f, 30 c, 14 u)
SELECT conrelid::regclass::text AS table_name, contype, conname,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY 1, 2, 3;

-- 4. Semua 53 indexes
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 5. Fungsi aplikasi (set_updated_at & current_user_role) dan trigger (9 triggers)
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       p.prosecdef, p.proconfig
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN ('set_updated_at', 'current_user_role')
ORDER BY p.proname;

SELECT event_object_table, trigger_name, action_timing, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'public'
ORDER BY event_object_table, trigger_name;

-- 6. Policies (target tepat 9 policies 0001) & Grants
SELECT tablename, policyname, cmd, roles, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

SELECT table_name, grantee, STRING_AGG(privilege_type, ',' ORDER BY privilege_type) AS privs
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee IN ('PUBLIC', 'anon', 'authenticated', 'service_role')
GROUP BY table_name, grantee
ORDER BY table_name, grantee;

-- 7. Cek integritas data & prasyarat sebelum 0002-0006
SELECT LOWER(email) AS lower_email, COUNT(*) FROM public.profiles GROUP BY 1 HAVING COUNT(*) > 1;
SELECT tournament_id, seed_number, COUNT(*) FROM public.registrations WHERE seed_number IS NOT NULL GROUP BY 1, 2 HAVING COUNT(*) > 1;
SELECT match_id, game_number, COUNT(*) FROM public.match_results GROUP BY 1, 2 HAVING COUNT(*) > 1;
SELECT COUNT(*) AS auth_users_count FROM auth.users;
SELECT 'profiles' AS tbl, COUNT(*) FROM public.profiles
UNION ALL SELECT 'games', COUNT(*) FROM public.games
UNION ALL SELECT 'tournaments', COUNT(*) FROM public.tournaments
UNION ALL SELECT 'tournament_staff', COUNT(*) FROM public.tournament_staff
UNION ALL SELECT 'teams', COUNT(*) FROM public.teams
UNION ALL SELECT 'team_members', COUNT(*) FROM public.team_members
UNION ALL SELECT 'registrations', COUNT(*) FROM public.registrations
UNION ALL SELECT 'matches', COUNT(*) FROM public.matches
UNION ALL SELECT 'match_results', COUNT(*) FROM public.match_results
UNION ALL SELECT 'payments', COUNT(*) FROM public.payments
UNION ALL SELECT 'announcements', COUNT(*) FROM public.announcements
UNION ALL SELECT 'activity_logs', COUNT(*) FROM public.activity_logs
ORDER BY 1;
```

**Keputusan Gate Stage 1:**
- Jika **seluruh** objek (12 tabel, 142 kolom, 83 constraints, 53 indexes, 2 fungsi, 9 trigger, 9 policies, grants, 0 duplikat data) **ekuivalen** dan `migration history` kosong -> **LANJUT** ke Stage 2 (`repair 0001`).
- Jika ditemukan **selisih objek atau kolom** (atau constraint missing seperti `uq_match_game_number`) -> **BERHENTI**, **JANGAN** tandai `0001` sebagai `applied`, buat skrip rekonsiliasi delta terlebih dahulu.

---

## 5. Backup & Recovery Requirements

Sebelum menjalankan mutasi apa pun di Cloud:

1. **Dashboard Snapshot / Automated Backup:**
   - Buka **Supabase Dashboard -> Project `cfdsgxciodfkamskafwe` -> Database -> Backups**, pastikan backup terbaru tersedia atau buat manual backup / catat titik waktu PITR sebelum maintenance.
2. **Logical Backup Lokal (`pg_dump`) Wajib:**
   - Ambil dump lengkap schema `public` (plus metadata `auth.users` jika ada) ke folder lokal aman **di luar repository Git**:
     ```powershell
     pg_dump "$CLOUD_DB_URL" --schema=public --schema=auth --format=custom --file="C:\Users\fikri\backups\turnamen_in_pre_w62_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump"
     pg_dump "$CLOUD_DB_URL" --schema=public --data-only --inserts --file="C:\Users\fikri\backups\turnamen_in_public_data_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
     ```
   - Verifikasi file dump non-kosong (`(Get-Item <dump>).Length -gt 0`) dan uji daftar isi dengan `pg_restore --list <dump>`.
3. **Menjaga Data Seeded (59 Baris):**
   - `0002`–`0006` tidak menjalankan `TRUNCATE`, `DROP TABLE`, maupun `DELETE` terhadap data `profiles`, `games`, `tournaments`, `teams`, `team_members`, `registrations`, `matches`, `match_results`, `payments`, `announcements`, atau `activity_logs`.
   - `seed.sql` **tidak dijalankan ulang**.

---

## 6. Signup Maintenance Procedure & Migration Execution Order (`0002 -> 0006`)

### Mengapa Maintenance Window & Pemblokiran Signup Wajib
- **`0002_security_hardening.sql`** memasang `handle_new_auth_user()` versi lama yang memiliki celah **SUPA-001** (auto-link berdasarkan `LOWER(email)` ketika `auth_user_id IS NULL`) dan pengecualian `OLD.auth_user_id IS NULL` pada `prevent_profile_privilege_escalation()`.
- **`0005_supa001_auth_trigger_hardening.sql`** menutup celah **SUPA-001** secara permanen (menolak auto-link email dengan `23505`, menghapus self-claim `auth_user_id`, memperketat policy `"Profiles select own or admin"`, mengunci `search_path = ''`, dan menambah `link_profile_auth_user()` + `assign_user_role()`).
- Oleh karena itu, **public signup wajib diblokir sebelum `0002` dijalankan**, dan baru boleh dibuka kembali **setelah `0005` & `0006` selesai dan terverifikasi**.

### Urutan & Dependensi Migrasi

| Urutan | File Migrasi | Dependensi | Efek Utama | Risiko Khusus |
| :---: | :--- | :--- | :--- | :--- |
| *(Skip SQL)* | `0001_initial_schema.sql` | Baseline Cloud | Hanya ditandai `applied` via `migration repair` sesudah lolos Stage 1 | **Gagal jika dijalankan ulang mentah** (`CREATE TRIGGER`/`CREATE POLICY` tanpa `IF NOT EXISTS`) |
| **1** | `0002_security_hardening.sql` | `0001` + `auth.users` | FK `fk_profiles_auth_user_id`, helper RLS, trigger anti-eskalasi, trigger Auth lama (**SUPA-001**), `replace_tournament_matches()`, policy 12 tabel | Membuka celah transient SUPA-001 jika signup tidak diblokir |
| **2** | `0003_wave2_rls_compatibility.sql` | `0001`, `0002` | Schema `private`, RPC `transition_tournament_status`, `get_public_profile_summary`, `register_team_atomic` | Aman jika `uq_tournament_seed` sudah ada (`IF NOT EXISTS`) |
| **3** | `0004_wave2_3_atomic_match_submission.sql` | `0001`, `0002`, `0003` | Tabel `match_submission_requests`, `validate_tournament_bracket_integrity`, upgrade `transition_tournament_status`, `submit_match_result_atomic` | Pastikan grant `match_submission_requests` (`SELECT` only untuk `authenticated`) |
| **4** | `0005_supa001_auth_trigger_hardening.sql` | `0001`–`0004` | `uq_profiles_lower_email`, hardens `search_path = ''`, menimpa `handle_new_auth_user()` & `prevent_profile_privilege_escalation()` (tutup SUPA-001), `"Profiles select own or admin"`, `link_profile_auth_user()`, `assign_user_role()` | Gagal jika ada duplikat `LOWER(email)` di `profiles` |
| **5** | `0006_wave5_functional_rpc.sql` | `0001`–`0005` | RPC `list_tournament_announcements()`, `list_committee_candidates()`, `list_tournament_staff()` (non-PII projection) | Dependensi ke `profiles`, `announcements`, `tournaments`, `tournament_staff` |

### Prosedur Maintenance Window (Estimasi 10–15 Menit)

1. **T-10 Menit — Blokir Public Signup:**
   - Buka **Supabase Dashboard -> Authentication -> Sign In / Providers -> User Signups**.
   - Nonaktifkan **Allow new users to sign up** (`DISABLE`), klik **Save**.
   - Verifikasi `auth.users` berjumlah `0` baris.
2. **T-5 Menit — Backup & Stage 1 Baseline Verification:**
   - Eksekusi backup Dashboard + `pg_dump` (Bagian 5).
   - Jalankan seluruh kueri Stage 1 (Bagian 4B) dan pastikan 100% ekuivalen dengan baseline `0001` + `seed.sql`.
3. **T-0 Menit — Link CLI, Repair `0001`, & Dry-Run:**
   ```powershell
   # Pastikan berada di root C:\Turnamen.in dan TIDAK menyertakan --include-seed
   supabase login
   supabase link --project-ref cfdsgxciodfkamskafwe
   supabase migration list --linked
   # Ekspektasi awal: Local 0001-0006 tampil, Remote kosong seluruhnya.

   # HANYA JIKA Stage 1 Baseline Verification lulus 100%:
   supabase migration repair --status applied 0001 --linked
   supabase migration list --linked
   # Ekspektasi: 0001 tampil di Local & Remote; 0002-0006 masih kosong di Remote.

   supabase db push --dry-run --linked
   # Ekspektasi: "Would push these migrations:" tepat 5 file (0002 s/d 0006).
   ```
4. **T+2 Menit — Eksekusi `0002 -> 0003 -> 0004 -> 0005 -> 0006`:**
   ```powershell
   supabase db push --linked
   ```
   - Konfirmasi daftar 5 migrasi (`0002` s/d `0006`) lalu tekan `y`.
   - **Expected Output:**
     - `Applying migration 0002_security_hardening.sql...`
     - `Applying migration 0003_wave2_rls_compatibility.sql...`
     - `Applying migration 0004_wave2_3_atomic_match_submission.sql...`
     - `Applying migration 0005_supa001_auth_trigger_hardening.sql...`
     - `Applying migration 0006_wave5_functional_rpc.sql...`
     - `Finished supabase db push.` (exit code `0`).
   - Pastikan langsung cek status histori:
     ```powershell
     supabase migration list --linked
     ```
     **Expected Output:** Semua 6 versi (`0001` s/d `0006`) terisi di kolom `Local` dan `Remote`.
5. **T+5 Menit — Post-Migration Verification (Bagian 8):**
   - Jalankan seluruh kueri verifikasi `0005`/`0006` sebelum membuka signup publik atau membuat user Auth.
6. **T+10 Menit — Super Admin Bootstrap (Bagian 7) & Pembukaan Kembali Signup:**
   - Lakukan Super Admin bootstrap saat signup publik masih terkunci (atau buka signup hanya sesudah `0005` + `super_admin` terverifikasi aktif).

*(Catatan cleanup workspace lokal setelah link/push: pastikan `supabase/.temp/` dan file lokal sensitif tidak ikut ter-commit ke Git.)*

---

## 7. Super Admin Bootstrap Procedure

Kondisi Cloud saat ini: `0` akun `auth.users`, `5` profil seeded (`auth_user_id = NULL`), termasuk profil `super_admin`:
- `profiles.id`: `11111111-1111-4111-8111-111111111101`
- `profiles.email`: `admin@turnamen.in`
- `profiles.role`: `'super_admin'`

Jalankan langkah berikut **hanya setelah `0005` dan `0006` lulus verifikasi**:

1. **Buat Akun Auth Pertama melalui Supabase Dashboard:**
   - Buka **Supabase Dashboard -> Authentication -> Users -> Add user -> Create new user**.
   - Masukkan email `admin@turnamen.in` (harus cocok case-insensitive dengan profil target `11111111-1111-4111-8111-111111111101`), tetapkan password kuat, dan **centang `Auto Confirm User`** agar `email_confirmed_at IS NOT NULL`.
   - **Catatan Trigger `on_auth_user_created` (`0005`):**
     - Karena `admin@turnamen.in` sudah ada pada `public.profiles`, trigger `handle_new_auth_user()` versi `0005` **akan menolak** pembuatan user melalui signup/insert jika email sudah terdaftar pada profil lain (`ERRCODE = '23505': Email sudah terdaftar pada profil lain dan tidak dapat ditautkan otomatis`).
     - Oleh sebab itu, jika `Dashboard -> Add user` memicu trigger `on_auth_user_created` dan ditolak karena `admin@turnamen.in` sudah berada di `public.profiles`, gunakan **salah satu dari dua prosedur tepercaya** berikut:
       - **Opsi Bootstrap A (Akun Admin dengan Email Baru Terpisah — Paling Bersih & Tanpa Bentrok Trigger):**
         1. Buka **Authentication -> Users -> Add user**, buat akun Auth nyata memakai email administrator khusus (misalnya `<admin-nyata>@domain.com`) dengan **Auto Confirm User** dicentang; trigger `0005` membuat baris `public.profiles` ber-role `'player'` (`id = NEW.id, auth_user_id = NEW.id`).
         2. Di **Supabase SQL Editor** (hak `postgres`), promosikan profil tersebut secara terkendali (trigger `prevent_profile_privilege_escalation` mengizinkan `postgres`/`supabase_admin`):
            ```sql
            UPDATE public.profiles
            SET role = 'super_admin', is_active = TRUE, updated_at = NOW()
            WHERE auth_user_id = '<auth_user_id_nyata>'::uuid;
            ```
         3. Nonaktifkan (`is_active = FALSE`) profil demo `admin@turnamen.in` (`11111111-1111-4111-8111-111111111101`) jika tidak dipakai di produksi.
       - **Opsi Bootstrap B (Menautkan ke Profil Seeded `admin@turnamen.in` Secara Terkendali via SQL Editor):**
         1. Buat user sementara dengan email placeholder di Dashboard (**Auto Confirm User** dicentang) atau buat dengan email baru lalu tautkan? Tidak — `link_profile_auth_user()` memverifikasi email `auth.users` == `profiles.email`! Jadi bila ingin mempertahankan profil seeded `11111111-1111-4111-8111-111111111101` (`admin@turnamen.in`) dan `Add user` di Dashboard gagal karena `handle_new_auth_user` menolak duplikat email, gunakan transaksi SQL Editor terkontrol (hanya pada maintenance window tertutup, jangan lewat signup publik) untuk sementara membuat user Auth atau gunakan **Opsi A** lalu memindahkan kepemilikan jika diperlukan, **atau** simpan email sementara pada profil `11111111-...-1101`? **Jangan ubah email seeded sembarangan**. Paling aman: uji dulu apakah `Add user` ditolak oleh trigger `0005`; **Opsi A** (email admin baru + promosi via `postgres` di SQL Editor) selalu berhasil tanpa mematikan trigger `0005`, sekaligus mempertahankan proteksi anti-takeover atas 5 profil seeded!
2. **Konfirmasi Email (`email_confirmed_at IS NOT NULL`):**
   - Verifikasi di SQL Editor:
     ```sql
     SELECT id, email, email_confirmed_at FROM auth.users ORDER BY created_at DESC;
     ```
3. **Jika Menggunakan `public.link_profile_auth_user` untuk Profil Unlinked yang Email-nya Cocok:**
   ```sql
   SELECT id, email, username, role, auth_user_id
   FROM public.link_profile_auth_user(
       '<profile_id_target>'::uuid,
       '<auth_user_id_nyata>'::uuid
   );
   ```
4. **Verifikasi `role` dan `auth_user_id`:**
   ```sql
   SELECT p.id, p.auth_user_id, p.email, p.role, p.is_active, u.email_confirmed_at
   FROM public.profiles p
   JOIN auth.users u ON u.id = p.auth_user_id
   WHERE p.role = 'super_admin';
   ```
   - Pastikan `role = 'super_admin'`, `is_active = TRUE`, `auth_user_id IS NOT NULL`, dan `email_confirmed_at IS NOT NULL`.
5. **Verifikasi Perlindungan 4 Profil Seeded Lainnya (`auth_user_id = NULL`):**
   - Pastikan signup publik dengan email `organizer@turnamen.in`, `committee@turnamen.in`, `captain@turnamen.in`, atau `player@turnamen.in` ditolak oleh `handle_new_auth_user()` (`23505`) dan `auth_user_id` tetap `NULL` (atau nonaktifkan `is_active = FALSE` untuk akun demo yang tidak dipakai di produksi).

---

## 8. Post-Migration Verification

Jalankan verifikasi read-only berikut segera setelah `supabase db push --linked`:

```sql
-- 1. Histori migrasi harus memiliki 6 baris (0001 s/d 0006)
SELECT version, name FROM supabase_migrations.schema_migrations ORDER BY version;

-- 2. Seluruh 13 tabel public harus memiliki RLS enabled (termasuk match_submission_requests)
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;

-- 3. Policy lama "Users read active profiles" & "Profiles select own or staff" HILANG;
--    "Profiles select own or admin" AKTIF; 4 tabel sebelumnya kosong kini ber-policy
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- 4. Unique index case-insensitive email & trigger auth/anti-eskalasi aktif
SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'uq_profiles_lower_email';
SELECT event_object_schema, event_object_table, trigger_name
FROM information_schema.triggers
WHERE event_object_schema IN ('public', 'auth')
ORDER BY 1, 2, 3;

-- 5. Seluruh fungsi private.* dan public.* memiliki search_path='' dan grant ketat
SELECT n.nspname, p.proname, p.prosecdef, p.proconfig
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname IN ('public', 'private')
  AND p.proname IN (
      'set_updated_at', 'current_profile_id', 'current_user_role',
      'is_tournament_organizer', 'is_tournament_committee', 'is_team_captain',
      'prevent_profile_privilege_escalation', 'handle_new_auth_user',
      'replace_tournament_matches', 'transition_tournament_status',
      'get_public_profile_summary', 'register_team_atomic',
      'validate_tournament_bracket_integrity', 'submit_match_result_atomic',
      'link_profile_auth_user', 'assign_user_role',
      'list_tournament_announcements', 'list_committee_candidates', 'list_tournament_staff'
  )
ORDER BY 1, 2;

-- 6. Hak eksekusi anon harus minimal (hanya current_user_role & list_tournament_announcements)
SELECT n.nspname, p.proname,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_exec,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_exec
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname IN ('public', 'private')
  AND p.proname NOT IN ('armor','dearmor','crypt','digest','encrypt','encrypt_iv','decrypt','decrypt_iv','gen_random_bytes','gen_random_uuid','gen_salt','hmac','pgp_armor_headers','pgp_key_id','pgp_pub_decrypt','pgp_pub_decrypt_bytea','pgp_pub_encrypt','pgp_pub_encrypt_bytea','pgp_sym_decrypt','pgp_sym_decrypt_bytea','pgp_sym_encrypt','pgp_sym_encrypt_bytea')
ORDER BY 1, 2;

-- 7. Verifikasi 59 baris data seeded tetap utuh
SELECT 'profiles' AS tbl, COUNT(*) FROM public.profiles
UNION ALL SELECT 'tournaments', COUNT(*) FROM public.tournaments
UNION ALL SELECT 'teams', COUNT(*) FROM public.teams
UNION ALL SELECT 'matches', COUNT(*) FROM public.matches
ORDER BY 1;
```

---

## 9. Recovery Strategy (Tanpa Asumsi Rollback Otomatis)

`supabase db push` mengeksekusi setiap file migrasi secara berurutan; apabila salah satu file gagal di tengah jalan, file yang gagal akan di-rollback oleh transaksi Postgres, namun migrasi sebelumnya yang sudah commit **tidak otomatis di-rollback**.

1. **Jika `migration repair` atau `db push` Gagal Sebelum `0005` Selesai:**
   - **HENTIKAN** proses segera dan **JANGAN** buka kembali public signup (mencegah celah SUPA-001 pada `0002` aktif untuk publik).
   - Catat nama file yang gagal dan pesan error Postgres dari stderr CLI.
   - Jalankan `supabase migration list --linked` untuk melihat versi terakhir yang tercatat `Remote`.
2. **Forward Fix Tanpa Menghapus Data:**
   - Apabila kegagalan disebabkan oleh data atau constraint pada satu file (mis. `0005` gagal karena duplikat `LOWER(email)`), perbaiki anomali data melalui SQL Editor atau buat migrasi forward-only baru setelah kondisi stabil; **jangan** pernah menjalankan `DROP TABLE`, `TRUNCATE`, atau `supabase db reset` di Cloud.
   - Setelah penyebab diperbaiki, jalankan ulang `supabase db push --linked` (CLI hanya akan menerapkan migrasi yang belum tercatat di `schema_migrations`).
3. **Full Restore dari Backup (Jika Terjadi Kerusakan Konsistensi Serius):**
   - Jika kondisi skema tidak konsisten dan tidak dapat diforward-fix dalam jendela pemeliharaan:
     1. Pertahankan public signup dalam status nonaktif.
     2. Pulihkan snapshot / backup dari **Supabase Dashboard -> Database -> Backups (Restore)** ke titik sebelum maintenance window, atau pulihkan dump lokal via `pg_restore` ke project/staging pemulihan terlebih dahulu untuk verifikasi.
     3. Pastikan 59 baris data seeded kembali utuh sebelum menjadwalkan ulang maintenance window.

---

## 10. Open Risks & Blockers Awareness

1. **Ekuivalensi Objek Baseline `0001` di Cloud Belum Diinspeksi Menyeluruh:** Inspeksi 2026-11-26 hanya membuktikan `12` tabel ber-RLS, `9` policies, `uq_tournament_seed`, `5` profil unlinked, dan `migration history` kosong. Stage 1 Read-Only Equivalence Gate (Bagian 4B) **wajib** lulus sebelum `repair 0001`.
2. **Interaksi `handle_new_auth_user()` (`0005`) dengan `Dashboard -> Add User` untuk Email Seeded:** Karena `0005` menolak email yang sudah ada di `public.profiles` (`23505`), pembuatan user Dashboard memakai `admin@turnamen.in` dapat ditolak oleh trigger `on_auth_user_created`. Prosedur aman yang direkomendasikan adalah **Opsi Bootstrap A** (buat user `super_admin` dengan email baru melalui Dashboard + promosikan `role` via `postgres` di SQL Editor) sambil menonaktifkan akun demo yang tidak dipakai.
3. **Pengujian Live GoTrue Auth + PostgREST Gateway (Wave 4C) Belum Pernah Dijalankan:** Perilaku HTTP nyata GoTrue email confirmation, refresh token, dan PostgREST terhadap `sb_publishable_*` maupun legacy `anon` JWT baru akan teruji penuh setelah deployment Cloud atau staging disetujui.
4. **Kapasitas & Kebutuhan Koneksi Operator:** `supabase link` / `supabase db push` membutuhkan `SUPABASE_ACCESS_TOKEN`, password DB Cloud, dan koneksi jaringan stabil ke host Supabase Cloud.
5. **Fitur Opsional `payments`:** Tabel `payments` tersedia dan ber-RLS di `0002`, tetapi belum memiliki endpoint API maupun UI di aplikasi (non-blocking).
