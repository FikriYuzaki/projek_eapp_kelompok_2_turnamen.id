---
name: turnamen-project-standards
description: Standar arsitektur, konvensi penamaan, kontrak API/database, kepemilikan modul, dan workflow pengembangan paralel Single-Main untuk seluruh anggota Turnamen.in.
---

# Turnamen.in — Project Standards (`turnamen-project-standards`)

Skill ini wajib dibaca oleh **seluruh anggota kelompok** (Ferlita, Fikri, Habil, Adriel, dan Anisa) sebelum menulis atau mengubah kode di repository Turnamen.in.

## 1. Scope
Mencakup standar global arsitektur aplikasi desktop Turnamen.in, konvensi kode Python/JavaScript/SQL, aturan kontrak antarmodul, mode operasi (`mock` dan `supabase`), serta alur kerja Git satu branch (`main`).

## 2. Responsibilities
- Menjaga konsistensi pemisahan layer antara Desktop UI, API Client/Bridge, Flask REST API, Application Services, dan Repository.
- Memastikan seluruh anggota mengembangkan fitur berdasarkan kontrak yang telah disepakati di `docs/contracts/`.
- Memastikan aplikasi selalu dapat dijalankan dalam `APP_MODE=mock` tanpa kredensial cloud.

## 3. Architecture Rules
Alur arsitektur resmi Turnamen.in:
```text
Desktop UI → API Client / Bridge → Flask REST API → Application Services → Repository → Supabase PostgreSQL (atau Mock Repository)
```
- **Satu Tempat Business Logic:** Jangan menduplikasi logika bisnis di Python Eel dan Flask secara terpisah. Seluruh aturan domain berada di `backend/modules/<module>/service.py`.
- **Bahasa Identifier vs Dokumentasi:** Gunakan bahasa Inggris (`snake_case` untuk Python/SQL, `camelCase` untuk JavaScript) pada identifier kode, nama fungsi, variabel, dan nama tabel. Gunakan bahasa Indonesia yang jelas untuk dokumentasi, komentar penjelas bisnis, dan pesan antarmuka pengguna.
- **Konvensi Response API:** Seluruh endpoint `/api/v1/*` wajib mengembalikan JSON dengan struktur `{ "success": bool, "message": str, "data": ... }` untuk sukses, atau `{ "success": false, "message": str, "error": { "code": str, "details": ... } }` untuk error.
- **Konvensi Database:** Gunakan UUID sebagai primary key, `created_at` dan `updated_at` (`TIMESTAMPTZ`), serta constraint eksplisit di PostgreSQL.

## 4. Allowed Directories (Module Ownership)
| Anggota | Peran | Direktori Utama |
| :--- | :--- | :--- |
| **Ferlita** | Project Coordinator & UI/UX Designer | `desktop/web/pages/`, `desktop/web/assets/css/`, `desktop/web/assets/images/`, `DESIGN.md` |
| **Fikri** | System Integration & Python Eel Developer | `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py` |
| **Habil** | Database & Authentication Developer | `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/` |
| **Adriel** | Tournament & Match System Developer | `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/` |
| **Anisa** | REST API, Reporting & Testing Developer | `backend/api/`, `backend/modules/reports/`, `backend/modules/announcements/`, `tests/`, `docs/api/` |

## 5. Prohibited Changes
- Dilarang mengubah file di luar direktori kepemilikan tanpa koordinasi terlebih dahulu.
- Dilarang mengubah struktur tabel database, format JSON API, atau tanda tangan interface repository tanpa memperbarui dokumen di `docs/contracts/`.
- Dilarang menambahkan framework besar (React, Vue, Angular, SQLAlchemy) tanpa persetujuan arsitektur.
- Dilarang menyimpan kredensial nyata, `.env`, atau `service_role` key ke dalam repository.
- Dilarang membuat branch Git terpisah atau melakukan `git push --force` ke `main`.

## 6. Required Dependencies
- Python 3.10+ (direkomendasikan 3.11/3.12 di Windows 10/11).
- Paket terpin di `requirements.txt` (`Flask`, `Eel`, `python-dotenv`, `supabase`, `pytest`, `requests`).

## 7. Development Workflow
1. Jalankan `git pull origin main` sebelum mulai bekerja.
2. Pastikan `.env` lokal menggunakan `APP_MODE=mock` untuk pengembangan harian.
3. Jalankan `pytest` untuk memastikan kondisi awal bersih.
4. Kembangkan modul pada folder masing-masing mengacu pada interface di `backend/repositories/interfaces/`.
5. Uji kembali dengan `pytest` sebelum melakukan commit dan push ke `main`.

## 8. Testing Requirements
- Setiap perubahan logika domain atau endpoint API wajib disertai unit/integration test di `tests/`.
- Seluruh pengujian wajib lulus dalam `APP_MODE=mock` tanpa akses internet.

## 9. Acceptance Criteria
- Kode mengikuti struktur modular tanpa circular import.
- Tidak ada kredensial atau secret yang bocor di kode maupun log.
- Seluruh test yang ada di `tests/` berjalan hijau (`pytest`).

## 10. Integration Contracts
- Database Contract: `docs/contracts/database-contract.md`
- REST API Contract: `docs/contracts/api-contract.md`
- Frontend Contract: `docs/contracts/frontend-contract.md`
- Module & Service Contract: `docs/contracts/module-contract.md`
- Role & Permission Matrix: `docs/contracts/role-permissions.md`
