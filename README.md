# Turnamen.in: Esports Tournament Management System (Starter Repository)

**Turnamen.in** adalah aplikasi desktop berbasis **Python Eel + Flask REST API + Supabase PostgreSQL** untuk Windows 10/11 yang membantu penyelenggara, panitia, kapten tim, dan pemain mengelola turnamen e-sport secara terpusat, mulai dari pembuatan turnamen, registrasi tim, verifikasi peserta, penyusunan bracket **Single Elimination**, pencatatan skor, pengumuman, hingga laporan hasil turnamen.

Sistem dirancang bersifat **game-agnostic** (mendukung *Mobile Legends: Bang Bang*, *VALORANT*, *PUBG Mobile*, *Free Fire*, *Dota 2*, *EA Sports FC*, dll.) dan menerapkan pendekatan **Contract-First Parallel Development** agar lima anggota kelompok dapat mengembangkan modul secara bersamaan menggunakan **`APP_MODE=mock`** tanpa bergantung pada kredensial cloud.

---

## 1. Teknologi yang Digunakan (Technology Stack)

| Layer | Teknologi | Keterangan |
| :--- | :--- | :--- |
| **Desktop Container** | Python 3.10 to 3.12, Python Eel `0.16.0` | Diikat ke `127.0.0.1` (`localhost`), versi dependensi dipin untuk stabilitas |
| **Frontend UI** | HTML5, CSS3, Vanilla JavaScript (ES6+) | *Dark Esports Management Dashboard*, tanpa framework frontend berat |
| **REST API Layer** | Flask `3.0.3` (`/api/v1`) | Format JSON terstandarisasi, validasi input, dan otorisasi RBAC |
| **Database & Cloud** | Supabase PostgreSQL, Auth, Storage, Realtime | Dilengkapi migrasi SQL 12 tabel, RLS, dan `MockRepository` lokal |
| **Testing & Config** | `pytest`, `python-dotenv` | Unit & integration tests berjalan 100% offline pada mode mock |

> **Catatan Pemeliharaan Python Eel:** Python Eel merupakan pustaka open-source yang tidak lagi aktif dipelihara di upstream. Proyek ini tetap menggunakannya sesuai spesifikasi platform dengan mitigasi ketat: seluruh paket dipin di `requirements.txt`, server lokal hanya mendengarkan pada `127.0.0.1`, dan fungsi `@eel.expose` dibatasi seminimal mungkin.

---

## 2. Pembagian Tim, Branch, & Kepemilikan Modul (Team Ownership)

| Anggota | Peran | Branch Resmi | Folder Tanggung Jawab Utama | File Instruksi Mandiri |
| :--- | :--- | :--- | :--- | :--- |
| **Ferlita** | Project Coordinator & UI/UX Designer | `feature/ferlita-ui-ux` | `desktop/web/pages/`, `desktop/web/assets/css/`, `desktop/web/assets/images/`, `DESIGN.md` | [`docs/tasks/ferlita.md`](docs/tasks/ferlita.md) |
| **Fikri** | System Integration & Python Eel Developer | `feature/fikri-eel` | `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py` | [`docs/tasks/fikri.md`](docs/tasks/fikri.md) |
| **Habil** | Database & Authentication Developer | `feature/habil-database-auth` | `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/` | [`docs/tasks/habil.md`](docs/tasks/habil.md) |
| **Adriel** | Tournament & Match System Developer | `feature/adriel-tournament-match` | `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/` | [`docs/tasks/adriel.md`](docs/tasks/adriel.md) |
| **Anisa** | REST API, Reporting & Testing Developer | `feature/anisa-api-report` | `backend/api/`, `backend/modules/reports/`, `backend/modules/announcements/`, `tests/`, `docs/api/` | [`docs/tasks/anisa.md`](docs/tasks/anisa.md) |

---

## 3. Struktur Direktori Proyek

```text
C:\Turnamen.in\
├── README.md
├── CONTRIBUTING.md
├── requirements.txt
├── .env.example
├── .gitignore
├── run.py
├── AGENTS.md
├── DESIGN.md
├── skills-lock.json
├── .agents/
│   └── skills/                      # 11 External Skills + 7 Custom Turnamen.in Skills
├── desktop/
│   ├── launcher/                    # Orchestrator proses Flask + Python Eel (Fikri)
│   ├── bridge/                      # Fungsi @eel.expose aman (Fikri)
│   └── web/
│       ├── index.html               # App shell utama (Ferlita)
│       ├── pages/                   # Template 10 halaman utama (Ferlita)
│       └── assets/
│           ├── css/                 # variables.css, layout.css, components.css (Ferlita)
│           ├── js/
│           │   ├── core/            # config.js, eel-bridge.js, api-client.js (Fikri)
│           │   ├── components/      # ui-components.js (Ferlita)
│           │   └── pages/           # app-pages.js (Ferlita)
│           └── images/              # Aset visual & logo (Ferlita)
├── backend/
│   ├── app.py                       # Flask application factory (Anisa & Fikri)
│   ├── api/
│   │   ├── routes/                  # Endpoint /api/v1/* (Anisa)
│   │   └── schemas/                 # Formatter JSON & validator request (Anisa)
│   ├── core/                        # Konfigurasi .env, logging, exceptions
│   ├── contracts/                   # Konstanta role, status, dan DTO
│   ├── infrastructure/
│   │   └── supabase/                # Inisialisasi klien Supabase (Habil)
│   ├── modules/
│   │   ├── auth/                    # Autentikasi & matriks RBAC 5 role (Habil)
│   │   ├── tournaments/             # Manajemen turnamen & registrasi (Adriel)
│   │   ├── teams/                   # Manajemen tim & anggota (Adriel)
│   │   ├── matches/                 # Single Elimination Bracket Engine & skor (Adriel)
│   │   ├── reports/                 # Statistik turnamen & klasemen/standings (Anisa)
│   │   └── announcements/           # Pengumuman turnamen (Anisa)
│   └── repositories/
│       ├── interfaces/              # DataStoreRepositoryProtocol (Habil)
│       ├── mock/                    # MockDataStoreRepository & demo data (Habil)
│       └── supabase/                # SupabaseDataStoreRepository (Habil)
├── supabase/
│   ├── migrations/                  # 0001_initial_schema.sql (12 tabel + RLS)
│   └── seed.sql                     # Data awal demo konsisten
├── docs/
│   ├── GIT_WORKFLOW.md              # Panduan lengkap Git Branch Workflow
│   ├── architecture.md
│   ├── database-schema.md
│   ├── security.md
│   ├── skill-sources.md
│   ├── tasks/                       # 5 file instruksi mandiri anggota
│   ├── contracts/                   # Kontrak DB, API, Frontend, Modul, & Role
│   ├── api/                         # Dokumentasi endpoint REST API
│   └── guides/                      # Panduan setup pengembang Windows
├── tests/
│   ├── unit/                        # Unit test config, auth/RBAC, & bracket engine
│   └── integration/                 # Integration test endpoint Flask REST API
└── scripts/
    └── verify_starter.py            # Skrip verifikasi struktur, skill, & kesehatan aplikasi
```

---

## 4. Persyaratan Python & Instalasi Virtual Environment

Pastikan **Python 3.10 / 3.11 / 3.12** sudah terpasang di Windows 10/11. Buka PowerShell pada direktori `C:\Turnamen.in`:

```powershell
# 1. Buat virtual environment
python -m venv .venv

# 2. Aktifkan virtual environment (PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Pasang seluruh dependensi yang telah dipin
pip install -r requirements.txt

# 4. Salin file contoh konfigurasi environment
Copy-Item .env.example .env
```

---

## 5. Cara Menjalankan Mock Mode (Default: Tanpa Kredensial Cloud)

Secara bawaan, `.env.example` menetapkan `APP_MODE=mock`. Anda **tidak perlu** mengisi kredensial Supabase untuk menjalankan dan menguji aplikasi:

```powershell
# Memeriksa kesehatan konfigurasi, mock repository, dan endpoint API:
python run.py --check

# Menjalankan aplikasi lengkap (Server Flask REST API + Jendela Desktop Python Eel):
python run.py

# Menjalankan hanya server Flask REST API + Web UI di http://127.0.0.1:5000:
python run.py --api-only
```

Saat berjalan dalam mode mock, Topbar aplikasi akan menampilkan badge **`MOCK MODE (DATA SIMULASI LOKAL)`** beserta pemilih cepat 5 role pengguna (*Super Admin*, *Tournament Organizer*, *Committee*, *Team Captain*, *Player*).

---

## 6. Cara Konfigurasi Supabase (`APP_MODE=supabase`)

Apabila tim siap menguji integrasi cloud bersama Habil:
1. Buat proyek di Supabase dan jalankan skrip [`supabase/migrations/0001_initial_schema.sql`](supabase/migrations/0001_initial_schema.sql) diikuti [`supabase/seed.sql`](supabase/seed.sql) pada SQL Editor Supabase.
2. Buka file `.env` lokal Anda (jangan pernah di-commit ke Git) dan ubah:
   ```ini
   APP_MODE=supabase
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_ANON_KEY=<publishable-anon-key-anda>
   ```
3. **Peringatan Keamanan:** Jangan pernah memasukkan `service_role` key ke dalam `.env` distribusi aplikasi desktop atau frontend.

---

## 7. Cara Menjalankan Pengujian (`pytest`)

Seluruh pengujian dasar (konfigurasi, `/api/v1/health`, format JSON, autentikasi mock, pembuatan turnamen, registrasi tim, algoritma bracket 8 tim, penanganan *bye*, validasi skor, perpindahan babak, dan matriks RBAC) dapat dijalankan dengan:

```powershell
pytest -v
```

Untuk menjalankan verifikasi menyeluruh atas kelengkapan file, YAML frontmatter Agent Skills, dan smoke test aplikasi:

```powershell
python scripts/verify_starter.py
```

---

## 8. Cara Berkontribusi & Git Branch Workflow

Repository ini menggunakan sistem **branch terpisah untuk setiap anggota**:
- **`main`** adalah branch integrasi utama untuk kode yang sudah diperiksa dan lulus pengujian.
- Setiap anggota bekerja pada branch khusus miliknya (`feature/ferlita-ui-ux`, `feature/fikri-eel`, `feature/habil-database-auth`, `feature/adriel-tournament-match`, dan `feature/anisa-api-report`).
- Anggota tidak mengerjakan fitur langsung di `main` dan tidak menggunakan `git push --force`.
- Seluruh perubahan dikirimkan ke branch masing-masing lalu digabungkan ke `main` melalui **Pull Request (PR)**.

Detail lengkap workflow, perintah Git harian, sinkronisasi branch, dan penanganan konflik tersedia di [`CONTRIBUTING.md`](CONTRIBUTING.md) dan [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md).

---

## 9. Cara Membaca File Tugas Anggota

Setiap anggota memiliki dokumen panduan mandiri di `docs/tasks/`:
- **Ferlita:** [`docs/tasks/ferlita.md`](docs/tasks/ferlita.md)
- **Fikri:** [`docs/tasks/fikri.md`](docs/tasks/fikri.md)
- **Habil:** [`docs/tasks/habil.md`](docs/tasks/habil.md)
- **Adriel:** [`docs/tasks/adriel.md`](docs/tasks/adriel.md)
- **Anisa:** [`docs/tasks/anisa.md`](docs/tasks/anisa.md)

---

## AI Agent Skills & Engineering Standards

Proyek ini dilengkapi dengan sistem **Agent Skills** tingkat proyek di `.agents/skills/` yang ikut disimpan ke GitHub (tidak diabaikan oleh `.gitignore`), sehingga seluruh anggota langsung memperoleh standar AI Agent yang seragam setelah melakukan `git clone` atau sinkronisasi dari `main`. Rincian lisensi, commit SHA, dan sumber repositori tercatat di [`docs/skill-sources.md`](docs/skill-sources.md).

### 1. External Skills (Terpasang di `.agents/skills/`)
- **Anti-Slop (`miqdadbadjuber/anti-slop` v3.2.28):** `antislop`, `antislop-ui`, `antislop-human`, `antislop-code`, `antislop-copywriting` (Catatan: `antislop-layoutmobile` sengaja tidak dipasang karena aplikasi bersifat desktop-first).
- **Supabase (`supabase/agent-skills`):** `supabase`, `supabase-postgres-best-practices`.
- **Hexagonal Architecture (`Remy349/skills`):** `hexagonal-python` (diadaptasi secara proporsional dengan Supabase SDK tanpa SQLAlchemy).
- **Engineering Workflow (`dgalarza/agent-skills`):** `tdd`, `team-code-review`.
- **Frontend Design (`Junaid-PK/frontend-design-skill`):** `frontend-design` (opsional untuk Ferlita; `DESIGN.md` tetap menjadi acuan utama).

### 2. Custom Turnamen.in Skills (Terpasang di `.agents/skills/`)
- `turnamen-project-standards`: Standar arsitektur, konvensi kode, dan workflow paralel seluruh anggota.
- `turnamen-frontend-ui`: Panduan UI/UX desktop dan komponen untuk Ferlita.
- `turnamen-python-eel`: Panduan launcher, Python Eel bridge, dan konfigurasi untuk Fikri.
- `turnamen-supabase-security`: Panduan PostgreSQL 12 tabel, Auth, RBAC 5 role, dan RLS untuk Habil.
- `turnamen-bracket-engine`: Panduan algoritma Single Elimination, *bye*, dan validasi skor untuk Adriel.
- `turnamen-flask-api`: Panduan Flask REST API `/api/v1`, laporan, dan testing untuk Anisa.
- `turnamen-quality-gates`: Standar unit/integration test dan *Definition of Done* seluruh anggota.

### 3. Repository Referensi Teknis
- **Python Eel:** <https://github.com/python-eel/Eel>
- **Flask:** <https://github.com/pallets/flask>
- **pytest:** <https://github.com/pytest-dev/pytest>
- **OWASP Cheat Sheet Series:** <https://github.com/OWASP/CheatSheetSeries>
- **Supabase Docs:** <https://supabase.com/docs>

### 4. Daftar Skill Wajib per Anggota
| Anggota | Skill Wajib | Skill Tambahan / Opsional |
| :--- | :--- | :--- |
| **Ferlita** | `antislop`, `antislop-ui`, `antislop-human`, `antislop-copywriting`, `turnamen-project-standards`, `turnamen-frontend-ui`, `turnamen-quality-gates` | `frontend-design`, `tdd` |
| **Fikri** | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-python-eel`, `turnamen-quality-gates` | `hexagonal-python`, `tdd`, `team-code-review` |
| **Habil** | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-supabase-security`, `turnamen-quality-gates` | `supabase`, `supabase-postgres-best-practices`, `tdd` |
| **Adriel** | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-bracket-engine`, `turnamen-quality-gates` | `tdd`, `team-code-review` |
| **Anisa** | `antislop`, `antislop-code`, `antislop-copywriting`, `turnamen-project-standards`, `turnamen-flask-api`, `turnamen-quality-gates` | `hexagonal-python`, `tdd`, `team-code-review` |

### 5. Cara Instalasi, Pembaruan, Verifikasi, dan Memulai Sesi AGY Baru
- **Verifikasi Skill Terpasang:**
  ```powershell
  npx skills list
  python scripts/verify_starter.py
  ```
- **Memulihkan External Skill dari Lockfile (Bila Diperlukan):**
  ```powershell
  npx skills experimental_install
  ```
- **Memperbarui External Skill (Setelah Meninjau Upstream):**
  ```powershell
  npx skills update -p
  ```
- **Memulai Sesi Antigravity (AGY) Baru:**
  1. Pastikan Anda berada di branch kerja masing-masing (`git switch <nama-branch-anda>`) dan sinkron dengan `origin/main`.
  2. Minta agent membaca `AGENTS.md`, `docs/tasks/<nama-anda>.md`, `docs/GIT_WORKFLOW.md`, seluruh skill wajib pada tabel di atas, dan kontrak di `docs/contracts/`.
  3. Kembangkan fitur pada folder tanggung jawab Anda, uji dengan `pytest`, lalu lakukan `git add`, `git commit`, `git push` ke branch Anda, dan ajukan Pull Request ke `main`.
