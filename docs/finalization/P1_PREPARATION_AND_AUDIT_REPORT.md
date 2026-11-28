# Laporan Audit & Persiapan P1: Turnamen.in

- **Tanggal Audit:** 28 November 2026
- **Branch Repository:** `feature/fikri-ui-ux` (`e01cb4e`)
- **Sifat Tugas:** Audit read-only pasca-penutupan P0 (belum mengubah kode, konfigurasi, migrasi SQL, maupun kontrak database)

---

## 1. Ringkasan Penutupan Tahap P0

Seluruh butir P0 prasyarat integrasi yang ditugaskan telah diselesaikan dan diverifikasi:

1. **P0.1 Hygiene `.gitignore` (`supabase/.temp/` & `.agent/` Opsi A):**
   - [`.gitignore`](file:///C:/Turnamen.in/.gitignore#L54-L58) sudah mengabaikan `supabase/.temp/` (`supabase/.temp/cli-latest`) dan `.agent/` (`28` file untracked `ui-ux-pro-max` + `5` cache `.pyc`).
   - Seluruh `33` file di `.agent/` tetap utuh di disk tanpa dihapus, dipindahkan, atau didaftarkan ke `skills-lock.json`; tidak ada aturan kerja tim yang tersembunyi di dalamnya.
2. **P0.2 Native Desktop Supabase UI Verification (`APP_MODE=supabase`, Read-Only, Pasca CSS Fix):**
   - Pengguna telah menjalankan [`wave611_native_supabase_ui.ps1`](file:///C:/Users/fikri/AppData/Local/TurnamenBackups/wave611_native_supabase_ui.ps1) pada `13:47:57` s/d `13:49:41` WIB dengan hasil **tanpa kendala** ([WAVE6_11_NATIVE_SUPABASE_UI_VERIFICATION.md](file:///C:/Turnamen.in/docs/finalization/WAVE6_11_NATIVE_SUPABASE_UI_VERIFICATION.md)).
   - Metadata sesi (`wave611_native_ui_session.json`) mencatat `precheck_exit_code: 0`, `app_exit_code: 0`, `env_vars_cleaned: true`, dan `dotenv_exists_after: false`. Arsip screenshot dicatat jujur `NOT TESTED` karena direktori screenshot kosong.

---

## 2. Audit P1.1: Sinkronisasi Dokumentasi Skema & Kontrak Database

### A. Temuan Drift Aktual vs 7 Migrasi SQL (`0001`-`0006` + `20261126232622`)

| Dokumen | Kondisi Saat Ini | Kesenjangan (Drift) Dibanding Skema Aktual |
| :--- | :--- | :--- |
| **[docs/database-schema.md](file:///C:/Turnamen.in/docs/database-schema.md)** | Masih mendokumentasikan `12` tabel inti dari `0001`-`0002` saja (`179` baris). | 1. Belum mencantumkan tabel **`public.match_submission_requests`** (`0004`: kolom `id`, `match_id`, `actor_id`, `idempotency_key`, `request_hash`, `response_payload`, `created_at`; `uq_match_submission_idempotency`; `idx_match_submission_requests_match_id`; RLS `SELECT` terbatas `authenticated`).<br>2. Belum mencantumkan tabel **`public.game_artwork_overrides`** (`20261126232622`: `id`, `game_id`, `storage_path`, `mime_type`, `file_size_bytes`, `width`, `height`, `uploaded_by`, `created_at`, `updated_at`) maupun relasinya di ERD Mermaid.<br>3. Masih menyebut policy lama `"Profiles select own or staff"` pada narasi `0002`, padahal `0003`/`0005` menggantinya dengan `"Profiles select own or admin"`.<br>4. Belum mencantumkan index `uq_profiles_lower_email`, trigger hardening `handle_new_auth_user()` (`SQLSTATE 23505`, tanpa email auto-link dari `0005`), `9` fungsi `private.*` (`SECURITY DEFINER`, `SET search_path = ''`) dan wrapper `public.*` dari `0003`-`0006`.<br>5. Bagian `"Cara Menjalankan Migrasi Database"` baru menyebut `0001` & `0002`; belum mencakup `0003`-`0006`, `20261126232622`, serta arsitektur split-deployment bucket **`game-artwork`** (4 policy `storage.objects` di Dashboard). |
| **[docs/contracts/database-contract.md](file:///C:/Turnamen.in/docs/contracts/database-contract.md)** | Sudah memuat Bagian `H. game_artwork_overrides (Wave 6.11)`. | 1. Bagian 1 masih berjudul `"Daftar 12 Tabel Inti"` (sekarang `14` tabel publik di skema aktif).<br>2. Belum memuat kontrak kolom & kebijakan RLS untuk tabel **`public.match_submission_requests`** (`0004`).<br>3. Peringatan di baris `6` masih hanya menyebut `0001_initial_schema.sql`, belum merujuk seluruh rangkaian `0001`-`20261126232622`. |

### B. Rekomendasi P1.1 & Risiko
- **Rekomendasi:** Perbarui [docs/database-schema.md](file:///C:/Turnamen.in/docs/database-schema.md) dan [docs/contracts/database-contract.md](file:///C:/Turnamen.in/docs/contracts/database-contract.md) agar mencakup penuh `14` tabel publik, ERD terbaru, fungsi RPC `0003`-`0006`, policy `"Profiles select own or admin"`, serta bucket Storage `game-artwork`.
- **Risiko jika ditunda:** Anggota tim atau reviewer eksternal akan salah memahami kontrak skema produksi (terutama idempotency `match_submission_requests` dan split ownership `storage.objects`).
- **Catatan kepemilikan (`AGENTS.md`):** Kedua dokumen ini berada di bawah area **Habil** (`feature/habil-database-auth`) dan kontrak bersama tim; perubahan perlu disetujui koordinator dan Habil.

---

## 3. Audit P1.2: Perbedaan Versi `Eel` (`requirements.txt` vs `.venv`)

### A. Hasil Audit `13` Paket di [`requirements.txt`](file:///C:/Turnamen.in/requirements.txt)

| Paket | Pin di `requirements.txt` | Versi Terpasang di `.venv` | Status |
| :--- | :---: | :---: | :---: |
| `Eel` | **`0.16.0`** | **`0.18.2`** | **MISMATCH** |
| `Flask`, `Werkzeug`, `requests`, `bottle`, `bottle-websocket`, `gevent`, `gevent-websocket`, `whichcraft`, `pyparsing`, `python-dotenv`, `supabase`, `pytest` (`12` paket lain) | Sesuai seluruhnya | Sama persis (`3.0.3`, `3.0.4`, `2.32.3`, `0.12.25`, `0.2.9`, `24.2.1`, `0.10.1`, `0.6.1`, `3.1.4`, `1.0.1`, `2.34.1`, `8.3.2`) | **MATCH** |

Temuan detail metadata `Eel==0.18.2` pada `.venv`:
- `Requires-Python: >=3.7`, dependensi runtime sama dengan yang terpasang di `.venv` (`bottle`, `bottle-websocket`, `future`, `pyparsing`, `typing_extensions`, `importlib_resources`).
- Versi `0.18.2` memakai `importlib_resources` (lebih aman untuk Python `3.12` dibanding `0.16.0` yang masih bergantung pada `pkg_resources` di sejumlah environment baru), dan sudah lulus `304` `pytest` serta verifikasi live **Native Desktop Supabase UI** bersama pengguna.
- Referensi versi `0.16.0` juga tercatat pada [`README.md:13`](file:///C:/Turnamen.in/README.md#L13) dan [`.agents/skills/turnamen-python-eel/SKILL.md:36`](file:///C:/Turnamen.in/.agents/skills/turnamen-python-eel/SKILL.md#L36).

### B. Rekomendasi P1.2 & Risiko
- **Rekomendasi:** Pada fase implementasi P1, naikkan pin di [`requirements.txt`](file:///C:/Turnamen.in/requirements.txt#L14) dari `Eel==0.16.0` ke **`Eel==0.18.2`** dan selaraskan [`README.md`](file:///C:/Turnamen.in/README.md#L13) (bukan men-downgrade `.venv` ke `0.16.0`).
- **Risiko jika salah langkah:** Downgrade ke `0.16.0` berisiko memecahkan kompatibilitas `pkg_resources` / setuptools di Python `3.12+` saat anggota tim membuat `.venv` baru; sedangkan mempertahankan `0.16.0` di `requirements.txt` menyebabkan dev environment baru memakai versi berbeda dari yang sudah teruji.

---

## 4. Audit P1.3: Penggunaan `SUPABASE_STORAGE_BUCKET` vs `GAME_ARTWORK_BUCKET`

### A. Pemetaan Referensi Aktual di Seluruh Repository

| Variabel / Konstanta | Nilai | Lokasi Kemunculan | Pemakaian Runtime |
| :--- | :--- | :--- | :--- |
| `SUPABASE_STORAGE_BUCKET` / `config.supabase_storage_bucket` | `"tournament-assets"` | [`.env.example:40`](file:///C:/Turnamen.in/.env.example#L40), [`backend/core/config.py:211,364`](file:///C:/Turnamen.in/backend/core/config.py#L211) | **`0` pemakaian runtime** di module bisnis, repository, maupun test. |
| `GAME_ARTWORK_BUCKET` | `"game-artwork"` | [`backend/modules/tournaments/artwork_validator.py:14`](file:///C:/Turnamen.in/backend/modules/tournaments/artwork_validator.py#L14), [`supabase_repository.py`](file:///C:/Turnamen.in/backend/repositories/supabase/supabase_repository.py#L691-L724), migrasi `20261126232622`, `4` Dashboard policies, dan suite unit/integrasi | **Aktif penuh di produksi & mock**; terikat pada RLS policy `bucket_id = 'game-artwork'` di Cloud. |

### B. Analisis Dampak & Rekomendasi P1.3
- **Dampak Kritis:** **Jangan mengganti `GAME_ARTWORK_BUCKET = "game-artwork"` agar membaca `SUPABASE_STORAGE_BUCKET`.** Jika env var `SUPABASE_STORAGE_BUCKET` bernilai `"tournament-assets"` (default di `config.py` dan `.env.example`), mengarahkannya ke sana akan menyebabkan upload Wave 6.11 gagal karena bucket produksi bernama `game-artwork` dan keempat policy `storage.objects` di Cloud hanya mengizinkan `bucket_id = 'game-artwork'`.
- **Rekomendasi Aman:**
  1. Pertahankan `GAME_ARTWORK_BUCKET = "game-artwork"` tetap konstan pada [`artwork_validator.py`](file:///C:/Turnamen.in/backend/modules/tournaments/artwork_validator.py#L14).
  2. Pertahankan atribut `supabase_storage_bucket` di [`config.py`](file:///C:/Turnamen.in/backend/core/config.py#L211) untuk kompatibilitas mundur / cadangan bucket fitur aset turnamen di masa depan.
  3. Perjelas keterangan di [`.env.example`](file:///C:/Turnamen.in/.env.example#L40) bahwa `SUPABASE_STORAGE_BUCKET` bersifat opsional/cadangan untuk aset turnamen umum, sementara poster kustom game menggunakan bucket `game-artwork`.

---

## 5. Audit P1.4: Pengujian & Tinjauan Cloud Lanjutan (Sebelum Public Signup)

| Agenda P1.4 | Kondisi Saat Ini | Langkah yang Dibutuhkan | Risiko / Batasan |
| :--- | :--- | :--- | :--- |
| **1. Tinjauan Security Advisors Supabase** | Laporan Wave 6.6 mencatat `2` fungsi `anon` `SECURITY DEFINER` (`current_user_role`, `list_tournament_announcements`), `6` fungsi `authenticated` `SECURITY DEFINER`, dan **`Leaked Password Protection: disabled`**. | Dokumentasikan penilaian keamanan tiap temuan Advisor; **jangan cabut `EXECUTE` `current_user_role()` atau `list_tournament_announcements()`** karena akan memutus policy RLS dan tampilan publik Guest. Aktifkan *Leaked Password Protection* di Auth Dashboard (jika tersedia pada paket project) sebelum membuka `Public Signup`. | Mengubah grants `SECURITY DEFINER` secara membabi buta dapat merusak seluruh fungsi RPC `0003`-`0006`. |
| **2. Pengujian Live Akun Non-Admin (`player`)** | Penolakan non-admin sudah teruji di unit/integrasi API & PG lokal (`403` / RLS error), tetapi **belum diuji live di Cloud** karena baru `1` Auth user (`super_admin`) & `Public Signup = DISABLED`. | Siapkan protokol uji terkendali (hanya setelah disetujui pengguna): buat `1` Auth user uji sementara via Dashboard/Auth terotorisasi -> tautkan atau uji sebagai `player` -> verifikasi penolakan (`403` / Storage RLS block) -> hapus akun uji -> pastikan `Public Signup` kembali/tetap `DISABLED` hingga rilis final. | Jangan membuka `Public Signup` tanpa pengawasan saat melakukan uji akun sementara. |
| **3. Benchmark Wall-Clock Live Cloud (`< 3 detik`)** | Benchmark lokal `mock` (`0.05 detik`) & pengurangan query Cloud (`78 -> 22` calls) sudah terukur di Wave 6.8/6.9; latensi jaringan riil ke `cfdsgxciodfkamskafwe.supabase.co` belum direkam angkanya secara otomatis. | Jalankan skrip pengukur non-PII (input `SUPABASE_PUBLISHABLE_KEY` + login interaktif tanpa menyimpan kredensial/token) untuk mencatat waktu muat aktual Dashboard Wave 1 + Wave 2 ke laporan. | Tidak ada mutasi data; perlu eksekusi dengan jaringan pengguna langsung. |

---

## 6. Urutan Pengerjaan P1, Risiko, & Daftar File Terdampak

Urutan pengerjaan yang direkomendasikan ketika pengguna memberi persetujuan implementasi P1 (tetap sebelum integrasi PR ke `main`):

| Urutan | Paket Kerja P1 | File / Target Terdampak | Pemilik Menurut `AGENTS.md` | Risiko Utama | Kriteria Selesai |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **P1.1** Sinkronisasi dokumentasi skema & kontrak | [`docs/database-schema.md`](file:///C:/Turnamen.in/docs/database-schema.md), [`docs/contracts/database-contract.md`](file:///C:/Turnamen.in/docs/contracts/database-contract.md) | **Habil** + Koordinasi 5 Anggota | Risiko rendah (hanya dokumentasi), harus akurat 100% terhadap `0001`-`20261126232622`. | Seluruh `14` tabel, `9` fungsi `private.*`, RPC `public.*`, dan bucket `game-artwork` terdokumentasi konsisten. |
| **2** | **P1.2** Penyelarasan versi `Eel` | [`requirements.txt`](file:///C:/Turnamen.in/requirements.txt), [`README.md`](file:///C:/Turnamen.in/README.md) *(opsional: [`SKILL.md` Eel](file:///C:/Turnamen.in/.agents/skills/turnamen-python-eel/SKILL.md))* | **Fikri** + Koordinasi Root | Hindari downgrade `.venv` ke `0.16.0`; uji ulang `pytest` & `run.py --check`. | `13/13` paket di `requirements.txt` cocok persis dengan `.venv`, `pytest` lulus penuh. |
| **3** | **P1.3** Klarifikasi komentar bucket Storage | [`.env.example`](file:///C:/Turnamen.in/.env.example#L40) | **Fikri** + **Habil** | Jangan ubah `GAME_ARTWORK_BUCKET` agar tidak memutus bucket & policy `game-artwork` di Cloud. | Komentar `.env.example` menjelaskan pemisahan `SUPABASE_STORAGE_BUCKET` vs `game-artwork`. |
| **4** | **P1.4** Penutupan item Cloud lanjutan | Supabase Dashboard (Advisors, Auth) & laporan verifikasi Cloud | **Habil** + **Fikri** + **Anisa** | Jangan buka `Public Signup` sebelum *Leaked Password Protection* & uji non-admin live selesai. | Checklist Advisor ditinjau, benchmark wall-clock Cloud tercatat, dan uji non-admin live terverifikasi atau terdokumentasi final. |
