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
1. Memelihara skema 12 tabel di [`supabase/migrations/0001_initial_schema.sql`](file:///C:/Turnamen.in/supabase/migrations/0001_initial_schema.sql) dan dokumentasi [`docs/database-schema.md`](file:///C:/Turnamen.in/docs/database-schema.md).
2. Memelihara data seed SQL di [`supabase/seed.sql`](file:///C:/Turnamen.in/supabase/seed.sql) agar selaras dengan data mock Python.
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
- `supabase/seed.sql`
- `backend/infrastructure/supabase/client.py`
- `backend/repositories/interfaces/repository_protocol.py`
- `backend/repositories/mock/mock_data.py`
- `backend/repositories/mock/mock_repository.py`
- `backend/repositories/supabase/supabase_repository.py`
- `backend/repositories/factory.py`
- `backend/modules/auth/permissions.py`
- `backend/modules/auth/service.py`

## 6. Batas File yang Tidak Boleh Diubah Tanpa Koordinasi
- `desktop/web/pages/*` dan `desktop/web/assets/css/*` (Milik **Ferlita**).
- `desktop/launcher/*`, `desktop/bridge/*`, dan `run.py` (Milik **Fikri**).
- `backend/modules/tournaments/*`, `backend/modules/teams/*`, dan `backend/modules/matches/*` (Milik **Adriel**).
- `backend/api/*`, `backend/modules/reports/*`, dan `backend/modules/announcements/*` (Milik **Anisa**).

## 7. Dependensi Modul
- Menyediakan instance repository melalui `get_repository()` (`backend/repositories/factory.py`) bagi seluruh service milik Adriel dan Anisa.
- Menyediakan layanan `AuthService` dan helper `RolePermissionGuard` bagi endpoint Flask API milik Anisa.

## 8. Kontrak Input / Output
- **Kontrak Database:** Sesuai [`docs/contracts/database-contract.md`](file:///C:/Turnamen.in/docs/contracts/database-contract.md).
- **Kontrak Repository:** Seluruh method di `DataStoreRepositoryProtocol` mengembalikan `dict` atau `list[dict]` dengan nama field yang identik antara mode `mock` dan `supabase`.
- **Kontrak Role & Izin:** Sesuai [`docs/contracts/role-permissions.md`](file:///C:/Turnamen.in/docs/contracts/role-permissions.md).

## 9. Mock Data yang Tersedia
File `backend/repositories/mock/mock_data.py` menyediakan dataset awal yang konsisten:
- 5 akun profil (`super_admin`, `organizer`, `committee`, `team_captain`, `player`) dengan password demo `turnamen123`.
- 3 game, 2 turnamen, 8 tim, 16 anggota tim, 8 registrasi `approved`, 7 pertandingan bracket 8 tim, pengumuman, dan activity logs.

## 10. Cara Menjalankan Modul
```powershell
# Menjalankan unit test khusus autentikasi, permission, dan repository dalam mock mode
pytest tests/unit/test_auth_and_permissions.py -v
```

## 11. Skenario Pengujian
1. **Test Login & Sesi Mock:** Login dengan `organizer@turnamen.in` / `turnamen123`, pastikan token dikembalikan dan `get_current_user(token)` mengenali role `organizer`.
2. **Test Anti-Privilege Escalation:** Coba lakukan `register` dengan meminta `role="super_admin"`, pastikan ditolak oleh `AuthService` dengan `FORBIDDEN`.
3. **Test Matriks RBAC:** Pastikan role `player` ditolak saat mencoba membuat turnamen atau mengesahkan skor pertandingan.
4. **Test Konsistensi Repository:** Pastikan operasi CRUD pada `MockDataStoreRepository` menjaga integritas foreign key (`game_id`, `tournament_id`, `team_id`).

## 12. Acceptance Criteria
- 12 tabel PostgreSQL lengkap dengan PK UUID, FK, unique/check constraints, trigger `updated_at`, index, dan kebijakan dasar RLS.
- Tidak ada penggunaan `service_role` key di sisi klien atau penyimpanan password plaintext.
- Keputusan otorisasi didasarkan pada `profiles.role`, bukan metadata yang dapat diedit pengguna.

## 13. Checklist Pekerjaan
- [ ] Memverifikasi DDL di `supabase/migrations/0001_initial_schema.sql` dan `supabase/seed.sql`.
- [ ] Memastikan `MockDataStoreRepository` dan `SupabaseDataStoreRepository` mematuhi `DataStoreRepositoryProtocol`.
- [ ] Memastikan seluruh 5 role diuji pada `tests/unit/test_auth_and_permissions.py`.
- [ ] Menyempurnakan kebijakan RLS dan adapter Supabase saat kredensial proyek uji tersedia.

## 14. Git Branch Assignment & Workflow

Lihat panduan lengkap Git di [`docs/GIT_WORKFLOW.md`](file:///C:/Turnamen.in/docs/GIT_WORKFLOW.md).

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
- **Jika branch sudah ada di remote (`origin`):**
  ```powershell
  git fetch origin
  git switch feature/habil-database-auth
  git pull --ff-only
  ```
- **Jika branch sudah ada di komputer lokal:**
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
