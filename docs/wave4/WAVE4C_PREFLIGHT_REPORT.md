# TURNAMEN.IN - WAVE 4C: ENVIRONMENT PREFLIGHT REPORT

**Tanggal Pemeriksaan:** 2026-11-26  
**Branch Aktif:** `feature/fikri-ui-ux`  
**Status Wave 4C:** **BLOCKED (Container Runtime Tidak Tersedia)**  
**Status Supabase Cloud:** **BELUM DISENTUH**

---

## 1. Keputusan Preflight

Tahap **Wave 4C (Real Supabase Auth / GoTrue & PostgREST HTTP Integration Validation)** **dihentikan pada Tahap Preflight** sesuai aturan Wave 4C Bagian 2 dan Bagian 10.

**Alasan Blocker:**
- Tidak ditemukan container runtime yang terpasang maupun aktif (**Docker Desktop**, **Rancher Desktop**, maupun **Podman**) pada mesin lokal Windows ini.
- `supabase start` pada Supabase CLI `2.104.0` bergantung pada container daemon yang kompatibel dengan Docker API untuk menjalankan container PostgreSQL, GoTrue (Auth), PostgREST, dan Kong/API Gateway.
- Sesuai ketentuan Wave 4C, agen tidak boleh menginstal Docker/Podman/Rancher Desktop secara otomatis, tidak boleh mengubah layanan Windows/Hyper-V/WSL, tidak boleh memakai native runtime eksperimental sebagai jalan pintas, dan tidak boleh mengganti pengujian GoTrue/PostgREST nyata dengan mock atau simulasi PostgreSQL.

Oleh karena itu, direktori `%TEMP%\turnamen_wave4c`, file `tests/integration/test_wave4c_supabase_http_integration.py`, serta layanan local stack **tidak dibuat dan tidak dijalankan**.

---

## 2. Hasil Pemeriksaan Preflight Terobservasi

### A. Supabase CLI
- `supabase --version`: **`2.104.0`** (tersedia dan berfungsi).
- `supabase --help` & `supabase start --help`: terkonfirmasi bahwa `supabase start` memulai container lokal dengan opsi `--exclude` untuk layanan (`analytics, db, edge-runtime, functions, imgproxy, inbucket, kong, meta, realtime, rest, storage, studio, vector`).

### B. Container Runtime & Layanan Windows
- `docker --version` / `docker info`: **Tidak ditemukan** (`CommandNotFoundException`); path standar `C:\Program Files\Docker\Docker\resources\bin\docker.exe` -> `False`.
- `podman --version` / `podman info`: **Tidak ditemukan** (`CommandNotFoundException`); path standar `C:\Program Files\RedHat\Podman\podman.exe` -> `False`.
- Rancher Desktop: path standar `C:\Program Files\Rancher Desktop\resources\resources\win32\bin\docker.exe` dan `%LOCALAPPDATA%\Programs\Rancher Desktop\resources\resources\win32\bin\docker.exe` -> `False`.
- `Get-Service` (layanan container/virtualisasi):
  - `HNS` (Host Network Service): `Running` (`Manual`)
  - `vmcompute` (Hyper-V Host Compute Service): `Running` (`Manual`)
  - `WSLService` (WSL Service): `Running` (`Manual`)
  - Tidak ada service daemon Docker, Podman, atau Rancher Desktop.
- `wsl --list --verbose`: Tidak ada distribusi Linux WSL yang terpasang.

### C. Ketersediaan Port, Disk, dan RAM
- **Port Lokal (`54321`–`54329`):** Seluruhnya kosong / bebas (`Get-NetTCPConnection` tidak mengembalikan listener aktif).
- **Ruang Disk (`C:`):** Terpakai `440.12 GB`, **tersisa `7.23 GB`**.
- **Memori (RAM):** Total `7.32 GB`, **tersisa `0.88 GB`** pada saat pemeriksaan.

**Catatan Kapasitas Tambahan:**
Selain tidak adanya container runtime, sisa ruang disk **`7.23 GB`** dan total RAM **`7.32 GB`** (free `0.88 GB`) juga berisiko tidak mencukupi untuk menarik image container Supabase stack (`postgres`, `gotrue`, `postgrest`, `kong`, `mailpit`/`inbucket`) beserta overhead VM/WSL2 Docker Desktop atau Podman machine di drive `C:`.

---

## 3. Baseline yang Sudah Terverifikasi Sebelum Wave 4C

Keputusan `BLOCKED` pada Wave 4C hanya berlaku untuk validasi **GoTrue + PostgREST HTTP lokal** dan tidak membatalkan hasil yang sudah lulus sebelumnya:
- **Wave 3.6:** `250 passed` (unit, API integration, dan mock/simulated RLS).
- **Wave 4A:** Audit read-only Cloud selesai ([README.md](./README.md)).
- **Wave 4B:** `257 passed` pada **PostgreSQL 18.6** terisolasi ([WAVE4B_REPORT.md](./WAVE4B_REPORT.md)), termasuk migrasi `0001`–`0005` dan perbaikan **SUPA-001**.
- **Wave 4B.1:** `257 passed` pada **PostgreSQL 17.11** terisolasi ([WAVE4B1_PG17_COMPATIBILITY_REPORT.md](./WAVE4B1_PG17_COMPATIBILITY_REPORT.md)), membuktikan kompatibilitas SQL/trigger/RLS/RPC/konkurensi `0001`–`0005` terhadap versi engine PostgreSQL yang sama dengan Supabase Cloud.

---

## 4. Cakupan yang Masih Belum Teruji Akibat Blocker

Karena layanan lokal GoTrue dan PostgREST belum dapat dijalankan, pengujian nyata berikut **masih berstatus belum terverifikasi**:
1. HTTP signup, email confirmation (via mail catcher / endpoint verifikasi), sign in, sign out, dan perilaku invalidasi token pada GoTrue sesungguhnya.
2. Penerbitan JWT asli GoTrue dan validasinya oleh PostgREST + Kong API Gateway.
3. Eksekusi HTTP langsung terhadap policy RLS untuk seluruh 12 tabel dan 7 RPC (`get_public_profile_summary`, `transition_tournament_status`, `register_team_atomic`, `replace_tournament_matches`, `submit_match_result_atomic`, `link_profile_auth_user`, `assign_user_role`) dengan token `anon`, `authenticated`, dan `service_role`.
4. Smoke test end-to-end `SupabaseDataStoreRepository` dan Flask/Eel terhadap HTTP endpoint Supabase nyata.

---

## 5. Opsi Tindak Lanjut Aman (Menunggu Keputusan Pengguna)

1. **Opsi A - Menjalankan Wave 4C di Mesin/Runner dengan Docker Aktif & Kapasitas Memadai:**
   Jalankan branch `feature/fikri-ui-ux` pada mesin atau CI runner (misalnya GitHub Actions Ubuntu dengan Docker pre-installed) yang memiliki ruang disk >= 20 GB dan RAM memadai untuk `supabase start -x studio,storage,realtime,edge-runtime,imgproxy,vector,analytics,logflare`.
2. **Opsi B - Menggunakan Staging Project Supabase Terpisah (Non-Production) dengan Persetujuan Eksplisit:**
   Apabila pemasangan Docker lokal tidak memungkinkan karena keterbatasan disk (`7.23 GB`) dan RAM (`7.32 GB`), pengguna dapat membuat project staging/dev terpisah (bukan production `cfdsgxciodfkamskafwe`) untuk menguji HTTP GoTrue + PostgREST secara nyata setelah memberikan persetujuan terpisah.
3. **Opsi C - Mengosongkan Ruang Disk & Memasang Docker Desktop / Podman Secara Manual oleh Pengguna:**
   Setelah pengguna membebaskan ruang disk dan memasang serta menyalakan container runtime secara manual, Wave 4C lokal dapat dilanjutkan kembali dari Tahap 3.

---

## 6. Keselamatan Repository & Cloud

- Branch tetap di `feature/fikri-ui-ux`.
- Tidak ada file migration (`0001`–`0005`), kode aplikasi, konfigurasi, maupun package yang diubah pada Wave 4C.
- Tidak ada instalasi software, perubahan Windows service, commit, push, merge, maupun akses/perubahan ke Supabase Cloud.
