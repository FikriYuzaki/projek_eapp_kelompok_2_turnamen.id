# TURNAMEN.IN - WAVE 6.1: SUPABASE PUBLISHABLE KEY COMPATIBILITY REPORT

- **Tanggal Laporan:** 2026-11-26
- **Branch Aktif:** `feature/fikri-ui-ux`
- **Repository:** `FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`
- **Status Wave 6.1:** **`PASS`** (seluruh 281 pengujian `pytest -v`, `run.py --check`, `node --check`, `git diff --check`, dan `pip check` lulus)
- **Status Aktivasi Online Mode (`APP_MODE=supabase`):** **Belum Aktif** (validasi konfigurasi dan kompatibilitas SDK telah selesai, namun integrasi langsung ke Supabase Cloud dan penerapan migrasi `0002`–`0006` belum dijalankan)

---

## 1. Configuration Audit

Audit menyeluruh terhadap konfigurasi dan klien Supabase sebelum perubahan menemukan hal-hal berikut:

1. **SDK `supabase==2.7.4` di [requirements.txt](file:///C:/Turnamen.in/requirements.txt):**
   - Pada `supabase==2.7.4` (`supabase._sync.client.SyncClient.__init__`), konstruktor SDK memaksa `supabase_key` cocok dengan regex JWT 3-segmen (`^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$`) dan melempar `SupabaseException("Invalid API key")` untuk key opaque `sb_publishable_*`.
2. **Validasi Kredensial di [client.py](file:///C:/Turnamen.in/backend/infrastructure/supabase/client.py):**
   - `validate_supabase_credentials()` sebelumnya menolak `sb_publishable_*` secara eksplisit dan mewajibkan `SUPABASE_ANON_KEY` berbentuk JWT.
   - `create_supabase_client()` hanya membaca `config.supabase_anon_key`.
3. **Konfigurasi Terpusat di [config.py](file:///C:/Turnamen.in/backend/core/config.py):**
   - `AppConfig` dan `load_config()` sebelumnya hanya mengenal `SUPABASE_ANON_KEY` (`supabase_anon_key`) dan belum membaca `SUPABASE_PUBLISHABLE_KEY` (`supabase_publishable_key`), belum menangani konflik nilai antara kedua variabel, serta belum melakukan validasi format key maupun penolakan `sb_secret_*` / `service_role` pada `AppConfig.validate()`.
4. **Sanitasi Log & Entry Point:**
   - [logging_config.py](file:///C:/Turnamen.in/backend/core/logging_config.py), [run.py](file:///C:/Turnamen.in/run.py), [app_launcher.py](file:///C:/Turnamen.in/desktop/launcher/app_launcher.py), dan [eel-bridge.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/eel-bridge.js) sebelumnya hanya mengekstrak dan menyensor `supabase_anon_key`, belum mencakup `supabase_publishable_key` dan pola token `sb_publishable_*` / `sb_secret_*`.
5. **Template Environment [.env.example](file:///C:/Turnamen.in/.env.example):**
   - Hanya mendokumentasikan `SUPABASE_ANON_KEY`, belum menampilkan `SUPABASE_PUBLISHABLE_KEY` sebagai prioritas utama.

---

## 2. Key Compatibility Changes

Perubahan implementasi diterapkan dengan mempertahankan kompatibilitas mundur (*backward compatibility*) tanpa mengubah default `APP_MODE=mock`:

1. **Representasi Konfigurasi Konsisten di [config.py](file:///C:/Turnamen.in/backend/core/config.py):**
   - Menambahkan field `supabase_publishable_key` pada `AppConfig` dan pembacaan `SUPABASE_PUBLISHABLE_KEY` di `load_config()`, sambil mempertahankan `supabase_anon_key` untuk fallback legacy.
   - Menambahkan properti `AppConfig.supabase_api_key` dan fungsi `resolve_supabase_api_key(publishable_key, anon_key)` sebagai satu sumber kebenaran internal:
     - Jika `SUPABASE_PUBLISHABLE_KEY` tersedia dan valid, key tersebut digunakan sebagai prioritas utama.
     - Jika `SUPABASE_PUBLISHABLE_KEY` kosong atau tidak disetel, `SUPABASE_ANON_KEY` yang valid digunakan sebagai fallback.
     - Jika kedua variabel diisi dengan nilai yang sama (konsisten), nilai tersebut diterima.
     - Jika kedua variabel diisi dengan nilai yang **berbeda**, konfigurasi ditolak secara eksplisit (`ValueError` / `RuntimeError`) dan tidak pernah memilih salah satu secara diam-diam.
   - Menambahkan `validate_supabase_config_values()` sebagai validator tunggal bersama antara `AppConfig.validate()` dan `validate_supabase_credentials()`:
     - Menolak `sb_secret_*` dan legacy `service_role` (baik pola string maupun klaim JWT `"role": "service_role"`).
     - Memvalidasi `SUPABASE_URL` (`http`/`https`, hostname valid, bukan URL placeholder).
     - Menerima `sb_publishable_*` sebagai string opaque (`^sb_publishable_[A-Za-z0-9_-]{4,}$`) tanpa memaksa decode JWT.
     - Tetap menerima legacy `anon` JWT yang valid.
     - Tetap mengizinkan `APP_MODE=mock` berjalan normal tanpa kredensial Cloud.
   - Memperbarui `AppConfig.to_safe_dict()` untuk menyensor `supabase_publishable_key` dan `supabase_anon_key` (`***REDACTED***`).
2. **Validasi Client di [client.py](file:///C:/Turnamen.in/backend/infrastructure/supabase/client.py):**
   - `validate_supabase_credentials()` mempertahankan signature posisi lama `(supabase_url, supabase_key)` sekaligus mendukung keyword `publishable_key` dan `anon_key`, serta mendelegasikan logika ke `validate_supabase_config_values()`.
3. **Sanitasi Log & Bridge:**
   - [logging_config.py](file:///C:/Turnamen.in/backend/core/logging_config.py), [run.py](file:///C:/Turnamen.in/run.py), [app_launcher.py](file:///C:/Turnamen.in/desktop/launcher/app_launcher.py), dan [eel-bridge.js](file:///C:/Turnamen.in/desktop/web/assets/js/core/eel-bridge.js) kini menyensor `supabase_publishable_key` serta pola literal `sb_publishable_*` dan `sb_secret_*`.

---

## 3. Python SDK Integration

- **Upgrade SDK Resmi:** [requirements.txt](file:///C:/Turnamen.in/requirements.txt) dan virtual environment `.venv` diperbarui dari `supabase==2.7.4` ke **`supabase==2.34.1`** (`pip check` bersih tanpa konflik dependensi).
- **Inisialisasi Resmi tanpa HTTP Client Buatan Sendiri:**
  - `create_supabase_client()` memanggil `supabase.create_client(url, resolved_key, options=ClientOptions(persist_session=False, auto_refresh_token=False, headers=headers))` secara resmi.
  - Pada `supabase==2.34.1`, `SyncClient` tidak lagi memaksa regex JWT pada `supabase_key`, sehingga `sb_publishable_*` diterima secara native tanpa monkey-patch pada modul internal SDK (`sync_client_mod.re.match is stdlib_re.match` tetap terjaga).
- **Pemisahan Header `apikey` dan `Authorization` Sesi Pengguna:**
  - Terverifikasi secara inspeksi langsung terhadap instance SDK:
    - `client.supabase_key` menyimpan key aplikasi (`sb_publishable_*` atau legacy anon JWT).
    - Header `apiKey` / `apikey` pada `client.options.headers`, `client.auth._headers`, dan `client.postgrest.session.headers` selalu berisi key aplikasi.
    - Saat `access_token` pengguna diteruskan, `Authorization` disetel ke `Bearer <user_jwt>` sementara `apiKey` tetap utuh.
    - Saat transisi event auth (`SIGNED_IN`, `TOKEN_REFRESHED`, `SIGNED_OUT`) melalui `_listen_to_auth_events()`, `Authorization` diperbarui sesuai sesi tanpa merusak `supabase_key` atau `apiKey`.
  - Tidak ada fallback diam-diam ke `service_role`, tidak ada pemaksaan decode JWT terhadap `sb_publishable_*`, dan tidak ada pencetakan key/token ke log.

---

## 4. Validation Tests

Seluruh pengujian berjalan lokal secara offline (tanpa HTTP request ke Supabase Cloud):

- **Suite Khusus Wave 6.1:** [test_supabase_publishable_key_compatibility.py](file:///C:/Turnamen.in/tests/unit/test_supabase_publishable_key_compatibility.py) (**18 test cases passed**) dan pembaruan [test_auth_and_permissions.py](file:///C:/Turnamen.in/tests/unit/test_auth_and_permissions.py):
  - Publishable key valid (`SUPABASE_PUBLISHABLE_KEY=sb_publishable_...`).
  - Legacy anon JWT valid (`SUPABASE_ANON_KEY=eyJ...`).
  - Publishable key kosong dengan fallback anon valid maupun gagal saat keduanya kosong.
  - Kedua key tersedia dengan nilai konsisten (berhasil) vs nilai berbeda (ditolak eksplisit).
  - URL Supabase kosong dan berbagai format URL tidak valid ditolak (`""`, whitespace, skema non-HTTP, host tidak valid, URL placeholder).
  - `sb_secret_*` dan legacy `service_role` JWT (serta literal `service_role`) ditolak pada `validate_supabase_credentials` maupun `load_config`.
  - Mock Mode tetap menjadi default (`APP_MODE=mock`) dan lulus `run_smoke_check()` tanpa kredensial Cloud.
  - Supabase Mode gagal dengan pesan konfigurasi yang jelas saat kredensial tidak tersedia.
  - SDK client menerima `sb_publishable_*` tanpa memanggil `decode_jwt_payload_unverified`, mengirim header `apikey`, meneruskan `Authorization: Bearer <user_jwt>`, mempertahankan `apikey` saat pergantian sesi, dan menyensor key/token dari `to_safe_dict()` serta log.
- **Hasil Quality Gate Penuh (setelah edit terakhir):**
  - `.venv\Scripts\python.exe -m pytest -v`: **`281 passed` in 47.05s** (exit code `0`, 0 failed, 0 skipped).
  - `.venv\Scripts\python.exe run.py --check`: **`health_ok: true`**, **`repository_ok: true`**, `app_mode: "mock"`, `supabase_configured: false`, `games_count: 3`, `tournaments_count: 2` (exit code `0`).
  - `node --check desktop/web/assets/js/core/eel-bridge.js`: **exit code `0`**.
  - `git diff --check`: **exit code `0`**.
  - `.venv\Scripts\python.exe -m pip check`: **`No broken requirements found.`** (exit code `0`).

---

## 5. Environment Configuration Guide

Template [.env.example](file:///C:/Turnamen.in/.env.example) telah diperbarui untuk memandu konfigurasi lokal secara aman (tanpa menyertakan key nyata, secret, password, atau JWT pengguna):

- **Mode Default (Offline/Development):** `APP_MODE=mock` — berjalan penuh dengan `MockDataStoreRepository` tanpa kredensial Cloud.
- **Mode Supabase (`APP_MODE=supabase`):**
  1. Salin `.env.example` menjadi `.env` secara lokal (file `.env` diabaikan oleh `.gitignore`).
  2. Isi:
     ```dotenv
     APP_MODE=supabase
     SUPABASE_URL=https://<project-ref>.supabase.co
     SUPABASE_PUBLISHABLE_KEY=<salin-publishable-key-sb_publishable_...-dari-dashboard>
     ```
  3. **Fallback Kompatibilitas (Deprecated):** `SUPABASE_ANON_KEY` hanya diisi apabila proyek masih memakai legacy `anon` public JWT dan `SUPABASE_PUBLISHABLE_KEY` tidak diisi. Jangan mengisi kedua variabel dengan nilai yang berbeda.
  4. **Aturan Keamanan Kredensial:** Publishable key boleh berada pada aplikasi desktop karena seluruh akses data tetap dibatasi oleh sesi pengguna (`Supabase Auth`) dan kebijakan **Row Level Security (RLS)** PostgreSQL. Secret key (`sb_secret_*`) maupun legacy `service_role` JWT **tidak boleh** dimasukkan ke aplikasi desktop maupun repository.

---

## 6. Security Considerations

1. **Penegakan Least-Privilege di Desktop Client:** Aplikasi desktop memperlakukan seluruh client key sebagai kunci publik yang hanya mengandalkan RLS PostgreSQL dan JWT sesi pengguna yang terverifikasi oleh Supabase Auth.
2. **Penolakan Kredensial Berbahaya Lebih Awal:** `sb_secret_*` dan `service_role` ditolak di level konfigurasi (`AppConfig.validate()`, `resolve_supabase_api_key()`) maupun factory client (`validate_supabase_credentials()`), termasuk pada `APP_MODE=mock`.
3. **Anti-Ambiguitas Konfigurasi:** Pengisian `SUPABASE_PUBLISHABLE_KEY` dan `SUPABASE_ANON_KEY` dengan nilai berbeda gagal secara eksplisit agar tidak terjadi *silent misconfiguration* antar-environment.
4. **Sanitasi Log & Bridge:** Key aplikasi (`sb_publishable_*`, legacy anon JWT), secret key, dan user bearer token disensor otomatis di logger Python (`SecretRedactingFilter`), ringkasan konfigurasi (`to_safe_dict()`), output `--check`, dan diagnostic bridge JS (`eel-bridge.js`).
5. **Isolasi Database & Migrasi:** Tidak ada perubahan terhadap `supabase/migrations/0001`–`0006` maupun database Supabase Cloud.

---

## 7. Remaining Limitations

1. **Belum Ada Uji Live HTTP ke Supabase Cloud:** Validasi Wave 6.1 menguji konfigurasi, logika resolusi key, header instance SDK resmi (`create_client`), serta mock/unit checks secara offline; handshake HTTP nyata (`sign_up`, `sign_in_with_password`, PostgREST query/RPC) ke project Supabase Cloud dengan `sb_publishable_*` nyata belum dijalankan.
2. **Online Mode (`APP_MODE=supabase`) Belum Aktif:** Sesuai kondisi akhir Wave 6, migrasi `0002`–`0006` belum diterapkan ke Supabase Cloud (`cfdsgxciodfkamskafwe`), akun `super_admin` belum ditautkan melalui `link_profile_auth_user()`, dan file `.env` produksi lokal belum dibuat.
3. **Persyaratan Versi Python SDK:** `supabase==2.34.1` mensyaratkan `Python >= 3.11` (telah diverifikasi berjalan pada `Python 3.12.10` di `.venv`).
