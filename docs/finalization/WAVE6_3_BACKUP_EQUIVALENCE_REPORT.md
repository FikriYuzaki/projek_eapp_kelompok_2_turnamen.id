# TURNAMEN.IN: WAVE 6.3 FINAL SCHEMA & DATA EQUIVALENCE REPORT

- **Tanggal Laporan:** 2026-11-26
- **Project Target:** `turnamen-in` (`cfdsgxciodfkamskafwe`, Region `ap-south-1`, PostgreSQL `17.11`)
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Status Akhir:** **`READY FOR EXPLICIT MIGRATION APPROVAL`**
- **Kepatuhan Keamanan & Batasan Mutlak:** Seluruh pengujian dilakukan 100% secara lokal pada cluster sementara PostgreSQL `17.11`. Tidak ada perubahan pada Supabase Cloud, tidak menjalankan `0002`-`0006`, `supabase db push`, `supabase migration repair`, perubahan Auth/role/RLS/konfigurasi Cloud, maupun `git commit`/`push`/`merge`/`reset`/`checkout`. File backup Cloud dan checksum dipertahankan utuh tanpa modifikasi.

---

## 1. Status Backup Cloud & Integritas Archive

### A. Logical Backup Aktual Supabase Cloud
- **Lokasi File:** `%LOCALAPPDATA%\TurnamenBackups\turnamen-in\turnamen-in-20261126-183150.dump`
- **Ukuran File:** `68,850` bytes
- **Format & Versi Tool:** PostgreSQL Custom Format (`1.16-0`), dibuat oleh `pg_dump (PostgreSQL) 17.11` dari server `17.11` (`2026-11-26 18:31:51`).
- **SHA-256 Terverifikasi:** `4B51A7A4CAFEACB1D43D9F3D15492F0B9E3B43C75C3A33DA7549A2A939D22459` (cocok 100% sebelum dan sesudah pengujian lokal).
- **Listing Archive (`turnamen-in-20261126-183150.dump.toc.txt`):** `166` total TOC entries (`159` selected TOC entries pada metadata), mencakup `1` schema (`public`), `2` functions, `12` tables + `12` table data, `26` PK/UNIQUE constraints, `27` indexes, `9` triggers, `27` FK constraints, `9` policies, `12` row security flags, ACLs, dan `6` default ACLs.

### B. Automated Backup & PITR (Supabase Dashboard)
- **Status Pemeriksaan Dashboard (`Database -> Backups`):** Tidak dapat diakses dari sesi CLI agen karena tidak ada login Dashboard.
- Ketersediaan backup otomatis harian, waktu snapshot terbaru, paket project, dan status **PITR** harus tetap dikonfirmasi langsung oleh pemilik project di Supabase Dashboard sebelum mengeksekusi maintenance window migrasi sesuai [WAVE6_2_CLOUD_DEPLOYMENT_RUNBOOK.md](file:///C:/Turnamen.in/docs/finalization/WAVE6_2_CLOUD_DEPLOYMENT_RUNBOOK.md).

---

## 2. Pengujian Restore & Setup Dua Database Lokal PostgreSQL 17.11

Pengujian dijalankan pada cluster sementara terisolasi (`127.0.0.1`) memakai binary resmi **PostgreSQL 17.11** (`%LOCALAPPDATA%\TurnamenBackups\tools\postgresql-17.11\pgsql\bin`):

1. **Database A (`db_a_cloud_restore`):**
   - Dibuat kosong pada PG `17.11`, `DROP SCHEMA IF EXISTS public CASCADE;` dijalankan agar pernyataan `CREATE SCHEMA public;` di dalam dump berjalan bersih, lalu dilengkapi stub minimal Supabase (`anon`, `authenticated`, `service_role`, `supabase_admin`, schema `auth`, `auth.users`, `auth.uid()`, `auth.role()`).
   - Direstorasi dari `turnamen-in-20261126-183150.dump` menggunakan `pg_restore.exe --exit-on-error --verbose`.
   - **Hasil:** **`exit code = 0`**, `0` baris `ERROR` maupun `WARNING` di stderr (`160` baris log verbose), `12` tabel dan `59` baris terpulihkan lengkap.
2. **Database B (`db_b_baseline`):**
   - Dibuat kosong pada cluster PG `17.11` yang sama, dilengkapi stub minimal Supabase/Auth yang sama (tanpa `supabase_admin` default ACL karena tidak didefinisikan oleh `0001`), lalu dieksekusi berurutan [0001_initial_schema.sql](file:///C:/Turnamen.in/supabase/migrations/0001_initial_schema.sql) dan [seed.sql](file:///C:/Turnamen.in/supabase/seed.sql) via `psql.exe -v ON_ERROR_STOP=1`.
   - **Hasil:** **`exit code = 0`**, `12` tabel dan `59` baris terbentuk lengkap.
3. **Cleanup Cluster Sementara:**
   - Cluster PostgreSQL `17.11` sementara dihentikan dengan aman menggunakan `pg_ctl.exe -m fast -w stop` (`exit code = 0`) dan seluruh direktori sementara telah dihapus.

*(Catatan diagnosis eksekusi: Pada percobaan awal, `compare_db_a_vs_db_b.py` sempat tertahan di `pg_ctl start` karena `postgres.exe` di Windows mewarisi handle pipe stdout/stderr dari `subprocess.run(capture_output=True)`. Skrip diperbaiki menggunakan `DEVNULL` + `DETACHED_PROCESS` untuk `pg_ctl start`, flush progres per tahap, serta timeout eksplisit pada setiap subprocess dan query, lalu seluruh perbandingan selesai dalam 9 detik.)*

---

## 3. Perbandingan Detail Skema (Database A vs Database B)

| Kategori Objek | Database A (Cloud Restore) | Database B (`0001` + `seed.sql`) | Hasil Perbandingan |
| :--- | :---: | :---: | :--- |
| **Tables (`public`)** | `12` | `12` | **MATCH 100%** (`activity_logs`, `announcements`, `games`, `match_results`, `matches`, `payments`, `profiles`, `registrations`, `team_members`, `teams`, `tournament_staff`, `tournaments`) |
| **Columns & Order** | `142` | `142` | **MATCH 100%** (urutan `attnum`, nama kolom, tipe data, panjang/presisi, `NOT NULL`, dan `column_default` identik pada seluruh 142 kolom) |
| **Primary Key (`p`)** | `12` | `12` | **MATCH 100%** (`<table>_pkey`) |
| **Foreign Key (`f`)** | `27` | `27` | **MATCH 100%** (`ON UPDATE` & `ON DELETE` identik) |
| **Unique Constraints (`u`)** | `14` | `14` | **MATCH 100%** (termasuk `uq_tournament_seed`, `uq_tournament_team_registration`, `uq_tournament_round_match`, `uq_match_game_number`, `uq_team_member_ingame`, `uq_tournament_staff_assignment`) |
| **Check Constraints (`c`)** | `30` | `30` | **21 MATCH 100%, 9 perbedaan sintaks deparse `ARRAY`** (semantik & daftar nilai enum identik 100%, lihat Bagian 6) |
| **Indexes (`pg_indexes`)** | `53` | `53` | **MATCH 100%** (nama dan `indexdef` identik pada seluruh 53 indeks) |
| **Application Functions (`public`)** | `2` | `2` | **Semantik MATCH 100%** (`current_user_role()`, `set_updated_at()`; hanya berbeda line ending `\r\n` vs `\n` pada `prosrc`, lihat Bagian 6) |
| **Extension Functions in `public`** | `0` (`pgcrypto` di schema platform `extensions`) | `36` (`pgcrypto` v1.3 di `public`) | **Perbedaan lokasi ekstensi platform** (`extensions` vs `public`, lihat Bagian 5 & 6) |
| **Triggers (`public`)** | `9` | `9` | **MATCH 100%** (`trg_*_updated_at`, `BEFORE UPDATE FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()`) |
| **RLS Enabled Tables** | `12` (`true`) | `12` (`true`) | **MATCH 100%** (`force_rls = false` pada kedua DB) |
| **RLS Policies (`pg_policies`)** | `9` | `9` | **MATCH 100%** (`7` kebijakan `Public read *`, `"Users read active profiles"`, `"Super admin full access profiles"`; `4` tabel tanpa policy: `activity_logs`, `payments`, `registrations`, `tournament_staff`) |
| **Table Grants & Default ACLs** | `48` grants (`postgres`, `anon`, `authenticated`, `service_role`), `6` default ACLs | `12` grants (`postgres`), `0` default ACLs | **Perbedaan default privilege platform Supabase** (lihat Bagian 5 & 6) |

---

## 4. Perbandingan Data Per Tabel (`59` Baris Total)

*(Tidak ada email, nomor telepon, atau konten PII yang dicetak pada laporan ini.)*

Perbandingan dilakukan baris-per-baris berdasarkan `id` (UUID) untuk seluruh `12` tabel (`59` baris):
- **Kolom non-dinamis (termasuk timestamp bisnis eksplisit pada `seed.sql` seperti `start_date`, `end_date`, `registration_start`, `registration_end`, `registrations.verified_at`, `payments.verified_at`, `matches.scheduled_at`, `matches.completed_at`, dan `announcements.published_at`):** **MATCH 100%** (`0` ID hilang, `0` ID tambahan, `0` selisih nilai kolom pada seluruh `59` baris).
- **Kolom timestamp dinamis `DEFAULT NOW()`:** Dipisahkan secara eksplisit. Seluruh baris di Database A memiliki nilai `2026-11-12T14:38:40.575559+00:00` (waktu eksekusi awal `seed.sql` di Cloud), sedangkan Database B memiliki timestamp saat eksekusi lokal `2026-11-26T12:25:31.*+00:00`. Tidak ada perbedaan data yang tidak terjelaskan.

| Tabel | Baris DB A | Baris DB B | Match Kolom Non-Dinamis | Kolom `DEFAULT NOW()` | Nilai DB A (Cloud) | Nilai DB B (Lokal `2026-11-26`) |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| `activity_logs` | `2` | `2` | **100% MATCH** | `created_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.586310+00:00` |
| `announcements` | `2` | `2` | **100% MATCH** | `created_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.583011+00:00` |
| `games` | `3` | `3` | **100% MATCH** | `created_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.536456+00:00` |
| `match_results` | `3` | `3` | **100% MATCH** | `created_at`, `verified_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.574778+00:00` |
| `matches` | `7` | `7` | **100% MATCH** | `created_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.568106+00:00` |
| `payments` | `1` | `1` | **100% MATCH** | `created_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.578676+00:00` |
| `profiles` | `5` | `5` | **100% MATCH** | `created_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.528506+00:00` |
| `registrations` | `8` | `8` | **100% MATCH** | `registered_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.561123+00:00` |
| `team_members` | `16` | `16` | **100% MATCH** | `created_at`, `joined_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.556231+00:00` |
| `teams` | `8` | `8` | **100% MATCH** | `created_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.550894+00:00` |
| `tournament_staff` | `2` | `2` | **100% MATCH** | `assigned_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.546783+00:00` |
| `tournaments` | `2` | `2` | **100% MATCH** | `created_at`, `updated_at` | `2026-11-12T14:38:40.575559+00:00` | `2026-11-26T12:25:31.539719+00:00` |

*(Catatan penting data profil: kelima baris di `public.profiles` memiliki `auth_user_id = NULL` pada Cloud maupun `seed.sql`.)*

---

## 5. Pemisahan Objek Aplikasi, Objek Platform Supabase, dan Stub Auth Lokal

### A. Objek Aplikasi (`public`) vs Objek Platform Supabase
- **Objek Aplikasi (`0001_initial_schema.sql`):** `12` tabel, `142` kolom, `83` constraints, `53` indexes, `2` fungsi (`public.set_updated_at()`, `public.current_user_role()`), `9` triggers `trg_*_updated_at`, `12` konfigurasi RLS table, `9` RLS policies, serta `59` baris data seed.
- **Objek Khusus Platform Supabase (Ada di Dump/Cloud, Bukan Objek Aplikasi):**
  - Grant eksplisit schema `public`, `2` fungsi, dan `12` tabel kepada role Data API (`anon`, `authenticated`, `service_role`).
  - `6` entri `ALTER DEFAULT PRIVILEGES` untuk role `postgres` dan `supabase_admin` (sequences, functions, tables di schema `public`).
  - Penempatan ekstensi `pgcrypto` pada schema managed `extensions` (tidak ikut terekspor ke dalam dump `--schema=public`).

### B. Stub Auth & Role Selama Restore Test Lokal
Agar archive Cloud `--schema=public` dapat direstorasi tanpa error pada PostgreSQL `17.11` lokal polos, stub minimal berikut dipasang sebelum `pg_restore`:
- **Roles:** `anon`, `authenticated`, `service_role` (`BYPASSRLS`), dan `supabase_admin` (`SUPERUSER`, dibutuhkan oleh pernyataan `ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin` di dalam dump).
- **Schema & Objek `auth`:** Schema `auth`, tabel minimal `auth.users`, serta fungsi `auth.uid()` (direferensikan oleh `public.current_user_role()`) dan `auth.role()`.

### C. Batasan Cakupan Pengujian Lokal
Pengujian lokal ini **hanya** membuktikan integritas archive dump, keberhasilan restore PostgreSQL `17.11`, serta kesetaraan struktur skema dan data `public`. Pengujian ini **tidak** membuktikan dan **tidak** menguji perilaku runtime layanan **GoTrue** (signup, verifikasi email, penerbitan JWT, trigger `auth.users`) maupun penegakan **PostgREST + RLS** secara HTTP langsung terhadap Supabase Cloud.

---

## 6. Analisis Perbedaan yang Ditemukan

| No | Objek yang Berbeda | Kondisi Cloud (DB A) | Kondisi Baseline (DB B) | Dampak Potensial | Perlu Perbaikan Sebelum Migrasi? |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | **9 `CHECK` constraint dengan `ARRAY[...]`** (`announcements_priority_check`, `matches_next_slot_check`, `matches_status_check`, `payments_status_check`, `profiles_role_check`, `registrations_status_check`, `team_members_member_role_check`, `tournament_staff_staff_role_check`, `tournaments_status_check`) | `pg_get_constraintdef` menampilkan cast per elemen `ARRAY['...'::character varying::text, ...]` karena round-trip deparse `pg_dump` -> `pg_restore` | `pg_get_constraintdef` menampilkan cast array `ARRAY['...'::character varying, ...]::text[]` | **Nol dampak.** Logika evaluasi SQL dan himpunan nilai yang diizinkan identik 100%. | **Tidak** |
| 2 | **Line ending `prosrc` pada `public.current_user_role()` dan `public.set_updated_at()`** | Body `prosrc` mengandung `\r\n` (CRLF) dari eksekusi awal melalui SQL Editor | Body `prosrc` mengandung `\n` (LF) dari `psql -f` | **Nol dampak.** Tanda tangan, bahasa, volatilitas, `SECURITY DEFINER`, `search_path=public`, dan logika SQL identik 100%. Kedua fungsi juga akan diperbarui/diperketat oleh migrasi `0002` & `0005`. | **Tidak** |
| 3 | **Lokasi ekstensi `pgcrypto` (`0` vs `36` fungsi di `public`)** | `pgcrypto` dikelola Supabase di schema `extensions`; `gen_random_uuid()` tersedia built-in di `pg_catalog` PG 17 | `CREATE EXTENSION IF NOT EXISTS "pgcrypto"` di `0001` memasang `36` fungsi `pgcrypto` ke schema `public` | **Nol dampak** untuk migrasi `0002`-`0006` (tidak ada migrasi lanjutan yang mengasumsikan `pgcrypto` berada di `public`). Menegaskan bahwa `0001` tidak boleh dijalankan ulang mentah di Cloud dan harus ditandai via `migration repair` setelah persetujuan. | **Tidak** |
| 4 | **Table grants (`anon`, `authenticated`, `service_role`) & Default ACL (`postgres`, `supabase_admin`)** | `48` table grants dan `6` default ACL aktif sesuai standar platform Supabase Data API | `12` table grants (`postgres` saja) dan `0` default ACL karena cluster PG lokal polos | **Dampak platform wajar.** Catatan keamanan baseline `0001`: policy lama `"Users read active profiles"` masih aktif di Cloud dan `4` tabel (`activity_logs`, `payments`, `registrations`, `tournament_staff`) masih tanpa policy. Kondisi ini memang merupakan target perbaikan oleh migrasi `0002` dan `0005`. | **Tidak** (diselesaikan langsung saat paket migrasi `0002`-`0006` disetujui & dijalankan) |
| 5 | **Kolom timestamp `DEFAULT NOW()` pada `59` baris data** | Terisi `2026-11-12T14:38:40.575559+00:00` (waktu seed Cloud) | Terisi `2026-11-26T12:25:31.*+00:00` (waktu eksekusi lokal) | **Nol dampak.** Perilaku normal kolom `DEFAULT NOW()`. | **Tidak** |

---

## 7. Kesimpulan & Status Akhir

- **Backup Cloud Aktual:** Tersimpan utuh, SHA-256 terverifikasi (`4B51A7A4CAFEACB1D43D9F3D15492F0B9E3B43C75C3A33DA7549A2A939D22459`), dan teruji restore dengan **`exit code = 0`** pada PostgreSQL `17.11` (`12` tabel, `59` baris).
- **Ekuivalensi Skema & Data (`DB A` vs `DB B`):** Seluruh `12` tabel, `142` kolom, `83` constraints, `53` indexes, `2` fungsi aplikasi, `9` triggers, `12` RLS flags, `9` policies, dan `59` baris data non-dinamis **ekuivalen 100%** dengan [0001_initial_schema.sql](file:///C:/Turnamen.in/supabase/migrations/0001_initial_schema.sql) dan [seed.sql](file:///C:/Turnamen.in/supabase/seed.sql). Tidak ditemukan selisih skema atau data yang belum terjelaskan maupun blocker sebelum migrasi.
- **Status Akhir:** **`READY FOR EXPLICIT MIGRATION APPROVAL`**

### Catatan Pra-Eksekusi Saat Pemilik Memberikan Persetujuan Migrasi
1. Konfirmasi ketersediaan backup otomatis / PITR di **Supabase Dashboard -> Database -> Backups** sebelum maintenance window dimulai.
2. Ikuti urutan [WAVE6_2_CLOUD_DEPLOYMENT_RUNBOOK.md](file:///C:/Turnamen.in/docs/finalization/WAVE6_2_CLOUD_DEPLOYMENT_RUNBOOK.md): blokir public signup terlebih dahulu, tandai `0001` via `supabase migration repair --status applied 0001` (tanpa menjalankan ulang `0001` dan tanpa `--include-seed`), lalu terapkan `0002` sampai `0006` dalam satu jendela pemeliharaan tertutup.
3. Setelah migrasi selesai, lakukan bootstrap akun `super_admin` dan pengujian runtime live GoTrue + PostgREST/RLS sebelum membuka kembali pendaftaran publik.
