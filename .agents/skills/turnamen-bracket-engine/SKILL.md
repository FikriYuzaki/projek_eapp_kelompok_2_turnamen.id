---
name: turnamen-bracket-engine
description: Panduan siklus hidup turnamen, registrasi tim, algoritma Single Elimination bracket, penanganan bye, validasi skor, dan perpindahan babak otomatis untuk Adriel.
---

# Turnamen.in — Tournament & Bracket Engine (`turnamen-bracket-engine`)

Skill ini ditujukan bagi **Adriel (Tournament & Match System Developer)** untuk mengembangkan logika domain turnamen, manajemen tim/peserta, dan mesin bracket Single Elimination.

## 1. Scope
Mencakup modul manajemen turnamen (`backend/modules/tournaments/`), manajemen tim & anggota (`backend/modules/teams/`), manajemen pertandingan & algoritma Single Elimination (`backend/modules/matches/`), serta unit test domain terkait.

## 2. Responsibilities
- Mengelola siklus status turnamen: `draft` → `open_registration` → `registration_closed` → `ongoing` → `completed` / `cancelled`.
- Mengelola pendaftaran tim (`pending`, `approved`, `rejected`, `withdrawn`) dan validasi kuota/roster.
- Membangun algoritma Single Elimination yang mendukung jumlah tim pangkat dua (mis. 8 tim: 4 QF → 2 SF → 1 Final) maupun bukan pangkat dua (otomatis menghitung slot *bye* ke pangkat dua terdekat berikutnya, mis. 5–7 tim dibulatkan ke bracket 8 slot dengan unggulan teratas mendapat status `bye`).
- Memvalidasi skor pertandingan sesuai format (`best_of`: 1, 3, 5, 7 dan aturan `allow_draw`), menetapkan pemenang, serta memajukan pemenang ke `next_match_id` pada `next_slot` (`A` atau `B`).

## 3. Architecture Rules
- **Pemenang Maju Hanya Setelah Hasil Sah:** Pertandingan berstatus `scheduled` atau `ongoing` tidak boleh memiliki `winner_team_id`. Pemenang hanya ditetapkan ketika hasil valid disahkan dan status berubah menjadi `completed` (atau `bye`).
- **Penanganan Seri (Draw):** Pada sistem gugur (*Single Elimination*), pertandingan tidak boleh berakhir seri kecuali aturan kompetisi secara eksplisit mengizinkan; jika `allow_draw=False`, skor imbang wajib ditolak dengan `VALIDATION_ERROR`.
- **Perlindungan Hasil yang Sudah Disahkan:** Pertandingan yang sudah `completed` tidak boleh diubah sembarangan tanpa otorisasi panitia/organizer dan pencatatan ke `activity_logs`.
- **Bebas Ketergantungan Infrastruktur:** Algoritma bracket harus dapat diuji murni di memori atau menggunakan `MockRepository` tanpa membutuhkan koneksi Supabase.

## 4. Allowed Directories
- `backend/modules/tournaments/`
- `backend/modules/teams/`
- `backend/modules/matches/`
- `tests/unit/` (khusus pengujian turnamen, tim, dan bracket)

## 5. Prohibited Changes
- Dilarang mengubah struktur response HTTP di `backend/api/` milik Anisa tanpa koordinasi.
- Dilarang mengubah skema tabel database di `supabase/` milik Habil tanpa kesepakatan kontrak.

## 6. Required Dependencies
- Python standard library (`math`, `uuid`, `dataclasses`, `datetime`, `typing`) dan `pytest` untuk pengujian TDD.

## 7. Development Workflow
1. Gunakan pendekatan **TDD (Red-Green-Refactor)**: tulis kasus uji bracket dan validasi skor di `tests/unit/test_bracket_engine.py` terlebih dahulu.
2. Implementasikan logika domain di `backend/modules/matches/bracket_engine.py` dan `service.py`.
3. Gunakan `MockRepository` (`APP_MODE=mock`) yang telah menyediakan 8 tim contoh untuk menguji simulasi penuh dari Quarter Final hingga Grand Final.

## 8. Testing Requirements
- Unit test pembuatan bracket 8 tim (memastikan terbentuk 4 QF, 2 SF, 1 Final dengan relasi `next_match_id` dan `next_slot` yang akurat).
- Unit test penanganan jumlah tim bukan pangkat dua (mis. 6 tim menghasilkan 2 *bye* otomatis maju ke Semi Final).
- Unit test validasi skor Best-of-3 (skor valid `2-0`, `2-1`; skor tidak valid `1-1`, `3-0`, `-1-0`).
- Unit test perpindahan pemenang otomatis dari Quarter Final ke Semi Final dan dari Semi Final ke Grand Final.

## 9. Acceptance Criteria
- Seluruh aturan pada Bagian 10 Master Prompt terpenuhi dan terverifikasi oleh `pytest`.
- Tidak ada pemenang acak atau perubahan hasil tanpa jejak audit.

## 10. Integration Contracts
- Module & Service Contract: `docs/contracts/module-contract.md`
- Database Contract: `docs/contracts/database-contract.md`
- REST API Contract: `docs/contracts/api-contract.md`
