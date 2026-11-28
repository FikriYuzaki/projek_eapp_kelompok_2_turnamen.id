# TURNAMEN.IN: WAVE 6.5 PRODUCTION DEPLOYMENT REPORT

- **Tanggal Deployment:** 2026-11-26 (`2026-11-26T14:20:47Z` s/d `2026-11-26T14:22:40Z` UTC)
- **Project Ref:** `cfdsgxciodfkamskafwe` (`turnamen-in`, Region `ap-south-1`, PostgreSQL `17.11`)
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Supabase CLI:** `2.104.0`
- **Sumber Bukti Utama:** `wave65_deploy_result.json` (`status: DEPLOYED_AND_VERIFIED`, `error_message: null`)
- **Status Akhir Wave 6.5:** **`DEPLOYMENT SUCCESSFUL`**

---

## 1. Informasi Backup Cloud (Dipertahankan Utuh)

- **Lokasi File Backup:** `%LOCALAPPDATA%\TurnamenBackups\turnamen-in\turnamen-in-20261126-183150.dump`
- **Ukuran File:** `68,850` bytes
- **SHA-256 Terverifikasi:** `4B51A7A4CAFEACB1D43D9F3D15492F0B9E3B43C75C3A33DA7549A2A939D22459` (`backup_sha256_ok: true`)
- **Status Restore Test (Wave 6.3):** Teruji lokal pada PostgreSQL `17.11` (`12` tabel, `59` baris, `exit code = 0`).

---

## 2. Ringkasan Eksekusi Deployment (`0001`-`0006`)

Seluruh rangkaian migrasi **`0001`-`0006`** kini resmi tercatat dan diterapkan pada Supabase Cloud melalui Session Pooler (`aws-0-ap-south-1.pooler.supabase.com:5432`, SSL `require`, tanpa menyimpan password di URL, file, log, maupun `.env`):

| Tahap | Hasil Aktual | Bukti dari `wave65_deploy_result.json` | Status |
| :--- | :---: | :--- | :---: |
| **Preflight Lokal** | `exit 0` | Branch `feature/fikri-ui-ux`, `6` file migrasi (`0001`-`0006`), `backup_sha256_ok: true` | **PASS** |
| **Preflight Cloud Read-Only** | `exit 0` | `cloud_history_existed: false`, `12` public tables, `9` policies, `0` duplikat `LOWER(email)`, `1` Auth user terverifikasi cocok dengan profil `super_admin` unlinked, `0` linked profiles | **PASS** |
| **Repair `0001`** | `rc = 0` | `Repaired migration history: [0001] => applied`; `schema_migrations` terisi `0001` (`initial_schema`), sementara `12` tabel, `9` policy, dan `5` profil tetap utuh (`skipped: false`) | **PASS** |
| **Dry-Run Push** | `rc = 0` | Mendeteksi tepat `0002_security_hardening.sql` s/d `0006_wave5_functional_rpc.sql` (tanpa `0001` dan tanpa `seed.sql`) | **PASS** |
| **Persetujuan & `db push`** | `rc = 0` | Konfirmasi eksplisit `DEPLOY` + `[Y/n] y`; menerapkan `0002 -> 0003 -> 0004 -> 0005 -> 0006` berurutan (`Finished supabase db push.`) | **PASS** |

---

## 3. Hasil Verifikasi Aktual Pasca-Deployment (Supabase Cloud)

### A. Ringkasan Kepatuhan Inti
| Item Verifikasi | Hasil Aktual Cloud | Target | Status |
| :--- | :--- | :--- | :---: |
| **Migration History (`supabase_migrations.schema_migrations`)** | **`6` baris** (`0001` `initial_schema`, `0002` `security_hardening`, `0003` `wave2_rls_compatibility`, `0004` `wave2_3_atomic_match_submission`, `0005` `supa001_auth_trigger_hardening`, `0006` `wave5_functional_rpc`), tanpa duplikat | `0001`-`0006` (`6` baris) | **PASS** |
| **Public Tables dengan RLS Aktif** | **`13` tabel**, seluruhnya `rls_enabled = true` (`12` tabel inti + `match_submission_requests`) | `13` tabel RLS aktif | **PASS** |
| **RLS Policies (`pg_policies`)** | **`43` policies** terpasang; policy lama `"Users read active profiles"` dan `"Profiles select own or staff"` hilang; `"Profiles select own or admin"` aktif | Least-privilege RLS `0002`-`0005` | **PASS** |
| **Auth Trigger Migration `0005` (`handle_new_auth_user`)** | **`auth_trigger_has_23505_reject: true`**, **`auth_trigger_has_autolink_update: false`**, **`auth_trigger_locked_search_path: true`** | SQLSTATE `23505` aktif & auto-link email nonaktif | **PASS** |
| **Linked Profiles (`auth_user_id IS NOT NULL`)** | **`0`** (akun `super_admin` sengaja belum ditautkan) | `0` pada tahap ini | **PASS** |
| **Status Public Signup** | **Tetap `DISABLED`** (tidak diubah selama maupun sesudah migrasi) | `DISABLED` | **PASS** |
| **Data Seed Existing (`12` Tabel Awal)** | **`59` baris utuh** (`activity_logs`: 2, `announcements`: 2, `games`: 3, `match_results`: 3, `matches`: 7, `payments`: 1, `profiles`: 5, `registrations`: 8, `team_members`: 16, `teams`: 8, `tournament_staff`: 2, `tournaments`: 2) + `match_submission_requests`: `0` | `59` baris lama tidak berubah | **PASS** |

### B. Rincian Policies Per Tabel (`43` Total)
- `activity_logs` (`2`): `Authenticated insert own activity_logs` (`INSERT`), `Authorized read activity_logs` (`SELECT`)
- `announcements` (`4`): `Public read announcements` (`SELECT`, `anon`/`authenticated`), `Staff or admin delete/insert/update announcements` (`authenticated`)
- `games` (`2`): `Public read games` (`SELECT`, `anon`/`authenticated`), `Super admin manage games` (`ALL`, `authenticated`)
- `match_results` (`4`): `Public read match_results` (`SELECT`, `anon`/`authenticated`), `Staff or admin insert/update match_results` (`authenticated`), `Admin delete match_results` (`DELETE`, `authenticated`)
- `match_submission_requests` (`1`): `Staff or self read match_submission_requests` (`SELECT`, `authenticated`)
- `matches` (`4`): `Public read matches` (`SELECT`, `anon`/`authenticated`), `Staff or admin insert/update/delete matches` (`authenticated`)
- `payments` (`3`): `Authorized read payments` (`SELECT`), `Captain or admin insert payments` (`INSERT`), `Staff or admin update payments` (`UPDATE`)
- `profiles` (`4`): `Profiles insert self registration` (`INSERT`), `Profiles select own or admin` (`SELECT`), `Profiles update own` (`UPDATE`), `Super admin full access profiles` (`ALL`)
- `registrations` (`5`): `Public read approved registrations` (`SELECT`, `anon`/`authenticated`), `Participants and staff read registrations` (`SELECT`), `Captain or admin insert registrations` (`INSERT`), `Staff or admin update registrations` (`UPDATE`), `Admin delete registrations` (`DELETE`)
- `team_members` (`4`): `Public read team_members` (`SELECT`, `anon`/`authenticated`), `Captain or admin insert/update/delete team_members` (`authenticated`)
- `teams` (`4`): `Public read teams` (`SELECT`, `anon`/`authenticated`), `Captain or admin insert/update teams` (`authenticated`), `Admin delete teams` (`DELETE`)
- `tournament_staff` (`2`): `Organizer or admin manage tournament_staff` (`ALL`), `Staff or organizer read tournament_staff` (`SELECT`)
- `tournaments` (`4`): `Public read tournaments` (`SELECT`, `anon`/`authenticated`), `Organizer or admin insert/update/delete tournaments` (`authenticated`)

### C. Triggers & Indexes Terverifikasi (`11` Triggers, `8` Indexes pada `profiles`)
- **Triggers (`11` total):**
  - `auth.users`: `on_auth_user_created` (`AFTER INSERT`)
  - `public.profiles`: `trg_prevent_profile_privilege_escalation` (`BEFORE UPDATE`), `trg_profiles_updated_at` (`BEFORE UPDATE`)
  - `9` tabel domain (`announcements`, `games`, `matches`, `payments`, `profiles`, `registrations`, `team_members`, `teams`, `tournaments`): masing-masing `trg_*_updated_at` (`BEFORE UPDATE`)
- **Indexes `public.profiles` (`8` total):** `idx_profiles_auth_user_id`, `idx_profiles_email`, `idx_profiles_role`, `profiles_auth_user_id_key`, `profiles_email_key`, `profiles_pkey`, `profiles_username_key`, `uq_profiles_lower_email`.

### D. Fungsi & RPC (`27` Fungsi: `9` `private.*`, `18` `public.*`)
Seluruh `27` fungsi di `wave65_deploy_result.json` memiliki **`config = ["search_path=\"\""]`** dan **`public_exec = false`**:
- **Schema `private` (`9` fungsi, seluruhnya `SECURITY DEFINER`, `anon_exec = false`):**
  - `auth_exec = true, service_exec = true`: `assign_user_role`, `link_profile_auth_user`, `list_committee_candidates`, `list_tournament_staff`
  - `auth_exec = true, service_exec = false`: `get_public_profile_summary`, `register_team_atomic`, `submit_match_result_atomic`, `transition_tournament_status`
  - `auth_exec = false, service_exec = false`: `validate_tournament_bracket_integrity` (helper internal `0004`)
- **Schema `public` (`18` fungsi):**
  - `anon_exec = true, auth_exec = true, service_exec = true` (tepat `2` fungsi yang diizinkan untuk `anon`): `current_user_role()` (`SECURITY DEFINER`), `list_tournament_announcements(UUID)` (`SECURITY DEFINER`)
  - `anon_exec = false, auth_exec = true, service_exec = true` (`13` fungsi): helper RLS `SECURITY DEFINER` (`current_profile_id`, `is_team_captain`, `is_tournament_committee`, `is_tournament_organizer`) dan wrapper RPC `SECURITY INVOKER` (`assign_user_role`, `get_public_profile_summary`, `link_profile_auth_user`, `list_committee_candidates`, `list_tournament_staff`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`, `transition_tournament_status`)
  - `anon_exec = false, auth_exec = false, service_exec = true` (`3` fungsi trigger): `handle_new_auth_user()` (`SECURITY DEFINER`), `prevent_profile_privilege_escalation()` (`SECURITY INVOKER`), `set_updated_at()` (`SECURITY INVOKER`)

---

## 4. Pemisahan Status Pemeriksaan (PASS vs Belum Dilakukan vs Perlu Verifikasi)

### A. Pemeriksaan yang Sudah PASS (Dengan Bukti Aktual)
- Preflight lokal (`feature/fikri-ui-ux`, 6 migrasi `0001`-`0006`, backup `.dump` SHA-256 `4B51A7A4...22459`).
- Preflight Cloud read-only (`12` tabel, `9` policies, `0` duplikat email, `1` Auth user cocok dengan profil `super_admin` terverifikasi dan belum tertaut).
- `supabase migration repair 0001 --status applied` (`rc=0`), `supabase db push --dry-run` (`rc=0`), dan `supabase db push` `0002`-`0006` (`rc=0`).
- Verifikasi post-deployment atas `schema_migrations` (`6` baris `0001`-`0006`), `13` tabel ber-RLS aktif, `43` policies, `11` triggers, `27` fungsi (`search_path=""` & `EXECUTE` grants), `uq_profiles_lower_email`, `59` baris data seed lama utuh + `0` baris `match_submission_requests`, `0` linked profiles, dan implementasi aman `handle_new_auth_user()` (`23505` aktif, auto-link nonaktif).

### B. Langkah yang Sengaja Belum Dilakukan (Sesuai Batas Henti Wave 6.5)
- **Linking eksplisit profil `super_admin` (`private.link_profile_auth_user`):** Belum dijalankan (`profiles_auth_linked_count = 0`); menunggu instruksi/gelombang selanjutnya sesudah laporan Wave 6.5 ini ditinjau.
- **Pembukaan kembali Public Signup:** Sengaja dipertahankan **`DISABLED`**; tidak boleh diaktifkan sebelum proses linking `super_admin` dan pemeriksaan keamanan lanjutan selesai.

### C. Pemeriksaan yang Masih Perlu Diverifikasi
1. **Security Advisors (Supabase Dashboard / Management API):** Belum dijalankan pada Wave 6.5 karena sesi agen dan skrip CLI memakai koneksi Postgres langsung (`--db-url`) tanpa `SUPABASE_ACCESS_TOKEN` atau login Dashboard. Pemilik project perlu memeriksa **Supabase Dashboard -> Project `cfdsgxciodfkamskafwe` -> Advisors -> Security Advisor** setelah migrasi ini.
2. **Inspeksi Langsung `role_table_grants` & Constraint `fk_profiles_auth_user_id` di Cloud:** Kueri verifikasi skrip belum mencetak ulang `information_schema.role_table_grants` (khususnya `match_submission_requests` untuk `anon`/`authenticated`) dan `pg_constraint` `fk_profiles_auth_user_id` di Cloud pasca-push (sudah teruji pada simulasi PG `17.11` di Wave 6.4, dapat dikonfirmasi cepat dengan query read-only bila diperlukan).
3. **Verifikasi Runtime GoTrue Auth, PostgREST RLS, & Klien Desktop (`APP_MODE=supabase`):** Belum diuji secara live; baru dapat dijalankan pada gelombang berikutnya setelah `super_admin` dihubungkan secara eksplisit via `link_profile_auth_user`.

---

## 5. Status Akhir

- **Status Akhir Wave 6.5:** **`DEPLOYMENT SUCCESSFUL`**
- **Tindakan Berikutnya (Menunggu Instruksi Terpisah):**
  1. Periksa **Security Advisors** di Supabase Dashboard dan konfirmasi hasilnya.
  2. Lakukan linking eksplisit akun `super_admin` via `private.link_profile_auth_user` / `public.link_profile_auth_user` (tetap pertahankan public signup `DISABLED` sampai seluruh verifikasi pasca-linking selesai).
