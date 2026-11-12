# Instruksi Tugas Mandiri: FIKRI (System Integration & Python Eel Developer)

---

## 1. Identitas dan Tanggung Jawab Anggota
- **Nama Anggota:** Fikri
- **Peran:** System Integration & Python Eel Developer
- **Branch Resmi:** `feature/fikri-eel`
- **Tanggung Jawab Utama:**
  - Membangun struktur utama aplikasi desktop dan *single launcher* (`run.py`).
  - Mengatur Python Eel, lifecycle proses Flask + Eel, serta *graceful shutdown*.
  - Menghubungkan frontend dengan backend melalui API client (`api-client.js`) dan Python Eel bridge (`desktop/bridge/`).
  - Mengelola konfigurasi aplikasi (`.env`), logging terstruktur, dan debugging lintas modul.
  - Mengintegrasikan modul dari Ferlita, Habil, Adriel, dan Anisa sesuai kontrak bersama.

## 2. Tujuan Pekerjaan
Menyediakan fondasi desktop dan integrasi sistem yang stabil pada Windows 10/11, di mana satu perintah `python run.py` dapat menyalakan Flask REST API lokal dan jendela desktop Python Eel secara aman di `127.0.0.1`, serta memastikan komunikasi frontend-backend berjalan mulus baik dalam `APP_MODE=mock` maupun `APP_MODE=supabase`.

## 3. Daftar Tugas Terperinci
1. Mengelola konfigurasi aplikasi terpusat di `backend/core/config.py` dan sanitasi log di `backend/core/logging_config.py`.
2. Mengembangkan orchestrator aplikasi di `desktop/launcher/app_launcher.py` dan entry point `run.py` yang mendukung mode:
   - Default (`python run.py`): Menjalankan Flask API di background thread + membuka jendela Python Eel.
   - API Only (`python run.py --api-only`): Menjalankan server Flask API + melayani static UI di `http://127.0.0.1:5000`.
   - Smoke Check (`python run.py --check`): Memeriksa konfigurasi, repositori, dan kesehatan aplikasi lalu keluar dengan kode `0`.
3. Mengembangkan fungsi jembatan Python-JavaScript di `desktop/bridge/eel_bridge.py` tanpa menduplikasi business logic.
4. Mengembangkan modul JavaScript inti di `desktop/web/assets/js/core/` (`config.js`, `eel-bridge.js`, `api-client.js`).

## 4. Folder yang Menjadi Tanggung Jawab
- `run.py`
- `desktop/launcher/`
- `desktop/bridge/`
- `desktop/web/assets/js/core/`
- `backend/core/` (koordinasi bersama Anisa & Habil)

## 5. File yang Harus Dibuat / Diubah
- `run.py`
- `backend/core/config.py`
- `backend/core/logging_config.py`
- `desktop/launcher/app_launcher.py`
- `desktop/bridge/eel_bridge.py`
- `desktop/web/assets/js/core/config.js`
- `desktop/web/assets/js/core/eel-bridge.js`
- `desktop/web/assets/js/core/api-client.js`

## 6. Batas File yang Tidak Boleh Diubah Tanpa Koordinasi
- `desktop/web/pages/*` dan `desktop/web/assets/css/*` (Milik **Ferlita**).
- `supabase/*`, `backend/modules/auth/*`, dan `backend/repositories/*` (Milik **Habil**).
- `backend/modules/tournaments/*`, `backend/modules/teams/*`, dan `backend/modules/matches/*` (Milik **Adriel**).
- `backend/api/routes/*`, `backend/modules/reports/*`, dan `backend/modules/announcements/*` (Milik **Anisa**).

## 7. Dependensi Modul
- Menggunakan factory Flask `create_app()` dari `backend/app.py` (Anisa).
- Menyediakan `window.TurnamenAPI` dan `window.TurnamenBridge` untuk komponen UI (Ferlita).

## 8. Kontrak Input / Output
- **Input Konfigurasi:** Variabel environment dari `.env` (atau nilai default aman dari `AppConfig` jika `.env` belum dibuat).
- **Output Bridge & API Client:** Objek response terstandarisasi `{ success: bool, message: str, data: any, error: dict | null }` sesuai [`docs/contracts/frontend-contract.md`](file:///C:/Turnamen.in/docs/contracts/frontend-contract.md).

## 9. Mock Data yang Tersedia
Saat `APP_MODE=mock` (default), launcher dan API client otomatis terhubung ke `MockDataStoreRepository` yang berisi 5 akun role, 3 game, 2 turnamen, 8 tim, dan bracket 8 tim.

## 10. Cara Menjalankan Modul
```powershell
# 1. Pemeriksaan kesehatan konfigurasi & integrasi cepat
python run.py --check

# 2. Menjalankan server API + Web UI di localhost:5000
python run.py --api-only

# 3. Menjalankan aplikasi desktop penuh (Flask + Python Eel Window)
python run.py
```

## 11. Skenario Pengujian
1. **Test Konfigurasi & Default Mock Mode:** Pastikan tanpa file `.env` sekalipun, aplikasi otomatis berjalan dengan `APP_MODE=mock` dan `API_HOST=127.0.0.1`.
2. **Test Launcher Check:** Jalankan `python run.py --check` dan pastikan status seluruh komponen bernilai `OK`.
3. **Test API Client & Bridge:** Pastikan fungsi bridge `get_runtime_info()` dan `check_api_health()` mengembalikan status `healthy` dan `is_simulation: true` pada mode mock.
4. **Test Keamanan Log:** Pastikan `AppConfig.to_safe_dict()` menyensor nilai `SECRET_KEY` dan `SUPABASE_ANON_KEY`.

## 12. Acceptance Criteria
- `run.py` dapat menyalakan dan mematikan Flask API serta Python Eel dengan bersih.
- Server lokal hanya terikat ke `127.0.0.1` (tidak terekspos ke jaringan luar).
- Keterbatasan pemeliharaan Python Eel terdokumentasi dan versinya terpin di `requirements.txt`.
- Tidak ada duplikasi business logic di dalam folder `desktop/bridge/`.

## 13. Checklist Pekerjaan
- [ ] Memverifikasi `backend/core/config.py` dan `logging_config.py`.
- [ ] Memastikan `run.py --check`, `run.py --api-only`, dan `run.py` berjalan lancar.
- [ ] Memastikan `api-client.js` mencakup seluruh endpoint kontrak `/api/v1`.
- [ ] Menjalankan `pytest` untuk memverifikasi integrasi antarmodul.

## 14. Git Branch Assignment & Workflow

Lihat panduan lengkap Git di [`docs/GIT_WORKFLOW.md`](file:///C:/Turnamen.in/docs/GIT_WORKFLOW.md).

### 1. Nama Branch Resmi
`feature/fikri-eel`

### 2. Tanggung Jawab pada Branch Ini
Mengembangkan dan memelihara application launcher (`run.py`, `desktop/launcher/`), Python Eel bridge (`desktop/bridge/`), JavaScript core client (`desktop/web/assets/js/core/`), serta konfigurasi dan logging aplikasi (`backend/core/`).

### 3. Instruksi Membuat atau Berpindah ke Branch
- **Membuat branch pertama kali (jika belum ada di lokal maupun remote):**
  ```powershell
  git fetch origin
  git switch main
  git pull --ff-only origin main
  git switch -c feature/fikri-eel
  git push -u origin feature/fikri-eel
  ```
- **Jika branch sudah ada di remote (`origin`):**
  ```powershell
  git fetch origin
  git switch feature/fikri-eel
  git pull --ff-only
  ```
- **Jika branch sudah ada di komputer lokal:**
  ```powershell
  git switch feature/fikri-eel
  git pull --ff-only
  ```

### 4. Perintah Git untuk Menyimpan Pekerjaan
Pastikan seluruh pengujian dan smoke check lulus sebelum melakukan commit:
```powershell
pytest -v
python run.py --check
git status
git add run.py desktop/launcher/ desktop/bridge/ desktop/web/assets/js/core/ backend/core/
git commit -m "feat(desktop): integrate eel launcher, bridge, and api client"
```

### 5. Instruksi Push ke Branch Milik Fikri
Jangan melakukan push langsung ke `main` dan jangan menggunakan `--force`:
```powershell
git push origin feature/fikri-eel
```
*(Atau cukup `git push` jika upstream `-u` sudah diatur).*

### 6. Instruksi Membuat Pull Request ke `main`
1. Buka repository GitHub: `https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`.
2. Pilih branch `feature/fikri-eel` lalu klik **`Compare & pull request`**.
3. Pastikan **base** adalah `main` dan **compare** adalah `feature/fikri-eel`.
4. Tulis ringkasan perubahan integrasi/Eel, daftar file yang diubah, serta hasil `pytest -v` dan `python run.py --check`.
5. Klik **`Create pull request`** dan tunggu review sebelum merge.
6. Untuk menyinkronkan branch dengan pembaruan terbaru dari `main`:
   ```powershell
   git fetch origin
   git switch feature/fikri-eel
   git merge origin/main
   ```

### 7. Aturan Koordinasi Lintas Modul
- Apabila perubahan pada `api-client.js` atau `eel-bridge.js` mengubah cara pemanggilan dari halaman UI, koordinasikan dengan **Ferlita** (`feature/ferlita-ui-ux`) dan perbarui `docs/contracts/frontend-contract.md`.
- Apabila penyesuaian konfigurasi di `backend/core/` berkaitan dengan inisialisasi Flask atau Supabase, koordinasikan dengan **Anisa** (`feature/anisa-api-report`) dan **Habil** (`feature/habil-database-auth`).

## 15. Agent Skills yang Wajib Dibaca Berdasarkan Addendum
Sebelum meminta bantuan AI Agent, pastikan agent membaca `AGENTS.md`, file tugas ini (`docs/tasks/fikri.md`), `docs/GIT_WORKFLOW.md`, dan memuat skill berikut dari `.agents/skills/`:
- **Wajib:**
  - `antislop` (`.agents/skills/antislop/SKILL.md`)
  - `antislop-code` (`.agents/skills/antislop-code/SKILL.md`)
  - `turnamen-project-standards` (`.agents/skills/turnamen-project-standards/SKILL.md`)
  - `turnamen-python-eel` (`.agents/skills/turnamen-python-eel/SKILL.md`)
  - `turnamen-quality-gates` (`.agents/skills/turnamen-quality-gates/SKILL.md`)
- **Tambahan:**
  - `hexagonal-python` (`.agents/skills/hexagonal-python/SKILL.md`)
  - `tdd` (`.agents/skills/tdd/SKILL.md`)
  - `team-code-review` (`.agents/skills/team-code-review/SKILL.md`)
