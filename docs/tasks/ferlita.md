# Instruksi Tugas Mandiri: FERLITA (Project Coordinator & UI/UX Designer)

---

## 1. Identitas dan Tanggung Jawab Anggota
- **Nama Anggota:** Ferlita
- **Peran:** Project Coordinator & UI/UX Designer
- **Branch Resmi:** `feature/ferlita-ui-ux`
- **Tanggung Jawab Utama:**
  - Mengkoordinasikan progres kelompok dan menjaga kesepakatan desain/kontrak antaranggota.
  - Menetapkan rancangan visual (*design system*) dan pengalaman pengguna aplikasi desktop Turnamen.in.
  - Mengembangkan dan menyempurnakan layout desktop, dashboard, halaman login, navigasi, halaman turnamen, peserta/registrasi, manajemen tim, manajemen pertandingan, bracket, pengumuman, laporan, dan profil.
  - Menjaga konsistensi visual dan keterbacaan informasi di seluruh halaman.

## 2. Tujuan Pekerjaan
Menghasilkan antarmuka desktop **Turnamen.in** bertema *Modern Dark Esports Management Dashboard* yang bersih, mudah dipahami panitia maupun pemain, memiliki komponen UI yang konsisten, menampilkan indikator jelas saat mode simulasi (`APP_MODE=mock`), dan terhubung secara rapi ke `window.TurnamenAPI`.

## 3. Daftar Tugas Terperinci
1. Meninjau dan menyempurnakan dokumen arahan visual [`DESIGN.md`](../../DESIGN.md) serta variabel CSS di `desktop/web/assets/css/variables.css`.
2. Mengembangkan dan memoles komponen dasar di `desktop/web/assets/css/components.css` dan `desktop/web/assets/js/components/ui-components.js`:
   - Sidebar & Topbar.
   - Dashboard summary cards.
   - Data tables dengan pencarian dan filter status.
   - Modal / dialog interaktif.
   - Forms input dengan umpan balik validasi.
   - Status badges (`ongoing`, `open_registration`, `completed`, `approved`, `pending`, `rejected`, `scheduled`, `bye`).
   - Toast notifications.
   - State tampilan: *Loading*, *Empty*, *Error*, dan *Success*.
3. Menyempurnakan 10 halaman utama di `desktop/web/index.html`, `desktop/web/pages/`, dan `desktop/web/assets/js/pages/app-pages.js`:
   - Login, Dashboard, Tournament List, Tournament Detail, Team Management, Match Management, Bracket (8 tim), Announcements, Reports, dan User Profile.
4. Memastikan tidak ada tombol aktif yang mati/palsu; setiap aksi harus menjalankan fungsi nyata melalui `TurnamenAPI` atau memberi keterangan status placeholder yang jelas.

## 4. Folder yang Menjadi Tanggung Jawab
- `desktop/web/pages/`
- `desktop/web/assets/css/`
- `desktop/web/assets/images/`
- `desktop/web/assets/js/components/`
- `desktop/web/assets/js/pages/`
- `DESIGN.md`

## 5. File yang Harus Dibuat / Diubah
- `DESIGN.md`
- `desktop/web/index.html`
- `desktop/web/assets/css/variables.css`
- `desktop/web/assets/css/layout.css`
- `desktop/web/assets/css/components.css`
- `desktop/web/assets/js/components/ui-components.js`
- `desktop/web/assets/js/pages/app-pages.js`
- `desktop/web/pages/*.html` (template referensi modular per halaman)

## 6. Batas File yang Tidak Boleh Diubah Tanpa Koordinasi
- `desktop/launcher/*`, `desktop/bridge/*`, `desktop/web/assets/js/core/*`, dan `run.py` (Milik **Fikri**).
- `supabase/*`, `backend/modules/auth/*`, dan `backend/repositories/*` (Milik **Habil**).
- `backend/modules/tournaments/*`, `backend/modules/teams/*`, dan `backend/modules/matches/*` (Milik **Adriel**).
- `backend/api/*`, `backend/modules/reports/*`, `backend/modules/announcements/*`, dan `tests/*` (Milik **Anisa**).

## 7. Dependensi Modul
- Bergantung pada `window.TurnamenConfig`, `window.TurnamenAPI`, dan `window.TurnamenBridge` di `desktop/web/assets/js/core/` yang disediakan Fikri.
- Mengonsumsi struktur JSON yang didefinisikan pada [`docs/contracts/frontend-contract.md`](../contracts/frontend-contract.md) dan [`docs/contracts/api-contract.md`](../contracts/api-contract.md).

## 8. Kontrak Input / Output
- **Input ke UI:** Objek respons `{ success: true, message: "...", data: ... }` dari `window.TurnamenAPI`.
- **Output dari UI:** Pemanggilan fungsi async pada `window.TurnamenAPI` (mis. `TurnamenAPI.createTournament(payload)`, `TurnamenAPI.submitMatchResult(matchId, payload)`) dengan payload yang telah divalidasi di form.

## 9. Mock Data yang Tersedia
Dalam `APP_MODE=mock`, UI langsung mendapatkan data konsisten tanpa perlu menunggu Supabase aktif:
- **5 Akun Role:** `super_admin`, `organizer`, `committee`, `team_captain`, `player` (dapat diganti langsung dari *Role Switcher* di Topbar atau halaman Login).
- **3 Game:** Mobile Legends: Bang Bang, VALORANT, EA Sports FC 25.
- **2 Turnamen:** *Nusantara Campus Cup 2026: MLBB Series* (`ongoing`, 8 tim) dan *Jakarta Tactical Clash: VALORANT Open 2026* (`open_registration`).
- **8 Tim & 16 Pemain:** Garuda Esports, Sriwijaya Vanguard, Majapahit Titans, Borneo Phantoms, Pasundan Wolves, Celebes Kraken, Mataram Knights, Dewata Phoenix.
- **Bracket 8 Tim:** 4 pertandingan Quarter Final (3 selesai, 1 terjadwal), 2 Semi Final, 1 Grand Final.

## 10. Cara Menjalankan Modul
```powershell
# 1. Aktifkan virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Jalankan aplikasi desktop + API lokal dalam mock mode
python run.py

# Alternatif: Jika ingin membuka di browser Chrome/Edge secara langsung saat mengedit CSS/HTML:
python run.py --api-only
# Lalu buka http://127.0.0.1:5000 di browser
```

## 11. Skenario Pengujian
1. **Navigasi 10 Halaman:** Klik seluruh menu di Sidebar dan pastikan setiap halaman tampil tanpa error di Console.
2. **Indikator Mock Mode:** Pastikan badge `MOCK MODE (SIMULASI LOKAL)` terlihat jelas di Topbar.
3. **Simulasi Role & Login:** Coba berganti role di halaman Login atau Topbar, lalu periksa perubahan informasi di halaman User Profile.
4. **Interaksi Bracket & Skor:** Buka halaman **Match Management**, masukkan skor untuk Quarter Final #4 (Mataram Knights vs Dewata Phoenix, mis. `2 - 1`), klik **Sahkan Skor**, lalu buka halaman **Bracket** dan pastikan pemenang otomatis masuk ke Semi Final #2.
5. **State Komponen:** Uji pencarian turnamen dengan kata kunci yang tidak ada untuk memastikan *Empty State* tampil dengan rapi.

## 12. Acceptance Criteria
- Seluruh 10 halaman awal tersedia, rapi, dan dapat dibuka dalam `APP_MODE=mock`.
- Palet warna dan tipografi di `DESIGN.md` telah ditinjau dan diterapkan secara konsisten.
- Semua angka skor dan tabel menggunakan `tabular-nums`.
- Tidak ada tombol aktif yang tidak berfungsi tanpa penjelasan placeholder yang jelas.

## 13. Checklist Pekerjaan
- [ ] Meninjau dan menyetujui `DESIGN.md`.
- [ ] Memastikan variabel CSS di `variables.css` sesuai kesepakatan desain.
- [ ] Memverifikasi tampilan 10 halaman pada resolusi desktop Windows.
- [ ] Menguji alur input turnamen baru, tim baru, pengumuman, dan update skor dari UI.
- [ ] Memeriksa kontras teks dan fokus keyboard (`:focus-visible`).

## 14. Git Branch Assignment & Workflow

Lihat panduan lengkap Git di [`docs/GIT_WORKFLOW.md`](../GIT_WORKFLOW.md).

### 1. Nama Branch Resmi
`feature/ferlita-ui-ux`

### 2. Tanggung Jawab pada Branch Ini
Mengembangkan dan menyempurnakan arahan desain (`DESIGN.md`), template halaman HTML (`desktop/web/index.html`, `desktop/web/pages/`), stylesheet (`desktop/web/assets/css/`), aset visual (`desktop/web/assets/images/`), serta komponen dan logika tampilan halaman (`desktop/web/assets/js/components/`, `desktop/web/assets/js/pages/`).

### 3. Instruksi Membuat atau Berpindah ke Branch
- **Membuat branch pertama kali (jika belum ada di lokal maupun remote):**
  ```powershell
  git fetch origin
  git switch main
  git pull --ff-only origin main
  git switch -c feature/ferlita-ui-ux
  git push -u origin feature/ferlita-ui-ux
  ```
- **Jika branch sudah tersedia di remote (`origin`), tetapi belum ada di lokal:**
  ```powershell
  git fetch origin
  git switch --track origin/feature/ferlita-ui-ux
  ```
- **Jika branch sudah tersedia secara lokal di komputer Anda:**
  ```powershell
  git switch feature/ferlita-ui-ux
  git pull --ff-only
  ```

### 4. Perintah Git untuk Menyimpan Pekerjaan
Sebelum menyimpan pekerjaan, pastikan pengujian tetap lulus:
```powershell
pytest
python run.py --check
git status
git add DESIGN.md desktop/web/
git commit -m "feat(ui): improve tournament dashboard and design system"
```

### 5. Instruksi Push ke Branch Milik Ferlita
Jangan melakukan push langsung ke `main` dan jangan menggunakan `--force`:
```powershell
git push origin feature/ferlita-ui-ux
```
*(Atau cukup `git push` jika upstream `-u` sudah diatur).*

### 6. Instruksi Membuat Pull Request ke `main`
1. Buka repository GitHub: `https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`.
2. Pilih branch `feature/ferlita-ui-ux` lalu klik **`Compare & pull request`**.
3. Pastikan **base** adalah `main` dan **compare** adalah `feature/ferlita-ui-ux`.
4. Tulis ringkasan perubahan UI/UX, daftar file yang diubah, dan hasil pengujian (`pytest` serta pengecekan tampilan).
5. Klik **`Create pull request`** dan tunggu review sebelum merge.
6. Untuk menyinkronkan branch dengan pembaruan terbaru dari `main`:
   ```powershell
   git fetch origin
   git switch feature/ferlita-ui-ux
   git merge origin/main
   ```

### 7. Aturan Koordinasi Lintas Modul
- Apabila perubahan UI pada `desktop/web/index.html` atau `app-pages.js` membutuhkan metode baru pada `window.TurnamenAPI` atau `window.TurnamenBridge`, koordinasikan terlebih dahulu dengan **Fikri** (`feature/fikri-eel`).
- Apabila tampilan membutuhkan field tambahan dari response JSON `/api/v1/*`, koordinasikan dengan **Anisa** (`feature/anisa-api-report`) dan perbarui kontrak di `docs/contracts/frontend-contract.md` serta `docs/contracts/api-contract.md`.

## 15. Agent Skills yang Wajib Dibaca Berdasarkan Addendum
Sebelum meminta bantuan AI Agent, pastikan agent membaca `AGENTS.md`, file tugas ini (`docs/tasks/ferlita.md`), `docs/GIT_WORKFLOW.md`, dan memuat skill berikut dari `.agents/skills/`:
- **Wajib:**
  - `antislop` (`.agents/skills/antislop/SKILL.md`)
  - `antislop-ui` (`.agents/skills/antislop-ui/SKILL.md`)
  - `antislop-human` (`.agents/skills/antislop-human/SKILL.md`)
  - `antislop-copywriting` (`.agents/skills/antislop-copywriting/SKILL.md`)
  - `turnamen-project-standards` (`.agents/skills/turnamen-project-standards/SKILL.md`)
  - `turnamen-frontend-ui` (`.agents/skills/turnamen-frontend-ui/SKILL.md`)
  - `turnamen-quality-gates` (`.agents/skills/turnamen-quality-gates/SKILL.md`)
- **Opsional:**
  - `frontend-design` (`.agents/skills/frontend-design/SKILL.md`)
  - `tdd` (`.agents/skills/tdd/SKILL.md`)
