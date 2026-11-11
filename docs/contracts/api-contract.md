# Kontrak REST API (`/api/v1`) — Turnamen.in

Dokumen ini mendefinisikan kontrak HTTP REST API antara **Anisa** (Flask API Developer), **Fikri** (API Client & Eel Bridge), **Ferlita** (Desktop UI), **Adriel** (Tournament & Match Services), dan **Habil** (Auth & Repository).

---

## 1. Konvensi Umum

- **Base URL Default:** `http://127.0.0.1:5000/api/v1`
- **Content-Type:** `application/json`
- **Autentikasi:**
  - Mengirimkan header `Authorization: Bearer <token>` (yang dikembalikan saat `POST /api/v1/auth/login`), atau
  - Pada `APP_MODE=mock`, klien juga dapat menyertakan header `X-Mock-User-Id` atau `X-Mock-Role` untuk pengujian lintas role secara cepat.

### Format Response Sukses (HTTP `200` / `201`)
```json
{
  "success": true,
  "message": "Data berhasil diperoleh",
  "data": {}
}
```

### Format Response Error (HTTP `400` / `401` / `403` / `404` / `409` / `422` / `500`)
```json
{
  "success": false,
  "message": "Terjadi kesalahan validasi input",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {}
  }
}
```

Daftar `error.code` standar:
- `VALIDATION_ERROR` (`400` / `422`): Input tidak lengkap atau skor/format tidak sah.
- `UNAUTHORIZED` (`401`): Belum login atau token tidak valid.
- `FORBIDDEN` (`403`): Role pengguna tidak memiliki izin untuk operasi tersebut.
- `NOT_FOUND` (`404`): Entitas (turnamen, tim, pertandingan, dll.) tidak ditemukan.
- `CONFLICT` (`409`): Duplikasi pendaftaran, nama tim, atau percobaan mengubah pertandingan yang sudah dikunci tanpa otorisasi.
- `INTERNAL_ERROR` (`500`): Kesalahan tak terduga di sisi server.

---

## 2. Daftar Lengkap Endpoint Kontrak `/api/v1`

| Kategori | Method & Path | Auth / Role yang Diizinkan | Status Implementasi Starter | Deskripsi |
| :--- | :--- | :--- | :--- | :--- |
| **Health** | `GET /api/v1/health` | Publik | **Berfungsi Penuh** | Memeriksa status server, versi, dan mode aplikasi (`mock` / `supabase`). |
| **Auth** | `POST /api/v1/auth/register` | Publik | **Berfungsi Penuh (Mock)** | Mendaftarkan pengguna baru (`player` atau `team_captain`). |
| **Auth** | `POST /api/v1/auth/login` | Publik | **Berfungsi Penuh (Mock)** | Login dengan `email` & `password`, mengembalikan token sesi dan profil. |
| **Auth** | `POST /api/v1/auth/logout` | Terautentikasi | **Berfungsi Penuh (Mock)** | Mengakhiri sesi aktif pengguna. |
| **Auth** | `GET /api/v1/auth/me` | Terautentikasi | **Berfungsi Penuh (Mock)** | Mengambil profil dan role pengguna yang sedang login. |
| **Games** | `GET /api/v1/games` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil daftar seluruh game yang tersedia. |
| **Games** | `GET /api/v1/games/<id>` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil detail konfigurasi satu game berdasarkan ID/slug. |
| **Tournaments** | `GET /api/v1/tournaments` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil daftar turnamen (mendukung filter `?status=` & `?game_id=`). |
| **Tournaments** | `POST /api/v1/tournaments` | `super_admin`, `organizer` | **Berfungsi Penuh** | Membuat turnamen baru. |
| **Tournaments** | `GET /api/v1/tournaments/<id>` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil detail turnamen beserta jumlah tim terdaftar. |
| **Tournaments** | `PATCH /api/v1/tournaments/<id>` | `super_admin`, `organizer` | **Berfungsi Penuh** | Memperbarui informasi atau status turnamen. |
| **Tournaments** | `DELETE /api/v1/tournaments/<id>` | `super_admin`, `organizer` | **Berfungsi Penuh** | Membatalkan atau menghapus turnamen berstatus draft. |
| **Teams** | `GET /api/v1/teams` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil daftar seluruh tim. |
| **Teams** | `POST /api/v1/teams` | `super_admin`, `team_captain` | **Berfungsi Penuh** | Membuat tim e-sport baru. |
| **Teams** | `GET /api/v1/teams/<id>` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil detail tim beserta daftar anggotanya (`members`). |
| **Teams** | `PATCH /api/v1/teams/<id>` | `super_admin`, `team_captain` | **Berfungsi Penuh** | Memperbarui nama, tag, atau region tim. |
| **Teams** | `POST /api/v1/teams/<id>/members` | `super_admin`, `team_captain` | **Berfungsi Penuh** | Menambahkan anggota pemain ke dalam tim. |
| **Registrations** | `GET /api/v1/tournaments/<id>/registrations` | Semua Role | **Berfungsi Penuh** | Mengambil daftar tim yang mendaftar pada turnamen `<id>`. |
| **Registrations** | `POST /api/v1/tournaments/<id>/registrations` | `super_admin`, `team_captain` | **Berfungsi Penuh** | Mendaftarkan tim ke turnamen `<id>`. |
| **Registrations** | `PATCH /api/v1/registrations/<id>/status` | `super_admin`, `organizer`, `committee` | **Berfungsi Penuh** | Mengubah status pendaftaran (`approved` / `rejected` / `withdrawn`). |
| **Matches** | `GET /api/v1/tournaments/<id>/matches` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil daftar pertandingan dan struktur bracket turnamen `<id>`. |
| **Matches** | `POST /api/v1/tournaments/<id>/bracket/generate` | `super_admin`, `organizer`, `committee` | **Berfungsi Penuh** | Membuat bracket Single Elimination dari daftar tim `approved`. |
| **Matches** | `PATCH /api/v1/matches/<id>/result` | `super_admin`, `organizer`, `committee` | **Berfungsi Penuh** | Memvalidasi skor, menetapkan pemenang, dan memajukan ke babak berikutnya. |
| **Announcements** | `GET /api/v1/tournaments/<id>/announcements` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil daftar pengumuman pada turnamen `<id>`. |
| **Announcements** | `POST /api/v1/tournaments/<id>/announcements` | `super_admin`, `organizer`, `committee` | **Berfungsi Penuh** | Mempublikasikan pengumuman baru pada turnamen `<id>`. |
| **Reports** | `GET /api/v1/tournaments/<id>/reports` | Semua Role | **Berfungsi Penuh** | Mengambil ringkasan statistik turnamen, progres pertandingan, dan juara. |
| **Reports** | `GET /api/v1/tournaments/<id>/standings` | Publik / Semua Role | **Berfungsi Penuh** | Mengambil peringkat/klasemen tim berdasarkan progres babak dan rekor menang-kalah. |

---

## 3. Contoh Spesifikasi Payload Penting

### A. `POST /api/v1/tournaments`
**Request Body:**
```json
{
  "title": "Piala Kemerdekaan MLBB 2026",
  "game_id": "22222222-2222-4222-8222-222222222201",
  "max_teams": 8,
  "best_of": 3,
  "registration_fee": 50000,
  "prize_pool": 5000000,
  "venue": "Online",
  "start_date": "2026-12-01T10:00:00+07:00"
}
```

### B. `PATCH /api/v1/matches/<id>/result`
**Request Body:**
```json
{
  "score_a": 2,
  "score_b": 1,
  "notes": "Disahkan oleh wasit utama",
  "force_override": false
}
```
**Response Data:** Mengembalikan objek `match` yang telah diperbarui (`status: "completed"`, `winner_team_id`) beserta `next_match` yang telah terisi tim pemenang pada slot `A` atau `B`.
