---
name: turnamen-supabase-security
description: Panduan desain PostgreSQL schema, Supabase Auth, RBAC 5 role, Row Level Security (RLS), repository pattern, dan keamanan kredensial untuk Habil.
---

# Turnamen.in — Supabase, Database & Security (`turnamen-supabase-security`)

Skill ini ditujukan bagi **Habil (Database & Authentication Developer)** untuk mengelola skema PostgreSQL, autentikasi, otorisasi berbasis role (RBAC), Row Level Security (RLS), serta lapisan repository.

## 1. Scope
Mencakup migrasi dan seed SQL (`supabase/`), modul autentikasi & otorisasi (`backend/modules/auth/`), klien infrastruktur Supabase (`backend/infrastructure/supabase/`), serta kontrak dan implementasi repository (`backend/repositories/`).

## 2. Responsibilities
- Merancang dan memelihara 12 tabel inti PostgreSQL beserta primary key UUID, foreign key, unique/check constraint, trigger `updated_at`, dan index pencarian.
- Mengimplementasikan autentikasi (`register`, `login`, `logout`, `me`) dan pengelolaan profil pengguna.
- Menegakkan kontrol akses untuk 5 role resmi: `super_admin`, `organizer`, `committee`, `team_captain`, dan `player`.
- Menjaga kesetaraan perilaku antara `MockRepository` (`APP_MODE=mock`) dan `SupabaseRepository` (`APP_MODE=supabase`).

## 3. Architecture Rules
- **Aturan Kredensial Mutlak:** Jangan pernah menaruh `service_role` key atau secret database di dalam kode aplikasi desktop, frontend, atau repository Git. Gunakan `SUPABASE_ANON_KEY` (publishable key) bersama sesi pengguna dan kebijakan RLS.
- **Keamanan Role (Anti-Privilege Escalation):** Jangan pernah mengambil keputusan otorisasi dari `raw_user_meta_data` yang dapat diubah sendiri oleh pengguna. Simpan dan periksa role dari tabel `public.profiles` yang dilindungi oleh RLS dan validasi backend.
- **Kemandirian Mock Mode:** Aplikasi wajib dapat dijalankan sepenuhnya ketika `APP_MODE=mock` tanpa koneksi internet atau proyek Supabase aktif.

## 4. Allowed Directories
- `supabase/migrations/`
- `supabase/seed.sql`
- `backend/modules/auth/`
- `backend/infrastructure/supabase/`
- `backend/repositories/interfaces/`
- `backend/repositories/mock/`
- `backend/repositories/supabase/`
- `docs/database-schema.md`
- `docs/security.md`

## 5. Prohibited Changes
- Dilarang mengubah nama tabel atau kolom yang sudah tercantum di `docs/contracts/database-contract.md` tanpa persetujuan seluruh anggota.
- Dilarang menjalankan migrasi otomatis ke proyek cloud milik pengguna tanpa instruksi dan konfigurasi eksplisit.

## 6. Required Dependencies
- `supabase==2.7.4`, `Werkzeug==3.0.4` (untuk password hashing ` generate_password_hash` / `check_password_hash`).
- Skill referensi: `supabase` dan `supabase-postgres-best-practices`.

## 7. Development Workflow
1. Perbarui DDL di `supabase/migrations/` dan data awal di `supabase/seed.sql`.
2. Pastikan interface di `backend/repositories/interfaces/` mencerminkan operasi data yang dibutuhkan modul lain.
3. Implementasikan perubahan terlebih dahulu di `backend/repositories/mock/` agar anggota lain tidak terhambat, lalu selaraskan di `backend/repositories/supabase/`.
4. Jalankan `pytest` untuk memverifikasi autentikasi dan matriks izin role.

## 8. Testing Requirements
- Unit test untuk registrasi, login, pemeriksaan sesi/token, dan penolakan akses bagi role yang tidak berwenang.
- Verifikasi bahwa pengguna biasa (`player` / `team_captain`) tidak dapat menaikkan role miliknya sendiri menjadi `super_admin` atau `organizer`.

## 9. Acceptance Criteria
- 12 tabel utama terdokumentasi di `docs/database-schema.md` dan tersedia di `supabase/migrations/0001_initial_schema.sql`.
- Seluruh 5 role memiliki aturan izin yang jelas di `docs/contracts/role-permissions.md` dan ditegakkan di backend.
- Mock repository menyediakan data demo yang konsisten (3 game, 2 turnamen, 8 tim, bracket aktif).

## 10. Integration Contracts
- Database Contract: `docs/contracts/database-contract.md`
- Role & Permission Matrix: `docs/contracts/role-permissions.md`
- Module Contract: `docs/contracts/module-contract.md`
