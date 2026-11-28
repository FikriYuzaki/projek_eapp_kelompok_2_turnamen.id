# P0 Repository Hygiene Preparation & Integration Strategy

- **Tanggal:** 28 November 2026
- **Repository:** `C:\Turnamen.in`
- **Branch Aktif:** `feature/fikri-ui-ux` (`e01cb4e`, `6` commit di depan `main` `4bb57b1`, `0` commit di belakang `main`)
- **Status Eksekusi Git:** **PREPARED ONLY** (belum ada `git add`, `commit`, `push`, `merge`, `checkout`, `reset`, `clean`, maupun `stash`)

---

## 1. Audit `.gitignore` & Artefak `supabase/.temp/cli-latest`

### A. Temuan Direktori `supabase/`
Pemeriksaan seluruh isi folder `supabase/` menunjukkan struktur berikut:
- **File Migrasi (Penting & Wajib Dipertahankan):**
  - `supabase/migrations/0001_initial_schema.sql` (`20,057` bytes, sudah tracked)
  - `supabase/migrations/0002_security_hardening.sql` (`31,669` bytes, sudah tracked)
  - `supabase/migrations/0003_wave2_rls_compatibility.sql` (`15,464` bytes, untracked baru)
  - `supabase/migrations/0004_wave2_3_atomic_match_submission.sql` (`26,194` bytes, untracked baru)
  - `supabase/migrations/0005_supa001_auth_trigger_hardening.sql` (`21,504` bytes, untracked baru)
  - `supabase/migrations/0006_wave5_functional_rpc.sql` (`9,128` bytes, untracked baru)
  - `supabase/migrations/20261126232622_wave6_11_custom_game_artwork.sql` (`5,717` bytes, untracked baru)
- **Seed Data (Penting & Wajib Dipertahankan):**
  - `supabase/seed.sql` (`17,281` bytes, sudah tracked)
- **Artefak Lokal CLI:**
  - `supabase/.temp/cli-latest` (`6` bytes, isi teks: `v3.4.0`). File ini dibuat otomatis oleh Supabase CLI untuk menyimpan cache lokal versi CLI terbaru dan bukan konfigurasi proyek maupun migrasi.

### B. Perubahan `.gitignore` yang Diterapkan
Aturan spesifik telah ditambahkan pada [`.gitignore`](file:///C:/Turnamen.in/.gitignore):
```gitignore
# Supabase CLI local cache/temporary metadata (keep migrations and seed tracked)
supabase/.temp/
```
Aturan ini hanya mengecualikan direktori `supabase/.temp/` agar tidak mengabaikan `supabase/migrations/*.sql`, `supabase/seed.sql`, maupun konfigurasi `supabase/` lain apabila ditambahkan di masa depan. File `supabase/.temp/cli-latest` tetap berada di disk lokal tanpa dihapus.

---

## 2. Audit Lengkap Seluruh 28 File Untracked di `.agent/` (+ 5 `.pyc`)

Folder `.agent/` berbeda dengan folder resmi tim `.agents/skills/` yang dilock di [skills-lock.json](file:///C:/Turnamen.in/skills-lock.json) dan dirujuk di [AGENTS.md](file:///C:/Turnamen.in/AGENTS.md). Di disk, `.agent/` berisi `33` file (`28` terlihat oleh Git sebesar **`502,413` bytes / `490.6 KB`**, ditambah `5` file bytecode `.pyc` di `__pycache__/` yang sudah otomatis di-ignore `.gitignore`).

**Catatan Status:** Belum ada file `.agent/` yang dihapus ataupun di-ignore hingga tim menentukan keputusannya.

### A. Klasifikasi Berdasarkan Fungsi

| Kategori Fungsi | Jumlah File | Total Ukuran | Rincian File | Status Lokal vs Tim |
| :--- | :---: | :---: | :--- | :--- |
| **1. Instruksi Agent / Skill** | `1` | `10,651 B` | `.agent/skills/ui-ux-pro-max/SKILL.md` | **Eksternal / opsional** (`AGENTS.md` secara eksplisit menegaskan keputusan `DESIGN.md` & Ferlita tetap di atas skill visual eksternal) |
| **2. Dataset CSV Referensi Desain Umum** | `11` | `275,492 B` | `charts.csv`, `colors.csv`, `icons.csv`, `landing.csv`, `products.csv`, `react-performance.csv`, `styles.csv`, `typography.csv`, `ui-reasoning.csv`, `ux-guidelines.csv`, `web-interface.csv` | **Referensi skill lokal** (data pencarian desain eksternal, bukan aset runtime Turnamen.in) |
| **3. Dataset CSV Framework/Stack Eksternal** | `13` | `156,951 B` | `data/stacks/{astro,flutter,html-tailwind,jetpack-compose,nextjs,nuxt-ui,nuxtjs,react-native,react,shadcn,svelte,swiftui,vue}.csv` | **Tidak relevan dengan stack proyek** (Turnamen.in memakai Vanilla JS/CSS + Python Eel + Flask, bukan React/Flutter/Vue/Svelte) |
| **4. Skrip Utilitas Pencarian Python** | `3` | `59,319 B` | `scripts/core.py`, `scripts/design_system.py`, `scripts/search.py` | **Tooling internal skill lokal** (tidak diimpor oleh `backend/`, `desktop/`, maupun `tests/`) |
| **5. Cache Bytecode Python** | `5` | *(auto-ignored)* | `scripts/__pycache__/*.pyc` (Python `3.12` & `3.14`) | **Murni cache lokal** (sudah ter-ignore oleh `__pycache__/` di `.gitignore`) |

### B. Referensi di Repository & Penilaian Kebutuhan Tim
- Tidak ada referensi kode di `backend/`, `desktop/`, `tests/`, `run.py`, `AGENTS.md`, maupun `skills-lock.json` yang bergantung pada `.agent/`.
- Satu-satunya kemunculan teks `.agent/` di repository hanya berupa catatan audit di `docs/wave4/README.md` (`L47`) dan `docs/finalization/FINAL_PROJECT_READINESS_AUDIT.md`.
- **Kesimpulan Evaluasi `.agent/`:** Seluruh `28` file merupakan paket skill eksternal (`ui-ux-pro-max`) yang dipasang terpisah dari `skills-lock.json` dan **tidak dibutuhkan oleh aplikasi saat runtime maupun oleh pipeline `pytest`**.
- **Opsi Keputusan untuk Tim:**
  - **Opsi A (Direkomendasikan):** Kecualikan `.agent/` melalui `.gitignore` (atau pindahkan keluar ke direktori skill global lokal) agar repository `main` tetap bersih dari `490.6 KB` CSV framework eksternal yang tidak dipakai.
  - **Opsi B:** Jika tim ingin membakukan penggunaan `ui-ux-pro-max` di repo bersama, pindahkan ke `.agents/skills/ui-ux-pro-max/`, daftarkan ke `skills-lock.json`, dan dokumentasikan di `AGENTS.md`.

---

## 3. Inventarisasi Kelompok Fitur, Migration, Test, Dokumentasi, & Konfigurasi

Baseline saat persiapan dimulai mencakup **`35` file tracked modified** (ditambah `.gitignore` pada tugas ini menjadi `36` tracked modified) dan **`77` file untracked** (sebelum mengabaikan `supabase/.temp/cli-latest` dan menambah laporan ini):

1. **Fitur & Logika Aplikasi:**
   - *Domain & Layanan Backend (`backend/modules/`):* `auth/{permissions.py,service.py}`, `tournaments/{service.py,artwork_validator.py [baru]}`, `teams/service.py`, `matches/{bracket_engine.py,service.py}`, `announcements/service.py`, `reports/service.py`.
   - *REST API & Infrastruktur Data:* `backend/api/routes/v1_routes.py`, `backend/infrastructure/supabase/client.py`, `backend/repositories/{interfaces/repository_protocol.py,mock/mock_repository.py,supabase/supabase_repository.py}`.
   - *Desktop Eel & Frontend:* `desktop/bridge/eel_bridge.py`, `desktop/launcher/app_launcher.py`, `desktop/web/index.html`, `desktop/web/assets/css/{components.css,layout.css,variables.css}`, `desktop/web/assets/images/games/ASSETS.md`, `desktop/web/assets/js/{components/ui-components.js,core/api-client.js,core/config.js,core/eel-bridge.js,pages/app-pages.js}`.
2. **Database Migrations (`5` file baru + `2` tracked lama):**
   - Baru (untracked): `supabase/migrations/0003_wave2_rls_compatibility.sql`, `0004_wave2_3_atomic_match_submission.sql`, `0005_supa001_auth_trigger_hardening.sql`, `0006_wave5_functional_rpc.sql`, `20261126232622_wave6_11_custom_game_artwork.sql`.
3. **Pengujian (`2` tracked modified + `20` untracked baru):**
   - Tracked modified: `tests/unit/test_auth_and_permissions.py`, `tests/unit/test_reports_service.py`.
   - Integration baru (`3`): `test_wave1_api_status_codes.py`, `test_wave2_api_access_and_visibility.py`, `test_wave4b_postgres_migrations_and_security.py`.
   - Unit baru (`17`): `test_password_recovery.py`, `test_supabase_publishable_key_compatibility.py`, `test_wave1_{auth,match,team,tournament}_rules.py`, `test_wave2_{1_supabase_rls_remediation,2_security_edge_cases,3_atomic_match_submission,repository_and_services}.py`, `test_wave3_6_interaction_hotfixes.py`, `test_wave3_frontend_role_integration.py`, `test_wave5_functional_gap_closure.py`, `test_wave6_{8_dashboard_performance,9_skeleton_loading,10_game_artwork,11_custom_game_artwork}.py`.
4. **Dokumentasi & Kontrak (`3` tracked modified + `23` untracked termasuk laporan ini):**
   - Kontrak: `docs/contracts/{api-contract.md,database-contract.md,module-contract.md}`.
   - Wave 4 Docs (`5`): `docs/wave4-supa001-auth-trigger-plan.md`, `docs/wave4/{README.md,WAVE4B1_PG17_COMPATIBILITY_REPORT.md,WAVE4B_REPORT.md,WAVE4C_PREFLIGHT_REPORT.md}`.
   - Finalization Reports (`18`): `docs/finalization/{APP_READINESS_REPORT,FINAL_PROJECT_READINESS_AUDIT,REPOSITORY_HYGIENE_PLAN,WAVE5_FUNCTIONAL_GAP_CLOSURE_REPORT,WAVE6_1_PUBLISHABLE_KEY_REPORT,WAVE6_2_CLOUD_DEPLOYMENT_RUNBOOK,WAVE6_3_BACKUP_EQUIVALENCE_REPORT,WAVE6_4_PRODUCTION_MIGRATION_IMPACT_REVIEW,WAVE6_5_PRODUCTION_DEPLOYMENT_REPORT,WAVE6_6_SUPER_ADMIN_LINKING_REPORT,WAVE6_8_DASHBOARD_PERFORMANCE_REPORT,WAVE6_9_SKELETON_LOADING_REPORT,WAVE6_10_GAME_ARTWORK_REPORT,WAVE6_11_CUSTOM_GAME_ARTWORK_REPORT,WAVE6_11_DESKTOP_UI_SMOKE_TEST,WAVE6_11_LAYOUT_OVERFLOW_FIX,WAVE6_11_NATIVE_SUPABASE_UI_VERIFICATION,WAVE6_ONLINE_READINESS_REPORT}.md` *(catatan: `16` laporan awal sebelum audit kesiapan & rencana hygiene ini, kini total `18` file di `docs/finalization/`)*.
5. **Konfigurasi, Dependencies, & Artefak Lokal:**
   - `.gitignore`, `.env.example`, `requirements.txt`, `run.py`, `backend/core/{config.py,logging_config.py}`, `supabase/.temp/cli-latest` (kini ter-ignore), `.agent/*` (`28` file + `5` `.pyc`).

---

## 4. Pemetaan Kepemilikan File Berdasarkan `AGENTS.md` & `docs/GIT_WORKFLOW.md`

| Anggota & Branch Resmi | Area Kepemilikan Resmi | File Terdampak di Working Tree |
| :--- | :--- | :--- |
| **Ferlita** (`feature/ferlita-ui-ux`) | `desktop/web/pages/`, `css/`, `images/`, `js/components/`, `js/pages/`, `DESIGN.md` | `desktop/web/assets/css/{components,layout,variables}.css`, `desktop/web/assets/images/games/ASSETS.md`, `desktop/web/assets/js/components/ui-components.js`, `desktop/web/assets/js/pages/app-pages.js` |
| **Fikri** (`feature/fikri-eel`) | `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py`, `backend/core/` | `run.py`, `backend/core/{config.py,logging_config.py}`, `desktop/bridge/eel_bridge.py`, `desktop/launcher/app_launcher.py`, `desktop/web/assets/js/core/{api-client,config,eel-bridge}.js` |
| **Habil** (`feature/habil-database-auth`) | `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/`, `docs/database-schema.md`, `docs/security.md` | `supabase/migrations/{0003..0006,20261126232622}*.sql`, `backend/modules/auth/{permissions,service}.py`, `backend/infrastructure/supabase/client.py`, `backend/repositories/{interfaces/repository_protocol,mock/mock_repository,supabase/supabase_repository}.py` |
| **Adriel** (`feature/adriel-tournament-match`) | `backend/modules/{tournaments,teams,matches}/`, `tests/unit/test_bracket_engine.py` | `backend/modules/tournaments/{service.py,artwork_validator.py}`, `backend/modules/teams/service.py`, `backend/modules/matches/{bracket_engine,service}.py` |
| **Anisa** (`feature/anisa-api-report`) | `backend/app.py`, `backend/api/`, `backend/modules/{reports,announcements}/`, `tests/`, `docs/api/` | `backend/api/routes/v1_routes.py`, `backend/modules/{announcements,reports}/service.py`, seluruh `22` file pada `tests/` |
| **Koordinasi Bersama (Shared Root & Kontrak)** | File integrasi lintas modul | `.gitignore`, `.env.example`, `requirements.txt`, `desktop/web/index.html`, `docs/contracts/{api,database,module}-contract.md`, `docs/wave4*`, `docs/finalization/*`, dan folder untracked `.agent/` |

**Catatan Kritis Governance Git:**
- Branch aktif `feature/fikri-ui-ux` (`6` commit ahead dari `main`) berada pada repository kerja yang merangkum integrasi lintas 5 anggota sekaligus, sementara di `origin` branch resmi anggota lain masing-masing tertinggal dari `main` (`feature/ferlita-ui-ux` behind `2`, `feature/habil-database-auth` behind `3`, `feature/anisa-api-report` behind `10`, `feature/adriel-tournament-match` behind `15`).
- Jangan melakukan `git push` atau `merge` sebelum mengecek apakah ada commit lokal/remote di salah satu branch anggota yang belum masuk ke `main` maupun ke `feature/fikri-ui-ux`.

---

## 5. Daftar Keputusan File: Dipertahankan vs Di-Ignore vs Ditinjau Bersama Tim

### A. Dipertahankan (Layak Masuk Commit & PR ke `main`)
1. Seluruh **35 file tracked modified** sebelumnya (`backend/`, `desktop/`, `docs/contracts/`, `.env.example`, `requirements.txt`, `run.py`, `tests/unit/test_*`) plus pembaruan **`.gitignore`**.
2. `backend/modules/tournaments/artwork_validator.py` (`1` file).
3. Seluruh **`5` file migrasi baru** di `supabase/migrations/` (`0003` s/d `0006` + `20261126232622_wave6_11_custom_game_artwork.sql`).
4. Seluruh **`20` file test baru** di `tests/unit/` (`17`) dan `tests/integration/` (`3`).
5. Seluruh **`23` dokumen laporan & catatan finalisasi/Wave 4** di `docs/wave4*` dan `docs/finalization/` (setelah melengkapi status akhir [WAVE6_11_NATIVE_SUPABASE_UI_VERIFICATION.md](file:///C:/Turnamen.in/docs/finalization/WAVE6_11_NATIVE_SUPABASE_UI_VERIFICATION.md)).

### B. Di-Ignore (Sudah Diterapkan Secara Aman)
1. `supabase/.temp/` (mengecualikan `supabase/.temp/cli-latest` dari Git status tanpa menyentuh `supabase/migrations/` maupun `supabase/seed.sql`).
2. `5` file `__pycache__/*.pyc` di bawah `.agent/` (sudah ter-ignore oleh aturan `__pycache__/` yang sudah ada di `.gitignore`).

### C. Ditinjau Bersama Tim Sebelum Staging / Commit
1. **Direktori `.agent/` (`28` file untracked, `490.6 KB`):** Tentukan bersama apakah dipilih **Opsi A** (tambahkan `.agent/` ke `.gitignore` atau pindahkan ke luar repo) atau **Opsi B** (pindahkan ke `.agents/skills/ui-ux-pro-max/` dan lock di `skills-lock.json`).
2. **File Bersama Lintas Modul & Ketidaksinkronan Minor:**
   - `requirements.txt` (`Eel==0.16.0` vs `.venv` aktual `eel==0.18.2`): putuskan apakah pin diperbarui atau diselaraskan.
   - `.env.example` & `backend/core/config.py` (`SUPABASE_STORAGE_BUCKET=tournament-assets` vs `GAME_ARTWORK_BUCKET="game-artwork"`).
   - `docs/contracts/{api,database,module}-contract.md` dan `desktop/web/index.html` (pastikan disetujui koordinator & pemilik modul terkait).
   - `docs/database-schema.md` (disarankan sinkronisasi P1 agar mencantumkan `match_submission_requests` dan `game_artwork_overrides`).
3. **Verifikasi Branch Remote Anggota Lain:** Konfirmasikan tidak ada pekerjaan terpisah yang tertinggal di `origin/feature/*` selain commit `d507085`.

---

## 6. Rekomendasi Strategi Staging & Integrasi PR *(Belum Dijalankan)*

### A. Rencana Pengelompokan Commit Logis (Referensi Staging Manual Setelah Keputusan Tim)

Setelah tim memutuskan nasib `.agent/` dan menyelesaikan verifikasi ulang Native Desktop UI, staging disarankan dipecah menjadi **6 commit atomik terstruktur** (bukan `git add .` massal):

1. **Commit 1 (`chore(repo): ignore supabase cli temp cache`):**
   - Path: `.gitignore` *(+ keputusan `.agent/` bila di-ignore)*
2. **Commit 2 (`feat(db,auth): apply waves 2-6 migrations, rls, rpc, and repository parity`):**
   - Path: `supabase/migrations/0003_*.sql`, `0004_*.sql`, `0005_*.sql`, `0006_*.sql`, `20261126232622_*.sql`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/`, `docs/contracts/database-contract.md`
3. **Commit 3 (`feat(domain): enhance tournament, team, match bracket, and artwork validation services`):**
   - Path: `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/`, `docs/contracts/module-contract.md`
4. **Commit 4 (`feat(api,reports): expand v1 endpoints, artwork api, announcements, and reports optimization`):**
   - Path: `backend/api/routes/v1_routes.py`, `backend/modules/announcements/`, `backend/modules/reports/`, `docs/contracts/api-contract.md`
5. **Commit 5 (`feat(desktop,ui): integrate eel concurrency, progressive skeleton, game artwork, and layout fix`):**
   - Path: `.env.example`, `requirements.txt`, `run.py`, `backend/core/`, `desktop/`
6. **Commit 6 (`test,docs: add wave 1-6.11 test suites and finalization reports`):**
   - Path: `tests/`, `docs/wave4/`, `docs/wave4-supa001-auth-trigger-plan.md`, `docs/finalization/`

### B. Rekomendasi Strategi Integrasi Pull Request ke `main`

- **Opsi 1 (Direkomendasikan): Consolidated Integration PR dari `feature/fikri-ui-ux` -> `main` dengan Review 5 Anggota**
  - **Alasan:** Seluruh perubahan backend, SQL, API, Eel, UI CSS/JS, dan `304` test telah teruji menyatu di working tree `feature/fikri-ui-ux`. Memecah ulang ke 5 PR terpisah berisiko memutus dependensi antar-commit (misalnya API route baru memanggil service baru dan diuji oleh test integrasi lintas modul).
  - **Alur Aman:**
    1. Tutup item P0 tersisa (keputusan `.agent/` + re-verifikasi Native Desktop UI pasca-perbaikan CSS).
    2. Konfirmasi tidak ada commit unik lain yang perlu diambil dari branch `feature/*` milik Ferlita, Habil, Adriel, dan Anisa.
    3. Buat 6 commit atomik di atas pada `feature/fikri-ui-ux`, push branch `feature/fikri-ui-ux`, lalu ajukan **1 Pull Request** ke `main` dengan review & persetujuan kelima anggota.
    4. Setelah PR masuk ke `main`, masing-masing branch resmi anggota melakukan `git fetch origin && git merge origin/main` sesuai [GIT_WORKFLOW.md](file:///C:/Turnamen.in/docs/GIT_WORKFLOW.md#L197-L249).
- **Opsi 2 (Alternatif Ketat Branch Ownership): 5 Stacked/Sequential PRs per Branch Anggota**
  - Cocok hanya bila diwajibkan secara administratif bahwa setiap commit harus berasal dari branch resmi pemiliknya (`Habil` -> `Adriel` -> `Anisa` -> `Fikri` -> `Ferlita`). Membutuhkan *cherry-pick*/pemindahan file antar 5 branch dengan risiko konflik dan overhead verifikasi ulang `pytest` di tiap langkah.

---

## 7. Verifikasi Pasca-Perubahan `.gitignore`

- `git check-ignore -v supabase/.temp/cli-latest`: cocok dengan aturan `.gitignore:55:supabase/.temp/` -> **IGNORED**.
- `git check-ignore -v supabase/migrations/0001_initial_schema.sql supabase/migrations/20261126232622_wave6_11_custom_game_artwork.sql supabase/seed.sql`: seluruhnya **tidak di-ignore** (exit code non-zero dari `check-ignore`).
- `git diff --check`: exit code `0`.
- Branch tetap `feature/fikri-ui-ux`, `0` file staged, `.env` tidak ada (`False`), dan tidak ada file `.agent/` atau pekerjaan tim yang dihapus.
