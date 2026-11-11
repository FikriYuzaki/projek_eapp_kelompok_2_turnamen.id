---
name: turnamen-quality-gates
description: Standar pengujian unit/integrasi, kontrak antarmodul, validasi input, Definition of Done, dan checklist serah terima untuk seluruh anggota Turnamen.in.
---

# Turnamen.in — Quality Gates & Testing Standards (`turnamen-quality-gates`)

Skill ini wajib dipatuhi oleh **seluruh anggota kelompok** untuk menjaga kualitas kode, mencegah regresi lintas modul, dan memastikan setiap fitur siap diintegrasikan ke branch `main`.

## 1. Scope
Mencakup standar pengujian otomatis (`tests/unit/` dan `tests/integration/`), pemeriksaan kontrak antarmodul, keamanan kredensial, kebersihan komentar kode, serta kriteria penyelesaian (*Definition of Done*).

## 2. Responsibilities
- Memastikan setiap modul dapat diuji secara terisolasi dalam `APP_MODE=mock`.
- Mencegah masuknya kode yang merusak modul anggota lain di branch `main`.
- Menjaga agar tidak ada fitur palsu (*fake buttons / dummy endpoints* yang menipu pengguna) atau klaim pengujian palsu.

## 3. Architecture Rules
- **Piramida Pengujian Proporsional:**
  1. **Unit Tests (`tests/unit/`):** Menguji fungsi murni, validasi domain, algoritma Single Elimination bracket, perpindahan babak, dan matriks permission tanpa jaringan/HTTP.
  2. **Integration Tests (`tests/integration/`):** Menguji alur Flask REST API (`/api/v1/*`) bersama `MockRepository` menggunakan Flask `test_client()`.
  3. **Manual Desktop Smoke Check:** Memastikan `python run.py --check` dan tampilan UI berjalan tanpa error console.
- **Kejujuran Verifikasi:** Jangan pernah mengklaim integrasi Supabase cloud berhasil apabila belum diuji dengan kredensial proyek yang valid.

## 4. Allowed Directories
- `tests/unit/`
- `tests/integration/`
- `scripts/`

## 5. Prohibited Changes
- Dilarang menghapus atau menonaktifkan (`@pytest.mark.skip`) pengujian milik anggota lain hanya agar test terlihat lulus.
- Dilarang menyertakan kredensial nyata atau data sensitif di dalam file test.

## 6. Required Dependencies
- `pytest==8.3.2`
- Skill pendukung: `tdd`, `team-code-review`, `antislop`, `antislop-code`.

## 7. Development Workflow
1. Sebelum menulis fitur baru, jalankan `pytest` untuk memastikan baseline bersih.
2. Terapkan siklus *Red-Green-Refactor* untuk logika bisnis dan endpoint API.
3. Sebelum melakukan `git commit` dan `git push origin main`, jalankan:
   ```bash
   pytest -v
   python run.py --check
   ```
4. Periksa `git status` dan `git diff` untuk memastikan tidak ada file `.env` atau perubahan tak sengaja pada folder anggota lain.

## 8. Testing Requirements
Minimal pengujian yang harus selalu hijau di repository:
1. Konfigurasi aplikasi dan mode default `APP_MODE=mock`.
2. Endpoint kesehatan `GET /api/v1/health`.
3. Konsistensi struktur JSON sukses dan error.
4. Autentikasi dasar (`login`, `register`, `me`, `logout`) dalam mode mock.
5. Pembuatan dan pembacaan turnamen.
6. Registrasi tim dan perubahan status verifikasi.
7. Algoritma bracket Single Elimination 8 tim (4 QF, 2 SF, 1 Final) serta penanganan *bye*.
8. Validasi skor, penentuan pemenang, dan perpindahan otomatis ke babak berikutnya.
9. Pemeriksaan izin (*Role-Based Access Control*) untuk 5 role.

## 9. Acceptance Criteria (Definition of Done)
- [ ] Seluruh unit test dan integration test lulus (`pytest` exit code `0`).
- [ ] Kode mengikuti kontrak di `docs/contracts/`.
- [ ] Tidak ada *hardcoded secret* atau `.env` yang ikut ter-stage di Git.
- [ ] Dokumentasi atau task checklist terkait telah diperbarui.

## 10. Integration Contracts
- Seluruh dokumen di `docs/contracts/` menjadi acuan utama *contract testing*.
