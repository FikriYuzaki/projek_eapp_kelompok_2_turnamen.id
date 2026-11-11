# Kontrak Role & Matriks Izin (RBAC) — Turnamen.in

Dokumen ini menetapkan aturan otorisasi resmi untuk **5 Role Pengguna** di Turnamen.in. Seluruh pemeriksaan izin wajib dilakukan di **Backend (Flask API / Application Service)** dan diperkuat dengan **Supabase Row Level Security (RLS)**.

> [!IMPORTANT]
> - Menyembunyikan tombol atau menu di frontend **bukanlah** mekanisme keamanan.
> - Role pengguna disimpan di kolom `public.profiles.role` dan **tidak boleh** dapat diubah sendiri oleh pengguna biasa atau dibaca dari `user_metadata` yang dapat diedit klien.

---

## 1. Definisi 5 Role Resmi

| Kode Role (`profiles.role`) | Nama Role | Deskripsi Tanggung Jawab Utama |
| :--- | :--- | :--- |
| `super_admin` | **Super Admin** | Mengelola akun pengguna dan penetapan role, mengakses seluruh turnamen lintas penyelenggara, mengelola konfigurasi sistem, serta melihat laporan keseluruhan. |
| `organizer` | **Tournament Organizer** | Membuat dan mengelola turnamen miliknya, menentukan game/aturan/format/kuota/biaya/hadiah/jadwal, menyetujui pendaftaran, men-generate bracket, menugaskan panitia, dan melihat laporan turnamennya. |
| `committee` | **Committee / Panitia** | Mengakses turnamen yang ditugaskan (`tournament_staff`), memverifikasi peserta dan pembayaran, mengelola jadwal pertandingan, memasukkan/mengesahkan skor sesuai aturan, dan mempublikasikan pengumuman. |
| `team_captain` | **Team Captain** | Membuat dan mengelola tim miliknya, menambah/mengatur anggota tim dan ID game pemain, mendaftarkan tim ke turnamen, mengunggah bukti pembayaran, serta memantau jadwal, bracket, dan hasil. |
| `player` | **Player** | Melihat daftar dan detail turnamen, profil tim, jadwal pertandingan, bracket, hasil pertandingan, dan pengumuman, serta mengelola profil pribadinya sendiri. |

---

## 2. Matriks Izin Operasi per Sumber Daya

Keterangan simbol:
- **✅ Penuh**: Diizinkan untuk seluruh data.
- **🔹 Terbatas (Own / Assigned)**: Hanya diizinkan untuk sumber daya milik sendiri atau turnamen yang ditugaskan.
- **❌ Ditolak**: Tidak diizinkan (Backend mengembalikan HTTP `403 FORBIDDEN`).

| Sumber Daya & Operasi | `super_admin` | `organizer` | `committee` | `team_captain` | `player` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Autentikasi & Profil** | | | | | |
| Registrasi akun baru (default `player` / `team_captain`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Melihat & memperbarui profil pribadi (`full_name`, `phone`, `avatar_url`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mengubah `role` pengguna lain | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Game Metadata** | | | | | |
| Melihat daftar & detail game (`GET /api/v1/games`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Menambah / mengubah katalog game | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Turnamen (`tournaments`)** | | | | | |
| Melihat daftar & detail turnamen (`GET /api/v1/tournaments`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Membuat turnamen baru (`POST /api/v1/tournaments`) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Mengubah turnamen (`PATCH /api/v1/tournaments/<id>`) | ✅ | 🔹 (Miliknya) | ❌ | ❌ | ❌ |
| Menghapus / membatalkan turnamen (`DELETE /api/v1/tournaments/<id>`) | ✅ | 🔹 (Miliknya) | ❌ | ❌ | ❌ |
| **Tim & Anggota (`teams`, `team_members`)** | | | | | |
| Melihat daftar & detail tim (`GET /api/v1/teams`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Membuat tim baru (`POST /api/v1/teams`) | ✅ | ❌ | ❌ | ✅ | ❌ |
| Mengubah data tim & menambah anggota (`PATCH/POST /api/v1/teams/<id>/*`) | ✅ | ❌ | ❌ | 🔹 (Timnya) | ❌ |
| **Registrasi & Pembayaran (`registrations`, `payments`)** | | | | | |
| Melihat daftar registrasi turnamen | ✅ | 🔹 (Turnamennya) | 🔹 (Ditugaskan) | ✅ (Ringkasan) | ✅ (Ringkasan) |
| Mendaftarkan tim ke turnamen (`POST /api/v1/tournaments/<id>/registrations`) | ✅ | ❌ | ❌ | 🔹 (Timnya) | ❌ |
| Memverifikasi status registrasi/pembayaran (`PATCH /api/v1/registrations/<id>/status`) | ✅ | 🔹 (Turnamennya) | 🔹 (Ditugaskan) | ❌ | ❌ |
| **Pertandingan & Bracket (`matches`, `match_results`)** | | | | | |
| Melihat daftar pertandingan & bracket (`GET /api/v1/tournaments/<id>/matches`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Men-generate bracket (`POST /api/v1/tournaments/<id>/bracket/generate`) | ✅ | 🔹 (Turnamennya) | 🔹 (Ditugaskan) | ❌ | ❌ |
| Memasukkan & mengesahkan hasil pertandingan (`PATCH /api/v1/matches/<id>/result`) | ✅ | 🔹 (Turnamennya) | 🔹 (Ditugaskan) | ❌ | ❌ |
| **Pengumuman (`announcements`)** | | | | | |
| Melihat pengumuman (`GET /api/v1/tournaments/<id>/announcements`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Membuat pengumuman (`POST /api/v1/tournaments/<id>/announcements`) | ✅ | 🔹 (Turnamennya) | 🔹 (Ditugaskan) | ❌ | ❌ |
| **Laporan & Klasemen (`reports`, `standings`)** | | | | | |
| Melihat klasemen & hasil akhir (`GET /api/v1/tournaments/<id>/standings`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Melihat laporan manajemen turnamen (`GET /api/v1/tournaments/<id>/reports`) | ✅ | 🔹 (Turnamennya) | 🔹 (Ditugaskan) | ✅ (Publik) | ✅ (Publik) |

---

## 3. Akun Demo pada Mock Mode (`APP_MODE=mock`)

Untuk memudahkan seluruh anggota menguji setiap role tanpa konfigurasi cloud, `MockRepository` menyediakan 5 akun siap pakai (password simulasi untuk semua akun demo di mode mock: `turnamen123`):

| Role | Email Demo | Username | User ID (UUID) |
| :--- | :--- | :--- | :--- |
| `super_admin` | `admin@turnamen.in` | `superadmin` | `11111111-1111-4111-8111-111111111101` |
| `organizer` | `organizer@turnamen.in` | `garuda_eo` | `11111111-1111-4111-8111-111111111102` |
| `committee` | `committee@turnamen.in` | `panitia_utama` | `11111111-1111-4111-8111-111111111103` |
| `team_captain` | `captain@turnamen.in` | `garuda_capt` | `11111111-1111-4111-8111-111111111104` |
| `player` | `player@turnamen.in` | `aruna_player` | `11111111-1111-4111-8111-111111111105` |
