# Wave 6.10: Laporan Integrasi Artwork Resmi Game

- **Tanggal:** 2026-11-27
- **Target Sistem:** Katalog Game & Artwork Desktop UI Turnamen.in ([ui-components.js](file:///C:/Turnamen.in/desktop/web/assets/js/components/ui-components.js), [app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js), [components.css](file:///C:/Turnamen.in/desktop/web/assets/css/components.css), [ASSETS.md](file:///C:/Turnamen.in/desktop/web/assets/images/games/ASSETS.md))
- **Tujuan:** Mengganti poster/thumbnail game yang sebelumnya memakai SVG generik lokal dengan artwork resmi terverifikasi dari publisher/developer dan Steam Store tanpa placeholder atau ilustrasi buatan AI, menjaga konsistensi lintas halaman, menerapkan lazy loading dan cache sesi, serta mempertahankan waktu muat Dashboard di bawah 3 detik.

---

## 1. Audit Katalog Game & Status RAWG

- **Total Game Katalog Seed & Produksi:** `3` game (`games_count: 3` pada `run.py --check`), seluruhnya teridentifikasi melalui UUID resmi, `slug`, platform, dan `external_rawg_slug`.
- **Status Integrasi RAWG:** `rawg_api_key` bernilai `""` (kosong, terverifikasi melalui `run.py --check`). Aplikasi tidak mengasumsikan `RAWG_API_KEY` tersedia dan tidak bergantung pada pemanggilan API eksternal saat runtime.

| Game UUID (`games.id`) | Slug | Nama Game | Genre & Platform | Sumber Resmi Terverifikasi | Detail HTTP & Dimensi Aktual | Fallback Lokal |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `22222222-2222-4222-8222-222222222201` | `mobile-legends` | Mobile Legends: Bang Bang | MOBA / Mobile | MOONTON Official (`mobilelegends.com`): `https://akmweb.youngjoygame.com/web/gms/image/c3d1596795b86dc26e5f1ef2d48c3dfd.jpg` | `HTTP 200`, `image/jpeg`, `600x315`, `25.588 bytes`, `max-age=1090697` | `assets/images/games/mobile-legends.svg` |
| `22222222-2222-4222-8222-222222222202` | `valorant` | VALORANT | Tactical Shooter / PC | Riot Games Official (`playvalorant.com`): `https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/a3d06721391f4c274e588c380ca6903c8b3e129e-1920x1080.jpg` | `HTTP 200`, `image/jpeg`, `1920x1080`, `229.404 bytes`, `public, max-age=31273477, s-maxage=2592000` | `assets/images/games/valorant.svg` |
| `22222222-2222-4222-8222-222222222203` | `ea-sports-fc` | EA Sports FC 25 | Sports / PC / Console | Steam Store Official (`App ID 2669320`): `https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2669320/capsule_616x353.jpg` | `HTTP 200`, `image/jpeg`, `616x353`, `78.829 bytes`, `max-age=315360000, public` | `assets/images/games/ea-sports-fc.svg` |
| *(Game baru tanpa artwork terverifikasi)* | `default-arena` | Esports Arena *(fallback)* | N/A | Tidak meminjam atau mensubstitusi artwork game lain (`hasOfficialArtwork: false`) | Aset SVG lokal | `assets/images/games/default-arena.svg` |

---

## 2. Implementasi Pemetaan, Lazy Loading, Cache & Fallback

1. **Pemetaan Ketat Berbasis ID & Slug ([ui-components.js](file:///C:/Turnamen.in/desktop/web/assets/js/components/ui-components.js)):**
   - `GAME_ARTWORK_BY_ID` memetakan UUID game secara langsung ke kunci `GAME_ARTWORK_REGISTRY`.
   - `resolveGameArtwork(game)` menyelesaikan sumber dengan prioritas ketat: UUID game -> `slug` -> pencocokan eksak `external_rawg_slug`, `officialTitle`, atau `aliases`. Game tidak dikenal jatuh ke `default-arena` sehingga tidak ada artwork salah game.
   - `isSafeArtworkUrl(rawUrl)` menerima hanya asset lokal `assets/images/...` (tanpa `..`) atau URL `https:` tanpa kredensial embedded dan tanpa parameter query sensitif (`token`, `access_token`, `api_key`, `secret`, `password`, `service_role`, dll.).
2. **Cache Sesi & Dual-Stage Fallback ([ui-components.js](file:///C:/Turnamen.in/desktop/web/assets/js/components/ui-components.js)):**
   - `ARTWORK_CACHE` mencatat status `"loaded"` melalui `handleArtworkLoad()` dan `"failed"` melalui `handleArtworkError()` per URL (dengan helper inspeksi/reset `getArtworkCacheStats()` dan `clearArtworkCache()`).
   - Jika URL CDN gagal dimuat atau sebelumnya sudah ditandai `"failed"` di sesi tersebut, `handleArtworkError()` melakukan fallback tahap pertama ke `fallbackSrc` (SVG lokal game terkait) dan tahap kedua ke `.artwork-fallback-svg.is-visible` jika asset fallback juga gagal.
3. **Konsistensi UI, Lazy Loading & Rasio Poster ([components.css](file:///C:/Turnamen.in/desktop/web/assets/css/components.css), [app-pages.js](file:///C:/Turnamen.in/desktop/web/assets/js/pages/app-pages.js)):**
   - Seluruh elemen `<img>` dari `renderGameArtwork()` dan `renderGameChip()` memakai atribut `loading="lazy"`, `decoding="async"`, dan `referrerpolicy="no-referrer"`, dengan `loading="eager"` dihapus agar tidak menghambat pemuatan awal Dashboard.
   - CSS menjaga `aspect-ratio: 16 / 9;` dan `object-fit: cover;` pada `.artwork-img` serta `.game-chip-thumb` (`22x14`, `object-fit: cover`).
   - Seluruh pemanggil di `app-pages.js` (Dashboard Guest/Player/Captain/Organizer/Super Admin, Jelajah Game, Daftar Turnamen, Detail Turnamen, dan Manajemen Tim & Game) diperbarui agar meneruskan objek game lengkap (`id` dan `slug`), serta perbaikan cakupan `gamesById` pada `renderTeamManagementContent` dan `renderOrganizerDashboard`.

---

## 3. Hasil Verifikasi Pasca-Edit Terakhir

1. **Automated Test Suite (`pytest -q`):**
   - **297 passed, 4 warnings in 56.18s** (`0 failed`, `0 skipped`).
   - Termasuk `tests/unit/test_wave6_10_game_artwork.py` (CSS aspect-ratio/object-fit, pemetaan ID/slug, isolasi game tak dikenal, validasi URL aman, lazy loading, cache & dual-stage fallback, konsistensi render Dashboard Super Admin & Guest, serta uji API `< 3.0s`), `tests/unit/test_wave6_9_skeleton_loading.py`, dan `tests/unit/test_wave6_8_dashboard_performance.py`.
2. **Smoke Check Konfigurasi & Katalog (`.\.venv\Scripts\python.exe run.py --check`):**
   - `health_ok: true`, `repository_ok: true`, `games_count: 3`, `tournaments_count: 2`, `rawg_api_key: ""`.
3. **Benchmark Kecepatan Dashboard (`APP_MODE=mock` via Eel `forward_api_request` + Flask Lokal):**
   - `wave1_ms = 12.94 ms` (`/games?include_inactive=true`, `/tournaments`, `/teams`, `/users` paralel)
   - `report_ms = 3.7 ms`
   - `dashboard_total_ms = 16.66 ms` (`0.017 detik`, jauh di bawah target `3 detik`)
   - `announcements_ms = 2.89 ms`
   - Catatan lingkungan Cloud: pengukuran wall-clock `APP_MODE=supabase` interaktif tidak dijalankan ulang pada gelombang ini karena autentikasi user dilakukan langsung di sesi desktop pengguna.
4. **Kebersihan Workspace (`git diff --check` & Keamanan):**
   - `git diff --check` keluar dengan kode `0`.
   - `DOTENV_EXISTS=False`; tidak ada secret/API key, file `.env`, atau `service_role` di repository maupun log.
   - Tidak ada perubahan pada database produksi, `supabase/seed.sql`, `mock_data.py` baris game, maupun `supabase/migrations/`; Public Signup tetap `DISABLED`.
