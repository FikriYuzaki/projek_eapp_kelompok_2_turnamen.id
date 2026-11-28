# Dokumentasi REST API Turnamen.in (`/api/v1`)

Dokumen ini menjadi referensi teknis untuk pengujian dan integrasi seluruh endpoint REST API Turnamen.in yang dikelola oleh Anisa. Kontrak ringkas lintas modul tersedia di [`docs/contracts/api-contract.md`](../contracts/api-contract.md) dan matriks izin di [`docs/contracts/role-permissions.md`](../contracts/role-permissions.md).

---

## 1. Informasi Server & Header

- **URL Lokal Default:** `http://127.0.0.1:5000/api/v1`
- **Header Standar:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>` (diperoleh dari `POST /api/v1/auth/login`)
  - `X-Mock-Role: <role>` atau `X-Mock-User-Id: <uuid>` (opsional, hanya aktif pada `APP_MODE=mock` untuk pengujian lintas role)

---

## 2. Format Response Standar

### Response Sukses (`200 OK`, `201 Created`)
```json
{
  "success": true,
  "message": "Data berhasil diperoleh",
  "data": {}
}
```

### Response Error (`400`, `401`, `403`, `404`, `405`, `409`, `500`)
```json
{
  "success": false,
  "message": "Field wajib belum lengkap: title.",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "missing_fields": ["title"]
    }
  }
}
```

| HTTP Status | `error.code` | Penyebab Umum |
| :--- | :--- | :--- |
| `400` | `VALIDATION_ERROR` | JSON tidak valid, field wajib kosong/whitespace, skor seri, atau nilai tipe tidak sesuai. |
| `401` | `UNAUTHORIZED` | Token tidak dikirim, sudah dicabut, atau sesi tidak valid. |
| `403` | `FORBIDDEN` | Role tidak memiliki izin atau mengakses sumber daya milik pihak lain. |
| `404` | `NOT_FOUND` | Endpoint atau entitas (game, turnamen, tim, pertandingan) tidak ditemukan. |
| `405` | `METHOD_NOT_ALLOWED` | Metode HTTP tidak didukung pada endpoint tersebut. |
| `409` | `CONFLICT` | Duplikasi data atau percobaan menimpa skor pertandingan yang sudah dikunci tanpa `force_override`. |
| `500` | `INTERNAL_ERROR` | Kesalahan internal tak terduga di server. |

---

## 3. Rincian Endpoint `/api/v1`

### 3.1 Health Check
- `GET /api/v1/health` (Publik): mengembalikan status kesehatan server, versi aplikasi, dan mode operasi (`mock` atau `supabase`).

### 3.2 Autentikasi (`/api/v1/auth/*`)
1. `POST /api/v1/auth/register` (Publik): mendaftarkan akun baru. Field wajib: `email`, `username`, `full_name`, `password`. Pendaftaran mandiri hanya mengizinkan role `player` atau `team_captain`; permintaan role `super_admin` atau `organizer` ditolak dengan `403 FORBIDDEN`.
2. `POST /api/v1/auth/login` (Publik): login dengan `email` dan `password`, mengembalikan `token` serta objek `user`.
3. `POST /api/v1/auth/logout` (Terautentikasi): mencabut token sesi aktif (`401 UNAUTHORIZED` jika belum terautentikasi).
4. `GET /api/v1/auth/me` (Terautentikasi): mengembalikan profil dan role pengguna aktif.

### 3.3 Katalog Game (`/api/v1/games/*`)
1. `GET /api/v1/games` (Publik): daftar seluruh game yang tersedia.
2. `GET /api/v1/games/<game_id>` (Publik): detail game berdasarkan UUID atau `slug`.

### 3.4 Manajemen Turnamen (`/api/v1/tournaments/*`)
1. `GET /api/v1/tournaments` (Publik): daftar turnamen, mendukung filter query `?status=` (`draft`, `open_registration`, `ongoing`, `completed`, `cancelled`) dan `?game_id=<uuid>`.
2. `POST /api/v1/tournaments` (`super_admin`, `organizer`): membuat turnamen baru. Field wajib: `title`, `game_id`, `start_date`. Opsional: `max_teams`, `best_of`, `registration_fee`, `prize_pool`, `venue`, `status`.
3. `GET /api/v1/tournaments/<tournament_id>` (Publik): detail turnamen.
4. `PATCH /api/v1/tournaments/<tournament_id>` (`super_admin`, `organizer` pemilik): memperbarui informasi atau status turnamen.
5. `DELETE /api/v1/tournaments/<tournament_id>` (`super_admin`, `organizer` pemilik): menghapus turnamen berstatus `draft`.

### 3.5 Manajemen Tim & Anggota (`/api/v1/teams/*`)
1. `GET /api/v1/teams` (Publik): daftar tim, mendukung filter `?game_id=<uuid>`.
2. `POST /api/v1/teams` (`super_admin`, `team_captain`): membuat tim baru. Field wajib: `name`, `tag`, `game_id`. Opsional: `region`.
3. `GET /api/v1/teams/<team_id>` (Publik): detail tim beserta daftar `members`.
4. `PATCH /api/v1/teams/<team_id>` (`super_admin`, `team_captain` pemilik): memperbarui nama, tag, atau region tim.
5. `POST /api/v1/teams/<team_id>/members` (`super_admin`, `team_captain` pemilik): menambahkan pemain ke tim. Field wajib: `nickname`, `ingame_id`. Opsional: `member_role`.

### 3.6 Registrasi Tim
1. `GET /api/v1/tournaments/<tournament_id>/registrations` (Publik): daftar registrasi tim pada turnamen.
2. `POST /api/v1/tournaments/<tournament_id>/registrations` (`super_admin`, `team_captain`): mendaftarkan tim ke turnamen. Field wajib: `team_id`. Opsional: `notes`.
3. `PATCH /api/v1/registrations/<registration_id>/status` (`super_admin`, `organizer` pemilik, `committee` ditugaskan): mengubah status registrasi (`approved`, `rejected`, `withdrawn`). Field wajib: `status`.

### 3.7 Pertandingan & Bracket
1. `GET /api/v1/tournaments/<tournament_id>/matches` (Publik): mengembalikan daftar pertandingan (`matches`) dan pengelompokan per babak (`rounds`).
2. `POST /api/v1/tournaments/<tournament_id>/bracket/generate` (`super_admin`, `organizer` pemilik, `committee` ditugaskan): menyusun bracket Single Elimination dari seluruh tim berstatus `approved`.
3. `PATCH /api/v1/matches/<match_id>/result` (`super_admin`, `organizer` pemilik, `committee` ditugaskan): memvalidasi skor sesuai `best_of`, menetapkan pemenang, dan memajukan pemenang ke slot babak berikutnya. Field wajib: `score_a`, `score_b`. Opsional: `notes`, `force_override`.

### 3.8 Pengumuman & Laporan
1. `GET /api/v1/tournaments/<tournament_id>/announcements` (Publik): daftar pengumuman terurut dari yang disematkan (`is_pinned`) dan terbaru.
2. `POST /api/v1/tournaments/<tournament_id>/announcements` (`super_admin`, `organizer` pemilik, `committee` ditugaskan): mempublikasikan pengumuman baru. Field wajib: `title` (min. 4 karakter), `content` (min. 5 karakter). Opsional: `priority` (`normal`, `important`, `urgent`), `is_pinned` (boolean).
3. `GET /api/v1/tournaments/<tournament_id>/reports` (Publik): ringkasan statistik turnamen (kuota, jumlah pendaftaran, progres pertandingan selesai, juara, klasemen, dan aktivitas terbaru).
4. `GET /api/v1/tournaments/<tournament_id>/standings` (Publik): klasemen tim terurut berdasarkan penempatan juara (`Juara 1`, `Juara 2`), babak tertinggi, jumlah kemenangan, selisih game, dan seed.
