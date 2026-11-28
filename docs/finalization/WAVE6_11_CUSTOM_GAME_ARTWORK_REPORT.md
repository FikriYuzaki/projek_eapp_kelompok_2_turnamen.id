# Wave 6.11: Laporan Manajemen Artwork Kustom Game

- **Tanggal:** 2026-11-28
- **Target Sistem:** Manajemen Game Desktop UI, REST API `/api/v1/games/<id>/artwork`, Validator Biner Gambar, Repository Mock & Supabase, serta Migration PostgreSQL & Storage Bucket `game-artwork`
- **Status Lingkungan Produksi:** Migration `20261126232622_wave6_11_custom_game_artwork.sql` sudah diterapkan (`DEPLOYED_AND_VERIFIED`), audit read-only 4 policy `storage.objects` lulus (`PASS`), dan pengujian live Supabase Cloud pada 28 November 2026 lulus `7/7` tahap (`PASSED`, memakai `publishable` key tanpa `service_role` dan tanpa `.env`). Artwork resmi Wave 6.10 sudah dipulihkan penuh (`0` baris override, `0` objek Storage tersisa); pengujian akun non-admin live tidak dijalankan karena hanya terdapat 1 Auth user dan Public Signup tetap `DISABLED`.

---

## 1. Arsitektur yang Dipilih

1. **Tabel Metadata Terpisah (`public.game_artwork_overrides`):**
   - Sesuai audit atas `public.games` (yang hanya dapat diubah oleh `super_admin` melalui kebijakan `"Super admin manage games"`), metadata poster kustom disimpan di tabel terpisah `public.game_artwork_overrides` (`game_id` unik dengan FK ke `public.games(id) ON DELETE CASCADE`, `storage_path`, `mime_type`, `file_size_bytes`, `width`, `height`, `uploaded_by` FK ke `public.profiles(id) ON DELETE SET NULL`, `created_at`, `updated_at`).
   - Desain ini menjaga tabel `public.games` tetap utuh tanpa memperluas hak tulis ke kolom katalog inti game.
2. **Pembentukan URL Tepercaya & Prioritas Resolver (Wave 6.10 Preserved):**
   - Database dan API tidak pernah menerima atau menyimpan URL eksternal arbitrer dari input pengguna; backend hanya menyimpan `storage_path` berformat `<slug>/<uuid>.<jpg|png|webp>` lalu membentuk URL publik tepercaya dari `config.supabase_url` (`https://<project-ref>.supabase.co/storage/v1/object/public/game-artwork/<storage_path>` pada `APP_MODE=supabase`, dan `/api/v1/games/artwork-assets/<storage_path>` pada `APP_MODE=mock`).
   - Prioritas resolusi terpusat pada `resolveGameArtwork(game)` di [ui-components.js](file:///C:/Turnamen.in/desktop/web/assets/js/components/ui-components.js):
     1. Poster kustom Super Admin (`custom_artwork_url`, dengan UUID path unik di setiap upload sehingga mematahkan cache browser poster lama).
     2. Artwork resmi Wave 6.10 (`GAME_ARTWORK_BY_ID` / `GAME_ARTWORK_REGISTRY`).
     3. Fallback lokal `assets/images/games/default-arena.svg` bila kedua sumber gagal atau game belum memiliki artwork resmi.
   - Seluruh pemanggilan poster dan chip game lintas halaman (Dashboard seluruh role, Jelajah Game, Daftar Turnamen, Detail Turnamen, Manajemen Tim, dan Manajemen Game) memakai resolver tunggal tersebut.
3. **Urutan Operasi Aman & Rollback Otomatis ([service.py](file:///C:/Turnamen.in/backend/modules/tournaments/service.py)):**
   - **Penggantian Poster:** validasi RBAC (`game:manage`) & signature file -> unggah file baru bernamakan UUID ke Storage -> simpan/upsert metadata `game_artwork_overrides` (bila gagal, file baru otomatis dihapus dari Storage) -> hapus file Storage lama hanya setelah metadata sukses tersimpan.
   - **Kembalikan Artwork Resmi:** hapus baris `game_artwork_overrides` terlebih dahulu agar seluruh UI langsung kembali ke registry Wave 6.10 -> hapus objek Storage lama yang tidak lagi direferensikan.

---

## 2. Perubahan UI, Kontrak & Backend

1. **Frontend Desktop UI:**
   - [app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js): Menambahkan halaman `game-management` ("Manajemen Game") khusus `super_admin` (dilindungi `checkPageAccess` dan tertaut dari sidebar Super Admin serta kartu `Katalog & Pengaturan Game` di Dashboard). Setiap kartu menampilkan poster aktif 16:9, badge sumber (`Poster Kustom` / `Artwork Resmi` / `Fallback Arena`), tombol `Ganti Poster` (JPEG/PNG/WebP max 5 MB), box preview lokal sebelum simpan lengkap dengan deteksi dimensi/rasio + optimasi Canvas 16:9 jika didukung browser, tombol `Simpan Poster` dengan progress bar, dan tombol `Kembalikan Artwork Resmi` yang meminta konfirmasi modal sebelum menjalankan `DELETE`. Juga menyelaraskan `renderGameChip` di Dashboard Kapten agar meneruskan objek game lengkap.
   - [ui-components.js](file:///C:/Turnamen.in/desktop/web/assets/js/components/ui-components.js): Memperbarui `isSafeArtworkUrl()` (mendukung asset lokal `/api/v1/games/artwork-assets/...` selain `https://` aman, tetap menolak HTTP eksternal, `javascript:`, kredensial, parameter token/key sensitif, dan path traversal `..`) serta `resolveGameArtwork()` untuk memprioritaskan `custom_artwork_url` di atas registry Wave 6.10 dan fallback bertahap ke SVG resmi.
   - [api-client.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/api-client.js): Menambahkan `uploadGameArtwork(gameId, payload)` dan `restoreGameArtwork(gameId)`.
   - [components.css](file:///C:/Turnamen.in/desktop/web/assets/css/components.css): Menambahkan styling `.artwork-manager-grid`, `.artwork-manager-card`, `.artwork-manager-poster`, `.artwork-manager-preview-box`, dan aturan responsif `<= 1024px` dengan mempertahankan rasio `16:9` dan `object-fit: cover`.
2. **Backend & Kontrak:**
   - [artwork_validator.py](file:///C:/Turnamen.in/backend/modules/tournaments/artwork_validator.py): Modul inspeksi biner murni stdlib (tanpa dependency tambahan) untuk verifikasi magic bytes JPEG (`SOF`), PNG (`IHDR`), dan WebP (`VP8`/`VP8L`/`VP8X`), penolakan `<svg>`, `<script>`, HTML, executable (`MZ`, ELF, ZIP, PDF, GIF), pemeriksaan kesesuaian ekstensi & MIME, batas 5 MB (`5.242.880` byte), batas dimensi (`320x180` hingga `4096x4096`), serta validasi batas rasio aspek (`0.75` hingga `2.6`).
   - [v1_routes.py](file:///C:/Turnamen.in/backend/api/routes/v1_routes.py): Menambahkan `POST /api/v1/games/<game_id>/artwork` (mendukung `multipart/form-data` dan JSON base64 dengan pengawasan batas 5 MB), `DELETE /api/v1/games/<game_id>/artwork`, dan `GET /api/v1/games/artwork-assets/<storage_path>` khusus mode mock lokal.
   - [supabase_repository.py](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py) & [mock_repository.py](file:///C:/Turnamen.in/backend/repositories/mock/mock_repository.py) & [repository_protocol.py](file:///C:/Turnamen.in/backend/repositories/interfaces/repository_protocol.py): Menambahkan operasi `game_artwork_overrides` dan Storage bucket `game-artwork` menggunakan JWT sesi pemanggil (`_get_client()`), mempertahankan `include_artwork_overrides=False` pada `list_tournaments()` dan `list_teams()` agar target query Wave 6.8 tetap terjaga, serta fallback aman bila tabel `game_artwork_overrides` belum dideploy (`PGRST205`).
   - Kontrak diperbarui pada [database-contract.md](file:///C:/Turnamen.in/docs/contracts/database-contract.md) dan [api-contract.md](file:///C:/Turnamen.in/docs/contracts/api-contract.md).

---

## 3. Migration & Kebijakan Storage RLS

- File migration dibuat melalui `supabase migration new wave6_11_custom_game_artwork`:
  [20261126232622_wave6_11_custom_game_artwork.sql](file:///C:/Turnamen.in/supabase/migrations/20261126232622_wave6_11_custom_game_artwork.sql) (`5,717` bytes, SHA-256 `F82A049975D9FBAD2273CD852604EC5639714EEB22C06208074E25FD36FBFA55`).
- **Keamanan & Least-Privilege SQL:**
  - Tidak membuat fungsi `SECURITY DEFINER` baru; seluruh kebijakan menggunakan helper teraudit yang sudah ada (`public.current_user_role()` dan `public.current_profile_id()` yang memverifikasi `public.profiles.auth_user_id = auth.uid()` dan `is_active = TRUE`).
  - `game_artwork_overrides` mengaktifkan RLS, mencabut seluruh privilege `PUBLIC`, memberi `SELECT` ke `anon` dan `authenticated` (terbatas pada game `is_active = TRUE` atau `super_admin`), serta membatasi `INSERT`, `UPDATE`, `DELETE` hanya untuk `super_admin` aktif dengan `uploaded_by = public.current_profile_id()`.
  - `CHECK` constraint memvalidasi `storage_path` UUID regex (menolak `..`, `://`, `/` awal), `mime_type IN ('image/jpeg', 'image/png', 'image/webp')`, `file_size_bytes <= 5242880`, dan dimensi gambar.
  - Storage bucket `game-artwork` diset `public = TRUE`, limit `5242880` bytes, dan MIME diizinkan JPEG/PNG/WebP pada blok `storage.buckets` (dijaga dengan `information_schema.tables`).
  - Seluruh DDL policy `storage.objects` **dipisahkan** dari file migrasi SQL karena tabel `storage.objects` di Cloud dimiliki `supabase_storage_admin`, sedangkan role deployment `postgres` bukan anggotanya. Keempat policy `storage.objects` (`SELECT`, `DELETE`, `UPDATE`, `INSERT` khusus `authenticated` `super_admin`, tanpa policy listing luas untuk `anon`) dikelola langsung melalui **Supabase Dashboard -> Storage -> Policies** (Bagian 7.5).

---

## 4. Hasil Keamanan & Verifikasi Pengujian

- Seluruh operasi tulis `APP_MODE=supabase` memakai JWT pengguna aktif; tidak ada `service_role`, `sb_secret_*`, `.env`, atau bypass RLS.
- **Pengujian Wave 6.11 & PostgreSQL RLS (`pytest`):** **6 passed** (`11.71s`):
  - [test_wave6_11_custom_game_artwork.py](file:///C:/Turnamen.in/tests/unit/test_wave6_11_custom_game_artwork.py) (**5 passed**): Super Admin unggah/ganti/restore poster + pembersihan objek lama; penolakan anonim (`401`) dan user non-admin (`player`, `organizer`, `committee`, `team_captain` -> `403`); penolakan file > 5 MB, SVG tersamar, executable `MZ`, ekstensi/MIME palsu, serta resolusi terlalu kecil; simulasi gagal unggah & gagal metadata (rollback menghapus objek Storage yatim); uji UI Node VM untuk kontrol Manajemen Game, preview sebelum simpan, kemunculan poster kustom di Dashboard Super Admin, Dashboard Player, Daftar Turnamen, Detail Turnamen, dan Manajemen Tim, fallback ke Wave 6.10 saat URL gagal/direstore; serta benchmark latency API `< 3.0s`.
  - [test_wave4b_postgres_migrations_and_security.py](file:///C:/Turnamen.in/tests/integration/test_wave4b_postgres_migrations_and_security.py) (`test_wave6_11_game_artwork_overrides_migration_and_rls` **PASSED**): Verifikasi langsung pada cluster PostgreSQL 18 lokal bahwa `super_admin` aktif dapat `INSERT`/`UPDATE`/`DELETE`, path ilegal ditolak constraint, serta `anon` dan `player` gagal memodifikasi `game_artwork_overrides`.
- **Keseluruhan Suite (`.\.venv\Scripts\python.exe -m pytest -q`):** **303 passed, 4 warnings in 59.58s** (`0 failed`, `0 skipped`).
- **Smoke Check (`.\.venv\Scripts\python.exe run.py --check`):** `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`.
- **Kebersihan Workspace (`git diff --check` & Keamanan):** keluar dengan kode `0`, `DOTENV_EXISTS=False`, tanpa perubahan branch/commit/push/merge.

---

## 5. Instruksi Deployment Selanjutnya (Menunggu Persetujuan Pengguna)

1. Review isi [20261126232622_wave6_11_custom_game_artwork.sql](file:///C:/Turnamen.in/supabase/migrations/20261126232622_wave6_11_custom_game_artwork.sql) dan rancangan 4 Storage Policies pada Bagian 7.5.
2. Setelah mendapat persetujuan eksplisit, ikuti prosedur **Split Deployment Fail-Closed** pada Bagian 7.6:
   - Jalankan `supabase db push` untuk menerapkan tabel `public.game_artwork_overrides` dan bucket `game-artwork` (upload Storage tetap tertolak otomatis dengan `0` policy hingga tahap berikutnya selesai).
   - Buat keempat policy `storage.objects` (`SELECT`, `DELETE`, `UPDATE`, `INSERT`, khusus `authenticated` `super_admin`) lewat **Supabase Dashboard -> Storage -> Policies**.
   - Jalankan verifikasi SQL pasca-deployment (Bagian 7.7) dan uji live khusus `super_admin` (Bagian 7.8) dalam `APP_MODE=supabase` tanpa `.env` maupun `service_role`, sambil mempertahankan Public Signup tetap `DISABLED`.

---

## 6. Hasil Final Security Review Pra-Deployment

- **Kesimpulan Keamanan:** **Aman dengan catatan (Split Deployment Storage Policies)** *(Belum ada perubahan ke Supabase Cloud; menunggu persetujuan eksplisit sebelum deployment).*

| Area Audit | Hasil Verifikasi Aktual | Status |
| :--- | :--- | :---: |
| **1. Migration `20261126232622`** | Idempotent, terurut aman sesudah `0001`-`0006`, memakai `public.set_updated_at()` (`SET search_path = ''` dari `0005`), tidak menyentuh `storage.objects` maupun kepemilikan role sehingga bersih dijalankan oleh role `postgres` non-superuser. | **PASS** |
| **2. Tabel `game_artwork_overrides` & Constraint** | Terpisah dari `public.games`; FK ke `games(id) ON DELETE CASCADE` & `profiles(id) ON DELETE SET NULL`; `CHECK` membatasi regex UUID `storage_path`, anti `..`/`://`, MIME JPEG/PNG/WebP, ukuran `<= 5242880` byte, dan dimensi `320x180`..`4096x4096`. | **PASS** |
| **3. RLS `game_artwork_overrides`** | `REVOKE ALL FROM PUBLIC`; `SELECT` untuk `anon`/`authenticated` dibatasi ke game aktif atau `super_admin`; `INSERT`/`UPDATE`/`DELETE` hanya `super_admin` aktif dengan `uploaded_by = public.current_profile_id()`. Terbukti pada klaster PostgreSQL lokal. | **PASS** |
| **4. Bucket `game-artwork` & Storage Policies** | Bucket `public = TRUE` melayani URL `/storage/v1/object/public/game-artwork/<path>` langsung tanpa membuka listing metadata untuk `anon`. Keempat policy `storage.objects` (`SELECT`, `DELETE`, `UPDATE`, `INSERT`) dibatasi ketat ke `authenticated` + `super_admin` dan dibuat lewat Supabase Dashboard (teruji di simulasi ownership `supabase_storage_admin` pada PG 17.11 lokal). | **PASS** |
| **5. Validasi Role `super_admin`** | Backend `get_user_by_token` memverifikasi JWT lewat Supabase Auth lalu membaca role aktif dari `public.profiles` (`is_active = TRUE`), sedangkan RLS mengevaluasi `public.current_user_role()` (`auth.uid()` -> `public.profiles`). Tidak bergantung pada `user_metadata` maupun klaim frontend. | **PASS** |
| **6. Upload, Replace, Restore & Anti-Orphan Cleanup** | Penamaan objek UUID murni dengan `upsert = "false"`; urutan upload -> upsert metadata (hapus file baru jika upsert gagal) -> hapus file lama; restore menghapus metadata lebih dahulu sebelum menghapus objek Storage. Pembersihan objek lama bersifat best-effort agar galat sementara Storage tidak memutus referensi poster aktif. | **PASS** |
| **7. Akses User Biasa & Anonim** | Uji API (`401` anon, `403` `player`/`organizer`/`committee`/`team_captain`), access guard UI, serta uji PostgreSQL 17.11/18 RLS (tabel dan `storage.objects`) membuktikan user biasa maupun anon tidak dapat me-list metadata Storage atau mengubah/menghapus artwork kustom. | **PASS** |
| **8. Interaksi Security Advisor Findings** | Migration tidak menambah fungsi `SECURITY DEFINER` baru. Policy hanya memakai `public.current_user_role()` dan `public.current_profile_id()` yang sudah di-harden (`SET search_path = ''` pada `0005`). Hak `EXECUTE` `anon` pada `current_user_role()` tidak boleh dicabut sepihak karena dipakai policy publik `games` dan `game_artwork_overrides`. | **PASS (Catatan Advisor)** |
| **9. Ketiadaan `service_role` / Secret di Client** | Pemindaian `desktop/` dan `backend/` mengonfirmasi tidak ada `service_role` maupun `sb_secret_*` di client atau frontend; kecocokan pola hanya ada pada guard penolakan di `config.py` dan redaksi log di `logging_config.py`. `DOTENV_EXISTS=False`. | **PASS** |
| **10. Kompatibilitas dengan `0001`-`0006` & Split Ownership** | Pengujian pada `test_wave4b_postgres_migrations_and_security.py` dan `test_wave6_11_custom_game_artwork.py` pada **PostgreSQL 17.11** (termasuk simulasi role non-superuser `cloud_deploy_postgres` vs `supabase_storage_admin`) lulus penuh. | **PASS** |

### Catatan Wajib Sebelum / Saat Deployment Produksi
1. **Split Deployment Wajib (`db push` lalu Dashboard Storage Policies):** Jangan pernah mengubah ownership `storage.objects` atau menambahkan `postgres` ke `supabase_storage_admin`. Jalankan `supabase db push` untuk membuat tabel `game_artwork_overrides` dan bucket `game-artwork`, lalu segera pasang keempat policy `storage.objects` (`SELECT`, `DELETE`, `UPDATE`, `INSERT`, target role `authenticated`, khusus `super_admin`) di **Supabase Dashboard -> Storage -> Policies** sebelum menguji upload.
2. **Kolom `uploaded_by` & Ketergantungan Advisor:** Policy `SELECT` langsung pada `game_artwork_overrides` mengekspos kolom UUID `uploaded_by` ke `anon` melalui Data API (bukan PII; setara `organizer_id` pada `tournaments`, dan endpoint `/api/v1/games` tidak mengembalikan `uploaded_by`). Pertahankan `EXECUTE` `public.current_user_role()` untuk `anon` selama policy baca tabel publik masih memakainya.

---

## 7. Hasil Persiapan Deployment Supabase Cloud (Pra-Eksekusi)

Seluruh persiapan deployment di bawah dijalankan pada **2026-11-28** terhadap project Supabase Cloud `turnamen-in` (`cfdsgxciodfkamskafwe`, Session Pooler `aws-0-ap-south-1.pooler.supabase.com:5432`, PostgreSQL `17.11`) menggunakan sesi `default_transaction_read_only=on`, tanpa menjalankan `supabase db push`, `supabase migration repair`, pembuatan bucket/policy produksi, upload Storage, maupun perubahan Auth/Public Signup (`DISABLED`).

### 7.1 Backup Terbaru Supabase Cloud & Verifikasi Integritas

| Item Backup | Hasil Aktual Terverifikasi | Status |
| :--- | :--- | :---: |
| **File Backup Pra-Wave 6.11** | `%LOCALAPPDATA%\TurnamenBackups\turnamen-in\turnamen-in-pre-w611-20261128-063810.dump` | **PASS** |
| **Waktu Pembuatan & Alat** | `2026-11-28T06:38:23.545309+07:00` via `pg_dump (PostgreSQL) 17.11` | **PASS** |
| **Schema Tercakup** | `public`, `private`, `supabase_migrations` | **PASS** |
| **Ukuran File** | `188,535` bytes | **PASS** |
| **SHA-256 Terverifikasi** | `3F852F4F432C5788088425889DA889898E9C38D5121104C642D358314CA2900F` (`sha256_match: true`) | **PASS** |
| **Listing Archive (`pg_restore --list`)** | `rc = 0`, `262` TOC entries (`public` tables, `private` functions, dan `supabase_migrations` ada) | **PASS** |
| **Backup Wave 6.5 Sebelumnya** | `%LOCALAPPDATA%\TurnamenBackups\turnamen-in\turnamen-in-20261126-183150.dump` tetap utuh (`68,850` bytes, SHA-256 `4B51A7A4CAFEACB1D43D9F3D15492F0B9E3B43C75C3A33DA7549A2A939D22459`) | **PASS** |

### 7.2 Pemeriksaan Read-Only Cloud & Analisis Anti-Bentrok

Audit read-only (`2026-11-28T06:49:28.493004+07:00`, sumber `wave611_prep_result.json`) memastikan kondisi aktual Cloud berikut:

1. **Migration History (`supabase_migrations.schema_migrations`):** Berisi tepat **`6` baris** (`0001` `initial_schema`, `0002` `security_hardening`, `0003` `wave2_rls_compatibility`, `0004` `wave2_3_atomic_match_submission`, `0005` `supa001_auth_trigger_hardening`, `0006` `wave5_functional_rpc`). Versi `20261126232622` belum diterapkan.
2. **Tabel `public` & Deteksi Benturan Wave 6.11:**
   - `13` tabel `public` existing (`activity_logs`, `announcements`, `games`, `match_results`, `match_submission_requests`, `matches`, `payments`, `profiles`, `registrations`, `team_members`, `teams`, `tournament_staff`, `tournaments`), seluruhnya `rls_enabled = true`.
   - `public.game_artwork_overrides`: belum ada (`regclass = null`).
   - Index `idx_game_artwork_overrides_uploaded_by`, trigger `trg_game_artwork_overrides_updated_at`, dan policy `game_artwork_overrides`: seluruhnya kosong (`[]`), nol benturan objek.
3. **Fungsi Helper Prasyarat (`public.*`):**
   - `public.set_updated_at()` (`SECURITY INVOKER`, `search_path=""`, `anon=false`, `auth=false`).
   - `public.current_user_role()` (`SECURITY DEFINER`, `search_path=""`, `anon=true`, `auth=true`).
   - `public.current_profile_id()` (`SECURITY DEFINER`, `search_path=""`, `anon=false`, `auth=true`).
4. **Status Data Domain & Auth:** `3` game aktif (`ea-sports-fc`, `mobile-legends`, `valorant`), `5` profil (`1` tertaut ke `auth_users_total = 1` sebagai `super_admin` aktif), dan Public Signup tetap `DISABLED`.
5. **Storage Cloud (`storage.buckets` & `storage.objects`) & Hak Akses:**
   - Daftar bucket saat ini: kosong (`[]`), `game-artwork` belum ada (`game_artwork_bucket_exists = false`).
   - Daftar policy pada `storage.objects`: kosong (`[]`), `objects_rls_enabled = true`, `objects_force_rls = false`.
   - Kolom `storage.buckets` terverifikasi memuat `id`, `name`, `public`, `file_size_limit`, `allowed_mime_types`. Role koneksi `postgres` memiliki `buckets_select = true`, `buckets_insert = true`, `buckets_update = true`.
   - **Temuan Penting Ownership `storage.objects`:** `buckets_owner = supabase_storage_admin`, `objects_owner = supabase_storage_admin`, sedangkan `current_user = postgres` memiliki `is_storage_admin_member = false` dan `has_storage_admin_usage = false`.

### 7.3 Hasil Dry-Run Deployment (`supabase` CLI `2.104.0`)

1. **Dry-Run Live Cloud (`wave611_prep_result.json`, `rc = 0`):**
   - `supabase migration list --db-url <no-pw>`: kolom `Local` dan `Remote` selaras pada `0001` sampai `0006`; hanya `20261126232622` (`2026-11-26 23:26:22`) yang masih pending (`Remote` kosong).
   - `supabase db push --dry-run --db-url <no-pw>`: `stderr` menampilkan secara eksplisit:
     ```text
     DRY RUN: migrations will *not* be pushed to the database.
     Connecting to remote database...
     Would push these migrations:
      • 20261126232622_wave6_11_custom_game_artwork.sql
     ```
     (`stdout`: `Finished supabase db push.`, `only_wave611_pending = true`, nol migrasi lama/seed).
2. **Verifikasi Dry-Run Pasca-Revisi SQL pada PostgreSQL 17.11 Lokal (`rc = 0`):**
   - Setelah DDL `storage.objects` dipisahkan dari file migrasi (`5,717` bytes, SHA-256 `F82A049975D9FBAD2273CD852604EC5639714EEB22C06208074E25FD36FBFA55`), `supabase db push --dry-run` dengan CLI `2.104.0` terhadap klaster lokal PostgreSQL `17.11` (`0001`-`0006` terpasang di `supabase_migrations.schema_migrations`) kembali mengonfirmasi hanya `20261126232622_wave6_11_custom_game_artwork.sql` yang pending.
3. **Verifikasi Ulang Dry-Run Live Cloud (Opsional Sebelum Persetujuan):**
   ```powershell
   .\.venv\Scripts\python.exe "$env:LOCALAPPDATA\TurnamenBackups\wave611_prep.py" --dry-run-only
   ```
   *(Mengulang `supabase db push --dry-run` read-only terhadap Cloud atas file migrasi revisi tanpa membuat backup duplikat dan tanpa mutasi Cloud.)*

### 7.4 Review SQL Final (`20261126232622_wave6_11_custom_game_artwork.sql`)

File [20261126232622_wave6_11_custom_game_artwork.sql](file:///C:/Turnamen.in/supabase/migrations/20261126232622_wave6_11_custom_game_artwork.sql) (`5,717` bytes, SHA-256 `F82A049975D9FBAD2273CD852604EC5639714EEB22C06208074E25FD36FBFA55`) sudah direvisi mengikuti temuan ownership Cloud:

1. **Tabel `public.game_artwork_overrides`, Constraint & RLS:**
   - Dipertahankan utuh: FK `ON DELETE CASCADE` ke `public.games(id)` dan `ON DELETE SET NULL` ke `public.profiles(id)`, `CHECK` constraint (`storage_path` regex UUID + anti `..`/`://`/`^/`, `mime_type`, `file_size_bytes <= 5242880`, dimensi `320x180`..`4096x4096`), index `uploaded_by`, trigger `public.set_updated_at()`, `REVOKE ALL`, grant terkendali, dan 4 policy RLS `super_admin`.
2. **Blok `storage.buckets` (`game-artwork`):**
   - Dipertahankan utuh (`public = TRUE`, `file_size_limit = 5242880`, `allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp']`, `ON CONFLICT (id) DO UPDATE`) karena audit live memastikan role `postgres` memiliki hak `SELECT`, `INSERT`, dan `UPDATE` pada `storage.buckets`.
   - **Mengapa `public = TRUE` Tidak Memerlukan Policy `SELECT` `anon` pada `storage.objects`:** Pada arsitektur Supabase Storage, bucket `public = TRUE` melayani pembacaan URL publik `/storage/v1/object/public/game-artwork/<slug>/<uuid>.<ext>` langsung melalui Storage CDN/endpoint publik tanpa memerlukan policy `SELECT` di tabel `storage.objects`. Sebaliknya, pemberian policy `SELECT` kepada `anon` pada `storage.objects` justru membuka endpoint API list/metadata objek Storage ke pengguna anonim.
3. **Pemisahan Penuh `storage.objects`:**
   - Seluruh `DROP POLICY` / `CREATE POLICY` pada `storage.objects` telah dihapus dari file migrasi. Tidak ada pernyataan `ALTER TABLE storage.objects`, `OWNER TO`, maupun pemberian peran `supabase_storage_admin` ke `postgres`.

### 7.5 Definisi Empat Storage Policies (Supabase Dashboard -> Storage -> Policies)

Keempat policy berikut dibuat pada bucket `game-artwork` (`storage.objects`) melalui **Supabase Dashboard -> Storage -> Buckets -> `game-artwork` -> Policies** (atau **Storage -> Policies -> `storage.objects`**) setelah migrasi `20261126232622` membuat bucket `game-artwork`.

| Urutan Pembuatan | Nama Policy | Operasi | Target Role | Ekspresi `USING` | Ekspresi `WITH CHECK` |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **1** | `Super admin select game-artwork objects` | `SELECT` | `authenticated` | `bucket_id = 'game-artwork' AND (SELECT public.current_user_role()) = 'super_admin'` | *(tidak berlaku untuk `SELECT`)* |
| **2** | `Super admin delete game-artwork objects` | `DELETE` | `authenticated` | `bucket_id = 'game-artwork' AND (SELECT public.current_user_role()) = 'super_admin'` | *(tidak berlaku untuk `DELETE`)* |
| **3** | `Super admin update game-artwork objects` | `UPDATE` | `authenticated` | `bucket_id = 'game-artwork' AND (SELECT public.current_user_role()) = 'super_admin'` | `bucket_id = 'game-artwork' AND (SELECT public.current_user_role()) = 'super_admin'` |
| **4** | `Super admin insert game-artwork objects` | `INSERT` | `authenticated` | *(tidak berlaku untuk `INSERT`)* | `bucket_id = 'game-artwork' AND (SELECT public.current_user_role()) = 'super_admin'` |

**Catatan Keamanan Policy:**
- Tidak ada policy `anon` maupun policy listing metadata untuk user biasa (`player`, `organizer`, `committee`, `team_captain`) pada `storage.objects`.
- Seluruh operasi `SELECT` (listing/metadata), `INSERT` (upload), `UPDATE` (replace/upsert), dan `DELETE` (cleanup/restore) di Storage API dikunci hanya untuk pengguna `authenticated` yang memiliki profil aktif ber-role `super_admin` (`public.current_user_role()` memeriksa `public.profiles.auth_user_id = (SELECT auth.uid()) AND is_active = TRUE`).
- **Langkah Pembuatan di Supabase Dashboard:**
  1. Buka **Supabase Dashboard -> Project `cfdsgxciodfkamskafwe` -> Storage -> Policies** pada tabel `storage.objects` (atau dari bucket `game-artwork` -> tab **Policies**).
  2. Klik **New policy -> For full customization** untuk masing-masing policy sesuai urutan **1 -> 2 -> 3 -> 4** di atas:
     - Isi **Policy name** persis sesuai tabel.
     - Pilih **Allowed operation** (`SELECT`, lalu `DELETE`, lalu `UPDATE`, lalu `INSERT`).
     - Pada **Target roles**, pilih **hanya `authenticated`** (biarkan `anon` dan `PUBLIC` tidak dipilih).
     - Tempel ekspresi `USING` dan/atau `WITH CHECK` persis sesuai tabel, lalu klik **Review** -> **Save policy**.
  3. **Urutan aman (`SELECT`, `DELETE`, `UPDATE` sebelum `INSERT`):** Karena `INSERT` dibuat paling akhir, tidak ada momen di mana upload diizinkan sebelum hak hapus/baca verifikasi milik `super_admin` terpasang.

### 7.6 Urutan Deployment Fail-Closed (Zero Upload Before Policies Ready)

1. **Prasyarat Sebelum Mulai:** Backup `turnamen-in-pre-w611-20261128-063810.dump` (`3F852F4F...CA2900F`) tersimpan aman; Public Signup di Dashboard Auth berstatus **`DISABLED`**; `APP_MODE=supabase` lokal belum dijalankan untuk upload.
2. **Tahap A: Terapkan Migration via `supabase db push` (Hanya Setelah Disetujui):**
   - Jalankan `supabase db push --db-url "postgresql://postgres.cfdsgxciodfkamskafwe@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"` (dengan `PGPASSWORD` hanya di memori/prompt CLI, tanpa `--include-seed`).
   - Migration membuat tabel `public.game_artwork_overrides` (RLS aktif, `0` baris) dan bucket `game-artwork` (`public = TRUE`, limit `5 MB`, JPEG/PNG/WebP).
   - **Jendela Fail-Closed:** Pada detik ini `storage.objects` sudah mengaktifkan RLS (`objects_rls_enabled = true`) dengan **`0` policy**. Oleh karena itu, **tidak satu pun role (`anon`, `authenticated`, termasuk `super_admin`) dapat mengunggah ke `game-artwork`** sampai Tahap B selesai; sementara seluruh halaman aplikasi tetap berjalan normal memakai artwork resmi Wave 6.10.
3. **Tahap B: Pasang 4 Storage Policies di Dashboard (Urutan `SELECT` -> `DELETE` -> `UPDATE` -> `INSERT`):**
   - Segera buat keempat policy pada Bagian 7.5 melalui **Supabase Dashboard -> Storage -> Policies** sebelum mengaktifkan atau menguji unggah poster di aplikasi desktop.
4. **Tahap C: Verifikasi SQL Pasca-Deployment & Security Advisor (Bagian 7.7):**
   - Jalankan seluruh query read-only Bagian 7.7 untuk memastikan tabel, constraint, RLS, bucket, keempat policy `storage.objects`, dan `0` policy `anon` pada `storage.objects` terpenuhi.
5. **Tahap D: Uji Live Khusus Super Admin (Bagian 7.8):**
   - Jalankan uji unggah, preview, tampil lintas halaman, ganti poster (verifikasi objek lama terhapus), dan restore ke artwork resmi Wave 6.10.

### 7.7 Paket Verifikasi Pasca-Deployment (Read-Only SQL)

Jalankan query read-only berikut segera setelah Tahap A dan Tahap B selesai:

```sql
-- 1. Migration history: harus tepat 7 baris (0001..0006 + 20261126232622)
SELECT version, name
FROM supabase_migrations.schema_migrations
ORDER BY version;

-- 2. Tabel baru, RLS aktif, jumlah kolom (10), index, dan trigger updated_at
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS force_rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;

SELECT ordinal_position, column_name, data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'game_artwork_overrides'
ORDER BY ordinal_position;

SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'game_artwork_overrides'
ORDER BY indexname;

SELECT trigger_name, action_timing, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'public' AND event_object_table = 'game_artwork_overrides'
ORDER BY trigger_name;

-- 3. Seluruh constraints pada public.game_artwork_overrides (PK, UNIQUE, FK, CHECK)
SELECT contype, conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.game_artwork_overrides'::regclass
ORDER BY contype, conname;

-- 4. Table grants & 4 RLS policies pada public.game_artwork_overrides
SELECT grantee, STRING_AGG(privilege_type, ',' ORDER BY privilege_type) AS privs
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND table_name = 'game_artwork_overrides'
  AND grantee IN ('PUBLIC', 'anon', 'authenticated', 'service_role')
GROUP BY grantee
ORDER BY grantee;

SELECT policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'game_artwork_overrides'
ORDER BY policyname;

-- 5. Bucket game-artwork pada storage.buckets
SELECT id, name, public, file_size_limit, allowed_mime_types
FROM storage.buckets
WHERE id = 'game-artwork';

-- 6. Keempat policy storage.objects khusus game-artwork (seluruhnya TO authenticated, 0 untuk anon)
SELECT policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
  AND (
      COALESCE(qual, '') ILIKE '%game-artwork%'
      OR COALESCE(with_check, '') ILIKE '%game-artwork%'
      OR policyname ILIKE '%game-artwork%'
  )
ORDER BY policyname;

SELECT COUNT(*) AS anon_storage_policies_count
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
  AND 'anon' = ANY(roles::text[]);

-- 7. Non-regresi data inti & Auth (Public Signup tetap DISABLED di Dashboard)
SELECT COUNT(*) AS games_total FROM public.games;
SELECT COUNT(*) AS overrides_total FROM public.game_artwork_overrides;
SELECT COUNT(*) AS auth_users_total FROM auth.users;
```

Selain SQL di atas, periksa **Supabase Dashboard -> Advisors -> Security Advisor** setelah deployment untuk memastikan tidak ada warning baru pada `public.game_artwork_overrides` maupun `storage.objects`, serta pastikan setting **Allow new users to sign up** tetap **DISABLED**.

### 7.8 Rencana Pengujian Live Khusus Super Admin (Upload, Penggantian Poster, dan Restore)

Pengujian dijalankan **hanya setelah** Tahap A, Tahap B, dan verifikasi Bagian 7.7 lulus seluruhnya, memakai variabel environment sementara di PowerShell tanpa menulis `.env` dan tanpa `service_role` / `sb_secret_*`:

1. **Setup Sesi Ephemeral & Smoke Check Read-Only:**
   ```powershell
   $env:APP_MODE = "supabase"
   $env:SECRET_KEY = "<string-acak-lokal-minimal-32-karakter>"
   $env:SUPABASE_URL = "https://cfdsgxciodfkamskafwe.supabase.co"
   $env:SUPABASE_PUBLISHABLE_KEY = "<salin-sb_publishable_...-dari-Dashboard>"
   .\.venv\Scripts\python.exe run.py --check --mode supabase
   ```
   - Target: `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`.
2. **Uji Kontrol Akses Negatif & Privasi Listing Storage:**
   - Pastikan request tanpa token ke `POST /api/v1/games/<game_id>/artwork` dan `DELETE /api/v1/games/<game_id>/artwork` ditolak dengan `401`.
   - Pastikan permintaan listing metadata Storage (`storage.from_("game-artwork").list()`) memakai kunci `anon`/publishable tanpa sesi `super_admin` mengembalikan daftar kosong (`[]`) atau ditolak RLS.
   - Login sebagai `super_admin` (`abc811ac-a57a-4d63-8c90-92280e4962c4`), lalu pastikan upload file `.svg` atau file `> 5 MB` ditolak (`400`/`422`) sebelum menyentuh Storage Cloud.
3. **Uji Upload Poster Pertama (Super Admin):**
   - Buka aplikasi desktop (`.\.venv\Scripts\python.exe run.py`), login sebagai `super_admin`, masuk ke menu **Manajemen Game**, pilih satu game uji (misalnya `mobile-legends`), unggah gambar PNG/JPEG/WebP valid (`>= 320x180`, `<= 5 MB`), verifikasi preview lokal sebelum simpan, lalu klik **Simpan Poster**.
   - Verifikasi:
     - Respons `200`, kartu menampilkan badge **`Poster Kustom`**, URL publik `https://cfdsgxciodfkamskafwe.supabase.co/storage/v1/object/public/game-artwork/<slug>/<uuid>.<ext>` dapat dimuat melalui HTTP `GET` (`200 OK`) oleh browser/klien tanpa login.
     - Halaman lain (Dashboard, Jelajah Game, Daftar Turnamen, Detail Turnamen, Manajemen Tim) ikut menampilkan poster baru.
     - SQL read-only Cloud: `1` baris pada `public.game_artwork_overrides` (`uploaded_by` terisi profil `super_admin`), `1` objek pada `storage.objects` (`bucket_id = 'game-artwork'`), dan `1` entri `GAME_ARTWORK_UPDATED` pada `public.activity_logs`.
4. **Uji Penggantian Poster (Replace + Anti-Orphan Cleanup):**
   - Unggah poster valid kedua pada game yang sama, catat `storage_path` lama dan `storage_path` baru.
   - Verifikasi:
     - Baris `public.game_artwork_overrides` untuk game tersebut ter-update ke `storage_path` baru (tetap `1` baris untuk game tersebut).
     - Objek Storage baru aktif (`HTTP 200`), sedangkan objek Storage lama sudah terhapus dari bucket `game-artwork` (hanya `1` objek untuk game tersebut di `storage.objects`; tidak ada file yatim).
5. **Uji Restore Artwork Resmi (Wave 6.10 Fallback):**
   - Klik **Kembalikan Artwork Resmi** pada kartu game uji tersebut dan konfirmasi dialog modal.
   - Verifikasi:
     - Kartu kembali menampilkan badge **`Artwork Resmi`** dan poster Wave 6.10 tampil kembali di seluruh halaman UI.
     - SQL read-only Cloud: `0` baris pada `public.game_artwork_overrides` untuk game tersebut, `0` objek tersisa di `storage.objects` (`bucket_id = 'game-artwork'`), dan entri `GAME_ARTWORK_RESTORED` tercatat di `public.activity_logs`.
6. **Pembersihan Sesi Lokal:**
   ```powershell
   Remove-Item Env:APP_MODE, Env:SECRET_KEY, Env:SUPABASE_URL, Env:SUPABASE_PUBLISHABLE_KEY -ErrorAction SilentlyContinue
   ```
   Pastikan `.env` tetap tidak ada (`False`) dan Public Signup tetap `DISABLED`.

### 7.9 Hasil Pengujian Aktual Pasca-Revisi Split Deployment

Seluruh pengujian di bawah dijalankan setelah revisi [20261126232622_wave6_11_custom_game_artwork.sql](file:///C:/Turnamen.in/supabase/migrations/20261126232622_wave6_11_custom_game_artwork.sql), [test_wave4b_postgres_migrations_and_security.py](file:///C:/Turnamen.in/tests/integration/test_wave4b_postgres_migrations_and_security.py), dan [test_wave6_11_custom_game_artwork.py](file:///C:/Turnamen.in/tests/unit/test_wave6_11_custom_game_artwork.py):

- **PostgreSQL 17.11 Migration & Split-Ownership Simulation (`TURNAMEN_EXPECTED_PG_MAJOR=17`):** **`15 passed in 24.94s`** (`0 failed`, `0 skipped`):
  - `test_wave6_11_split_storage_deployment_ownership_and_dashboard_policies`: Membuktikan secara langsung pada PostgreSQL `17.11` bahwa role non-superuser `cloud_deploy_postgres` (bukan anggota `supabase_storage_admin`) ditolak jika mencoba `CREATE POLICY` di `storage.objects`, berhasil menjalankan `20261126232622_wave6_11_custom_game_artwork.sql` (`exit code = 0`) untuk tabel `game_artwork_overrides` + bucket `game-artwork`, gagal-tertutup (`InsufficientPrivilege`) saat upload sebelum 4 policy Dashboard dipasang, lalu keempat policy `storage.objects` (dipasang sebagai `supabase_storage_admin`) mengizinkan `super_admin` aktif dan memblokir listing maupun mutasi dari `anon` dan `player`.
  - `test_upload_failure_and_metadata_rollback_cleanup_with_supabase_adapter`: Memastikan pada kondisi fail-closed (`403` saat upload ke `storage.objects`), `GET /api/v1/games` tetap mengembalikan `200` dengan artwork resmi Wave 6.10.
- **Keseluruhan Suite (`.\.venv\Scripts\python.exe -m pytest -q`):** **`304 passed, 4 warnings in 64.36s`** (`0 failed`, `0 skipped`).
- **Dry-Run CLI `2.104.0` pada PostgreSQL 17.11 Lokal (`PGSSLMODE=disable`):** `rc = 0`, `Would push these migrations: • 20261126232622_wave6_11_custom_game_artwork.sql` (nol migrasi lama/seed).

### 7.10 Status Akhir & Titik Henti

- **Status Persiapan Deployment:** **`READY FOR EXPLICIT DEPLOYMENT APPROVAL (HELD)`** *(Tahap persiapan selesai sebelum eksekusi deployment pada Bagian 8).*

---

## 8. Hasil Aktual Deployment Migration Wave 6.11 (`DEPLOYED_AND_VERIFIED`)

Eksekusi deployment Tahap A (`supabase db push`) dijalankan pada **`2026-11-28T07:36:50+07:00`** terhadap project `cfdsgxciodfkamskafwe` (PostgreSQL `17.11`, Supabase CLI `2.104.0`, bukti utama `wave611_deploy_result.json`):

| Pemeriksaan Pasca-Deployment | Hasil Aktual Cloud | Target | Status |
| :--- | :--- | :--- | :---: |
| **Preflight Lokal & Hash SQL** | `20261126232622_wave6_11_custom_game_artwork.sql` (`5,717` bytes, SHA-256 `F82A0499...36FBFA55`), backup `turnamen-in-pre-w611-20261128-063810.dump` utuh (`188,535` bytes, SHA-256 `3F852F4F...CA2900F`), `.env` tidak ada | Cocok 100% | **PASS** |
| **Dry-Run Gate & `supabase db push`** | `dry_run rc = 0` (`only_wave611_pending: true`), lalu `db push rc = 0` (`Applying migration 20261126232622_wave6_11_custom_game_artwork.sql...`, tanpa `--include-all` & tanpa `--include-seed`) | 1 migrasi diterapkan bersih | **PASS** |
| **Migration History (`schema_migrations` & CLI)** | **`7` baris** (`0001`-`0006` + `20261126232622` `wave6_11_custom_game_artwork`); `supabase migration list` menampilkan `Local == Remote` seluruhnya | `7` baris tersinkron | **PASS** |
| **Tabel `public.game_artwork_overrides`** | Terbentuk (`10` kolom, `3` index, `1` trigger `trg_game_artwork_overrides_updated_at`, `9` constraints `c/f/p/u`, `rls_enabled = true`, `14` total tabel `public` ber-RLS aktif) | Struktur & RLS aktif | **PASS** |
| **Grants & 4 RLS Policies Tabel** | `anon`: `SELECT`; `authenticated`: `DELETE,INSERT,SELECT,UPDATE`; `4` policy terpasang (`Public read`, `Super admin insert/update/delete`) | Least-privilege RLS | **PASS** |
| **Bucket `game-artwork` (`storage.buckets`)** | `id = 'game-artwork'`, `public = true`, `file_size_limit = 5242880`, `allowed_mime_types = ['image/jpeg', 'image/png', 'image/webp']` | Sesuai spesifikasi | **PASS** |
| **Non-Regresi Data & Auth** | `games = 3`, `profiles = 5` (`1` linked active `super_admin`), `auth.users = 1`, `game_artwork_overrides = 0` baris, `0` objek terunggah, Public Signup tetap `DISABLED` | Data inti utuh & 0 upload | **PASS** |
| **Status `storage.objects` Saat Titik Henti** | `0` policy saat verifikasi pasca-push (`storage_objects_policies_still_0 = true`); kemudian 4 policy dibuat melalui Dashboard dan diaudit pada Bagian 9 | Audit read-only Cloud **PASS** | **DONE** |

---

## 9. Hasil Final Audit Read-Only 4 Storage Policies (`PASS`) & Kesiapan Pengujian Live

### 9.1 Hasil Audit Catalog Cloud (`2026-11-28T08:50:03+07:00`, PostgreSQL `17.11`)

Audit read-only (`default_transaction_read_only=on`, `SET LOCAL search_path = ''`, sumber `wave611_storage_policy_audit_result.json`) memastikan bahwa `storage.objects` (`relrowsecurity = true`, owner `supabase_storage_admin`, `0` objek pada bucket `game-artwork`) memiliki tepat **4 policy** `PERMISSIVE` yang hanya berlaku untuk `authenticated`, seluruhnya membatasi `bucket_id = 'game-artwork'`, dan seluruhnya memeriksa `public.current_user_role() = 'super_admin'`:

| # | Nama Policy Aktual (`polname`) | Operasi (`polcmd`) | `polroles` | `polqual` (`USING`) | `polwithcheck` (`WITH CHECK`) & Sumber Efektif | Status |
| :-: | :--- | :---: | :---: | :--- | :--- | :---: |
| **1** | `Super admin delete game-artwork objects 7v7oyh_0` | `DELETE` (`d`) | `["authenticated"]` | `((bucket_id = 'game-artwork'::text) AND ((( SELECT public.current_user_role() AS current_user_role))::text = 'super_admin'::text))` | `NULL` (`not_applicable`) | **PASS** |
| **2** | `\tSuper admin insert game-artwork objects 7v7oyh_0` | `INSERT` (`a`) | `["authenticated"]` | `NULL` | `((bucket_id = 'game-artwork'::text) AND ((( SELECT public.current_user_role() AS current_user_role))::text = 'super_admin'::text))` (`explicit_polwithcheck`) | **PASS** |
| **3** | `Super admin update game-artwork objects 7v7oyh_1` | `SELECT` (`r`) | `["authenticated"]` | `((bucket_id = 'game-artwork'::text) AND ((( SELECT public.current_user_role() AS current_user_role))::text = 'super_admin'::text))` | `NULL` (`not_applicable`) | **PASS** |
| **4** | `Super admin update game-artwork objects 7v7oyh_0` | `UPDATE` (`w`) | `["authenticated"]` | `((bucket_id = 'game-artwork'::text) AND ((( SELECT public.current_user_role() AS current_user_role))::text = 'super_admin'::text))` | `NULL` (`implicit_from_using`: PostgreSQL menegakkan ekspresi `USING` sebagai `WITH CHECK` efektif) | **PASS** |

- **Seluruh 9 Pemeriksaan Validator (`wave611_audit_storage_policies.py --reevaluate-json`, `rc = 0`):**
  - `objects_rls_enabled`: **PASS** (`true`)
  - `bucket_game_artwork_valid`: **PASS** (`public = true`, `5242880` bytes, `['image/jpeg', 'image/png', 'image/webp']`)
  - `total_policies_is_4`: **PASS** (`4`)
  - `exact_4_operations_present`: **PASS** (`SELECT`, `INSERT`, `UPDATE`, `DELETE`)
  - `all_only_authenticated`: **PASS** (`["authenticated"]` pada keempat policy)
  - `zero_anon_or_public_policies`: **PASS** (`0` policy `anon`/`PUBLIC`)
  - `all_restrict_bucket_game_artwork`: **PASS**
  - `all_require_public_current_user_role_super_admin`: **PASS**
  - `no_or_bypass_or_unintended_roles`: **PASS**
- **Catatan Kosmetik Dashboard (Non-Keamanan):** Nama policy `INSERT` diawali karakter tab (`\t`) dan policy `SELECT` memakai nama `Super admin update game-artwork objects 7v7oyh_1` (dibuat otomatis oleh UI Dashboard sebagai pasangan `SELECT`), namun predikat `polqual` dan target role-nya identik 100% dan aman. Keempat policy Cloud dipertahankan utuh tanpa diubah atau dihapus.

### 9.2 Penjelasan False Positive Validator Sebelumnya & Pembuktian PostgreSQL `17.11`

- Pada eksekusi audit awal (`2026-11-28T08:50:03+07:00`), tiga pemeriksaan (`all_restrict_bucket_game_artwork`, `all_require_public_current_user_role_super_admin`, dan `no_or_bypass_or_unintended_roles`) gagal bukan karena celah Cloud, melainkan karena validator versi pertama mewajibkan `polwithcheck IS NOT NULL` pada operasi `UPDATE`.
- Ketika policy `UPDATE` dibuat lewat UI Storage Policies Dashboard dengan hanya `USING`, PostgreSQL menyimpan `polwithcheck = NULL` dan **otomatis menggunakan ekspresi `USING` (`polqual`) untuk memvalidasi baris baru hasil pembaruan (`WITH CHECK`)**.
- Pembuktian langsung pada klaster lokal **PostgreSQL `17.11`** memastikan bahwa `UPDATE storage.objects SET bucket_id = 'other-bucket'` di bawah role `authenticated` dengan `polwithcheck IS NULL` tetap **ditolak** (`SQLSTATE 42501: new row violates row-level security policy for table "objects"`).
- Setelah `wave611_audit_storage_policies.py` diperbarui untuk mengenali `implicit_from_using` pada `UPDATE` (dan tetap memeriksa `explicit_polwithcheck` bila diisi), re-evaluasi atas snapshot Cloud menghasilkan **`PASS` penuh (9/9 checks, 4/4 policies)**.

### 9.3 Kesiapan Skrip Pengujian Live (Menunggu Persetujuan Eksplisit)

Skrip pengujian live sudah disiapkan di luar repository pada `%LOCALAPPDATA%\TurnamenBackups\wave611_live_test.py` (`py_compile` exit `0`, tanpa `.env`, tanpa `service_role`, Public Signup tetap `DISABLED`, seluruh secret di-scrub dari `wave611_live_test_result.json`):

1. **Uji Penolakan Anonim, Payload Berbahaya & User Biasa (Stage 2):**
   - Request anonim ke `POST /api/v1/games/<id>/artwork` dan `DELETE /api/v1/games/<id>/artwork` wajib mengembalikan `401`.
   - Permintaan listing objek pada bucket `game-artwork` dengan kunci `anon`/publishable tanpa JWT wajib mengembalikan `[]` (atau ditolak RLS).
   - Opsional uji akun non-admin live (jika kredensial non-admin dimasukkan operator; bila di-skip karena Public Signup `DISABLED` dan `auth.users = 1`, penolakan `403` + RLS tetap terverifikasi pada suite `pytest` & PG `17.11`).
   - Upload SVG tersamar dan file `> 5 MB` sebagai `super_admin` wajib ditolak `400` sebelum menyentuh Storage Cloud.
2. **Siklus Upload, Ganti Poster, Verifikasi Lintas Halaman & Restore (Stage 3-6):**
   - **Upload Poster Baru (`super_admin`):** Unggah PNG 16:9 valid (`640x360`), verifikasi `200`, `artwork_source = "custom"`, HTTP `GET` publik ke `custom_artwork_url` mengembalikan `200 OK` (`image/png`), dan endpoint `/api/v1/games`, `/api/v1/tournaments`, serta `/api/v1/teams` konsisten.
   - **Ganti Poster (`super_admin`):** Unggah WebP 16:9 valid (`1280x720`), verifikasi URL baru aktif (`200 OK`), URL lama sudah terhapus (`400`/`404`, anti-orphan), dan opsi `--pause-for-ui-check` memungkinkan pemeriksaan visual lintas halaman pada Desktop UI sebelum restore.
   - **Restore Artwork Resmi (`super_admin`):** Jalankan `DELETE /api/v1/games/<id>/artwork`, verifikasi kembali ke `artwork_source = "official"`, `custom_artwork_url = null`, objek kedua terhapus dari Storage (`400`/`404`), dan logout bersih.

### 9.4 Status Akhir & Titik Henti

- **Status Tahap Audit Storage Policies:** **`STORAGE POLICIES AUDITED PASS`** *(Dilanjutkan ke verifikasi live Supabase Cloud pada Bagian 10).*

---

## 10. Hasil Verifikasi Live Supabase Cloud (28 November 2026)

### 10.1 Metadata Eksekusi & Keamanan Kredensial

- **Waktu Eksekusi Aktual:** `2026-11-28T09:20:23.574019+07:00`
- **Lokasi File Hasil Ter-Redaksi:** `%LOCALAPPDATA%\TurnamenBackups\wave611_live_test_result.json` (`status: "PASSED"`, `ok: true`)
- **Konfigurasi Klien:** `supabase_url = https://cfdsgxciodfkamskafwe.supabase.co`, `app_mode = supabase`, `key_type = publishable` (menggunakan `SUPABASE_PUBLISHABLE_KEY`, tanpa `service_role` maupun `sb_secret_*`), dan **`dotenv_exists = false`** (`.env` tidak dibuat).
- **Target Game Uji:** `Mobile Legends: Bang Bang` (`id: 22222222-2222-4222-8222-222222222201`, `slug: mobile-legends`).
- **Pengaturan Auth & Signup:** Public Signup tetap `DISABLED`; seluruh rahasia/token/password di-redaksi dari output dan file hasil.

### 10.2 Ringkasan Hasil 7 Tahap Pengujian Live (`7/7 PASS`)

| Tahap Pengujian | Bukti Respons & Observasi Aktual | Status |
| :--- | :--- | :---: |
| **1. `stage1_smoke`** | `GET /api/v1/health` -> `200`; `GET /api/v1/games` -> `200` (`3` game, seluruhnya `artwork_source = "official"`, `custom_artwork_url = null`). | **PASS** |
| **2. `stage2_negative_security`** | Anon `POST` -> `401`; Anon `DELETE` -> `401`; Anon `storage.from_("game-artwork").list()` -> `0` entri (`anon_storage_list_blocked: true`); Anon `storage.upload()` -> ditolak RLS (`StorageApiError`); Login `super_admin` -> `200` (`role = "super_admin"`); Upload SVG tersamar -> `400`; Upload `> 5 MB` -> `400`. *(Uji akun non-admin live tidak dijalankan; lihat Bagian 10.3.)* | **PASS** |
| **3. `stage3_upload_new_poster`** | `POST /api/v1/games/22222222-2222-4222-8222-222222222201/artwork` (PNG) -> **`200`** (`storage_path: mobile-legends/84ea7d36-b90d-44b4-ad71-342fccca0fb3.png`); HTTP `GET` publik ke URL objek PNG -> **`200`** (`Content-Type: image/png`); `games_api_reflects_custom_url: true`; `GET /api/v1/tournaments` -> `200`; `GET /api/v1/teams` -> `200`. | **PASS** |
| **4. `stage4_replace_poster`** | `POST /api/v1/games/22222222-2222-4222-8222-222222222201/artwork` (WebP) -> **`200`** (`storage_path: mobile-legends/332316b4-2944-4363-86e3-eef45ecffdb3.webp`); HTTP `GET` URL WebP baru -> **`200`** (`Content-Type: image/webp`); HTTP `GET` URL PNG lama pasca-cleanup -> **`400`** (`Content-Type: application/json; charset=utf-8`, `bytes_preview_len: 0`, objek lama sudah terhapus); `games_api_reflects_replaced_url: true`. | **PASS** |
| **5. `stage5_restore_official`** | `DELETE /api/v1/games/22222222-2222-4222-8222-222222222201/artwork` -> **`200`** (`artwork_source: "official"`, `custom_artwork_url: null`); HTTP `GET` URL WebP kedua pasca-restore -> **`400`** (`Content-Type: application/json; charset=utf-8`, `bytes_preview_len: 0`); `all_games_official_after_restore: true`. | **PASS** |
| **6. `stage6_post_restore_verification`** | `games_count = 3`, `overrides_count = 0`, `storage_root_file_count = 0`, `storage_mlbb_file_count = 0`, `profiles_unchanged = true`, dan `dotenv_exists = false`. | **PASS** |
| **7. `stage7_logout`** | `POST /api/v1/auth/logout` -> **`200`**. | **PASS** |

*(Catatan cakupan visual UI: `pause_for_ui_check = false`, sehingga verifikasi tampilan lintas halaman Desktop UI pada sesi uji live ini dicakup melalui verifikasi API `/api/v1/games`, `/api/v1/tournaments`, dan `/api/v1/teams` beserta pengujian Node VM UI pada Bagian 4.)*

### 10.3 Catatan Eksplisit Pengujian Akun Non-Admin Live (TIDAK DIJALANKAN)

- Pengujian live untuk akun non-admin (`player`, `organizer`, `committee`, atau `team_captain`) **tidak dijalankan** (`non_admin.executed = false`, `status: "skipped_single_auth_user_public_signup_disabled"`).
- Alasan teknis: Pada Supabase Cloud hanya terdapat `1` Auth user aktif (`super_admin`) dan Public Signup tetap `DISABLED`, sehingga tidak tersedia akun Auth non-admin untuk login live.
- **Kejelasan Status:** Pengujian akun non-admin live **tidak diklaim PASS**. Penegakan izin non-admin (`403` pada API dan penolakan `INSERT`/`UPDATE`/`DELETE`/`SELECT` listing pada PostgreSQL `game_artwork_overrides` & `storage.objects`) dibuktikan pada suite unit/integrasi lokal (Bagian 4 dan 7.9) dan dapat diuji live apabila akun non-admin ditambahkan di masa mendatang.

### 10.4 Perbandingan Snapshot Sebelum vs Sesudah Pengujian Live

| Metrik Snapshot (`pre_test_snapshot` vs `post_snapshot`) | Sebelum Uji Live | Sesudah Restore | Status |
| :--- | :---: | :---: | :---: |
| **`games_count`** | `3` | `3` | **MATCH** |
| **`overrides_count` (`public.game_artwork_overrides`)** | `0` | `0` | **MATCH** |
| **`storage_root_entries_count` (`game-artwork`)** | `0` | `0` | **MATCH** |
| **`storage_root_file_count` (`game-artwork`)** | `0` | `0` | **MATCH** |
| **`storage_mlbb_file_count` (`mobile-legends/`)** | `0` | `0` | **MATCH** |
| **`profiles_total`** | `5` | `5` | **MATCH** |
| **`profiles_active`** | `5` | `5` | **MATCH** |
| **`profiles_linked` (`auth_user_id IS NOT NULL`)** | `1` | `1` | **MATCH** |
| **`profiles_role_counts`** | `committee: 1, organizer: 1, player: 1, super_admin: 1, team_captain: 1` | `committee: 1, organizer: 1, player: 1, super_admin: 1, team_captain: 1` | **MATCH** |
| **`dotenv_exists`** | `false` | `false` | **MATCH** |

### 10.5 Kesimpulan & Status Penyelesaian Wave 6.11

- Seluruh **3 game** pada Supabase Cloud telah kembali menggunakan artwork resmi Wave 6.10 (`artwork_source = "official"`, `custom_artwork_url = null`).
- Tidak ada objek Storage pengujian maupun baris metadata `public.game_artwork_overrides` yang tertinggal (`0` objek, `0` baris).
- Tidak ada perubahan pada akun Auth, tabel `public.profiles`, kebijakan RLS, maupun konfigurasi Public Signup (`DISABLED`), serta tidak ada file `.env` atau penggunaan `service_role`.
- **Status Akhir Wave 6.11:** **`COMPLETED & LIVE-VERIFIED ON SUPABASE CLOUD`** *(dengan catatan eksplisit bahwa uji akun non-admin live ditangguhkan/tidak dijalankan karena hanya ada 1 Auth user dan Public Signup `DISABLED`)*.
