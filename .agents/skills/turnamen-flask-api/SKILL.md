---
name: turnamen-flask-api
description: Panduan arsitektur Flask REST API (/api/v1), validasi request, standarisasi response JSON, pengumuman, laporan turnamen, dan pengujian integrasi untuk Anisa.
---

# Turnamen.in — Flask REST API, Reporting & Testing (`turnamen-flask-api`)

Skill ini ditujukan bagi **Anisa (REST API, Reporting & Testing Developer)** untuk mengembangkan lapisan HTTP REST API, modul pengumuman, modul laporan/statistik, dokumentasi API, serta pengujian lintas modul.

## 1. Scope
Mencakup factory aplikasi Flask (`backend/app.py`), blueprint endpoint & validator (`backend/api/`), modul pengumuman (`backend/modules/announcements/`), modul laporan & klasemen (`backend/modules/reports/`), dokumentasi API (`docs/api/`), serta suite pengujian (`tests/`).

## 2. Responsibilities
- Menyediakan seluruh endpoint kontrak `/api/v1/*` dengan format JSON yang seragam untuk sukses maupun error.
- Memvalidasi setiap payload request sebelum meneruskannya ke Application Service.
- Memeriksa autentikasi dan otorisasi role pada setiap endpoint yang dilindungi.
- Mengembangkan fitur pengumuman turnamen serta ringkasan laporan/klasemen (*standings* & *tournament summary report*).
- Memelihara dokumentasi endpoint di `docs/api/` dan pengujian integrasi di `tests/integration/`.

## 3. Architecture Rules
- **Prefix Wajib:** Seluruh endpoint API wajib menggunakan prefix `/api/v1`.
- **Keamanan Jaringan Lokal:** Server Flask secara default hanya mendengarkan pada `127.0.0.1` (`localhost`), bukan `0.0.0.0`.
- **Format JSON Konsisten:**
  - Sukses: `{"success": true, "message": "...", "data": ...}`
  - Error: `{"success": false, "message": "...", "error": {"code": "...", "details": ...}}`
- **Tipis di Controller, Kuat di Service:** Route handler di `backend/api/routes/` hanya menangani penguraian HTTP request, pemeriksaan izin, pemanggilan service, dan pemformatan response HTTP. Jangan menaruh algoritma bracket atau query mentah di dalam route.

## 4. Allowed Directories
- `backend/app.py`
- `backend/api/`
- `backend/modules/announcements/`
- `backend/modules/reports/`
- `docs/api/`
- `tests/`

## 5. Prohibited Changes
- Dilarang mengubah struktur JSON standar (`success`, `message`, `data`, `error`) karena akan merusak `api-client.js` milik Fikri dan komponen UI milik Ferlita.
- Dilarang mengubah algoritma bracket di `backend/modules/matches/` tanpa berkoordinasi dengan Adriel.

## 6. Required Dependencies
- `Flask==3.0.3`, `Werkzeug==3.0.4`, `pytest==8.3.2`.
- Skill referensi: `hexagonal-python`, `antislop-copywriting`, `tdd`, `team-code-review`.

## 7. Development Workflow
1. Periksa spesifikasi endpoint di `docs/contracts/api-contract.md`.
2. Tambahkan atau perbarui schema validasi request di `backend/api/schemas/`.
3. Hubungkan route di `backend/api/routes/` ke service modul terkait.
4. Tulis integration test menggunakan Flask `test_client()` di `tests/integration/`.
5. Perbarui dokumentasi di `docs/api/` bila ada penambahan detail parameter.

## 8. Testing Requirements
- Uji `/api/v1/health`, autentikasi, daftar game, pembuatan/pembacaan turnamen, pendaftaran tim, pembuatan bracket, pembaruan skor, pengumuman, dan laporan menggunakan `pytest`.
- Pastikan kasus gagal (input kosong, tidak punya akses role, ID tidak ditemukan) mengembalikan HTTP status code (`400`, `401`, `403`, `404`, `422`) dan `error.code` yang tepat.

## 9. Acceptance Criteria
- Seluruh endpoint pada Bagian 8 Master Prompt terdaftar dan terdokumentasi dengan jujur.
- Pesan respons berbahasa Indonesia yang jelas, sopan, dan informatif sesuai standar `antislop-copywriting`.

## 10. Integration Contracts
- REST API Contract: `docs/contracts/api-contract.md`
- Role & Permission Matrix: `docs/contracts/role-permissions.md`
- Frontend Contract: `docs/contracts/frontend-contract.md`
