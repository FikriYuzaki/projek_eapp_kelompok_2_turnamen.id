# Wave 6.11: Laporan Desktop UI Smoke Test (Custom Game Artwork Management)

- **Tanggal Pengujian:** 2026-11-28
- **Repository & Branch:** `C:\Turnamen.in` (`feature/fikri-ui-ux`, dipertahankan utuh tanpa commit/push/merge/checkout)
- **Kondisi Kredensial & Cloud:** `.env` tidak ada (`False`), tidak ada variabel environment `APP_MODE`/`SUPABASE_*` di sesi agen, tidak ada mutasi database/Storage/Auth Cloud, Public Signup tetap `DISABLED`.
- **Cakupan Aktual Pengujian UI:**
  - **Dijalankan Secara Nyata (`APP_MODE=mock`):** Server lokal Flask + Web UI (`run.py --api-only --mode mock --port 5051`) dibuka melalui browser Chromium nyata (Playwright MCP) dalam mode **read-only** sebagai simulasi `super_admin` (`1366x820` & `1024x768`).
  - **Tidak Dijalankan (`NOT TESTED`):** Sesi Desktop UI `APP_MODE=supabase` + jendela Python Eel native (karena tidak ada `.env` atau kredensial Supabase tersimpan secara lokal pada sesi agen), serta aksi mutasi upload/restore di UI (dilarang oleh batas read-only).

---

## 1. Pemeriksaan Awal & Kesiapan Launcher

| Pemeriksaan | Hasil Aktual | Status |
| :--- | :--- | :---: |
| **Branch & Working Tree** | Branch aktif `feature/fikri-ui-ux`; tidak ada checkout, reset, clean, commit, push, maupun merge. | **PASS** |
| **Keberadaan `.env` & Env Rahasia** | `.env` tidak ada (`False`); tidak ada `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_ANON_KEY`, maupun `SECRET_KEY` di environment proses. | **PASS** |
| **Smoke Check `mock` (`run.py --check`)** | Exit code `0`: `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`. | **PASS** |
| **Smoke Check `supabase` (`run.py --check --mode supabase`)** | Exit code `1` sesuai rancangan karena `.env`/env tidak tersedia (`"APP_MODE=supabase membutuhkan SUPABASE_URL serta SUPABASE_PUBLISHABLE_KEY ***REDACTED*** legacy SUPABASE_ANON_KEY) pada file .env."`). | **NOT TESTED** *(Mode Online UI)* |

---

## 2. Hasil Pemeriksaan Desktop Web UI (`APP_MODE=mock`, Read-Only)

| # | Item Pemeriksaan UI | Observasi Aktual di Browser Chromium | Status |
| :-: | :--- | :--- | :---: |
| **1** | **Pembukaan Halaman Manajemen Game** | Role dialihkan ke `Super Admin` (`superadmin (super_admin)`), klik menu sidebar `Manajemen Game` menampilkan judul `Manajemen Game & Poster Arena`. | **PASS** |
| **2** | **Daftar Game Tampil Benar** | Tepat `3` kartu game tampil: `Mobile Legends: Bang Bang` (`mobile-legends`), `VALORANT` (`valorant`), dan `EA Sports FC 25` (`ea-sports-fc`), masing-masing ber-badge `Artwork Resmi`. | **PASS** |
| **3** | **Poster Resmi Tampil & Tidak Pecah** | Seluruh `3` gambar poster memuat sempurna (`complete: true`): MLBB `600x315`, VALORANT `1920x1080`, EA Sports FC 25 `616x353`; `0` gambar pecah (`naturalWidth > 0`). | **PASS** |
| **4** | **Informasi Format & Batas Ukuran** | Teks deskripsi halaman tampil jelas: `"Format didukung: JPEG, PNG, atau WebP maksimal 5 MB."` serta metadata sumber, dimensi (`16:9 Siap`), dan format default per kartu. | **PASS** |
| **5** | **Tombol Pemilihan File** | Setiap kartu memiliki tombol `Ganti Poster` (`data-action="trigger-game-artwork-picker"`) yang terhubung ke `<input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp">` dan `Simpan Poster` (`disabled` saat belum ada draft). | **PASS** |
| **6** | **Preview Gambar Lokal (Tanpa Upload)** | Memilih `smoke_preview_valid.png` (`640x360`, `1 KB`, `image/png`) memunculkan box `"Preview Poster Baru (Belum Disimpan)"` dengan `<img>` `data:image/png;base64,...` (`640x360`, `complete: true`), mengaktifkan `Simpan Poster` (tidak diklik), dan tombol `Batalkan Preview` mengembalikan kondisi awal bersih. | **PASS** |
| **7** | **Penolakan File Tidak Valid di UI** | Memilih `smoke_preview_fake_svg.png` (SVG tersamar `.png`) memicu banner error `.notice-banner-danger`: `"Format SVG, HTML, atau executable tidak diperbolehkan. Gunakan JPEG, PNG, atau WebP."`, tanpa preview dan `Simpan Poster` tetap `disabled`. | **PASS** |
| **8** | **Responsivitas Layout (`1366x820` & `1024x768`)** | Pada `1366x820`: grid 2 kolom rapi (`scrollWidth = 1366 <= 1366`, kartu lebar `522px`). Pada `1024x768`: grid otomatis menumpuk 1 kolom (`scrollWidth = 1009 <= 1024`, kartu lebar `962px`), `hasHorizontalOverflow: false`. | **PASS** |
| **9** | **Navigasi Lintas Halaman & Loading State** | Navigasi ke `dashboard` (`3` img), `tournament-list` (`2` img), `tournament-detail` (`2` img), `team-management` (`8` img), dan kembali ke `game-management` (`3` img): seluruh `<img>` termuat (`brokenImgsCount: 0`), `hasSkeletonLeftover: false`, `hasHorizontalOverflow: false`. | **PASS** |
| **10** | **Pemeriksaan Console JavaScript** | **0 runtime error JavaScript** dan **0 warning**; tercatat `1` error resource `404 (NOT FOUND)` untuk `http://127.0.0.1:5051/eel.js:1`, yang merupakan perilaku wajar saat menjalankan server dengan `--api-only` tanpa runtime Python Eel desktop. | **PASS (Dengan Catatan `--api-only`)** |
| **11** | **Indikator Upload Aktif (`.artwork-upload-status`)** | Tidak muncul saat idle (sesuai rancangan di [app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js#L3836-L3844)); tidak dipicu karena batas pengujian read-only melarang klik `Simpan Poster`. | **NOT TESTED** |
| **12** | **Tombol Restore (`Kembalikan Artwork Resmi`)** | Secara desain hanya dirender ketika `isCustom === true` ([app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js#L3870-L3880)). Karena seluruh 3 game berstatus `Artwork Resmi` (`0` override aktif), tombol tidak tampil dan tidak diuji kliknya pada sesi read-only ini. | **NOT TESTED** |
| **13** | **Login Live `super_admin` (`APP_MODE=supabase`) & Jendela Python Eel Native** | Tidak dijalankan karena tidak ada `.env`/kredensial Supabase tersimpan secara lokal di sesi agen (dan runtime shell agen tidak menampilkan jendela GUI desktop pengguna). | **NOT TESTED** |
| **14** | **Penutupan Aplikasi & Keamanan Akhir** | Browser Playwright ditutup (`browser_close`), proses server `run.py --api-only --port 5051` dihentikan bersih, `.env` tetap tidak ada (`False`), dan tidak ada mutasi Cloud. | **PASS** |

---

## 3. Bukti Screenshot & Temuan Tambahan

Screenshot hasil pengujian disimpan di direktori scratch percakapan (di luar repository Git agar working tree tetap bersih):
- Dashboard Super Admin (`1366x820`): [w611_dashboard_super_admin.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_dashboard_super_admin.png)
- Halaman Manajemen Game (`1366x820`): [w611_game_management_desktop.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_game_management_desktop.png)
- Preview Poster Baru Lokal (`1366x820`, tanpa upload): [w611_game_management_preview.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_game_management_preview.png)
- Tampilan Responsif Manajemen Game (`1024x768`): [w611_game_management_1024.png](file:///C:/Users/fikri/.gemini/antigravity-cli/brain/274303d8-550f-4c58-8111-10915bd021a5/scratch/w611_game_management_1024.png)

**Catatan observasi kecil (non-blocking):**
1. Dalam mode `--api-only`, `<script src="/eel.js">` pada `desktop/web/index.html` menghasilkan `404` di konsol browser karena endpoint `/eel.js` hanya disediakan oleh Python Eel saat `run.py` dijalankan tanpa `--api-only`. `eel-bridge.js` tetap aman dan aplikasi berjalan penuh lewat Flask REST API.
2. Evaluasi DOM mencatat `#topbar-title` kosong (`topbarTitle: ""`) karena judul halaman atas memakai elemen heading terpisah (`<h1>` di banner `Manajemen Game` / `Dashboard Administrasi Sistem`), bukan ID `#topbar-title`.

---

## 4. Ringkasan Item `NOT TESTED` & Rekomendasi Langkah Berikutnya

### Item yang Belum Diuji Secara Visual pada Sesi Ini (`NOT TESTED`)
1. Pembukaan jendela **Python Eel native** (`run.py` tanpa `--api-only`) dan login **live `super_admin`** dalam `APP_MODE=supabase` terhadap Supabase Cloud.
2. Tampilan visual live **indikator progress bar upload** (`.artwork-upload-status`) saat proses unggah nyata berlangsung.
3. Tampilan visual live tombol **Kembalikan Artwork Resmi** & modal konfirmasinya ketika suatu game berstatus `Poster Kustom` (sebelumnya sudah teruji via Node VM di `test_wave6_11_custom_game_artwork.py`).

### Rekomendasi Langkah Berikutnya
Bila Anda ingin memverifikasi jendela Python Eel native secara **read-only** dengan kredensial Supabase sementara (tanpa membuat `.env` dan tanpa `service_role`), jalankan di PowerShell lokal Anda (`C:\Turnamen.in`):

```powershell
$env:APP_MODE = "supabase"
$env:SECRET_KEY = "<string-acak-minimal-32-karakter>"
$env:SUPABASE_URL = "https://cfdsgxciodfkamskafwe.supabase.co"
$env:SUPABASE_PUBLISHABLE_KEY = "<salin-sb_publishable_...-dari-Dashboard>"
.\.venv\Scripts\python.exe run.py
```

Setelah login sebagai `super_admin` dan memeriksa halaman **Manajemen Game** (termasuk preview lokal tanpa menekan `Simpan Poster`) lalu menutup jendela desktop, bersihkan environment sesi:

```powershell
Remove-Item Env:APP_MODE, Env:SECRET_KEY, Env:SUPABASE_URL, Env:SUPABASE_PUBLISHABLE_KEY -ErrorAction SilentlyContinue
```
