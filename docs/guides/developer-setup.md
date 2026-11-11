# Panduan Setup Pengembang (Developer Setup Guide) — Turnamen.in

Panduan singkat ini membantu kelima anggota kelompok menyiapkan lingkungan pengembangan lokal pada **Windows 10/11**.

---

## 1. Prasyarat Sistem
- **OS:** Windows 10 atau Windows 11 (64-bit)
- **Python:** Python 3.10, 3.11, atau 3.12 (pastikan `python` dan `pip` terdaftar di `PATH`)
- **Browser:** Google Chrome atau Microsoft Edge (digunakan oleh Python Eel untuk merender jendela aplikasi desktop)
- **Git:** Git CLI atau GitHub Desktop

---

## 2. Langkah Instalasi Awal

1. **Buka PowerShell di direktori proyek `C:\Turnamen.in`:**
   ```powershell
   cd C:\Turnamen.in
   ```
2. **Buat dan aktifkan Virtual Environment (`.venv`):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. **Pasang seluruh dependensi yang telah dipin:**
   ```powershell
   pip install -r requirements.txt
   ```
4. **Siapkan file konfigurasi lokal `.env`:**
   ```powershell
   Copy-Item .env.example .env
   ```
   Secara default `.env.example` sudah mengatur `APP_MODE=mock` sehingga aplikasi dapat langsung dijalankan tanpa kredensial Supabase.

---

## 3. Menjalankan Aplikasi & Pengujian

- **Memeriksa kesiapan konfigurasi dan modul (Smoke Check):**
  ```powershell
  python run.py --check
  ```
- **Menjalankan aplikasi lengkap (Flask REST API + Desktop Python Eel):**
  ```powershell
  python run.py
  ```
- **Menjalankan hanya server Flask REST API (tanpa membuka jendela Eel):**
  ```powershell
  python run.py --api-only
  ```
- **Menjalankan seluruh unit test dan integration test:**
  ```powershell
  pytest -v
  ```
