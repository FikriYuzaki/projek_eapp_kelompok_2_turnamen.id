# Instruksi Tugas Mandiri: HABIL (Database & Authentication Developer)

---

## 1. Identitas dan Tanggung Jawab Anggota
- **Nama Anggota:** Habil
- **Peran:** Database & Authentication Developer
- **Branch Resmi:** `feature/habil-database-auth`
- **Tanggung Jawab Utama:**
  - Merancang ERD, 12 tabel PostgreSQL, relasi, constraints, trigger, dan index.
  - Menyiapkan file migrasi Supabase PostgreSQL (`0001_initial_schema.sql`) dan data awal (`seed.sql`).
  - Mengembangkan modul autentikasi (`register`, `login`, `logout`, `me`) dan pengelolaan profil.
  - Mengatur Role-Based Access Control (RBAC 5 role) dan Row Level Security (RLS).
  - Menyiapkan interface repository, `MockDataStoreRepository`, dan `SupabaseDataStoreRepository`.

## 2. Tujuan Pekerjaan
Menyediakan fondasi penyimpanan data dan keamanan identitas yang kokoh, di mana seluruh modul memiliki kontrak repository yang konsisten, dapat diuji secara penuh menggunakan `MockDataStoreRepository` (`APP_MODE=mock`), dan siap dihubungkan ke Supabase PostgreSQL (`APP_MODE=supabase`) dengan perlindungan RBAC dan RLS.

## 3. Daftar Tugas Terperinci
1. Memelihara skema 12 tabel di [`supabase/migrations/0001_initial_schema.sql`](../../supabase/migrations/0001_initial_schema.sql) dan dokumentasi [`docs/database-schema.md`](../database-schema.md).
2. Memelihara data seed SQL di [`supabase/seed.sql`](../../supabase/seed.sql) agar selaras dengan data mock Python.
3. Mengembangkan dan menyempurnakan kontrak repository di `backend/repositories/interfaces/repository_protocol.py`.
4. Memelihara implementasi `MockDataStoreRepository` di `backend/repositories/mock/` dan mengimplementasikan query nyata pada `SupabaseDataStoreRepository` di `backend/repositories/supabase/` saat proyek cloud siap diuji.
5. Mengembangkan layanan autentikasi dan otorisasi 5 role di `backend/modules/auth/` (`service.py` dan `permissions.py`).

## 4. Folder yang Menjadi Tanggung Jawab
- `supabase/`
- `backend/modules/auth/`
- `backend/infrastructure/supabase/`
- `backend/repositories/`
- `docs/database-schema.md`
- `docs/security.md`

## 5. File yang Harus Dibuat / Diubah
- `supabase/migrations/0001_initial_schema.sql`
- `supabase/migrations/0002_security_hardening.sql`
- `supabase/seed.sql`
- `backend/infrastructure/supabase/client.py`
- `backend/repositories/interfaces/repository_protocol.py`
- `backend/repositories/mock/mock_data.py`
- `backend/repositories/mock/mock_repository.py`
- `backend/repositories/supabase/supabase_repository.py`
- `backend/repositories/factory.py`
- `backend/modules/auth/permissions.py`
- `backend/modules/auth/service.py`
- `tests/unit/test_auth_and_permissions.py`

## 6. Batas File yang Tidak Boleh Diubah Tanpa Koordinasi
- `desktop/web/pages/*` dan `desktop/web/assets/css/*` (Milik **Ferlita**).
- `desktop/launcher/*`, `desktop/bridge/*`, dan `run.py` (Milik **Fikri**).
- `backend/modules/tournaments/*`, `backend/modules/teams/*`, dan `backend/modules/matches/*` (Milik **Adriel**).
- `backend/api/*`, `backend/modules/reports/*`, dan `backend/modules/announcements/*` (Milik **Anisa**).

## 7. Dependensi Modul
- Menyediakan instance repository melalui `get_repository()` (`backend/repositories/factory.py`) bagi seluruh service milik Adriel dan Anisa.
- Menyediakan layanan `AuthService` dan helper `RolePermissionGuard` bagi endpoint Flask API milik Anisa.

## 8. Kontrak Input / Output
- **Kontrak Database:** Sesuai [`docs/contracts/database-contract.md`](../contracts/database-contract.md).
- **Kontrak Repository:** Seluruh method di `DataStoreRepositoryProtocol` mengembalikan `dict` atau `list[dict]` dengan nama field yang identik antara mode `mock` dan `supabase`.
- **Kontrak Role & Izin:** Sesuai [`docs/contracts/role-permissions.md`](../contracts/role-permissions.md).

## 9. Mock Data yang Tersedia
File `backend/repositories/mock/mock_data.py` menyediakan dataset awal yang konsisten:
- 5 akun profil (`super_admin`, `organizer`, `committee`, `team_captain`, `player`) dengan password demo `turnamen123`.
- 3 game, 2 turnamen, 8 tim, 16 anggota tim, 8 registrasi `approved`, 7 pertandingan bracket 8 tim, pengumuman, dan activity logs.

## 10. Konfigurasi `.env`, Migrasi, dan Cara Menjalankan Pengujian

### A. Konfigurasi `.env`
- Mode default pengembangan lokal adalah `APP_MODE=mock` (tidak memerlukan koneksi internet atau kredensial cloud).
- Untuk mode online (`APP_MODE=supabase`), isi variabel berikut di `.env` lokal (jangan pernah di-commit ke Git):
  ```env
  APP_MODE=supabase
  SUPABASE_URL=https://<project-ref>.supabase.co
  SUPABASE_ANON_KEY=eyJ... # Gunakan 'anon' 'public' key berformat JWT dari Project Settings -> API
  ```
- **Penting:** Jangan pernah menggunakan `service_role` key atau `sb_secret_` key. `create_supabase_client()` akan menolak key tersebut secara otomatis.

### B. Cara Menjalankan Migrasi Database
Jalankan secara berurutan pada Supabase SQL Editor:
1. `supabase/migrations/0001_initial_schema.sql`
2. `supabase/migrations/0002_security_hardening.sql`
3. `supabase/seed.sql` *(opsional untuk data awal)*

### C. Cara Menjalankan Pengujian
```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe run.py --check
.\.venv\Scripts\python.exe scripts/verify_starter.py
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

## 11. Skenario Pengujian
1. **Test Login & Sesi Mock:** Login 5 akun demo (`admin`, `organizer`, `committee`, `captain`, `player`) dengan password `turnamen123`, pastikan token `tok_` dikembalikan, `get_user_by_token()` mengenali role, dan `logout()` menghapus sesi.
2. **Test Pemisahan Mode Online Supabase Auth:** Pastikan pada mode Supabase (`is_supabase_mode=True`), registrasi, login, verifikasi token JWT, dan logout didelegasikan ke Supabase Auth (`auth_sign_up`, `auth_sign_in`, `auth_get_user`, `auth_sign_out`), tidak menyimpan `_sessions` atau `_password_hashes` di memori, menolak token `tok_`, dan menonaktifkan header simulasi mock.
3. **Test Validasi Kredensial Supabase Client:** Pastikan `create_supabase_client()` menolak `service_role` JWT, `sb_secret_` key, dan URL tidak valid tanpa melakukan monkey-patch pada modul internal SDK.
4. **Test Anti-Privilege Escalation:** Coba lakukan `register` dengan meminta `role="super_admin"`, `organizer`, atau `committee`, pastikan ditolak oleh `AuthService` dengan `FORBIDDEN` serta dijaga oleh trigger `trg_prevent_profile_privilege_escalation` di PostgreSQL.
5. **Test Konsistensi Repository & Transaksi Atomik Bracket:** Pastikan operasi CRUD menjaga integritas foreign key dan `replace_tournament_matches()` bersifat atomik (menggunakan RPC `public.replace_tournament_matches` pada Supabase dan validasi pra-mutasi pada Mock).

## 12. Acceptance Criteria
- 12 tabel PostgreSQL lengkap dengan PK UUID, FK (termasuk `profiles.auth_user_id -> auth.users(id)`), unique/check constraints, trigger `updated_at`, index, dan kebijakan RLS least-privilege di `0002_security_hardening.sql`.
- Tidak ada kebijakan RLS tulis terbuka (`FOR ALL USING (true)`) atau pembacaan publik pada tabel sensitif (`profiles`, `payments`, `activity_logs`, `tournament_staff`).
- Tidak ada penggunaan `service_role` key di sisi klien, monkey-patch SDK, atau penyimpanan password plaintext/fallback demo hash pada mode produksi.
- Keputusan otorisasi selalu didasarkan pada `public.profiles.role`, bukan metadata yang dapat diedit pengguna.

## 13. Checklist Pekerjaan
- [x] Memverifikasi DDL dasar di `supabase/migrations/0001_initial_schema.sql` dan `supabase/seed.sql`.
- [x] Menambahkan migrasi korektif keamanan RLS & Supabase Auth di `supabase/migrations/0002_security_hardening.sql`.
- [x] Memperbaiki `backend/infrastructure/supabase/client.py` tanpa monkey-patch regex global.
- [x] Memisahkan alur autentikasi `mock` dan `supabase` secara bersih di `AuthService` dan `SupabaseDataStoreRepository`.
- [x] Memastikan `MockDataStoreRepository` dan `SupabaseDataStoreRepository` mematuhi `DataStoreRepositoryProtocol` dengan penggantian bracket atomik.
- [x] Memastikan seluruh 5 role, validasi client, pemisahan auth online, dan kebijakan RLS diuji pada `tests/unit/test_auth_and_permissions.py`.

## 14. Git Branch Assignment & Workflow

Lihat panduan lengkap Git di [`docs/GIT_WORKFLOW.md`](../GIT_WORKFLOW.md).

### 1. Nama Branch Resmi
`feature/habil-database-auth`

### 2. Tanggung Jawab pada Branch Ini
Mengembangkan dan memelihara skema migrasi dan seed Supabase (`supabase/`), infrastruktur klien Supabase (`backend/infrastructure/supabase/`), kontrak dan implementasi repository (`backend/repositories/`), modul autentikasi dan matriks RBAC 5 role (`backend/modules/auth/`), serta dokumentasi database dan keamanan (`docs/database-schema.md`, `docs/security.md`).

### 3. Instruksi Membuat atau Berpindah ke Branch
- **Membuat branch pertama kali (jika belum ada di lokal maupun remote):**
  ```powershell
  git fetch origin
  git switch main
  git pull --ff-only origin main
  git switch -c feature/habil-database-auth
  git push -u origin feature/habil-database-auth
  ```
- **Jika branch sudah tersedia di remote (`origin`), tetapi belum ada di lokal:**
  ```powershell
  git fetch origin
  git switch --track origin/feature/habil-database-auth
  ```
- **Jika branch sudah tersedia secara lokal di komputer Anda:**
  ```powershell
  git switch feature/habil-database-auth
  git pull --ff-only
  ```

### 4. Perintah Git untuk Menyimpan Pekerjaan
Pastikan seluruh pengujian lulus dan tidak ada file `.env` atau kredensial rahasia yang ikut ditambahkan:
```powershell
pytest -v
python run.py --check
git status
git add supabase/ backend/modules/auth/ backend/infrastructure/supabase/ backend/repositories/ docs/database-schema.md docs/security.md
git commit -m "feat(db-auth): implement schema, rbac permissions, and repository layer"
```

### 5. Instruksi Push ke Branch Milik Habil
Jangan melakukan push langsung ke `main` dan jangan menggunakan `--force`:
```powershell
git push origin feature/habil-database-auth
```
*(Atau cukup `git push` jika upstream `-u` sudah diatur).*

### 6. Instruksi Membuat Pull Request ke `main`
1. Buka repository GitHub: `https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`.
2. Pilih branch `feature/habil-database-auth` lalu klik **`Compare & pull request`**.
3. Pastikan **base** adalah `main` dan **compare** adalah `feature/habil-database-auth`.
4. Tulis ringkasan perubahan database/auth/repository, daftar file yang diubah, dan hasil pengujian `pytest -v`.
5. Klik **`Create pull request`** dan tunggu review sebelum merge.
6. Untuk menyinkronkan branch dengan pembaruan terbaru dari `main`:
   ```powershell
   git fetch origin
   git switch feature/habil-database-auth
   git merge origin/main
   ```

### 7. Aturan Koordinasi Lintas Modul
- Apabila ada perubahan pada tanda tangan method di `DataStoreRepositoryProtocol` atau struktur field tabel, wajib dikoordinasikan terlebih dahulu dengan **Adriel** (`feature/adriel-tournament-match`) dan **Anisa** (`feature/anisa-api-report`), serta diperbarui pada `docs/contracts/database-contract.md` dan `docs/contracts/module-contract.md`.
- Apabila ada penambahan atau perubahan variabel environment untuk koneksi Supabase, koordinasikan dengan **Fikri** (`feature/fikri-eel`).

## 15. Agent Skills yang Wajib Dibaca Berdasarkan Addendum
Sebelum meminta bantuan AI Agent, pastikan agent membaca `AGENTS.md`, file tugas ini (`docs/tasks/habil.md`), `docs/GIT_WORKFLOW.md`, dan memuat skill berikut dari `.agents/skills/`:
- **Wajib:**
  - `antislop` (`.agents/skills/antislop/SKILL.md`)
  - `antislop-code` (`.agents/skills/antislop-code/SKILL.md`)
  - `turnamen-project-standards` (`.agents/skills/turnamen-project-standards/SKILL.md`)
  - `turnamen-supabase-security` (`.agents/skills/turnamen-supabase-security/SKILL.md`)
  - `turnamen-quality-gates` (`.agents/skills/turnamen-quality-gates/SKILL.md`)
- **Tambahan:**
  - `supabase` (`.agents/skills/supabase/SKILL.md`)
  - `supabase-postgres-best-practices` (`.agents/skills/supabase-postgres-best-practices/SKILL.md`)
  - `tdd` (`.agents/skills/tdd/SKILL.md`)
