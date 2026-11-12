# Instruksi Tugas Mandiri: ANISA (REST API, Reporting & Testing Developer)

---

## 1. Identitas dan Tanggung Jawab Anggota
- **Nama Anggota:** Anisa
- **Peran:** REST API, Reporting & Testing Developer
- **Branch Resmi:** `feature/anisa-api-report`
- **Tanggung Jawab Utama:**
  - Mengembangkan aplikasi Flask REST API (`backend/app.py` dan `backend/api/`) dengan prefix `/api/v1`.
  - Membuat validasi request dan memelihara konsistensi format response JSON (`success`, `message`, `data` / `error`).
  - Mengembangkan modul pengumuman (`backend/modules/announcements/`) serta statistik, klasemen, dan laporan turnamen (`backend/modules/reports/`).
  - Menyusun dan memelihara dokumentasi REST API (`docs/api/`).
  - Menguji endpoint API dan integrasi lintas modul menggunakan `pytest` (`tests/`).

## 2. Tujuan Pekerjaan
Menyediakan lapisan REST API `/api/v1` yang konsisten, tervalidasi, aman, dan terdokumentasi dengan baik, serta menyajikan laporan statistik dan pengumuman turnamen yang siap dikonsumsi oleh aplikasi desktop.

## 3. Daftar Tugas Terperinci
1. Mengelola Flask application factory di `backend/app.py` dan error handler global agar setiap pengecualian (`DomainError`, `404`, `405`, `500`) selalu mengembalikan JSON standar.
2. Mengembangkan helper response dan schema validator di `backend/api/schemas/`.
3. Mengembangkan dan memelihara blueprint route di `backend/api/routes/v1_routes.py` untuk seluruh grup kontrak:
   - `Health`, `Authentication`, `Games`, `Tournaments`, `Teams`, `Registrations`, `Matches`, `Announcements`, dan `Reports`.
4. Mengembangkan `AnnouncementService` (`backend/modules/announcements/service.py`) dan `ReportService` (`backend/modules/reports/service.py` untuk laporan statistik & klasemen `standings`).
5. Memelihara dokumentasi endpoint di [`docs/api/openapi-overview.md`](file:///C:/Turnamen.in/docs/api/openapi-overview.md) dan suite pengujian integrasi di `tests/integration/test_api_endpoints.py`.

## 4. Folder yang Menjadi Tanggung Jawab
- `backend/app.py`
- `backend/api/`
- `backend/modules/reports/`
- `backend/modules/announcements/`
- `tests/`
- `docs/api/`

## 5. File yang Harus Dibuat / Diubah
- `backend/app.py`
- `backend/api/schemas/responses.py`
- `backend/api/schemas/validators.py`
- `backend/api/routes/v1_routes.py`
- `backend/modules/announcements/service.py`
- `backend/modules/reports/service.py`
- `docs/api/openapi-overview.md`
- `tests/conftest.py`
- `tests/integration/test_api_endpoints.py`

## 6. Batas File yang Tidak Boleh Diubah Tanpa Koordinasi
- `desktop/web/pages/*` dan `desktop/web/assets/css/*` (Milik **Ferlita**).
- `desktop/launcher/*`, `desktop/bridge/*`, dan `run.py` (Milik **Fikri**).
- `supabase/*`, `backend/modules/auth/*`, dan `backend/repositories/*` (Milik **Habil**).
- `backend/modules/tournaments/*`, `backend/modules/teams/*`, dan `backend/modules/matches/*` (Milik **Adriel**).

## 7. Dependensi Modul
- Memanggil `AuthService` & `RolePermissionGuard` (Habil).
- Memanggil `TournamentService`, `TeamService`, & `MatchService` (Adriel).
- Dikonsumsi oleh `api-client.js` (Fikri) dan komponen UI (Ferlita).

## 8. Kontrak Input / Output
Wajib mematuhi struktur JSON pada [`docs/contracts/api-contract.md`](file:///C:/Turnamen.in/docs/contracts/api-contract.md):
- **Response Sukses:** `{"success": true, "message": "...", "data": ...}`
- **Response Error:** `{"success": false, "message": "...", "error": {"code": "...", "details": ...}}`

## 9. Mock Data yang Tersedia
Seluruh endpoint `/api/v1/*` langsung menggunakan `MockDataStoreRepository` saat `APP_MODE=mock`, sehingga Anisa dapat menguji seluruh skenario HTTP (200, 201, 400, 401, 403, 404, 409) menggunakan `pytest` tanpa server database eksternal.

## 10. Cara Menjalankan Modul
```powershell
# 1. Menjalankan seluruh unit & integration test
pytest -v

# 2. Menjalankan khusus integration test REST API
pytest tests/integration/test_api_endpoints.py -v

# 3. Menjalankan server Flask API secara mandiri untuk uji manual (curl / Postman / Browser)
python run.py --api-only
```

## 11. Skenario Pengujian
1. **Health & Format Response:** Panggil `GET /api/v1/health`, pastikan mengembalikan HTTP `200` dengan `success: true`, `message`, dan `data.status == "healthy"`.
2. **Validasi Request:** Kirim `POST /api/v1/tournaments` dengan body kosong `{}` sebagai `organizer`, pastikan mengembalikan HTTP `400` dengan `error.code == "VALIDATION_ERROR"`.
3. **Otorisasi Role di Endpoint:** Kirim `POST /api/v1/tournaments` sebagai `player`, pastikan ditolak dengan HTTP `403` dan `error.code == "FORBIDDEN"`.
4. **Alur End-to-End Turnamen & Laporan:** Uji pembuatan turnamen, pendaftaran tim, verifikasi registrasi, generate bracket, update skor pertandingan, publikasi pengumuman, serta pengambilan `/reports` dan `/standings`.

## 12. Acceptance Criteria
- Seluruh endpoint pada Bagian 8 Master Prompt tersedia pada prefix `/api/v1`.
- Format JSON sukses dan error 100% seragam di seluruh endpoint.
- Pesan respons API ditulis dengan bahasa Indonesia yang jelas sesuai standar `antislop-copywriting`.
- Seluruh integration test di `tests/integration/test_api_endpoints.py` lulus (`pytest`).

## 13. Checklist Pekerjaan
- [ ] Memverifikasi seluruh endpoint `/api/v1/*` pada `backend/api/routes/v1_routes.py`.
- [ ] Memastikan validasi request dan penanganan error berjalan konsisten.
- [ ] Memverifikasi perhitungan statistik di `ReportService` (`reports` & `standings`).
- [ ] Memelihara dokumentasi di `docs/api/openapi-overview.md` dan test di `tests/`.

## 14. Git Branch Assignment & Workflow

Lihat panduan lengkap Git di [`docs/GIT_WORKFLOW.md`](file:///C:/Turnamen.in/docs/GIT_WORKFLOW.md).

### 1. Nama Branch Resmi
`feature/anisa-api-report`

### 2. Tanggung Jawab pada Branch Ini
Mengembangkan dan memelihara Flask application factory (`backend/app.py`), route handler dan validator `/api/v1` (`backend/api/`), modul laporan dan statistik (`backend/modules/reports/`), modul pengumuman (`backend/modules/announcements/`), dokumentasi REST API (`docs/api/`), serta suite pengujian integrasi (`tests/`).

### 3. Instruksi Membuat atau Berpindah ke Branch
- **Membuat branch pertama kali (jika belum ada di lokal maupun remote):**
  ```powershell
  git fetch origin
  git switch main
  git pull --ff-only origin main
  git switch -c feature/anisa-api-report
  git push -u origin feature/anisa-api-report
  ```
- **Jika branch sudah ada di remote (`origin`):**
  ```powershell
  git fetch origin
  git switch feature/anisa-api-report
  git pull --ff-only
  ```
- **Jika branch sudah ada di komputer lokal:**
  ```powershell
  git switch feature/anisa-api-report
  git pull --ff-only
  ```

### 4. Perintah Git untuk Menyimpan Pekerjaan
Pastikan seluruh unit test dan integration test lulus sebelum melakukan commit:
```powershell
pytest -v
python run.py --check
git status
git add backend/app.py backend/api/ backend/modules/announcements/ backend/modules/reports/ docs/api/ tests/
git commit -m "feat(api): implement v1 endpoints, reporting, and integration tests"
```

### 5. Instruksi Push ke Branch Milik Anisa
Jangan melakukan push langsung ke `main` dan jangan menggunakan `--force`:
```powershell
git push origin feature/anisa-api-report
```
*(Atau cukup `git push` jika upstream `-u` sudah diatur).*

### 6. Instruksi Membuat Pull Request ke `main`
1. Buka repository GitHub: `https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`.
2. Pilih branch `feature/anisa-api-report` lalu klik **`Compare & pull request`**.
3. Pastikan **base** adalah `main` dan **compare** adalah `feature/anisa-api-report`.
4. Tulis ringkasan perubahan endpoint API/laporan/test, daftar file yang diubah, dan hasil pengujian `pytest -v`.
5. Klik **`Create pull request`** dan tunggu review sebelum merge.
6. Untuk menyinkronkan branch dengan pembaruan terbaru dari `main`:
   ```powershell
   git fetch origin
   git switch feature/anisa-api-report
   git merge origin/main
   ```

### 7. Aturan Koordinasi Lintas Modul
- Apabila ada perubahan path endpoint, metode HTTP, atau format payload JSON pada `/api/v1/*`, koordinasikan terlebih dahulu dengan **Fikri** (`feature/fikri-eel`) dan **Ferlita** (`feature/ferlita-ui-ux`), serta perbarui `docs/contracts/api-contract.md`.
- Apabila route handler membutuhkan penyesuaian pada `TournamentService`, `TeamService`, atau `MatchService`, koordinasikan dengan **Adriel** (`feature/adriel-tournament-match`).
- Apabila route handler membutuhkan penyesuaian otorisasi atau query repository baru, koordinasikan dengan **Habil** (`feature/habil-database-auth`).

## 15. Agent Skills yang Wajib Dibaca Berdasarkan Addendum
Sebelum meminta bantuan AI Agent, pastikan agent membaca `AGENTS.md`, file tugas ini (`docs/tasks/anisa.md`), `docs/GIT_WORKFLOW.md`, dan memuat skill berikut dari `.agents/skills/`:
- **Wajib:**
  - `antislop` (`.agents/skills/antislop/SKILL.md`)
  - `antislop-code` (`.agents/skills/antislop-code/SKILL.md`)
  - `antislop-copywriting` (`.agents/skills/antislop-copywriting/SKILL.md`)
  - `turnamen-project-standards` (`.agents/skills/turnamen-project-standards/SKILL.md`)
  - `turnamen-flask-api` (`.agents/skills/turnamen-flask-api/SKILL.md`)
  - `turnamen-quality-gates` (`.agents/skills/turnamen-quality-gates/SKILL.md`)
- **Tambahan:**
  - `hexagonal-python` (`.agents/skills/hexagonal-python/SKILL.md`)
  - `tdd` (`.agents/skills/tdd/SKILL.md`)
  - `team-code-review` (`.agents/skills/team-code-review/SKILL.md`)
