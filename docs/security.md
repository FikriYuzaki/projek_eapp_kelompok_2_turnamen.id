# Kebijakan Keamanan & Batasan Aplikasi Desktop — Turnamen.in

Dokumen ini menjelaskan keputusan arsitektur keamanan, perlindungan kredensial Supabase, aturan autentikasi/otorisasi (RBAC & RLS), serta mitigasi risiko penggunaan Python Eel pada proyek **Turnamen.in**.

---

## 1. Manajemen Kredensial & Rahasia (Secrets Management)

1. **Tidak Ada Secret di Repository:**
   - File `.env` diabaikan secara permanen oleh `.gitignore`.
   - Repository hanya menyertakan `.env.example` yang berisi nilai contoh/placeholder.
2. **Larangan Mutlak `service_role` Key di Klien Desktop:**
   - Aplikasi desktop yang didistribusikan ke pengguna akhir (panitia, kapten tim, pemain) harus diperlakukan sebagai **public client** karena kode atau binernya berada di perangkat pengguna.
   - **JANGAN PERNAH** menaruh Supabase `service_role` key atau password database PostgreSQL di `.env` aplikasi desktop yang didistribusikan, di kode JavaScript frontend, atau di GitHub.
   - Gunakan `SUPABASE_ANON_KEY` (publishable key) yang dipadukan dengan autentikasi sesi pengguna (`Supabase Auth`) dan kebijakan **Row Level Security (RLS)** di PostgreSQL.
3. **Sanitasi Log:**
   - Konfigurasi logger (`backend/core/logging_config.py`) menyaring dan tidak pernah mencetak nilai `SECRET_KEY`, `SUPABASE_ANON_KEY`, password, atau token `Authorization` ke terminal maupun file log.

---

## 2. Keamanan Autentikasi & Otorisasi (RBAC + RLS)

1. **Verifikasi di Sisi Backend & Database:**
   - Menyembunyikan tombol di antarmuka HTML/JS hanyalah fitur kenyamanan UX, bukan batas keamanan.
   - Setiap endpoint perubahan data (`POST`, `PATCH`, `DELETE`) di Flask REST API wajib memeriksa identitas pengguna dan matriks izin di `backend/modules/auth/permissions.py`.
2. **Perlindungan Role dari Manipulasi Klien:**
   - Role pengguna (`super_admin`, `organizer`, `committee`, `team_captain`, `player`) disimpan pada tabel `public.profiles` yang dilindungi RLS.
   - Sistem **tidak pernah** membaca klaim otorisasi dari `raw_user_meta_data` (`user_metadata`) Supabase Auth karena field tersebut dapat dimodifikasi oleh pengguna melalui client SDK.
   - Pengguna biasa yang melakukan registrasi mandiri hanya dapat memperoleh role dasar (`player` atau `team_captain`); peningkatan role menjadi `organizer`, `committee`, atau `super_admin` hanya dapat dilakukan oleh pihak terpercaya (`super_admin` / penugasan resmi).
3. **Row Level Security (RLS):**
   - Seluruh 12 tabel pada skema `public` mengaktifkan `ENABLE ROW LEVEL SECURITY` sejak migrasi pertama (`0001_initial_schema.sql`).

---

## 3. Mitigasi Risiko Python Eel & Server Lokal

1. **Status Pemeliharaan Python Eel:**
   - Python Eel merupakan pustaka yang sudah diarsipkan dan tidak lagi aktif dipelihara oleh pengembang asalnya.
   - Untuk menjaga keamanan dan stabilitas, versi `Eel` beserta seluruh rantai dependensinya (`bottle`, `gevent`, `gevent-websocket`) dipin pada versi yang telah diuji di `requirements.txt`.
2. **Isolasi Jaringan Lokal (`127.0.0.1`):**
   - Baik server Flask REST API (`API_HOST=127.0.0.1`) maupun server web internal Python Eel (`EEL_HOST=127.0.0.1`) diikat secara ketat ke antarmuka loopback lokal (`localhost`).
   - Server **tidak diekspos** ke jaringan LAN/Wi-Fi publik (`0.0.0.0`).
3. **Pembatasan `@eel.expose`:**
   - Hanya fungsi bridge minimal yang diekspos ke JavaScript (`get_runtime_info`, `check_api_health`, dan `api_request`). Tidak ada fungsi akses sistem file (`os`, `subprocess`, `eval`) yang diekspos ke browser.

---

## 4. Validasi Input & Pencegahan Injeksi

- Seluruh input JSON pada Flask REST API divalidasi tipe data, panjang string, rentang nilai angka (`score_a >= 0`, `best_of in (1, 3, 5, 7)`), dan format UUID-nya melalui `backend/api/schemas/validators.py`.
- Tidak ada penggabungan string SQL mentah (*raw string concatenation*) dari input pengguna.
- Password pada mode lokal/mock di-hash menggunakan `werkzeug.security.generate_password_hash` (bukan disimpan sebagai plaintext).
