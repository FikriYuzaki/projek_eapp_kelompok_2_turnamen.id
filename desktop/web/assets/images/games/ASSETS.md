# Game Artwork Assets & Provenance (`desktop/web/assets/images/games/`)

Dokumen ini mencatat seluruh aset ilustrasi cabang game lokal untuk Turnamen.in (`Futuristic Arena`), pemetaan terhadap slug game dari REST API, serta panduan penggantian *drop-in* ke format `.webp` di masa mendatang.

## Daftar Aset Lokal Saat Ini

| Slug API (`games.slug`) | Nama Game | File Aset | Format | Rasio & Dimensi | Lisensi & Sumber |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mobile-legends` | Mobile Legends: Bang Bang | `mobile-legends.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi kustom original untuk Turnamen.in (bukan media kit resmi penerbit) |
| `valorant` | VALORANT | `valorant.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi kustom original untuk Turnamen.in (bukan media kit resmi penerbit) |
| `ea-sports-fc` | EA Sports FC 25 | `ea-sports-fc.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi kustom original untuk Turnamen.in (bukan media kit resmi penerbit) |
| *(Fallback umum)* | Game Baru / Lainnya | `default-arena.svg` | SVG lokal | `16:9` (`960x540`) | Ilustrasi arena esports original untuk Turnamen.in |

## Arsitektur Siap-WebP (Zero Business-Logic Changes)

1. Seluruh pemetaan aset terpusat pada `GAME_ARTWORK_REGISTRY` dan `resolveGameArtwork(game)` di `desktop/web/assets/js/components/ui-components.js`.
2. Halaman UI (`desktop/web/assets/js/pages/app-pages.js`) memanggil `window.TurnamenUI.renderGameArtwork(game, labelOverride, options)` tanpa pernah melakukan *hardcode* path file gambar secara langsung.
3. Tidak ada *hotlink* eksternal ke URL pihak ketiga, sehingga seluruh aplikasi berjalan 100% lokal (`APP_MODE=mock` dan `APP_MODE=supabase`).
4. `renderGameArtwork()` juga menyertakan *fallback* SVG inline apabila elemen `<img>` gagal dimuat.

## Cara Mengganti ke Aset `.webp` di Masa Mendatang

1. Simpan file `.webp` berukuran `960x540` (rasio `16:9`, optimal `< 180 KB`) ke folder ini dengan nama sesuai slug game:
   - `desktop/web/assets/images/games/mobile-legends.webp`
   - `desktop/web/assets/images/games/valorant.webp`
   - `desktop/web/assets/images/games/ea-sports-fc.webp`
   - `desktop/web/assets/images/games/default-arena.webp`
2. Perbarui properti `src` pada `GAME_ARTWORK_REGISTRY` di `desktop/web/assets/js/components/ui-components.js` dari `.svg` ke `.webp` (pertahankan `.svg` pada `svgFallbackSrc` atau inline fallback).
3. Tidak diperlukan perubahan pada `app-pages.js`, backend Flask, skema Supabase, ataupun kontrak REST API.
