# Dokumentasi REST API Turnamen.in (`/api/v1`)

Dokumen ini merupakan referensi teknis untuk pengujian dan integrasi seluruh endpoint REST API Turnamen.in yang dikelola oleh **Anisa**. Untuk aturan kontrak ringkas lintas modul, lihat pula [`docs/contracts/api-contract.md`](file:///C:/Turnamen.in/docs/contracts/api-contract.md).

---

## 1. Informasi Server & Header

- **URL Lokal Default:** `http://127.0.0.1:5000/api/v1`
- **Header Standar:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>` (diperoleh dari endpoint `/api/v1/auth/login`)
  - `X-Mock-Role: <role>` (Opsional, khusus saat `APP_MODE=mock` untuk menguji otorisasi role secara cepat dari UI atau `pytest`)

---

## 2. Rincian Endpoint & Contoh Penggunaan

### 2.1 Health Check
- **Endpoint:** `GET /api/v1/health`
- **Akses:** Publik
- **Response `200 OK`:**
```json
{
  "success": true,
  "message": "Layanan API Turnamen.in berjalan normal",
  "data": {
    "app_name": "Turnamen.in",
    "version": "0.1.0",
    "app_mode": "mock",
    "is_simulation": true,
    "status": "healthy"
  }
}
```

### 2.2 Autentikasi (`/api/v1/auth/*`)
1. **`POST /api/v1/auth/login`**
   - Body: `{"email": "organizer@turnamen.in", "password": "turnamen123"}`
   - Response `200 OK`: Mengembalikan `token` dan objek `user` (`id`, `email`, `username`, `full_name`, `role`).
2. **`POST /api/v1/auth/register`**
   - Body: `{"email": "baru@turnamen.in", "username": "tim_baru", "full_name": "Kapten Baru", "password": "password123", "role": "team_captain"}`
   - Catatan Keamanan: Pendaftaran mandiri hanya mengizinkan role `player` atau `team_captain`. Permintaan role `super_admin` atau `organizer` saat registrasi publik akan ditolak (`403 FORBIDDEN`).
3. **`GET /api/v1/auth/me`**
   - Mengembalikan profil pengguna berdasarkan token sesi aktif.
4. **`POST /api/v1/auth/logout`**
   - Mencabut token sesi aktif.

### 2.3 Katalog Game (`/api/v1/games/*`)
1. **`GET /api/v1/games`** — Daftar seluruh game yang didukung (MLBB, VALORANT, EA Sports FC 25).
2. **`GET /api/v1/games/<id>`** — Detail game berdasarkan UUID atau `slug`.

### 2.4 Manajemen Turnamen (`/api/v1/tournaments/*`)
1. **`GET /api/v1/tournaments`** — Mendukung query `?status=ongoing&game_id=<uuid>`.
2. **`POST /api/v1/tournaments`** — Role: `super_admin`, `organizer`.
3. **`GET /api/v1/tournaments/<id>`** — Detail lengkap turnamen beserta statistik ringkas pendaftaran & pertandingan.
4. **`PATCH /api/v1/tournaments/<id>`** — Role: `super_admin`, `organizer` (pemilik turnamen).
5. **`DELETE /api/v1/tournaments/<id>`** — Role: `super_admin`, `organizer` (pemilik turnamen).

### 2.5 Manajemen Tim & Anggota (`/api/v1/teams/*`)
1. **`GET /api/v1/teams`** — Daftar tim e-sport.
2. **`POST /api/v1/teams`** — Role: `super_admin`, `team_captain`. Body: `{"name": "Borneo Tigers", "tag": "BTG", "game_id": "<uuid>", "region": "Samarinda"}`.
3. **`GET /api/v1/teams/<id>`** — Detail tim beserta array `members`.
4. **`PATCH /api/v1/teams/<id>`** — Role: `super_admin`, `team_captain` (kapten pemilik tim).
5. **`POST /api/v1/teams/<id>/members`** — Role: `super_admin`, `team_captain`. Body: `{"nickname": "BTG.Razor", "ingame_id": "ML-999111", "member_role": "starter"}`.

### 2.6 Registrasi Tim (`/api/v1/tournaments/<id>/registrations` & `/api/v1/registrations/<id>/status`)
1. **`GET /api/v1/tournaments/<id>/registrations`** — Daftar tim yang mendaftar pada turnamen `<id>`.
2. **`POST /api/v1/tournaments/<id>/registrations`** — Role: `super_admin`, `team_captain`. Body: `{"team_id": "<uuid>", "notes": "Siap bertanding"}`.
3. **`PATCH /api/v1/registrations/<id>/status`** — Role: `super_admin`, `organizer`, `committee`. Body: `{"status": "approved", "notes": "Pembayaran QRIS terverifikasi"}`.

### 2.7 Pertandingan & Bracket (`/api/v1/tournaments/<id>/matches`, `bracket/generate`, `/api/v1/matches/<id>/result`)
1. **`GET /api/v1/tournaments/<id>/matches`** — Mengembalikan daftar semua pertandingan dan pengelompokan per babak (`rounds`).
2. **`POST /api/v1/tournaments/<id>/bracket/generate`** — Role: `super_admin`, `organizer`, `committee`. Membuat bagan Single Elimination dari seluruh tim berstatus `approved`.
3. **`PATCH /api/v1/matches/<id>/result`** — Role: `super_admin`, `organizer`, `committee`. Body: `{"score_a": 2, "score_b": 1, "notes": "Disahkan wasit"}`.

### 2.8 Pengumuman & Laporan (`/api/v1/tournaments/<id>/announcements`, `reports`, `standings`)
1. **`GET /api/v1/tournaments/<id>/announcements`** — Daftar pengumuman terurut dari yang disematkan (`is_pinned`) dan terbaru.
2. **`POST /api/v1/tournaments/<id>/announcements`** — Role: `super_admin`, `organizer`, `committee`. Body: `{"title": "Jadwal Final", "content": "...", "priority": "important", "is_pinned": true}`.
3. **`GET /api/v1/tournaments/<id>/reports`** — Statistik ringkasan turnamen (jumlah tim, progres pertandingan selesai, juara/runner-up jika sudah selesai).
4. **`GET /api/v1/tournaments/<id>/standings`** — Peringkat dan rekor kemenangan tim dalam turnamen.
