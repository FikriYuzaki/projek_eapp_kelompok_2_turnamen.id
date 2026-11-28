# TURNAMEN.IN - WAVE 4B.1: POSTGRESQL 17.11 COMPATIBILITY VALIDATION REPORT

**Tanggal Laporan:** 2026-11-26  
**Branch Aktif:** `feature/fikri-ui-ux`  
**Keputusan Wave 4B.1:** **PASS (PostgreSQL 17.11 & PostgreSQL 18.6 Lokal Terisolasi)**  
**Status Supabase Cloud:** **BELUM DISENTUH (Dilarang pada Wave 4B.1)**  

---

## 1. Ringkasan Eksekutif

Wave 4B.1 memvalidasi kompatibilitas penuh seluruh migrasi (`0001`–`0005`), skenario security regression **SUPA-001**, RLS, RPC, serta uji konkurensi pada **PostgreSQL 17.11** (versi minor yang sama persis dengan target Supabase Cloud `turnamen-in` / `cfdsgxciodfkamskafwe`).

Hasil utama:
- **Seluruh 5 migrasi (`0001` -> `0002` -> `0003` -> `0004` -> `0005`) berjalan sukses 100% pada PostgreSQL 17.11** tanpa modifikasi SQL apa pun pada `0001`–`0005`.
- **Full test suite pada PostgreSQL 17.11:** **`257 passed, 1 warning in 44.04s`** (`pytest -v` dengan `TURNAMEN_PG_BIN_DIR` diarahkan ke binary portabel PostgreSQL 17.11).
- **Verifikasi ulang pada PostgreSQL 18.6:** **`7 passed in 15.39s`** (`test_wave4b_postgres_migrations_and_security.py`), memastikan tidak ada regresi pada mesin utama.
- **Keamanan & kebersihan lingkungan:** PostgreSQL 18.6 di `C:\Program Files\PostgreSQL\18` tetap utuh, tidak ada Windows service yang diubah, seluruh cluster sementara telah dihentikan aman, dan direktori sementara PostgreSQL 17.11 (`%TEMP%\turnamen_pg17_11`) serta folder cluster (`turnamen_wave4b_pg_*`) telah dibersihkan (`0` tersisa).

---

## 2. Penyediaan Lingkungan PostgreSQL 17.11 Side-by-Side

1. **Kondisi Awal Mesin:** Hanya PostgreSQL 18.6 yang terpasang (`C:\Program Files\PostgreSQL\18`); Docker tidak tersedia; WSL tidak memiliki distro terpasang.
2. **Evaluasi & Metode Aman:** Daripada menjalankan installer sistem yang menyentuh registry, service Windows, atau `Program Files`, pengujian menggunakan paket binary portabel resmi EnterpriseDB **PostgreSQL 17.11** (`postgresql-17.11-5-windows-x64-binaries.zip`, SHA-256 terverifikasi `80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f`).
3. **Isolasi Cluster Uji:**
   - Binary diekstrak sementara ke `%TEMP%\turnamen_pg17_11\pgsql\bin` (`psql`, `initdb`, `pg_ctl` terkonfirmasi versi `17.11`).
   - Cluster baru dibuat lewat `initdb` di `%TEMP%\turnamen_wave4b_pg_*`, diikat ketat ke `127.0.0.1` pada port acak bebas, memakai data sintetis (`seed.sql` + UUID acak), dan dimatikan dengan `pg_ctl -m immediate -w stop` lalu dihapus setelah sesi pytest selesai.
   - Direktori binary sementara `%TEMP%\turnamen_pg17_11` juga dihapus sesudah pengujian selesai.
4. **Penyesuaian Test Harness:** [test_wave4b_postgres_migrations_and_security.py](../../tests/integration/test_wave4b_postgres_migrations_and_security.py) diperbarui secara minimal agar mendukung env var opsional `TURNAMEN_PG_BIN_DIR` dan `TURNAMEN_EXPECTED_PG_MAJOR` (dengan default tetap `18`). Tidak ada perubahan pada `0001`–`0005` maupun kode aplikasi.

---

## 3. Validasi Migrasi & Keamanan pada PostgreSQL 17.11

1. **Migration Validation (`0001 -> 0002 -> 0003 -> 0004 -> 0005`):**
   - Dijalankan pada dua fresh database independen (`turnamen_wave4b_fresh` dan `turnamen_wave4b_fresh_2`) dengan `psql -v ON_ERROR_STOP=1`.
   - Nol syntax error, nol function signature mismatch, dan nol error PL/pgSQL.
   - Seluruh 13 tabel `public` aktif RLS (`relrowsecurity = true`), index `uq_tournament_seed` dan `uq_profiles_lower_email` terbentuk, trigger `on_auth_user_created` dan `trg_prevent_profile_privilege_escalation` aktif, schema `private` serta seluruh 7 fungsi `private.*` dan wrapper `public.*` memiliki `search_path=""` dan hak `EXECUTE` yang ketat.
2. **Security Regression SUPA-001 (PostgreSQL 17.11):**
   - Signup publik memakai email profil seeded (`admin@turnamen.in`, `ADMIN@TURNAMEN.IN`, `organizer@turnamen.in`, `committee@turnamen.in`): ditolak (`23505`), baris `auth.users` di-rollback, `auth_user_id` profil tetap `NULL`.
   - Signup duplikat case-insensitive (`MixedCase_*` vs lowercase) dan duplicate username: ditolak (`23505`) dan `auth.users` di-rollback.
   - Self-claim `auth_user_id` dan modifikasi `role`/`is_active`/`email`/`username` oleh user biasa: ditolak (`42501` oleh `prevent_profile_privilege_escalation` pada profil sendiri; `0` baris terubah pada profil lain/unlinked).
   - Manipulasi `raw_user_meta_data` (`super_admin`, `organizer`, `committee`, `ADMIN`): selalu diturunkan menjadi `'player'`; role `player` dan `team_captain` tetap berjalan normal.
   - Pengaitan profil via `public.link_profile_auth_user`: menolak email belum terkonfirmasi (`42501`), menolak email tidak cocok (`22023`), menolak overwrite profil yang sudah tertaut (`P0009`), mengizinkan `super_admin` aktif dan `service_role` (`request.jwt.claims`), serta tetap berfungsi ketika `profiles.id != profiles.auth_user_id`.
   - Role assignment via `public.assign_user_role`: ditolak untuk non-`super_admin` (`42501`) dan profil belum tertaut (`P0009`), berhasil untuk `super_admin` aktif dan menulis audit `USER_ROLE_UPDATED` ke `activity_logs`.
   - User `auth.users` tanpa profil (`orphan`) menghasilkan `current_profile_id() = NULL`, `current_user_role() = NULL`, dan `0` baris dari `profiles`.
3. **RPC & Concurrency (PostgreSQL 17.11):**
   - `get_public_profile_summary`, `transition_tournament_status`, `register_team_atomic`, `replace_tournament_matches`, dan `submit_match_result_atomic` seluruhnya lulus.
   - Konkurensi 4 kapten berebut kuota `max_teams = 2`: tepat 2 sukses (`seed_number` `[1, 2]`) dan 2 ditolak `P0009`.
   - Konkurensi 3 request `submit_match_result_atomic` pada Grand Final dengan `idempotency_key` sama: 1 eksekusi utama + 2 `idempotent_replay = true`, tepat 1 baris `match_results`.
   - Pemakaian `idempotency_key` yang sama dengan payload berbeda ditolak (`P0009`), sedangkan `force_override` dengan `idempotency_key` baru memperbarui skor Grand Final tanpa menduplikasi `match_results`.

---

## 4. Perbandingan PostgreSQL 18.6 vs PostgreSQL 17.11

| Test | PostgreSQL 18.6 | PostgreSQL 17.11 | Keterangan |
|---|---|---|---|
| `test_fresh_database_migration_order_and_schema_objects` | PASS | PASS | Eksekusi `0001`–`0005` bersih; 13 tabel RLS, index, trigger, `private.*` & `public.*` RPC identik |
| `test_second_fresh_database_independence` | PASS | PASS | Fresh DB kedua + `seed.sql` (5 profil awal) bersih dan independen |
| `test_supa001_public_signup_cannot_hijack_seeded_profiles` | PASS | PASS | Signup email seeded (`admin`/`organizer`/`committee`, mixed case) ditolak `23505` & rollback `auth.users` |
| `test_supa001_raw_user_meta_data_cannot_grant_privileged_roles` | PASS | PASS | Role privileged di `raw_user_meta_data` turun ke `'player'`; `team_captain` tetap berfungsi |
| `test_security_regression_privilege_escalation_linking_and_case_sensitivity` | PASS | PASS | Self-claim, eskalasi kolom, `anon` RLS, orphan auth user, `link_profile_auth_user` (`super_admin` & `service_role`), `assign_user_role`, audit log identik |
| `test_rpc_integration_and_concurrent_registration_and_match_submission` | PASS | PASS | Semua 5 RPC domain, konkurensi slot terakhir `register_team_atomic`, konkurensi & replay `submit_match_result_atomic`, dan `force_override` lulus |
| `test_linked_seeded_profile_id_distinct_from_auth_uid_works_across_rls_and_rpcs` | PASS | PASS | Profil seeded tertaut (`profiles.id != auth_user_id`) bekerja normal pada RLS & RPC |
| Full pytest suite (`257` tests) | PASS (257 passed) | PASS (257 passed) | Termasuk 250 test unit/API Wave 1–3.6 + 7 test PostgreSQL Wave 4B/4B.1 |

**Catatan Perbedaan & Batasan Simulasi:**
- **Tidak ada perbedaan perilaku SQL, trigger, RLS, locking, maupun SQLSTATE** antara PostgreSQL 18.6 dan PostgreSQL 17.11 untuk seluruh skema `0001`–`0005`. Tidak diperlukan migration perbaikan forward-only.
- **Batasan Simulasi:** Pengujian pada kedua versi tetap menggunakan simulasi lokal schema `auth` (`auth.users`, `auth.uid()`, `auth.role()`) dan role `authenticator`/`anon`/`authenticated`/`service_role` dengan GUC JWT. Hasil ini **tidak setara dengan pengujian runtime Supabase GoTrue (signup/email confirmation/JWT issuer) maupun PostgREST HTTP gateway di Supabase Cloud**.

---

## 5. Status Quality Gate Wave 4B.1

- [x] Semua migration (`0001`–`0005`) berhasil pada PostgreSQL **17.11**.
- [x] Seluruh security regression kritis lulus.
- [x] RPC dan concurrency test kritis lulus.
- [x] Tidak ada perubahan pada `0001`–`0005`, Wave 1–4B, atau `requirements.txt`.
- [x] Instalasi PostgreSQL 18.6 utama tetap utuh; database sementara telah dihentikan aman; tidak ada direktori temporary yang tertinggal.
- [x] Supabase Cloud belum disentuh dan repository belum di-commit/push/merge.
