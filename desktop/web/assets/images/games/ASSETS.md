# Game Artwork Assets & Official Sources (`desktop/web/assets/images/games/`)

Dokumen ini mencatat konfigurasi artwork resmi game pada aplikasi Turnamen.in serta aset SVG lokal yang dipertahankan sebagai fallback offline/error.

## Daftar Game & Sumber Resmi (Wave 6.10)

| Game UUID (`games.id`) | Slug (`games.slug`) | Nama Game | Sumber Resmi Terverifikasi | Fallback Lokal (`assets/images/games/`) |
| :--- | :--- | :--- | :--- | :--- |
| `22222222-2222-4222-8222-222222222201` | `mobile-legends` | Mobile Legends: Bang Bang | `https://akmweb.youngjoygame.com/web/gms/image/c3d1596795b86dc26e5f1ef2d48c3dfd.jpg` (MOONTON Official `mobilelegends.com`, `600x315` JPEG) | `mobile-legends.svg` |
| `22222222-2222-4222-8222-222222222202` | `valorant` | VALORANT | `https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/a3d06721391f4c274e588c380ca6903c8b3e129e-1920x1080.jpg` (Riot Games Official `playvalorant.com`, `1920x1080` JPEG) | `valorant.svg` |
| `22222222-2222-4222-8222-222222222203` | `ea-sports-fc` | EA Sports FC 25 | `https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2669320/capsule_616x353.jpg` (Steam Store Official App ID `2669320`, `616x353` JPEG) | `ea-sports-fc.svg` |
| *(Game lain tanpa artwork terverifikasi)* | `default-arena` | Game Baru / Tidak Dikenal | Tidak ada substitusi artwork game lain | `default-arena.svg` |

## Mekanisme Pemetaan, Lazy Loading & Fallback

1. Seluruh pemetaan dipusatkan di `GAME_ARTWORK_BY_ID`, `GAME_ARTWORK_REGISTRY`, `resolveGameArtwork(game)`, `renderGameArtwork()`, dan `renderGameChip()` dalam `desktop/web/assets/js/components/ui-components.js`.
2. Seluruh `<img>` memakai `loading="lazy"`, `decoding="async"`, `referrerpolicy="no-referrer"`, serta `object-fit: cover` pada kontainer berasio `16:9`.
3. `ARTWORK_CACHE` mencatat status `"loaded"` dan `"failed"` per URL selama sesi berjalan. Apabila URL resmi gagal dimuat (misalnya mode offline), `handleArtworkError()` langsung beralih ke fallback lokal lalu SVG inline jika diperlukan.
