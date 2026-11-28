# TURNAMEN.IN - WAVE 6: SUPABASE ONLINE READINESS & CLOUD RECONCILIATION REPORT

- **Tanggal Laporan:** 2026-11-26
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Target Project Supabase:** `turnamen-in` (`cfdsgxciodfkamskafwe`, PostgreSQL `17.11`, status `ACTIVE_HEALTHY`)
- **Status Kesiapan Migrasi Cloud:** **`READY FOR CONTROLLED CLOUD MIGRATION`**
- **Status Aktivasi Online (`APP_MODE=supabase`):** Belum aktif sampai migrasi Cloud (`0002` sampai `0006`) diterapkan, `.env` lokal dikonfigurasi, `super_admin` ditautkan, dan verifikasi GoTrue + PostgREST selesai.

---

## 1. Executive Summary

Wave 6 menyelesaikan validasi kompatibilitas PostgreSQL **17.11** atas migration `0006_wave5_functional_rpc.sql`, memetakan perbedaan skema lokal (`0001` sampai `0006`) terhadap kondisi aktual project Cloud `turnamen-in` (`cfdsgxciodfkamskafwe`) per inspeksi read-only `2026-11-26`, serta menyusun rencana rekonsiliasi forward-only tanpa mengubah database Cloud maupun `0001` sampai `0005`.

Temuan inti:
1. **Seluruh rangkaian migration `0001 -> 0002 -> 0003 -> 0004 -> 0005 -> 0006` lulus `8 passed in 18.51s` pada PostgreSQL 17.11** (binary portabel resmi EnterpriseDB, SHA-256 terverifikasi). Tidak ada error sintaks, ketidaksesuaian tipe data, maupun error PL/pgSQL pada engine PostgreSQL 17.11.
2. **Identifikasi tepat baseline Cloud (inspeksi 2026-11-26):** Kondisi `12` tabel publik ber-RLS enabled, tepat `9` RLS policies, `uq_tournament_seed` aktif, `5` profil berstatus `auth_user_id = NULL`, `migration history` kosong, serta `4` tabel tanpa policy (`activity_logs`, `payments`, `registrations`, `tournament_staff`) cocok persis dengan hasil eksekusi manual [0001_initial_schema.sql](file:///C:/Turnamen.in/supabase/migrations/0001_initial_schema.sql) dan [seed.sql](file:///C:/Turnamen.in/supabase/seed.sql) melalui SQL Editor.
3. **Aturan kunci rekonsiliasi Cloud:** File `0001_initial_schema.sql` **tidak boleh dijalankan ulang mentah** di Cloud karena seluruh 12 tabel, constraint `uq_tournament_seed`, 9 trigger, dan 9 policy awal sudah terpasang tanpa klausul `DROP ... IF EXISTS`. Sebagai gantinya, versi `0001` harus disinkronkan ke riwayat migrasi tanpa dieksekusi ulang, lalu `0002` sampai `0006` diterapkan secara forward-only dan terpadu dalam satu jendela pemeliharaan terkontrol.

---

## 2. PostgreSQL 17.11 Migration 0006 Result

Pengujian dilakukan menggunakan cluster sementara terisolasi di `127.0.0.1` memakai binary portabel resmi EnterpriseDB **PostgreSQL 17.11** (`postgresql-17.11-5-windows-x64-binaries.zip`, SHA-256 `80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f`), terpisah dari PostgreSQL 18.6 lokal. Seluruh direktori temporary telah dihapus bersih setelah pengujian selesai.

- **Perintah:** `pytest tests/integration/test_wave4b_postgres_migrations_and_security.py -v` (`TURNAMEN_EXPECTED_PG_MAJOR=17`)
- **Hasil:** **`8 passed in 18.51s`** (nol failure, nol skip).

| Fokus Pengujian PG 17.11 | Hasil | Detail Verifikasi |
| :--- | :--- | :--- |
| Fresh DB sequence `0001` -> `0006` (2 DB independen) | **PASS** | `psql -v ON_ERROR_STOP=1` bersih tanpa error pada kedua fresh database. |
| `public.list_tournament_announcements(UUID)` | **PASS** | Teruji pada `anon` (Guest), `player`, `organizer`, dan `committee`; menampilkan `author_name` berbeda dan fallback `'Panitia'` untuk profil nonaktif; tidak mengembalikan `email`/`phone`; menyembunyikan pengumuman `draft` dari `anon` dan `player`. |
| `public.list_committee_candidates()` & `private.*` | **PASS** | `organizer` pemilik melihat kandidat aktif (`committee`) tanpa kolom PII; `anon` dan `player` ditolak `42501`; schema `private` tetap `REVOKE ALL FROM PUBLIC, anon`. |
| `public.list_tournament_staff(UUID)` | **PASS** | `organizer` pemilik melihat daftar panitia beserta `username`/`full_name` tanpa `email`/`phone`. |
| `public.assign_user_role()` & `link_profile_auth_user()` | **PASS** | Hanya `super_admin` aktif (dan `service_role`/`postgres` untuk linking), menolak non-admin `42501` dan profil belum tertaut `P0009`. |
| `search_path`, `SECURITY DEFINER`, `EXECUTE` grants | **PASS** | Seluruh fungsi `private.*` dan `public.*` `SECURITY DEFINER` mengunci `search_path=""`; hak `anon` dibatasi ketat (`list_tournament_announcements` & `current_user_role` saja; seluruh RPC mutasi/sensitif dicabut dari `PUBLIC` & `anon`). |
| RLS Compatibility (`profiles`, `registrations`, `matches`, `tournaments`) | **PASS** | `"Profiles select own or admin"` tetap membatasi `SELECT` langsung `profiles` ke baris milik sendiri atau `super_admin`. |

---

## 3. Cloud Schema Comparison (Local `0001`–`0006` vs Cloud Baseline 2026-11-26)

Sumber kondisi Cloud berasal dari inspeksi read-only tanggal `2026-11-26` pada project `cfdsgxciodfkamskafwe`:

| Database Object | Local Migration (`0001`–`0006`) | Cloud Actual (Inspeksi 2026-11-26) | Required Action |
| :--- | :--- | :--- | :--- |
| **12 Core Tables (`profiles` .. `activity_logs`)** | `0001` (`CREATE TABLE IF NOT EXISTS`) | Ada (`12` public tables, RLS enabled di semua 12 tabel) | **Pertahankan**; jangan buat ulang tabel. |
| **Table `public.match_submission_requests`** | `0004` (`CREATE TABLE IF NOT EXISTS` + RLS + `uq_match_submission_idempotency`) | **Belum ada** (jumlah tabel publik masih `12`, bukan `13`) | **Buat** via bagian DDL `0004`. |
| **Seeded `public.profiles` (`5` baris)** | `seed.sql` (`auth_user_id = NULL`) | `5` profiles, seluruhnya `auth_user_id = NULL` | **Pertahankan data**; tautkan ke user Auth nyata lewat `link_profile_auth_user` atau nonaktifkan akun demo sebelum signup publik dibuka. |
| **Constraint `uq_tournament_seed`** | `0001:184` (`UNIQUE (tournament_id, seed_number)`) | **Sudah tersedia** | **Pertahankan**; tidak ada perubahan dibutuhkan. |
| **FK `fk_profiles_auth_user_id` & `idx_profiles_auth_user_id`** | `0002:6-27` (`ON DELETE SET NULL`, guarded `IF NOT EXISTS`) | Belum terpasang (`0002` belum ada) | **Tambah** lewat `0002`. |
| **Index `uq_profiles_lower_email`** | `0005:11-12` (`UNIQUE INDEX ON (LOWER(email))`) | Belum terpasang | **Buat** lewat `0005` (pastikan cek 0 duplikat email case-insensitive sebelum eksekusi). |
| **9 Policies Awal `0001` (`Public read *`, `Users read active profiles`, `Super admin full access profiles`)** | Dihapus dan diganti di `0002` lalu diperketat di `0005` | **Masih terpasang** (`9 RLS policies` total di Cloud), sehingga `"Users read active profiles"` masih membuka PII | **Hapus `"Users read active profiles"`** dan ganti seluruh policy via `0002` + `"Profiles select own or admin"` di `0005`. |
| **Policies pada `activity_logs`, `payments`, `registrations`, `tournament_staff`** | `0002` (kebijakan baca/tulis berbasis kepemilikan & role) | **Belum ada policy** (`4` tabel ber-RLS aktif tanpa policy) | **Terapkan** policy lengkap `0002`. |
| **Schema `private` & Functions (`0002`–`0006`)** | Schema `private`, helper RLS (`search_path=""`), 10+ RPC (`transition_tournament_status`, `get_public_profile_summary`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`, `link_profile_auth_user`, `assign_user_role`, `list_tournament_announcements`, `list_committee_candidates`, `list_tournament_staff`) | Belum ada (hanya `public.set_updated_at()` tanpa lock `search_path` dan `public.current_user_role()` dari `0001`) | **Terapkan** schema `private`, helper hardened `0005`, dan seluruh fungsi/RPC `0002`–`0006` + `REVOKE/GRANT`. |
| **Profile & Auth Triggers (`trg_prevent_profile_privilege_escalation`, `on_auth_user_created`)** | `0002` lalu di-harden di `0005` (`handle_new_auth_user()` menolak auto-link email & role privileged) | **Belum terpasang** di `profiles` / `auth.users` | **Pasang langsung versi `0005`** (jangan tinggalkan versi `0002` aktif tanpa `0005`). |
| **PostgreSQL Table Grants (`anon` / `authenticated`)** | Mengandalkan default schema grants Supabase (`USAGE`, table privileges dibatasi RLS) | Default Supabase Data API | Verifikasi pasca-migrasi bahwa `match_submission_requests` `REVOKE INSERT, UPDATE, DELETE FROM PUBLIC, anon, authenticated` dan `SELECT` aktif untuk `authenticated`. |
| **Migration History (`supabase_migrations.schema_migrations`)** | `0001`–`0006` | **Kosong** | **Sinkronkan** entri `0001` tanpa eksekusi ulang DDL, lalu catat `0002`–`0006` setelah diterapkan. |
| **Supabase Storage (`tournament-assets`)** | `config.py:68` menyimpan nama default bucket; aplikasi belum memanggil `client.storage` | Belum digunakan oleh kode aplikasi | **Opsional / non-blocking**; tidak perlu bucket atau storage policy untuk aktivasi awal fitur inti. |

### Identifikasi Risiko & Potensi Duplikasi
- **Risiko Duplikasi Objek jika `0001` Dijalankan Ulang:** `0001_initial_schema.sql` tidak memiliki `DROP TRIGGER IF EXISTS` (baris `315–340`) maupun `DROP POLICY IF EXISTS` (baris `372–398`). Menjalankan `0001` atau `supabase db push` tanpa menandai `0001` sudah terpasang akan gagal.
- **Risiko Data Saat Memasang Constraint Baru:** Tidak ada operasi `DROP TABLE` atau `TRUNCATE`. Satu-satunya prasyarat data sebelum `0005`/`0004` adalah memastikan di Cloud tidak ada dua profil dengan `LOWER(email)` identik (agar `uq_profiles_lower_email` sukses) serta tidak ada duplikat `(match_id, game_number)` pada `match_results`.
- **Celah Transien `0002` sebelum `0005`:** Jika `0002` dijalankan terpisah jauh sebelum `0005`, `handle_new_auth_user()` versi `0002` sempat aktif dengan celah `SUPA-001`. Eksekusi `0002` sampai `0006` dalam satu maintenance window atau transaksi gabungan menghilangkan celah tersebut.

---

## 4. RLS and RPC Compatibility

1. **Kompatibilitas Policy `0002` + `0005` dengan `0001`:**
   - `0002` menjalankan `DROP POLICY IF EXISTS` untuk seluruh 9 policy lama `0001` sebelum membuat kebijakan baru, lalu `0005` mengganti `"Users read active profiles"` dan `"Profiles select own or staff"` menjadi `"Profiles select own or admin"`.
   - Keempat tabel yang saat ini terkunci total (`activity_logs`, `payments`, `registrations`, `tournament_staff`) langsung mendapat kebijakan terotentikasi tanpa merusak data existing.
2. **Kompatibilitas RPC Aplikasi (`supabase_repository.py`):**
   - `get_public_profile_summary`, `transition_tournament_status`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`, `assign_user_role`, `list_tournament_announcements`, `list_committee_candidates`, dan `list_tournament_staff` seluruhnya kompatibel dengan RLS `0005` (tidak memerlukan pelonggaran `SELECT` pada `public.profiles`) dan telah teruji pada PostgreSQL `17.11`.

---

## 5. Auth Bootstrap & Akun Super Admin Pertama

Karena `0005` menutup auto-link email dan melarang penetapan role lewat `raw_user_meta_data`:
1. **Pengguna Publik Baru:** Pendaftaran via aplikasi (`POST /api/v1/auth/register`) atau Supabase Auth hanya bisa membuat role `player` atau `team_captain` (`auth_user_id = NEW.id`). Email yang bertabrakan dengan profil seeded (`admin@turnamen.in`, dll.) akan ditolak (`23505`) dan baris `auth.users` otomatis dibatalkan.
2. **Prosedur Bootstrap `super_admin` Pertama (Untuk Pemilik Project):**
   - **Langkah 1:** Setelah migrasi `0002` sampai `0006` aktif di Cloud, buat akun Auth nyata untuk administrator utama melalui **Supabase Dashboard -> Authentication -> Users -> Add User** (atau Admin API) dengan email yang cocok dengan profil `super_admin` target (misalnya `admin@turnamen.in`) dan centang **Auto Confirm User** (`email_confirmed_at IS NOT NULL`).
   - **Langkah 2:** Catat `User UID` (`<auth_uid>`) dan ID profil target (`<profile_id>`). Di **Supabase SQL Editor** (hak `postgres`), jalankan:
     ```sql
     SELECT * FROM public.link_profile_auth_user(
         '<profile_id_super_admin>'::uuid,
         '<auth_user_id_nyata>'::uuid
     );
     ```
   - **Langkah 3:** Pemilik aplikasi kini dapat login via desktop app memakai email & password akun Auth tersebut (`APP_MODE=supabase`), tanpa `service_role` key di aplikasi desktop.
   - **Langkah 4:** Untuk 4 akun demo lain yang `auth_user_id = NULL`, pemilik dapat menghubungkannya dengan `public.link_profile_auth_user(...)` (via `super_admin` yang sudah login atau SQL Editor), atau menonaktifkan (`is_active = false`) / menghapus profil demo yang tidak dipakai di produksi.
   - **Langkah 5:** Kenaikan role pengguna baru di dalam aplikasi dilakukan eksklusif oleh `super_admin` melalui UI Admin atau `PATCH /api/v1/users/<id>/role` -> `public.assign_user_role(...)`.

---

## 6. Required Cloud Changes

Ringkasan perubahan minimum yang dibutuhkan di Cloud (tidak perlu membuat ulang tabel `0001` maupun index `uq_tournament_seed`):
1. Tandai baseline `0001` sudah diterapkan di `supabase_migrations.schema_migrations`.
2. Terapkan DDL/policy/trigger/RPC dari `0002`, `0003`, `0004`, `0005`, dan `0006` (`match_submission_requests`, `fk_profiles_auth_user_id`, `uq_profiles_lower_email`, policy 13 tabel termasuk penghapusan `"Users read active profiles"`, hardening helper `search_path=""`, trigger `on_auth_user_created` versi `0005`, `trg_prevent_profile_privilege_escalation`, dan 10+ fungsi RPC `private.*`/`public.*`).
3. Terapkan `REVOKE ALL` / `GRANT SELECT` ketat pada `public.match_submission_requests`.
4. Bootstrap akun `super_admin` pertama dan selesaikan 4 profil `auth_user_id = NULL` lainnya sebelum membuka pendaftaran publik.

---

## 7. Forward-Only Reconciliation Plan (Tanpa Mutasi Saat Ini)

Urutan eksekusi aman ketika pemilik project siap menyetujui migrasi Cloud:
1. **Backup:** Ambil snapshot / logical backup database `cfdsgxciodfkamskafwe` dari Supabase Dashboard.
2. **Pre-Flight Audit Read-Only di SQL Editor Cloud:**
   ```sql
   -- Cek 0 duplikat email case-insensitive pada profiles
   SELECT LOWER(email), COUNT(*) FROM public.profiles GROUP BY 1 HAVING COUNT(*) > 1;
   -- Cek daftar 12 tabel & 9 policies saat ini
   SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public' ORDER BY 2, 3;
   ```
3. **Sync Migration History (Skip `0001` Raw Execution):**
   ```bash
   supabase migration repair --status applied 0001
   ```
   (Atau sisipkan versi `0001` ke `supabase_migrations.schema_migrations` setelah `supabase link` tanpa mengeksekusi ulang SQL `0001`.)
4. **Terapkan `0002` -> `0003` -> `0004` -> `0005` -> `0006` Secara Terpadu:**
   - Bungkus atau jalankan berurutan `0002_security_hardening.sql`, `0003_wave2_rls_compatibility.sql`, `0004_wave2_3_atomic_match_submission.sql`, `0005_supa001_auth_trigger_hardening.sql`, dan `0006_wave5_functional_rpc.sql` dalam satu jendela pemeliharaan tertutup (sehingga trigger `0002` langsung ditimpa oleh versi hardened `0005` sebelum trafik user masuk), ditambah perintah `GRANT SELECT` / `REVOKE` standar Data API untuk `match_submission_requests`.
   - Lalu tandai versi `0002`, `0003`, `0004`, `0005`, `0006` sebagai `applied` (jika dijalankan manual via SQL Editor) atau verifikasi hasil `supabase db push` bila CLI dipakai setelah step #3.
5. **Post-Migration Verification (Read-Only):**
   - Pastikan `13` tabel `public` ber-RLS enabled, `"Users read active profiles"` sudah hilang, `"Profiles select own or admin"` aktif, 4 tabel yang sebelumnya kosong kini ber-policy, `on_auth_user_created` aktif pada `auth.users`, dan seluruh RPC `public.*` tersedia.
6. **Bootstrap `super_admin` & Akun Awal** sesuai Bagian 5.

---

## 8. Supabase Configuration Guide (Tanpa Secret di Repo)

Berdasarkan audit [config.py](file:///C:/Turnamen.in/backend/core/config.py), [client.py](file:///C:/Turnamen.in/backend/infrastructure/supabase/client.py), [factory.py](file:///C:/Turnamen.in/backend/repositories/factory.py), [app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js), dan [.env.example](file:///C:/Turnamen.in/.env.example):

- **Template Lokal (Sudah Ada & Tidak Ditimpa):** [.env.example](file:///C:/Turnamen.in/.env.example) tetap dipertahankan utuh.
- **Mekanisme Pemilihan Mode (`backend/core/config.py` & `factory.py`):**
  - Jika `.env` tidak ada atau `APP_MODE=mock`, aplikasi memakai `MockDataStoreRepository`.
  - Jika `APP_MODE=supabase`, `load_config()` mewajibkan `SUPABASE_URL` (`https://<project-ref>.supabase.co`) dan `SUPABASE_ANON_KEY`.
  - `API_HOST` dan `EEL_HOST` dikunci strictly ke `127.0.0.1` (`api_base_url` = `http://127.0.0.1:5000/api/v1`).
- **Perhatian Penting Tipe Key (`client.py:135-144`):**
  - Aplikasi memakai `supabase==2.7.4`. `validate_supabase_credentials()` **menolak** `service_role`, `sb_secret_*`, dan **`sb_publishable_*`**, serta mewajibkan **legacy public `anon` JWT key** (awalan `eyJ...` dari **Supabase Dashboard -> Project Settings -> API -> Project API keys -> `anon` `public`**).
- **Cara Pemilik Memasukkan Kredensial Secara Lokal:**
  1. Salin `.env.example` menjadi `.env` secara lokal (pastikan `.env` tetap berada dalam `.gitignore` dan tidak pernah di-commit).
  2. Isi:
     ```dotenv
     APP_MODE=supabase
     SECRET_KEY=<isi-string-acak-minimal-32-karakter-lokal>
     SUPABASE_URL=https://cfdsgxciodfkamskafwe.supabase.co
     SUPABASE_ANON_KEY=<salin-legacy-anon-public-JWT-eyJ...-dari-dashboard>
     ```
  3. Jalankan `.\.venv\Scripts\python.exe run.py --check` untuk memverifikasi `app_mode: "supabase"`, `supabase_configured: true`, dan `health_ok: true` tanpa mengekspos kunci rahasia.

---

## 9. Remaining Blockers

1. **Wave 4C GoTrue + PostgREST Integration Belum Teruji Secara Nyata:** Lingkungan lokal tidak memiliki `Docker` / `Podman` / `Rancher Desktop`, sehingga alur JWT issuer nyata, GoTrue signup/email confirmation, dan HTTP PostgREST gateway belum diuji runtime.
2. **Cloud Belum Dimigrasi & Belum Dikonfigurasi `.env` Lokal:** Project `cfdsgxciodfkamskafwe` masih berada pada kondisi `0001` + `seed.sql` (per `2026-11-26`), dan file `.env` valid belum tersedia di workspace pengguna.
3. **5 Profil Seeded `auth_user_id = NULL`:** Akun demo tidak dapat login di Cloud sebelum ditautkan via `link_profile_auth_user()` ke user Supabase Auth nyata.

---

## 10. Online Activation Readiness

- **Controlled Cloud Migration Readiness:** **`READY FOR CONTROLLED CLOUD MIGRATION`** (seluruh skrip `0001` sampai `0006` teruji di **PostgreSQL 17.11**, skema aktual Cloud telah direkonsiliasi lengkap, `0001` tidak dijalankan ulang, dan langkah bootstrap/rollback aman sudah siap dijalankan atas persetujuan pemilik).
- **Live Online Production Activation (`APP_MODE=supabase`):** Belum aktif sampai 4 langkah pasca-persetujuan selesai dijalankan secara berurutan:
  1. Eksekusi Forward-Only Reconciliation (`sync 0001` + terapkan `0002` sampai `0006`) pada database Cloud.
  2. Buat user Auth & jalankan `public.link_profile_auth_user(...)` untuk `super_admin` pertama (serta putuskan nasib 4 akun demo lainnya).
  3. Buat `.env` lokal dengan `APP_MODE=supabase` + legacy `anon` JWT key (`eyJ...`).
  4. Jalankan smoke test E2E nyata (`run.py --check`, login GoTrue, create tournament, staff assignment, bracket, match submit, announcements) terhadap Supabase Cloud / staging sebelum demonstrasi online.
