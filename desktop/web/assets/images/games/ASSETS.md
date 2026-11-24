# Game Artwork Assets & Licensing (`desktop/web/assets/images/games/`)

Dokumen ini mencatat seluruh aset ilustrasi cabang game lokal untuk Turnamen.in (`Futuristic Arena`), pemetaan terhadap slug game dari REST API, hasil peninjauan lisensi aset penerbit, serta panduan penggantian *drop-in* ke format `.webp` di masa mendatang.

## Evaluasi Lisensi Sumber Aset Resmi

Sebelum memilih sumber visual untuk repository ini, dilakukan pemeriksaan terhadap ketentuan penggunaan aset resmi masing-masing penerbit:

1. **Mobile Legends: Bang Bang (Moonton):** Splash art, hero art, logo, dan aset resmi Moonton bersifat *proprietary* tanpa izin redistribusi ulang ke dalam repository open-source publik tanpa perjanjian lisensi tertulis.
2. **EA Sports FC 25 (Electronic Arts):** Press kit dan media kit EA ditujukan untuk liputan pers/editorial dan bukan untuk dibundel ulang sebagai file distribusi bebas dalam repository source code tanpa perjanjian khusus.
3. **VALORANT (Riot Games):** Kebijakan *Legal Jibber Jabber* membolehkan proyek komunitas non-komersial dengan disclaimer dan atribut kepemilikan Riot Games, namun tetap melarang klaim kepemilikan logo resmi maupun pembundelan bebas tanpa konteks aset resmi CDN; sementara Turnamen.in dilarang melakukan *hotlink* eksternal demi keandalan lokal offline-first.

**Keputusan Teknis:** Seluruh file pada folder ini adalah ilustrasi SVG kustom bergaya *promotional key art* **original buatan proyek Turnamen.in** (bebas klaim merek penerbit, 0 *hotlink* eksternal, dapat berjalan penuh pada mode `APP_MODE=mock` maupun `APP_MODE=supabase` tanpa internet).

## Daftar Aset Lokal Saat Ini

| Slug API (`games.slug`) | Nama Game | File Aset | Format | Rasio & Dimensi | Lisensi & Sumber |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mobile-legends` | Mobile Legends: Bang Bang | `mobile-legends.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi *promotional key art* kustom original Turnamen.in (MOBA Arcane Nexus & Energy River) |
| `valorant` | VALORANT | `valorant.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi *promotional key art* kustom original Turnamen.in (Tactical Courtyard & Holo Barrier) |
| `ea-sports-fc` | EA Sports FC 25 | `ea-sports-fc.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi *promotional key art* kustom original Turnamen.in (Night Floodlit Stadium & Match Ball) |
| *(Fallback umum)* | Game Baru / Lainnya | `default-arena.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi *promotional key art* arena kejuaraan original Turnamen.in |

## Arsitektur Siap-WebP (Zero Business-Logic Changes)

1. Seluruh pemetaan aset terpusat pada `GAME_ARTWORK_REGISTRY` dan `resolveGameArtwork(game)` di `desktop/web/assets/js/components/ui-components.js`.
2. Seluruh kartu dan banner di `desktop/web/assets/js/pages/app-pages.js` memanggil `window.TurnamenUI.renderGameArtwork(game, labelOverride, options)` tanpa pernah melakukan *hardcode* path file.
3. Tidak ada teks atau logo yang tertanam permanen di dalam file SVG; label kategori dan judul game selalu dirender sebagai HTML di atas *contrast scrim*.
4. `renderGameArtwork()` menyertakan *fallback* SVG inline apabila elemen `<img>` gagal dimuat.

## Cara Mengganti ke Aset `.webp` di Masa Mendatang

1. Simpan file `.webp` berukuran `960x540` (rasio `16:9`, optimal `< 180 KB`) ke folder ini dengan nama sesuai slug game (`mobile-legends.webp`, `valorant.webp`, `ea-sports-fc.webp`, `default-arena.webp`).
2. Perbarui properti `src` pada `GAME_ARTWORK_REGISTRY` di `desktop/web/assets/js/components/ui-components.js` dari `.svg` ke `.webp`.
3. Tidak diperlukan perubahan pada `app-pages.js`, backend Flask, skema Supabase, ataupun kontrak REST API.
