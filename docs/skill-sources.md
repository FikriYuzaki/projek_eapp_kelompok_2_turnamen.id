# Sumber Agent Skills & Repository Referensi Teknis — Turnamen.in

Dokumen ini mencatat seluruh **External Agent Skills**, **Custom Turnamen.in Skills**, dan **Repository Referensi Teknis** yang dipasang atau dirujuk di dalam Starter Repository Turnamen.in sesuai `TURNAMEN-IN-AGENT-SKILLS-ADDENDUM.md`.

---

## 1. Daftar External Agent Skills (Terpasang di `.agents/skills/`)

Seluruh external skill dipasang pada level proyek (*project-level copy mode*) menggunakan `npx skills add <repo> --skill <name> -a antigravity --copy -y` dan tercatat pada `skills-lock.json` agar langsung tersedia bagi seluruh 5 anggota setelah melakukan `git clone` atau `git pull origin main`.

| No | Nama Skill | Repository Asal | URL Repository | Folder Skill | Versi / Commit SHA | Lisensi | Anggota Pengguna | Fungsi Utama | Status Instalasi |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `antislop` | `miqdadbadjuber/anti-slop` | <https://github.com/miqdadbadjuber/anti-slop> | `.agents/skills/antislop/` | `v3.2.28` (`4520786d3dff09eb295a2c563c7fab50063f00fb`) | MIT | Seluruh Anggota | Filter inti pencegah pola generik AI (*AI slop*) | Terpasang & Terverifikasi (beserta `VERSION` & `LICENSE`) |
| 2 | `antislop-ui` | `miqdadbadjuber/anti-slop` | <https://github.com/miqdadbadjuber/anti-slop> | `.agents/skills/antislop-ui/` | `v3.2.28` (`4520786d3dff09eb295a2c563c7fab50063f00fb`) | MIT | Ferlita | Standar kualitas visual UI, warna, layout, dan performa halaman | Terpasang & Terverifikasi |
| 3 | `antislop-human` | `miqdadbadjuber/anti-slop` | <https://github.com/miqdadbadjuber/anti-slop> | `.agents/skills/antislop-human/` | `v3.2.28` (`4520786d3dff09eb295a2c563c7fab50063f00fb`) | MIT | Ferlita, Habil | Aksesibilitas, kontras warna, fokus keyboard, dan kejelasan state interaksi | Terpasang & Terverifikasi |
| 4 | `antislop-code` | `miqdadbadjuber/anti-slop` | <https://github.com/miqdadbadjuber/anti-slop> | `.agents/skills/antislop-code/` | `v3.2.28` (`4520786d3dff09eb295a2c563c7fab50063f00fb`) | MIT | Fikri, Habil, Adriel, Anisa | Kebersihan komentar kode: mencegah komentar bising dan mempertahankan komentar bernilai | Terpasang & Terverifikasi |
| 5 | `antislop-copywriting` | `miqdadbadjuber/anti-slop` | <https://github.com/miqdadbadjuber/anti-slop> | `.agents/skills/antislop-copywriting/` | `v3.2.28` (`4520786d3dff09eb295a2c563c7fab50063f00fb`) | MIT | Ferlita, Anisa | Penulisan teks UI, tombol CTA, dan pesan response API yang jernih | Terpasang & Terverifikasi |
| 6 | `supabase` | `supabase/agent-skills` | <https://github.com/supabase/agent-skills> | `.agents/skills/supabase/` | `c9be0e931b7930f7d02126d04774d904c381e7d7` | MIT | Habil, Fikri, Anisa | Panduan ekosistem Supabase (Database, Auth, Storage, Realtime, RLS) | Terpasang & Terverifikasi |
| 7 | `supabase-postgres-best-practices` | `supabase/agent-skills` | <https://github.com/supabase/agent-skills> | `.agents/skills/supabase-postgres-best-practices/` | `c9be0e931b7930f7d02126d04774d904c381e7d7` | MIT | Habil | Best practice desain skema PostgreSQL, migrasi, indexing, dan kebijakan RLS | Terpasang & Terverifikasi |
| 8 | `hexagonal-python` | `Remy349/skills` | <https://github.com/Remy349/skills> | `.agents/skills/hexagonal-python/` | `5d9eae132afea72518ba0f1f41919f9e37964362` | MIT | Fikri, Anisa | Pemisahan Ports & Adapters, service layer, repository boundary, dan REST API (diadaptasi tanpa SQLAlchemy) | Terpasang & Terverifikasi |
| 9 | `tdd` | `dgalarza/agent-skills` | <https://github.com/dgalarza/agent-skills> | `.agents/skills/tdd/` | `f0968fe98fd66f43ea4cda4f2b77c69bda273700` | MIT | Seluruh Anggota | Siklus pengembangan *Red-Green-Refactor* dan pemilihan level pengujian | Terpasang & Terverifikasi |
| 10 | `team-code-review` | `dgalarza/agent-skills` | <https://github.com/dgalarza/agent-skills> | `.agents/skills/team-code-review/` | `f0968fe98fd66f43ea4cda4f2b77c69bda273700` | MIT | Fikri, Adriel, Anisa | Audit kualitas perubahan kode dan verifikasi regresi sebelum integrasi | Terpasang & Terverifikasi |
| 11 | `frontend-design` | `Junaid-PK/frontend-design-skill` | <https://github.com/Junaid-PK/frontend-design-skill> | `.agents/skills/frontend-design/` | `5623a21235aa7949b3968dd48f54e147d31ce2b2` | Apache-2.0 | Ferlita (Opsional) | Referensi tata letak dashboard, hierarki visual, dan konsistensi komponen | Terpasang & Terverifikasi |

> **Catatan tentang `antislop-layoutmobile`:** Sengaja **tidak dipasang** sesuai spesifikasi karena Turnamen.in merupakan aplikasi desktop-first untuk Windows 10/11.  
> **Catatan tentang `npx antislop-ai`:** CLI interaktif `npx antislop-ai` membutuhkan TTY interaktif; seluruh 5 skill Anti-Slop beserta file `VERSION` (`3.2.28`), `LICENSE` (MIT), dan pointer resmi di `AGENTS.md` telah dipasang secara non-interaktif melalui `npx skills add miqdadbadjuber/anti-slop` dari repositori resmi yang sama dan terverifikasi di `skills-lock.json`.

---

## 2. Daftar Custom Turnamen.in Skills (Terpasang di `.agents/skills/`)

Custom skills berikut dibuat khusus untuk arsitektur, kontrak data, dan pembagian tugas proyek Turnamen.in:

| No | Nama Skill | Folder Skill | Anggota Pengguna | Fokus Utama | Status |
| :- | :--- | :--- | :--- | :--- | :--- |
| 1 | `turnamen-project-standards` | `.agents/skills/turnamen-project-standards/` | Seluruh Anggota | Arsitektur resmi, konvensi kode, kepemilikan modul, dan alur Single-Main | Tersedia & Valid |
| 2 | `turnamen-frontend-ui` | `.agents/skills/turnamen-frontend-ui/` | Ferlita | Design system dark dashboard, komponen UI, state halaman, dan kontrak API client | Tersedia & Valid |
| 3 | `turnamen-python-eel` | `.agents/skills/turnamen-python-eel/` | Fikri | Lifecycle Python Eel + Flask launcher, JS-Python bridge, konfigurasi, dan keamanan lokal | Tersedia & Valid |
| 4 | `turnamen-supabase-security` | `.agents/skills/turnamen-supabase-security/` | Habil | Skema 12 tabel PostgreSQL, Supabase Auth, RBAC 5 role, RLS, dan repository pattern | Tersedia & Valid |
| 5 | `turnamen-bracket-engine` | `.agents/skills/turnamen-bracket-engine/` | Adriel | Siklus turnamen, registrasi tim, algoritma Single Elimination, bye, dan validasi skor | Tersedia & Valid |
| 6 | `turnamen-flask-api` | `.agents/skills/turnamen-flask-api/` | Anisa | Struktur blueprint `/api/v1`, validasi request, format JSON standar, laporan, dan testing | Tersedia & Valid |
| 7 | `turnamen-quality-gates` | `.agents/skills/turnamen-quality-gates/` | Seluruh Anggota | Standar unit/integration test, contract testing, dan Definition of Done | Tersedia & Valid |

---

## 3. Repository Referensi Teknis Resmi (Non-Skill Reference Sources)

Repository di bawah ini digunakan sebagai rujukan dokumentasi arsitektur, keamanan, dan pustaka resmi (bukan diinstal sebagai folder skill):

| Sumber Referensi | URL Resmi | Anggota Terkait | Cakupan Referensi |
| :--- | :--- | :--- | :--- |
| **Python Eel** | <https://github.com/python-eel/Eel> | Fikri | Lifecycle aplikasi desktop, `@eel.expose`, bridge JS-Python, batasan pemeliharaan |
| **Flask** | <https://github.com/pallets/flask> | Anisa, Fikri | Application factory, Blueprint, routing, request validation, error handler |
| **pytest** | <https://github.com/pytest-dev/pytest> | Seluruh Anggota | Unit testing, fixtures, parameterized test, Flask test client |
| **OWASP Cheat Sheet Series** | <https://github.com/OWASP/CheatSheetSeries> | Habil, Fikri, Anisa | Autentikasi, otorisasi RBAC, penyimpanan password, validasi input, manajemen secret |
| **Supabase & Docs** | <https://github.com/supabase/supabase> / <https://supabase.com/docs> | Habil, Fikri, Anisa | Konfigurasi PostgreSQL, Auth, RLS, Storage, dan Realtime |

---

## 4. Aturan Lisensi & Pembaruan Skill

1. **Jangan Mengubah Isi External Skill Secara Langsung:** Seluruh penyesuaian spesifik proyek diletakkan pada Custom Skill `turnamen-*` atau `DESIGN.md`.
2. **Memulihkan atau Memperbarui Skill:**
   - Untuk memeriksa daftar skill yang terpasang: `npx skills list`
   - Untuk memulihkan dari `skills-lock.json`: `npx skills experimental_install`
   - Untuk memperbarui skill eksternal setelah meninjau upstream: `npx skills update -p`
