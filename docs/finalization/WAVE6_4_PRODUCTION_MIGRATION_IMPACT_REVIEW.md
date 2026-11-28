# TURNAMEN.IN: WAVE 6.4 PRODUCTION MIGRATION IMPACT REVIEW

- **Tanggal Audit:** 2026-11-26
- **Project Target:** `turnamen-in` (`cfdsgxciodfkamskafwe`, Region `ap-south-1`, PostgreSQL `17.11`)
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Supabase CLI Teruji:** `2.104.0`
- **Status Akhir:** **`READY FOR EXPLICIT MIGRATION APPROVAL`**
- **Kepatuhan Batasan Mutlak:** Seluruh verifikasi dijalankan secara lokal pada cluster sementara PostgreSQL `17.11` menggunakan hasil restore backup Cloud aktual. Tidak ada eksekusi ke Supabase Cloud (`db push`, `migration repair`, perubahan Auth/RLS/role/konfigurasi), tidak ada perubahan pada file migrasi `0001`-`0006`, tidak ada pembuatan `.env`, dan tidak ada operasi Git mutatif.

---

## 1. Ringkasan Eksekutif & Bukti Simulasi Lokal pada Backup Cloud

Berdasarkan pembacaan langsung atas [0002_security_hardening.sql](file:///C:/Turnamen.in/supabase/migrations/0002_security_hardening.sql) sampai [0006_wave5_functional_rpc.sql](file:///C:/Turnamen.in/supabase/migrations/0006_wave5_functional_rpc.sql) serta simulasi replay lokal pada PostgreSQL `17.11` di atas hasil restore backup Cloud `turnamen-in-20261126-183150.dump` (SHA-256 `4B51A7A4CAFEACB1D43D9F3D15492F0B9E3B43C75C3A33DA7549A2A939D22459`):

1. **`supabase migration repair --status applied 0001` hanya memodifikasi metadata histori:** Pada DB simulasi hasil restore dump Cloud, tabel `supabase_migrations.schema_migrations` awalnya `NULL`. Setelah `migration repair` (`rc=0`), hanya `supabase_migrations.schema_migrations` yang dibuat dan diisi 1 baris `('0001', 'initial_schema')`; `12` tabel aplikasi, `59` baris data, dan `9` policy awal tetap utuh.
2. **`supabase db push` `0002`-`0006` berhasil bersih (`rc=0`):** Seluruh `5` migrasi berjalan berurutan di PostgreSQL `17.11` tanpa konflik dengan objek `0001` maupun `ALTER DEFAULT PRIVILEGES` milik Cloud. Seluruh `59` baris data pada `12` tabel awal tetap utuh, dan tabel baru `public.match_submission_requests` terbentuk dengan `0` baris dan RLS aktif.
3. **Temuan kritis mekanisme transaksi CLI (`supabase db push`):** Uji kegagalan terarah membuktikan bahwa `supabase db push` mengeksekusi **setiap file migrasi dalam transaksi terpisah**, bukan satu transaksi global. Ketika `0003` gagal di tengah push, `0003` di-rollback, tetapi **`0002` tetap ter-commit**. Oleh karena itu, penonaktifan public signup sebelum deployment wajib dilakukan agar celah `SUPA-001` pada `0002` tidak pernah terbuka bila terjadi kegagalan parsial sebelum `0005` selesai.

---

## 2. Audit Detail Setiap Migration (`0002` sampai `0006`)

| File | Objek Dibuat / Diubah / Dihapus | Perubahan Tabel, Kolom, Constraint, Index, Trigger, & RLS | Pengaruh ke Data Existing & Konflik Cloud | Dependensi & Keamanan Eksekusi PG 17.11 |
| :--- | :--- | :--- | :--- | :--- |
| [0002_security_hardening.sql](file:///C:/Turnamen.in/supabase/migrations/0002_security_hardening.sql) | **Index & FK:** `idx_profiles_auth_user_id`, `fk_profiles_auth_user_id`. **Functions (8):** `current_profile_id()`, `current_user_role()`, `is_tournament_organizer(UUID)`, `is_tournament_committee(UUID)`, `is_team_captain(UUID)`, `prevent_profile_privilege_escalation()`, `handle_new_auth_user()`, `replace_tournament_matches(UUID, JSONB)`. **Triggers (2):** `trg_prevent_profile_privilege_escalation`, `on_auth_user_created` (`auth.users`). **Policies:** `DROP POLICY IF EXISTS` pada seluruh `9` policy `0001` lalu membuat `42` policy baru di `12` tabel. | Tidak menambah/mengubah kolom atau menghapus tabel. Menambah FK `profiles.auth_user_id -> auth.users(id) ON DELETE SET NULL` (guarded `IF NOT EXISTS`). Mengaktifkan kembali RLS di `12` tabel dan menutup 4 tabel yang sebelumnya tanpa policy (`tournament_staff`, `registrations`, `payments`, `activity_logs`). | **Aman terhadap 59 baris existing:** Tidak ada `TRUNCATE`/`DELETE`/`UPDATE` data. `5` profil seeded (`auth_user_id = NULL`) lolos `fk_profiles_auth_user_id`. Seluruh `DROP` memakai `IF EXISTS` sehingga bebas konflik. | Bergantung pada `0001` dan `auth.users`. Aman pada PG `17.11`, **namun masih memuat logika auto-link email SUPA-001 yang baru ditutup oleh `0005`**. |
| [0003_wave2_rls_compatibility.sql](file:///C:/Turnamen.in/supabase/migrations/0003_wave2_rls_compatibility.sql) | **Schema:** `private` (`REVOKE ALL FROM PUBLIC, anon`; `GRANT USAGE TO authenticated`). **Functions (6):** pasangan `private.*` (`SECURITY DEFINER`, `search_path = ''`) dan wrapper `public.*` (`SECURITY INVOKER`) untuk `transition_tournament_status(UUID, VARCHAR)`, `get_public_profile_summary(UUID, UUID)`, dan `register_team_atomic(UUID, UUID, TEXT)`. | Tidak mengubah tabel, kolom, constraint, index, trigger, atau policy tabel. Mencabut hak `EXECUTE` dari `PUBLIC` & `anon` dan memberi `EXECUTE` ke `authenticated`. | **Nol dampak ke 59 baris data existing.** Tidak bentrok dengan objek `0001` maupun `0002` (`DROP FUNCTION IF EXISTS` signature lama `get_public_profile_summary(UUID)` aman). | Bergantung pada tabel `0001` dan konteks RLS `0002`. Aman berurutan pada PG `17.11`. |
| [0004_wave2_3_atomic_match_submission.sql](file:///C:/Turnamen.in/supabase/migrations/0004_wave2_3_atomic_match_submission.sql) | **Table (1):** `public.match_submission_requests` + `uq_match_submission_idempotency` + `idx_match_submission_requests_match_id`. **Policy (1):** `"Staff or self read match_submission_requests"` (`SELECT`, `authenticated`). **Functions (4):** `private.validate_tournament_bracket_integrity(...)`, upgrade `private.transition_tournament_status(...)`, serta pasangan `private`/`public.submit_match_result_atomic(...)`. | Menambah 1 tabel ke-13 (`match_submission_requests`) dengan RLS aktif, `REVOKE ALL FROM PUBLIC, anon`, `REVOKE INSERT, UPDATE, DELETE FROM authenticated`, `GRANT SELECT TO authenticated`. | **Aman terhadap 59 baris existing.** `submit_match_result_atomic` memakai `ON CONFLICT (match_id, game_number)` yang cocok dengan constraint `uq_match_game_number` yang sudah terkonfirmasi ada di Cloud sejak `0001`. | Bergantung pada `0001` (`matches`, `match_results`, `uq_match_game_number`), `0002` (`current_user_role`), dan `0003` (`private`, `transition_tournament_status`). Aman pada PG `17.11`. |
| [0005_supa001_auth_trigger_hardening.sql](file:///C:/Turnamen.in/supabase/migrations/0005_supa001_auth_trigger_hardening.sql) | **Index:** `uq_profiles_lower_email` (`UNIQUE ON (LOWER(email))`). **Functions di-harden/diperbarui (13):** `set_updated_at()`, `current_profile_id()`, `current_user_role()`, `is_tournament_*`, `is_team_captain()`, `replace_tournament_matches()`, `prevent_profile_privilege_escalation()` (`SECURITY INVOKER`), `handle_new_auth_user()`, plus RPC baru pasangan `private`/`public` `link_profile_auth_user(UUID, UUID)` dan `assign_user_role(UUID, VARCHAR)`. **Policy:** menghapus `"Users read active profiles"` & `"Profiles select own or staff"`, membuat `"Profiles select own or admin"`. | Mengunci `search_path = ''` pada seluruh fungsi `0002`, menghapus pengecualian self-claim `OLD.auth_user_id IS NULL`, menutup auto-link email di `handle_new_auth_user()`, dan membatasi `SELECT` `profiles` hanya ke pemilik `auth_user_id` atau `super_admin`. | **Prasyarat data:** tidak boleh ada 2 baris di `public.profiles` dengan `LOWER(email)` identik. Pada Cloud saat ini (`5` profil seeded, terverifikasi di Wave 6.3), `0` duplikat ditemukan sehingga `uq_profiles_lower_email` aman. | Bergantung pada `0001`-`0003`. Menutup celah `SUPA-001` dan risiko `search_path` dari `0002`. Aman pada PG `17.11`. |
| [0006_wave5_functional_rpc.sql](file:///C:/Turnamen.in/supabase/migrations/0006_wave5_functional_rpc.sql) | **Functions (5):** `public.list_tournament_announcements(UUID)` (`SECURITY DEFINER`, `search_path = ''`), serta pasangan `private`/`public` `list_committee_candidates()` dan `list_tournament_staff(UUID)`. **Grants:** `anon, authenticated, service_role` untuk `list_tournament_announcements`; `authenticated, service_role` untuk dua RPC panitia. | Tidak mengubah tabel, constraint, trigger, atau policy tabel. Menyediakan proyeksi aman non-PII (`author_name` / `username` / `full_name`) untuk menggantikan query langsung ke `profiles` yang dibatasi oleh RLS `0005`. | **Nol dampak ke data existing.** Kompatibel dengan seluruh pemanggilan `.rpc(...)` pada [supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py). | Bergantung pada `0001`-`0005` (`private`, `announcements`, `tournaments`, `tournament_staff`, `profiles`). Aman pada PG `17.11`. |

---

## 3. Pemeriksaan Keamanan Khusus

### A. Analisis Celah `SUPA-001` pada `0002` vs `0005`
1. **Apakah auto-link berdasarkan email masih ada pada `0002`?**
   **Ya.** Pada [0002_security_hardening.sql](file:///C:/Turnamen.in/supabase/migrations/0002_security_hardening.sql#L199-L205), `handle_new_auth_user()` melakukan `UPDATE public.profiles SET auth_user_id = NEW.id ... WHERE LOWER(email) = LOWER(NEW.email) AND auth_user_id IS NULL`. Selain itu, [prevent_profile_privilege_escalation()](file:///C:/Turnamen.in/supabase/migrations/0002_security_hardening.sql#L143-L146) masih mengizinkan self-claim `auth_user_id` ketika `OLD.auth_user_id IS NULL`. Karena di Cloud saat ini seluruh `5` profil seeded (termasuk `super_admin`, `organizer`, `committee`) memiliki `auth_user_id = NULL`, pendaftaran user baru dengan email yang cocok akan otomatis mengambil alih akun istimewa tersebut jika hanya `0002` yang aktif.
2. **Apakah `0005` benar-benar meniadakan risiko tersebut?**
   **Ya.** Pada [0005_supa001_auth_trigger_hardening.sql](file:///C:/Turnamen.in/supabase/migrations/0005_supa001_auth_trigger_hardening.sql#L312-L353):
   - `handle_new_auth_user()` memeriksa `id = NEW.id OR pg_catalog.lower(email) = v_clean_email` dan langsung menolak dengan `ERRCODE = '23505'` jika profil sudah ada, sehingga baris `auth.users` ikut batal di-insert.
   - `prevent_profile_privilege_escalation()` diubah menjadi `SECURITY INVOKER` (`SET search_path = ''`) dan menolak setiap perubahan `auth_user_id` oleh caller non-`super_admin`, tanpa pengecualian `OLD.auth_user_id IS NULL`.
   - `uq_profiles_lower_email` mencegah duplikasi email beda huruf besar/kecil.
   - Penautan profil unlinked hanya bisa dilakukan oleh `super_admin` aktif atau `service_role`/`postgres`/`supabase_admin` via `link_profile_auth_user()`, yang juga memverifikasi `email_confirmed_at IS NOT NULL` dan kesamaan email.
3. **Apakah ada jendela waktu rentan selama deployment?**
   **Ya, ada jendela transien** selama rentang eksekusi antara commit `0002` dan commit `0005` (baik beberapa detik saat `supabase db push` berjalan normal, maupun berkepanjangan jika `0003`, `0004`, atau `0005` gagal di tengah jalan).
4. **Cara meminimalkan risiko selama deployment:**
   - Nonaktifkan **Allow new users to sign up** di **Supabase Dashboard -> Authentication -> Sign In / Providers** sebelum menjalankan `0002`-`0006`.
   - Verifikasi `SELECT COUNT(*) FROM auth.users;` bernilai `0` sebelum deployment dimulai.
   - Pertahankan signup tetap nonaktif sampai `0002`-`0006` terkonfirmasi `applied` seluruhnya, verifikasi pasca-migrasi lulus, dan akun `super_admin` pertama selesai di-bootstrap.

### B. Audit RLS & Grants (Terverifikasi dengan `ALTER DEFAULT PRIVILEGES` Cloud)
Karena Cloud memiliki `ALTER DEFAULT PRIVILEGES ... GRANT ALL ON TABLES/FUNCTIONS TO anon, authenticated, service_role`, audit replay lokal memverifikasi hasil grant aktual sesudah `0002`-`0006`:
- **Tidak ada pertentangan policy lama vs baru:** `0002` menghapus seluruh `9` policy `0001` sebelum memasang `42` policy baru, lalu `0005` mengganti `"Profiles select own or staff"` menjadi `"Profiles select own or admin"`. Total pasca-migrasi: `43` policy di `13` tabel, seluruhnya `relrowsecurity = true`.
- **Akses `anon`:**
  - Tidak dapat mengakses `profiles`, `tournament_staff`, `payments`, `activity_logs`, maupun `match_submission_requests`.
  - Hanya dapat `SELECT` pada tabel publik kompetisi (`games` aktif, `tournaments`, `teams`, `team_members`, `registrations` berstatus `approved`, `matches`, `match_results`, `announcements`).
  - Catatan `announcements`: policy `"Public read announcements"` (`USING (true)`) mengizinkan `SELECT` tabel `announcements`, sedangkan pembatasan pengumuman turnamen `draft` ditegakkan melalui RPC `list_tournament_announcements` (`0006`) yang dipakai oleh [supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py#L1034-L1037). Tabel `announcements` sendiri tidak menyimpan PII.
- **Akses `authenticated`:**
  - Dibatasi RLS kepemilikan/role pada seluruh `13` tabel.
  - Pada `match_submission_requests`, `0004` mencabut `INSERT`, `UPDATE`, `DELETE` dari `authenticated` dan membatasi `SELECT` hanya untuk `actor_id` milik sendiri atau `super_admin` (catatan: `REFERENCES`, `TRIGGER`, `TRUNCATE` dari default ACL tetap tersisa di metadata grant tabel, tetapi tidak memberi izin baca/tulis baris maupun DDL karena bukan pemilik tabel; dapat dibersihkan opsional di migrasi terpisah jika diinginkan, non-blocking).
- **Akses `service_role`:** Tetap memiliki akses penuh (`BYPASSRLS` dan table/RPC grants administratif). Tidak pernah disimpan atau dipakai di aplikasi desktop maupun frontend.

### C. Audit RPC `0004` dan `0006`
- **Seluruh fungsi (`9` di `private`, `18` di `public`) mengunci `search_path = ""`** setelah `0005` selesai.
- **Hak `EXECUTE` pasca-`0006` (teruji di atas `ALTER DEFAULT PRIVILEGES` Cloud):**
  - `PUBLIC`: `FALSE` pada semua `27` fungsi.
  - `anon`: `TRUE` **hanya** pada `public.current_user_role()` dan `public.list_tournament_announcements(UUID)`; `FALSE` pada `25` fungsi lainnya (seluruh `private.*` dan seluruh RPC mutasi/sensitif).
  - `authenticated`: `TRUE` pada helper RLS dan RPC publik aplikasi (`transition_tournament_status`, `get_public_profile_summary`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`, `link_profile_auth_user`, `assign_user_role`, `list_tournament_announcements`, `list_committee_candidates`, `list_tournament_staff`); `FALSE` pada `prevent_profile_privilege_escalation()`, `handle_new_auth_user()`, `set_updated_at()`, dan `private.validate_tournament_bracket_integrity()`.
- **Kompatibilitas Aplikasi:** Seluruh nama fungsi dan parameter `.rpc(...)` pada [supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py) (`get_public_profile_summary`, `assign_user_role`, `transition_tournament_status`, `list_tournament_staff`, `list_committee_candidates`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`, `list_tournament_announcements`) cocok 1:1 dengan definisi `0003`-`0006`.

---

## 4. Matriks Risiko Deployment

| ID | Risiko | Probabilitas | Dampak | Mitigasi |
| :---: | :--- | :---: | :---: | :--- |
| **R-01** | **Celah transien `SUPA-001` antara `0002` dan `0005`** jika ada signup masuk saat window atau jika push berhenti di `0003`/`0004` | Rendah (jika dimitigasi) | **Kritis** (pengambilalihan profil seeded `super_admin`/`organizer`) | Matikan public signup di Dashboard sebelum push, pastikan `auth.users = 0`, dan jangan buka signup sebelum `0005` + `super_admin` terverifikasi. |
| **R-02** | **Kegagalan parsial `supabase db push` di tengah `0002`-`0006`** karena tiap file berjalan di transaksi terpisah | Rendah (sudah lulus uji PG 17.11) | Sedang (skema berada di state antara, mis. `0002` committed tapi `0003` gagal) | Jangan jalankan ulang `0001`; pertahankan signup nonaktif; perbaiki penyebab pada file yang gagal (atau restore backup) lalu lanjutkan push atau forward-fix. |
| **R-03** | **Kegagalan `uq_profiles_lower_email` (`0005`)** jika ada perubahan manual di Cloud yang menciptakan duplikat `LOWER(email)` setelah Wave 6.3 | Sangat Rendah | Sedang (`0005` gagal & rollback, `0002`-`0004` sudah committed) | Jalankan kueri pre-flight `LOWER(email)` dan pengecekan checksum/baseline sebelum `migration repair 0001`. |
| **R-04** | **Eksekusi ulang `0001_initial_schema.sql` atau `seed.sql` secara tidak sengaja** | Rendah | Tinggi (error `trigger/policy already exists` atau potensi mutasi tidak perlu) | Jalankan `supabase migration repair --status applied 0001` sebelum `db push`; dilarang keras memakai flag `--include-seed` atau `--include-all`. |
| **R-05** | **Perbedaan konektivitas jaringan lokal ke port `5432`** (kendala historis IPv6/Session Pooler dari jaringan lokal) | Sedang | Rendah (deployment CLI tertunda sebelum mutasi dimulai) | Gunakan operator/jaringan yang dapat menjangkau Session Pooler (`port 5432`) atau IPv6 Direct (`port 5432`), atau jalankan dari lingkungan ber-akses pooler `5432`. |

---

## 5. Potensi Downtime, Gangguan Aplikasi, & Urutan Penerapan

- **Urutan Wajib:** `0001` (repair metadata saja) -> `0002` -> `0003` -> `0004` -> `0005` -> `0006`.
- **Maintenance Window & Pembatasan Registrasi/Login:**
  - Aplikasi saat ini belum beroperasi di produksi dengan `APP_MODE=supabase` (`0` user di `auth.users`), sehingga dampak ke pengguna aktif saat ini **nol**, namun **pembatasan registrasi publik di Dashboard Supabase Auth tetap wajib** selama jendela pemeliharaan (`10-15` menit) untuk menutup jendela `SUPA-001` antara `0002` dan `0005` serta sampai `super_admin` selesai di-bootstrap.
  - Apabila sebelumnya terdapat klien API/PostgREST yang membaca `public.profiles` secara anonim lewat policy lama `"Users read active profiles"`, akses tersebut sengaja diputus mulai `0002`/`0005` demi perlindungan PII dan digantikan oleh RPC non-PII `0003` & `0006`.

---

## 6. Prosedur Deployment Konkret (Menunggu Persetujuan Eksplisit)

> **Peringatan:** Jangan jalankan perintah di bawah sebelum pemilik project memberikan persetujuan eksplisit dan backup Dashboard/PITR dikonfirmasi.

### Langkah 1: Validasi Backup & Baseline Cloud Read-Only
```powershell
# 1. Verifikasi checksum backup lokal Wave 6.3 tidak berubah
(Get-FileHash "$env:LOCALAPPDATA\TurnamenBackups\turnamen-in\turnamen-in-20261126-183150.dump" -Algorithm SHA256).Hash
# Target: 4B51A7A4CAFEACB1D43D9F3D15492F0B9E3B43C75C3A33DA7549A2A939D22459
```
Di **Supabase Dashboard -> Database -> Backups**, pastikan automated backup / snapshot terbaru tersedia. Lalu jalankan query **read-only** di SQL Editor Cloud untuk memastikan baseline Wave 6.3 tidak berubah dan migration history masih kosong:
```sql
SELECT to_regclass('supabase_migrations.schema_migrations') AS migration_table; -- target: NULL
SELECT COUNT(*) AS auth_users_count FROM auth.users; -- target: 0
SELECT COUNT(*) AS public_table_count FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'; -- target: 12
SELECT LOWER(email), COUNT(*) FROM public.profiles GROUP BY 1 HAVING COUNT(*) > 1; -- target: 0 baris
SELECT COUNT(*) AS total_policies FROM pg_policies WHERE schemaname = 'public'; -- target: 9
```

### Langkah 2: Blokir Public Signup di Dashboard
- Buka **Supabase Dashboard -> Authentication -> Sign In / Providers -> User Signups**, nonaktifkan **Allow new users to sign up**, lalu simpan.

### Langkah 3: Link CLI, Repair `0001`, Dry-Run, & Push `0002`-`0006`
```powershell
supabase login
supabase link --project-ref cfdsgxciodfkamskafwe
supabase migration list --linked
# Ekspektasi: Local menampilkan 0001-0006, Remote kosong

# Tandai 0001 sebagai applied (hanya menulis metadata supabase_migrations.schema_migrations)
supabase migration repair --status applied 0001 --linked
supabase migration list --linked
# Ekspektasi: 0001 tampil di Local & Remote; 0002-0006 belum di Remote

# Dry-run sebelum mutasi (PASTIKAN tidak ada --include-seed)
supabase db push --dry-run --linked
# Ekspektasi: hanya 0002 sampai 0006 yang akan diterapkan

# Terapkan 0002 -> 0006 berurutan
supabase db push --linked
supabase migration list --linked
# Ekspektasi: 0001 sampai 0006 seluruhnya tampil di Local dan Remote
```

### Langkah 4: Verifikasi Pasca-Migrasi (Read-Only di SQL Editor Cloud)
```sql
-- 1. 6 migrasi tercatat
SELECT version, name FROM supabase_migrations.schema_migrations ORDER BY version;

-- 2. Seluruh 13 tabel public memiliki RLS enabled
SELECT c.relname, c.relrowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY 1;

-- 3. Policy lama hilang, "Profiles select own or admin" aktif, 43 policy terpasang
SELECT tablename, policyname, cmd, roles
FROM pg_policies WHERE schemaname = 'public'
ORDER BY 1, 2;

-- 4. Index email case-insensitive & trigger auth/anti-eskalasi aktif
SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'uq_profiles_lower_email';
SELECT event_object_schema, event_object_table, trigger_name
FROM information_schema.triggers
WHERE event_object_schema IN ('public', 'auth')
ORDER BY 1, 2, 3;

-- 5. Seluruh fungsi private.* & public.* mengunci search_path='' dan hak anon minimal
SELECT n.nspname, p.proname, p.prosecdef, p.proconfig,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_exec,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_exec
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname IN ('public', 'private')
ORDER BY 1, 2;

-- 6. Verifikasi 59 baris seeded utuh & match_submission_requests = 0
SELECT 'profiles' AS tbl, COUNT(*) FROM public.profiles
UNION ALL SELECT 'tournaments', COUNT(*) FROM public.tournaments
UNION ALL SELECT 'teams', COUNT(*) FROM public.teams
UNION ALL SELECT 'matches', COUNT(*) FROM public.matches
UNION ALL SELECT 'match_submission_requests', COUNT(*) FROM public.match_submission_requests
ORDER BY 1;
```
Setelah verifikasi lulus, lakukan bootstrap `super_admin` pertama sesuai [WAVE6_2_CLOUD_DEPLOYMENT_RUNBOOK.md](file:///C:/Turnamen.in/docs/finalization/WAVE6_2_CLOUD_DEPLOYMENT_RUNBOOK.md) Bagian 7 (disarankan membuat akun admin dengan email terpisah atau menautkan terkontrol via SQL Editor, serta menonaktifkan akun demo unlinked yang tidak dipakai) sebelum membuka kembali pendaftaran publik.

---

## 7. Langkah Pemulihan Jika Salah Satu Migration Gagal

Karena `supabase db push` mengeksekusi setiap file migrasi dalam transaksi terpisah:
1. **Hentikan proses segera & pertahankan public signup dalam status NONAKTIF.** Jangan pernah menjalankan `supabase db reset`, `DROP TABLE`, atau `TRUNCATE` di Cloud.
2. **Identifikasi titik berhenti:** Jalankan `supabase migration list --linked` dan catat pesan error SQLSTATE dari stderr CLI. File yang gagal sudah otomatis di-rollback oleh PostgreSQL; file sebelumnya yang sudah tercatat di `schema_migrations` tetap committed.
3. **Skenario per file gagal:**
   - **Gagal pada `0002`:** `0002` di-rollback utuh; Cloud masih berada di baseline `0001`. Periksa pesan error (mis. izin `auth.users` atau tipe data) sebelum mencoba ulang.
   - **Gagal pada `0003` atau `0004`:** `0002` sudah aktif (dengan trigger `handle_new_auth_user()` versi `SUPA-001`). **Jangan buka signup.** Perbaiki penyebab error `0003`/`0004`, atau jika perbaikan tidak cepat selesai, lakukan **Full Restore** dari snapshot Dashboard / `turnamen-in-20261126-183150.dump` sebelum membuka layanan.
   - **Gagal pada `0005` (mis. error `23505` saat membuat `uq_profiles_lower_email`):** `0002`-`0004` sudah aktif. **Jangan buka signup.** Periksa duplikat `LOWER(email)` di `public.profiles`, bersihkan anomali data secara terkontrol, lalu jalankan ulang `supabase db push --linked` (CLI akan melanjutkan dari `0005` -> `0006`).
   - **Gagal pada `0006`:** `0002`-`0005` sudah aktif (`SUPA-001` sudah tertutup), hanya RPC `list_tournament_announcements`/`list_committee_candidates`/`list_tournament_staff` yang belum terpasang. Perbaiki penyebab di forward-fix lalu jalankan ulang `supabase db push --linked`.
4. **Full Restore (opsi darurat jika konsistensi terganggu):** Pulihkan snapshot dari **Supabase Dashboard -> Database -> Backups** ke titik sebelum maintenance window (atau gunakan archive terverifikasi `turnamen-in-20261126-183150.dump`), lalu verifikasi kembali `12` tabel dan `59` baris seeded.

---

## 8. Keputusan Akhir

- **Status Akhir:** **`READY FOR EXPLICIT MIGRATION APPROVAL`**
- Menunggu persetujuan eksplisit dari pemilik project sebelum menjalankan deployment produksi ke Supabase Cloud (`cfdsgxciodfkamskafwe`).
