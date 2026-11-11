---
name: turnamen-python-eel
description: Panduan arsitektur Python Eel, application launcher, lifecycle manajemen proses Flask + Eel, JS-Python bridge, dan logging untuk Fikri.
---

# Turnamen.in — Python Eel & System Integration (`turnamen-python-eel`)

Skill ini ditujukan bagi **Fikri (System Integration & Python Eel Developer)** untuk mengelola aplikasi desktop, launcher terpadu, dan jembatan komunikasi antara frontend dan backend.

## 1. Scope
Mencakup entry point utama (`run.py`), pengelola proses aplikasi (`desktop/launcher/`), fungsi bridge Python Eel (`desktop/bridge/`), konfigurasi terpusat (`backend/core/config.py` & `logging_config.py`), serta core JavaScript client (`desktop/web/assets/js/core/`).

## 2. Responsibilities
- Menyediakan satu launcher (`run.py`) yang menjalankan server lokal Flask REST API dan jendela desktop Python Eel secara terkoordinasi, serta menghentikan keduanya dengan bersih saat aplikasi ditutup (*graceful shutdown*).
- Menyediakan bridge Python-JavaScript (`@eel.expose`) hanya untuk informasi runtime aplikasi, pemeriksaan kesehatan lokal, dan penerusan request ke Flask REST API.
- Mengelola konfigurasi environment (`.env`), logging terstruktur tanpa membocorkan token/secret, serta indikator mode aplikasi (`mock` vs `supabase`).
- Membantu integrasi antarmodul dari Ferlita, Habil, Adriel, dan Anisa.

## 3. Architecture Rules
- **Catatan Keamanan Python Eel:** Karena library Python Eel sudah tidak aktif dipelihara di upstream, wajib mengikat server Eel dan Flask hanya ke `127.0.0.1` (`localhost`), mem-pin versi paket di `requirements.txt`, dan membatasi fungsi yang diekspos dengan `@eel.expose`.
- **Hindari Duplikasi Business Logic:** Fungsi di `desktop/bridge/` tidak boleh berisi query database langsung atau perhitungan bracket. Seluruh operasi bisnis harus diteruskan ke Flask REST API atau Application Service resmi.
- **Fallback Mode Headless/API-Only:** Launcher wajib mendukung argumen CLI seperti `--api-only` atau `--check` agar anggota tim dan pengujian otomatis dapat memverifikasi sistem meskipun sedang berjalan di terminal tanpa GUI browser.

## 4. Allowed Directories
- `run.py`
- `desktop/launcher/`
- `desktop/bridge/`
- `desktop/web/assets/js/core/`
- `backend/core/` (koordinasi bersama Anisa dan Habil)

## 5. Prohibited Changes
- Dilarang mengubah tampilan visual atau palet warna di `desktop/web/assets/css/` tanpa persetujuan Ferlita.
- Dilarang mengubah algoritma bracket di `backend/modules/matches/` milik Adriel atau skema SQL di `supabase/` milik Habil tanpa koordinasi.

## 6. Required Dependencies
- `Eel==0.16.0`, `bottle==0.12.25`, `gevent==24.2.1`, `Flask==3.0.3`, `requests==2.32.3`, `python-dotenv==1.0.1`.

## 7. Development Workflow
1. Pastikan konfigurasi `.env` (atau default `.env.example`) terbaca melalui `backend/core/config.py`.
2. Uji kesiapan sistem menggunakan `python run.py --check`.
3. Uji mode API lokal menggunakan `python run.py --api-only`.
4. Uji peluncuran penuh desktop + API menggunakan `python run.py`.

## 8. Testing Requirements
- Uji pemuatan konfigurasi dan default `APP_MODE=mock`.
- Uji fungsi bridge dan koneksi ke endpoint `/api/v1/health`.
- Pastikan log tidak pernah mencetak nilai `SECRET_KEY` atau `SUPABASE_ANON_KEY`.

## 9. Acceptance Criteria
- `python run.py` berhasil menyalakan Flask API di background thread/process, memverifikasi `/api/v1/health`, dan membuka jendela desktop Eel (atau menampilkan instruksi URL lokal jika Chrome/Edge tidak ditemukan).
- Ketika jendela ditutup atau menerima sinyal `SIGINT`/`SIGTERM`, proses server lokal berhenti tanpa menyisakan *zombie process*.

## 10. Integration Contracts
- Menyediakan objek global `window.TurnamenAPI` dan `window.TurnamenBridge` bagi kode frontend Ferlita sesuai `docs/contracts/frontend-contract.md`.
- Memanggil endpoint Flask REST API sesuai `docs/contracts/api-contract.md`.
