# MASTER PROMPT — TURNAMEN.IN STARTER REPOSITORY

## ROLE

Bertindaklah sebagai Senior Software Architect, Python Desktop Developer, Backend Engineer, Database Architect, dan Technical Project Lead.

Bangun fondasi awal proyek **Turnamen.in — Esports Tournament Management System**, sebuah aplikasi desktop untuk mengelola turnamen e-sport di Indonesia.

Jangan hanya memberikan rekomendasi atau contoh kode. Periksa repository aktif, buat struktur folder, tulis base code, konfigurasi, dokumentasi, database schema, mock data, dan pengujian dasar. Hasil harus siap digunakan oleh lima anggota kelompok untuk mengembangkan modul secara paralel.

Gunakan `TURNAMEN-IN-AGENT-SKILLS-ADDENDUM.md` sebagai addendum wajib untuk sistem Agent Skills dan repository referensi. Baca kedua file sebelum melakukan perubahan.

---

# 1. PROJECT OVERVIEW

**Nama:** Turnamen.in  
**Jenis:** Desktop Application  
**Platform target:** Windows 10/11  
**Tema:** Esports Tournament Management System  

Turnamen.in adalah aplikasi desktop untuk membantu penyelenggara mengelola turnamen e-sport secara terpusat, mulai dari pembuatan turnamen, pendaftaran tim, verifikasi peserta, penjadwalan pertandingan, pembuatan bracket, pencatatan skor, pengumuman, hingga laporan hasil turnamen.

Target pengguna:
- Penyelenggara turnamen e-sport.
- Panitia turnamen.
- Komunitas gaming.
- Tim e-sport dan kapten tim.
- Pemain.
- Sekolah dan universitas.
- Warnet dan event organizer lokal.

Game yang dapat dicatat antara lain Mobile Legends, Free Fire, PUBG Mobile, Valorant, Dota 2, dan EA Sports FC. Sistem harus bersifat game-agnostic, bukan bergantung pada satu game saja.

Masalah yang ingin diselesaikan adalah pengelolaan turnamen yang sering tersebar di WhatsApp, Google Forms, spreadsheet, dan pencatatan manual. Aplikasi menyatukan proses tersebut agar data lebih terstruktur, mudah diperiksa, dan dapat diakses oleh pengguna yang berwenang melalui internet.

# 2. TEAM MEMBERS & OWNERSHIP

Kelompok terdiri dari lima anggota. Gunakan nama dan tanggung jawab berikut secara konsisten dalam dokumentasi dan task files.

## FERLITA — Project Coordinator & UI/UX Designer

Tanggung jawab:
- Mengkoordinasikan progres kelompok dan menjaga kesepakatan antaranggota.
- Menentukan rancangan visual dan pengalaman pengguna.
- Membuat layout desktop, dashboard, login, navigasi, halaman turnamen, peserta, dan tim.
- Menjaga konsistensi desain seluruh halaman.

Folder utama:
- `desktop/web/pages/`
- `desktop/web/assets/css/`
- `desktop/web/assets/images/`

## FIKRI — System Integration & Python Eel Developer

Tanggung jawab:
- Membuat struktur utama aplikasi desktop.
- Mengatur Python Eel dan application launcher.
- Menghubungkan frontend dengan backend/API client.
- Mengatur konfigurasi aplikasi, logging, lifecycle, dan debugging.
- Mengintegrasikan modul anggota lain sesuai kontrak bersama.

Folder utama:
- `desktop/launcher/`
- `desktop/bridge/`
- `desktop/web/js/core/`
- `run.py`

## HABIL — Database & Authentication Developer

Tanggung jawab:
- Mendesain ERD, tabel, relasi, constraints, dan index.
- Menyiapkan Supabase PostgreSQL schema dan migration.
- Mengembangkan autentikasi dan pengelolaan profil.
- Mengatur role, authorization, dan Row Level Security (RLS).
- Menyiapkan repository database dan integrasi Storage/Realtime sesuai kebutuhan.

Folder utama:
- `supabase/`
- `backend/modules/auth/`
- `backend/infrastructure/supabase/`
- `backend/repositories/`

## ADRIEL — Tournament & Match System Developer

Tanggung jawab:
- Mengembangkan manajemen turnamen dan registrasi tim.
- Mengelola data tim dan pemain.
- Membuat algoritma bracket Single Elimination.
- Mengelola jadwal, status pertandingan, skor, pemenang, dan perpindahan babak.
- Menulis unit test untuk logika pertandingan.

Folder utama:
- `backend/modules/tournaments/`
- `backend/modules/teams/`
- `backend/modules/matches/`

## ANISA — REST API, Reporting & Testing Developer

Tanggung jawab:
- Mengembangkan Flask REST API dan endpoint.
- Membuat request validation dan response format.
- Mengembangkan pengumuman, statistik, dan laporan.
- Menyusun dokumentasi API.
- Menguji endpoint dan integrasi lintas modul.

Folder utama:
- `backend/api/`
- `backend/modules/reports/`
- `backend/modules/announcements/`
- `tests/`
- `docs/api/`

Folder ownership adalah batas tanggung jawab utama, bukan larangan mutlak. Jika perubahan lintas modul diperlukan, koordinasikan terlebih dahulu dan jangan mengubah kontrak bersama secara sepihak.

# 3. TECHNOLOGY STACK

Gunakan stack berikut:

### Desktop
- Python.
- Python Eel.

### Frontend
- HTML5.
- CSS3.
- Vanilla JavaScript.

Jangan menambahkan React, Vue, Angular, atau framework frontend besar tanpa alasan arsitektur yang jelas dan persetujuan proyek.

### Backend
- Python.
- Flask untuk REST API.
- Supabase Python SDK jika sesuai untuk akses layanan Supabase.

### Database dan layanan
- Supabase PostgreSQL.
- Supabase Auth.
- Supabase Storage.
- Supabase Realtime.

### Utilitas
- Chart.js untuk grafik bila diperlukan.
- pytest untuk testing.
- python-dotenv untuk konfigurasi lokal.
- Git dan GitHub.

RAWG API boleh dipertimbangkan sebagai integrasi metadata game opsional, tetapi jangan membuat fungsi utama bergantung padanya. Periksa persyaratan API, batas penggunaan, dan ketersediaannya sebelum implementasi.

Catatan: Python Eel merupakan proyek yang tidak lagi aktif dipelihara. Tetap gunakan karena merupakan pilihan platform proyek, tetapi pin dependency yang kompatibel, periksa keamanan, batasi server lokal, dan dokumentasikan keterbatasannya. Jangan mengklaim bahwa Eel aktif dipelihara.

# 4. SYSTEM ARCHITECTURE

Gunakan arsitektur modular dan proporsional, tidak overengineered.

Alur yang diharapkan:

`Desktop UI → API Client → Flask REST API → Application Services → Repository → Supabase PostgreSQL`

Tanggung jawab layer:

**Desktop Layer**
- Menampilkan UI dan navigasi.
- Mengirim permintaan melalui API client atau bridge yang ditentukan.
- Menampilkan loading, error, empty, dan success states.

**Application Layer**
- Menangani business logic.
- Validasi domain.
- Manajemen turnamen, tim, pertandingan, dan laporan.

**REST API Layer**
- Menangani HTTP request/response.
- Validasi request.
- Autentikasi dan authorization.
- Format response dan error yang konsisten.

**Infrastructure Layer**
- Supabase client.
- Repository database.
- Storage.
- Realtime.
- External API adapters.

Jangan membuat dua implementasi business logic yang berbeda di Eel dan Flask. Tentukan satu tempat untuk business logic dan gunakan dari entry points yang sesuai.

Flask API berjalan pada localhost secara default dan tidak diekspos ke jaringan publik. Desktop dan API harus dapat dijalankan melalui satu launcher yang menangani startup dan shutdown proses dengan benar.

# 5. DATABASE DESIGN

Rancang PostgreSQL schema yang mendukung banyak turnamen sekaligus. Tabel awal yang direncanakan:

1. `profiles`
2. `games`
3. `tournaments`
4. `teams`
5. `team_members`
6. `tournament_staff`
7. `registrations`
8. `matches`
9. `match_results`
10. `payments`
11. `announcements`
12. `activity_logs`

Tentukan secara tepat:
- Primary key dan foreign key.
- Relasi dan cardinality.
- Unique constraints.
- Check constraints.
- Default values.
- Timestamp `created_at` dan `updated_at` jika relevan.
- Index untuk kolom pencarian dan foreign key yang sering digunakan.
- Aturan delete/update.

Gunakan UUID untuk ID utama, kecuali ada alasan teknis kuat untuk tipe lain.

Buat:
- `supabase/migrations/0001_initial_schema.sql`
- `supabase/seed.sql`
- `docs/database-schema.md`

Seed harus berisi data demo konsisten untuk pengujian lokal. Sertakan data contoh game, turnamen, tim, anggota, jadwal, hasil, dan pengumuman.

Jangan melakukan migrasi ke project Supabase milik pengguna, membuat project cloud, atau mengubah data cloud tanpa konfigurasi dan persetujuan eksplisit.

# 6. ROLE-BASED ACCESS CONTROL

Gunakan lima role berikut secara konsisten:

## Super Admin
- Mengelola akun pengguna dan role.
- Mengakses seluruh turnamen.
- Mengelola konfigurasi sistem.
- Melihat laporan keseluruhan.

## Tournament Organizer
- Membuat dan mengelola turnamen miliknya.
- Menentukan game, aturan, format, kuota, biaya, hadiah, dan jadwal.
- Mengelola pendaftaran.
- Membuat bracket.
- Melihat laporan turnamen yang menjadi tanggung jawabnya.

## Committee / Panitia
- Mengakses turnamen yang ditugaskan.
- Memverifikasi peserta dan pembayaran.
- Mengelola jadwal sesuai kewenangan.
- Memasukkan dan memperbarui skor sesuai aturan.
- Membuat pengumuman sesuai izin.

## Team Captain
- Membuat atau mendaftarkan tim.
- Mengelola anggota tim miliknya.
- Mengisi ID game dan informasi pemain.
- Mengirim bukti pembayaran.
- Melihat status pendaftaran, jadwal, bracket, dan hasil.

## Player
- Melihat informasi turnamen.
- Melihat profil tim dan informasi pemain yang memang boleh ditampilkan.
- Melihat jadwal, bracket, hasil, dan pengumuman.
- Mengelola profil pribadi.

Authorization wajib diperiksa di backend dan diperkuat dengan Supabase RLS. Jangan hanya menyembunyikan tombol/menu di frontend.

Role tidak boleh dapat diubah sendiri oleh pengguna biasa. Gunakan mekanisme tepercaya untuk pemberian role. Jangan memakai user-editable metadata sebagai dasar keputusan authorization.

Buat `docs/contracts/role-permissions.md` berisi matriks izin setiap role terhadap operasi dan sumber daya.

# 7. PARALLEL DEVELOPMENT — CONTRACT FIRST

Fondasi proyek harus memungkinkan lima anggota bekerja bersamaan tanpa menunggu modul lain selesai.

Sebelum implementasi penuh, tetapkan kontrak:
- Database contract.
- API contract.
- Service contract.
- Frontend contract.
- Module ownership.
- Format data dan error.

Buat dokumen:
- `docs/contracts/database-contract.md`
- `docs/contracts/api-contract.md`
- `docs/contracts/frontend-contract.md`
- `docs/contracts/module-contract.md`
- `docs/contracts/role-permissions.md`

Sediakan mock data dan mock repository agar setiap modul dapat dikembangkan tanpa Supabase/API yang sudah aktif.

Gunakan interface/protocol repository yang konsisten. Mock repository dan Supabase repository harus memenuhi kontrak yang sama.

Sediakan konfigurasi:

`APP_MODE=mock`

sebagai mode awal. Aplikasi harus bisa dibuka dan diuji dalam mock mode tanpa kredensial cloud.

Sediakan opsi:

`APP_MODE=supabase`

untuk integrasi online. Jangan mencampur implementasi mock dan production secara sembarangan. Tampilkan indikator yang jelas ketika aplikasi memakai data simulasi.

# 8. REST API CONTRACT

Gunakan prefix `/api/v1`.

Siapkan endpoint berikut sebagai kontrak awal:

### Health
- `GET /api/v1/health`

### Authentication
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Games
- `GET /api/v1/games`
- `GET /api/v1/games/<id>`

### Tournaments
- `GET /api/v1/tournaments`
- `POST /api/v1/tournaments`
- `GET /api/v1/tournaments/<id>`
- `PATCH /api/v1/tournaments/<id>`
- `DELETE /api/v1/tournaments/<id>`

### Teams
- `GET /api/v1/teams`
- `POST /api/v1/teams`
- `GET /api/v1/teams/<id>`
- `PATCH /api/v1/teams/<id>`
- `POST /api/v1/teams/<id>/members`

### Registrations
- `GET /api/v1/tournaments/<id>/registrations`
- `POST /api/v1/tournaments/<id>/registrations`
- `PATCH /api/v1/registrations/<id>/status`

### Matches
- `GET /api/v1/tournaments/<id>/matches`
- `POST /api/v1/tournaments/<id>/bracket/generate`
- `PATCH /api/v1/matches/<id>/result`

### Announcements
- `GET /api/v1/tournaments/<id>/announcements`
- `POST /api/v1/tournaments/<id>/announcements`

### Reports
- `GET /api/v1/tournaments/<id>/reports`
- `GET /api/v1/tournaments/<id>/standings`

Gunakan response JSON konsisten.

Sukses:

```json
{
  "success": true,
  "message": "Data berhasil diperoleh",
  "data": {}
}
```

Error:

```json
{
  "success": false,
  "message": "Terjadi kesalahan",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {}
  }
}
```

Dokumentasikan HTTP method, request body, response, authentication, dan akses role untuk setiap endpoint. Jangan implementasikan semua fitur secara penuh pada tahap starter. Implementasikan health endpoint dan beberapa contoh endpoint yang benar-benar berfungsi; sisanya boleh berupa blueprint/contract yang jelas, bukan tombol atau endpoint palsu.

# 9. MOCK DATA & REPOSITORY

Sediakan mock data minimal:
- 3 game.
- 2 turnamen.
- 8 tim untuk simulasi bracket.
- Beberapa pemain per tim.
- Beberapa jadwal dan hasil pertandingan.
- Pengumuman contoh.

Data harus konsisten antar entitas.

Adriel harus dapat menguji Single Elimination dengan 8 tim tanpa Supabase.

Buat mock repository dengan interface sama seperti repository produksi.

# 10. TOURNAMENT LOGIC FOUNDATION

Siapkan fondasi algoritma Single Elimination.

Untuk 8 tim:
- Quarter Final: 4 pertandingan.
- Semi Final: 2 pertandingan.
- Final: 1 pertandingan.

Struktur match setidaknya memuat:
- Round.
- Match number.
- Team A.
- Team B.
- Score A.
- Score B.
- Winner.
- Match status.
- Next match.
- Next slot.

Aturan:
- Pemenang maju otomatis hanya setelah hasil valid disahkan.
- Skor divalidasi sesuai aturan kompetisi yang ditetapkan.
- Match belum dimainkan tidak boleh memiliki pemenang.
- Seri harus ditangani berdasarkan aturan game/turnamen, bukan diputuskan secara acak.
- Hasil yang sudah disahkan tidak boleh diubah tanpa otorisasi dan audit trail.
- Tentukan dan dokumentasikan penanganan jumlah tim yang bukan pangkat dua, termasuk bye.

Buat unit tests untuk algoritma bracket, perpindahan pemenang, validasi skor, bye, dan edge cases.

# 11. UI/UX FOUNDATION

Arah desain:
- Modern esports management dashboard.
- Desktop-first untuk Windows.
- Dark theme yang profesional.
- Bersih, mudah dipahami, tidak terlalu ramai.
- Hierarki informasi jelas.
- Tipografi terbaca.
- Fokus pada informasi turnamen dan pertandingan.

Buat komponen dasar:
- Sidebar.
- Topbar.
- Dashboard cards.
- Data tables.
- Modal/dialog.
- Forms.
- Search dan filter.
- Status badges.
- Toast notifications.
- Loading, empty, error, dan success states.

Halaman awal:
- Login.
- Dashboard.
- Tournament List.
- Tournament Detail.
- Team Management.
- Match Management.
- Bracket.
- Announcements.
- Reports.
- User Profile.

Buat halaman yang dapat dibuka dalam mock mode. Jangan membuat tombol aktif yang tidak memiliki fungsi tanpa memberi status placeholder yang jelas.

Buat `DESIGN.md` sebagai draft arahan visual untuk ditinjau Ferlita. Jangan mengunci palet warna, font, atau layout final tanpa persetujuan koordinator desain.

# 12. MEMBER TASK FILES

Wajib buat lima file instruksi mandiri:

- `docs/tasks/ferlita.md`
- `docs/tasks/fikri.md`
- `docs/tasks/habil.md`
- `docs/tasks/adriel.md`
- `docs/tasks/anisa.md`

Setiap file memuat:
1. Identitas dan tanggung jawab anggota.
2. Tujuan pekerjaan.
3. Daftar tugas terperinci.
4. Folder yang menjadi tanggung jawab.
5. File yang harus dibuat/diubah.
6. Batas file yang tidak boleh diubah tanpa koordinasi.
7. Dependensi modul.
8. Kontrak input/output.
9. Mock data yang tersedia.
10. Cara menjalankan modul.
11. Skenario pengujian.
12. Acceptance criteria.
13. Checklist pekerjaan.
14. Cara menyerahkan hasil ke repository utama.
15. Agent Skills yang wajib dibaca berdasarkan addendum.

Instruksi harus cukup jelas agar anggota dapat bekerja tanpa menunggu anggota lain, selama kontrak bersama sudah tersedia.

# 13. GITHUB WORKFLOW — SINGLE MAIN BRANCH

Kelompok hanya menggunakan satu branch: `main`.

Jangan membuat branch individual dan jangan menerapkan workflow yang terlalu kompleks.

Buat `CONTRIBUTING.md` dengan panduan berikut:

Sebelum bekerja:

```bash
git pull origin main
```

Setelah menyelesaikan satu bagian:

```bash
git add .
git commit -m "feat: descriptive feature name"
git push origin main
```

Aturan:
- Hindari dua anggota mengedit file yang sama pada waktu bersamaan.
- Jangan menghapus hasil kerja anggota lain.
- Jangan menggunakan force push.
- Selalu pull sebelum mulai bekerja.
- Komunikasikan perubahan kontrak bersama.
- Jika push ditolak karena remote memiliki commit baru, lakukan pull/rebase dengan hati-hati dan selesaikan konflik. Jangan menimpa perubahan orang lain.
- Sediakan GitHub Desktop sebagai opsi untuk anggota yang belum terbiasa terminal.

Jangan melakukan commit atau push otomatis.

# 14. PROJECT DIRECTORY STRUCTURE

Gunakan struktur ini sebagai dasar. Lakukan penyesuaian kecil hanya bila ada alasan arsitektur yang kuat.

```text
turnamen-in/
├── README.md
├── CONTRIBUTING.md
├── requirements.txt
├── .env.example
├── .gitignore
├── run.py
├── AGENTS.md
├── DESIGN.md
├── desktop/
│   ├── launcher/
│   ├── bridge/
│   └── web/
│       ├── index.html
│       ├── pages/
│       └── assets/
│           ├── css/
│           ├── js/
│           │   ├── core/
│           │   ├── components/
│           │   └── pages/
│           └── images/
├── backend/
│   ├── app.py
│   ├── api/
│   │   ├── routes/
│   │   └── schemas/
│   ├── core/
│   ├── contracts/
│   ├── infrastructure/
│   │   └── supabase/
│   ├── modules/
│   │   ├── auth/
│   │   ├── tournaments/
│   │   ├── teams/
│   │   ├── matches/
│   │   ├── reports/
│   │   └── announcements/
│   └── repositories/
│       ├── interfaces/
│       ├── mock/
│       └── supabase/
├── supabase/
│   ├── migrations/
│   └── seed.sql
├── docs/
│   ├── architecture.md
│   ├── database-schema.md
│   ├── tasks/
│   ├── contracts/
│   ├── api/
│   └── guides/
├── tests/
│   ├── unit/
│   └── integration/
└── scripts/
```

Skill folders yang diminta addendum berada di `.agents/skills/` dan harus ikut masuk Git. Hindari file kosong tanpa tujuan; gunakan stub dengan TODO dan dokumentasi interface jika implementasi belum tersedia.

# 15. SECURITY REQUIREMENTS

- Jangan menyimpan credential nyata di repository.
- Buat `.env.example`, bukan `.env` berisi secret.
- Jangan pernah mengekspos Supabase `service_role` atau secret key ke frontend, desktop client yang didistribusikan, atau GitHub.
- Gunakan publishable key bersama autentikasi pengguna dan RLS.
- Operasi istimewa dilakukan melalui backend terpercaya.
- Jangan mempercayai role dari frontend atau user-editable metadata.
- Terapkan RLS pada tabel yang diekspos melalui Data API.
- Batasi Flask API ke localhost secara default.
- Validasi seluruh input.
- Hindari SQL injection.
- Jangan menyimpan password plaintext.
- Jangan menampilkan token atau secret di log.

Buat `docs/security.md` yang menjelaskan keputusan keamanan dan batasan aplikasi desktop. Verifikasi dokumentasi Supabase terkini sebelum menerapkan konfigurasi Auth, RLS, Storage, dan Data API.

# 16. TESTING

Gunakan pytest untuk testing dasar. Minimal:
- Test konfigurasi dan mock mode.
- Test health endpoint.
- Test format response.
- Test autentikasi dasar dalam mock mode.
- Test pembuatan turnamen.
- Test registrasi tim.
- Test bracket 8 tim.
- Test penentuan pemenang dan perpindahan babak.
- Test permission dasar.

Jangan mengklaim integrasi Supabase berhasil jika belum diuji dengan konfigurasi dan kredensial yang valid.

# 17. SETUP & DEVELOPER EXPERIENCE

README harus menjelaskan:
1. Deskripsi proyek dan stack.
2. Struktur folder.
3. Persyaratan Python dan cara membuat virtual environment.
4. Instalasi requirements.
5. Cara menjalankan mock mode.
6. Cara konfigurasi Supabase.
7. Cara menjalankan aplikasi desktop dan API.
8. Cara menjalankan test.
9. Cara bekerja dengan satu branch.
10. Cara membaca task file anggota.
11. Cara menggunakan Agent Skills sesuai addendum.

Mode mock harus berjalan tanpa kredensial cloud. Jangan mewajibkan pengguna mengisi Supabase sebelum dapat melihat dan menguji base application.

# 18. IMPLEMENTATION RULES

1. Periksa repository aktif dan status Git sebelum mengubah file.
2. Jangan menghapus atau menimpa pekerjaan yang sudah ada tanpa alasan dan persetujuan.
3. Gunakan struktur modular dan konsisten.
4. Identifier kode menggunakan bahasa Inggris; dokumentasi/instruksi anggota menggunakan bahasa Indonesia.
5. Hindari duplikasi business logic.
6. Hindari overengineering dan dependency yang tidak perlu.
7. Jangan membuat fitur palsu hanya untuk memenuhi daftar.
8. Pastikan import dan launcher berfungsi.
9. Pin dependency yang digunakan pada versi kompatibel dan sertakan file lock bila sesuai.
10. Periksa dokumentasi resmi untuk fitur yang berubah cepat.
11. Jangan melakukan deployment eksternal.
12. Jangan membuat project Supabase atau mengubah project cloud pengguna.
13. Jangan melakukan Git commit atau push otomatis.
14. Pertahankan satu branch `main`.
15. Fokus pada fondasi dan base code, bukan implementasi seluruh fitur produksi.
16. Baca dan ikuti `TURNAMEN-IN-AGENT-SKILLS-ADDENDUM.md` untuk integrasi skill, sumber eksternal, dan mapping masing-masing anggota.

# 19. FINAL ACCEPTANCE CHECKLIST

Pastikan dan laporkan status setiap item:

- [ ] Struktur folder terbentuk.
- [ ] Base code Python Eel tersedia.
- [ ] Flask REST API dapat berjalan.
- [ ] Desktop dan API dapat dijalankan melalui launcher.
- [ ] Mock mode berjalan tanpa kredensial cloud.
- [ ] SQL migration tersedia.
- [ ] Database schema terdokumentasi.
- [ ] Role dan permission terdokumentasi.
- [ ] API contract tersedia.
- [ ] Mock data tersedia dan konsisten.
- [ ] Repository interfaces tersedia.
- [ ] Task file Ferlita tersedia.
- [ ] Task file Fikri tersedia.
- [ ] Task file Habil tersedia.
- [ ] Task file Adriel tersedia.
- [ ] Task file Anisa tersedia.
- [ ] README lengkap.
- [ ] CONTRIBUTING menjelaskan single-main workflow.
- [ ] `.env.example` tersedia.
- [ ] `.gitignore` aman.
- [ ] Unit tests dasar berhasil.
- [ ] Tidak ada secret yang terekspos.
- [ ] Addendum Agent Skills sudah diproses atau status kebutuhan manualnya dijelaskan.

# 20. FINAL REPORT

Setelah pekerjaan selesai, laporkan dalam bahasa Indonesia:
1. Struktur folder yang dibuat.
2. File penting yang berhasil dibuat.
3. Base code yang dapat dijalankan.
4. Lima file instruksi anggota.
5. Database schema dan REST API contract.
6. Hasil pengujian yang benar-benar dijalankan.
7. Cara menjalankan aplikasi.
8. Konfigurasi manual yang masih dibutuhkan.
9. Bagian yang belum selesai atau belum dapat diverifikasi.
10. Langkah pertama yang harus dilakukan setiap anggota.

Jangan mengklaim suatu fitur atau integrasi berhasil jika belum diuji.

---

# PERINTAH AKHIR

Mulai dengan memeriksa repository aktif dan membaca kedua dokumen:
- `MASTER-PROMPT-TURNAMEN-IN.md` (dokumen ini).
- `TURNAMEN-IN-AGENT-SKILLS-ADDENDUM.md`.

Implementasikan Starter Repository Turnamen.in sesuai spesifikasi. Gunakan folder repository aktif sebagai root; jangan membuat folder project bersarang. Jangan membangun ulang atau menghapus pekerjaan yang sudah ada. Utamakan konsistensi arsitektur, kontrak antarmodul, pengembangan paralel, dan kemampuan menjalankan base project dalam mock mode.
