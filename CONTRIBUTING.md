# Panduan Kontribusi: Turnamen.in

Proyek **Turnamen.in** dikerjakan secara paralel oleh **5 anggota kelompok** menggunakan sistem **branch terpisah untuk setiap anggota** dan **`main` sebagai branch integrasi utama**. Panduan lengkap penggunaan Git langkah demi langkah juga tersedia di [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md).

> [!IMPORTANT]
> Setiap anggota wajib bekerja pada branch khusus miliknya. Jangan mengerjakan fitur langsung pada branch `main`, jangan mengubah kontrak bersama secara sepihak, dan jangan pernah menggunakan `git push --force`.

---

## 1. Pembagian Kepemilikan Folder (Module Ownership)

Setiap anggota bertanggung jawab penuh pada area kerjanya masing-masing agar tidak terjadi bentrokan file (*merge conflict*):

| Anggota | Peran | Branch Resmi | Folder Utama |
| :--- | :--- | :--- | :--- |
| **Ferlita** | Project Coordinator & UI/UX Designer | `feature/ferlita-ui-ux` | `desktop/web/pages/`, `desktop/web/assets/css/`, `desktop/web/assets/images/`, `desktop/web/assets/js/components/`, `desktop/web/assets/js/pages/`, `DESIGN.md` |
| **Fikri** | System Integration & Python Eel Developer | `feature/fikri-eel` | `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py`, `backend/core/` |
| **Habil** | Database & Authentication Developer | `feature/habil-database-auth` | `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/`, `docs/database-schema.md`, `docs/security.md` |
| **Adriel** | Tournament & Match System Developer | `feature/adriel-tournament-match` | `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/`, `tests/unit/test_bracket_engine.py` |
| **Anisa** | REST API, Reporting & Testing Developer | `feature/anisa-api-report` | `backend/app.py`, `backend/api/`, `backend/modules/reports/`, `backend/modules/announcements/`, `tests/`, `docs/api/` |

Kepemilikan folder adalah batas tanggung jawab utama. Apabila suatu perubahan menyentuh folder anggota lain atau mengubah kontrak bersama (`docs/contracts/`), wajib dikoordinasikan terlebih dahulu.

---

## 2. Git Branch Workflow

### A. Fungsi Branch `main` dan Branch Anggota

- **Fungsi Branch `main`:**
  Branch `main` adalah pusat integrasi resmi seluruh pekerjaan tim. Branch ini hanya boleh berisi kode yang sudah diperiksa, lulus pengujian otomatis (`pytest`), dan siap dijalankan oleh seluruh anggota.
- **Fungsi Branch Masing-Masing Anggota:**
  Setiap anggota memiliki satu branch kerja khusus (`feature/ferlita-ui-ux`, `feature/fikri-eel`, `feature/habil-database-auth`, `feature/adriel-tournament-match`, dan `feature/anisa-api-report`) sebagai ruang kerja mandiri untuk mengembangkan, menguji, dan menyimpan fitur sesuai perannya sebelum digabungkan ke `main`.

### B. Aturan Kerja Menggunakan Branch

1. Setiap anggota wajib bekerja pada branch khusus miliknya.
2. Branch `main` hanya untuk kode yang sudah diperiksa dan siap diintegrasikan.
3. Anggota tidak boleh mengerjakan perubahan fitur secara langsung pada `main`.
4. Setiap anggota hanya boleh melakukan `git push` ke branch miliknya sendiri.
5. Penggabungan kode ke `main` harus melalui **Pull Request (PR)** di GitHub.
6. Dilarang menggunakan `git push --force`.
7. Jangan menghapus branch anggota ketika masih digunakan untuk pengembangan.
8. Jangan mengubah atau menghapus commit awal repository (`29350bd`).

### C. Cara Membuat atau Berpindah ke Branch Anggota

Saat pertama kali menyiapkan branch kerja (ketika branch belum ada di lokal maupun di remote):

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c <nama-branch-anggota>
git push -u origin <nama-branch-anggota>
```

Daftar nama branch anggota:
- Ferlita: `feature/ferlita-ui-ux`
- Fikri: `feature/fikri-eel`
- Habil: `feature/habil-database-auth`
- Adriel: `feature/adriel-tournament-match`
- Anisa: `feature/anisa-api-report`

**Catatan penting untuk pemula (perbedaan kondisi branch):**
- **Kondisi 1 (Branch belum ada di lokal maupun remote):** Gunakan `git switch -c <nama-branch>` **hanya satu kali** saat branch belum pernah dibuat sama sekali.
- **Kondisi 2 (Branch sudah tersedia di remote GitHub, tetapi belum ada di lokal):** Jangan gunakan `-c`. Jalankan perintah eksplisit berikut untuk mengambil dan melacak branch remote:
  ```powershell
  git fetch origin
  git switch --track origin/<nama-branch-anggota>
  ```
- **Kondisi 3 (Branch sudah tersedia secara lokal di komputer Anda):** Cukup berpindah ke branch tersebut lalu tarik pembaruan terbaru:
  ```powershell
  git switch <nama-branch-anggota>
  git pull --ff-only
  ```

### D. Cara Commit dan Push Pekerjaan Harian

1. Sebelum mulai mengedit kode, pastikan Anda berada di branch milik sendiri:
   ```powershell
   git status
   git switch <nama-branch-anggota>
   git pull --ff-only
   ```
2. Kembangkan fitur pada folder tanggung jawab Anda dalam mode `APP_MODE=mock`, lalu jalankan pengujian:
   ```powershell
   pytest
   python run.py --check
   ```
3. Simpan perubahan (*commit*) dan unggah (*push*) ke branch Anda:
   ```powershell
   git status
   git add .
   git commit -m "feat(scope): deskripsi singkat perubahan"
   git push
   ```

Format pesan commit yang disarankan:
- `feat(ui): improve tournament dashboard`
- `feat(desktop): refine eel launcher lifecycle`
- `feat(auth): enforce role permission checks on repository`
- `feat(bracket): handle bye advancement for 6 teams`
- `feat(api): add tournament standings report endpoint`

### E. Cara Menyinkronkan Branch dengan `main`

Ketika ada pekerjaan anggota lain yang baru selesai digabungkan ke `main`, tarik pembaruan tersebut ke branch Anda agar kode tetap sinkron:

```powershell
git fetch origin
git switch <nama-branch-anggota>
git merge origin/main
```

Setelah proses merge selesai tanpa konflik, jalankan `pytest` lalu unggah ke branch Anda dengan `git push`.

### F. Cara Membuat Pull Request (PR)

Setelah fitur pada branch Anda selesai dan seluruh pengujian lulus:

1. Buka repository GitHub: `https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`.
2. Pilih branch milik Anda.
3. Klik tombol **`Compare & pull request`**.
4. Pastikan branch tujuan (**base**) adalah `main` dan branch sumber (**compare**) adalah branch milik Anda.
5. Tulis ringkasan perubahan yang mudah dipahami.
6. Cantumkan daftar file atau fitur yang diubah.
7. Cantumkan hasil pengujian (`pytest` dan `python run.py --check`).
8. Klik **`Create pull request`**.
9. Tunggu pemeriksaan dan persetujuan sebelum Pull Request di-merge ke `main`.
10. Setelah Pull Request di-merge, perbarui `main` lokal Anda:
    ```powershell
    git switch main
    git pull --ff-only origin main
    git switch <nama-branch-anggota>
    git merge main
    ```

### G. Cara Menangani Konflik Kode (Merge Conflict)

Konflik dapat dicegah dengan mematuhi kepemilikan folder, tidak mengubah kontrak bersama (`docs/contracts/`) tanpa diskusi, serta berkoordinasi terlebih dahulu sebelum menyentuh file konfigurasi atau file milik anggota lain.

Apabila terjadi konflik saat menjalankan `git merge origin/main`:

1. Periksa `git status` untuk melihat file mana yang mengalami konflik.
2. Buka dan baca file yang mengalami konflik, lalu perhatikan bagian di antara `<<<<<<<`, `=======`, dan `>>>>>>>`.
3. Bandingkan perubahan dari branch Anda dengan perubahan dari `origin/main`.
4. Diskusikan dengan pemilik perubahan terkait jika Anda ragu. Jangan asal menghapus kode milik anggota lain.
5. Selesaikan konflik dengan mempertahankan kode yang valid dan menghapus baris penanda `<<<<<<<`, `=======`, serta `>>>>>>>`.
6. Jalankan pengujian (`pytest` dan `python run.py --check`) untuk memastikan aplikasi tetap berjalan normal.
7. Simpan hasil penyelesaian konflik:
   ```powershell
   git add <file-yang-diselesaikan>
   git commit -m "chore(merge): resolve merge conflict with main"
   git push
   ```

---

## 3. Penggunaan GitHub Desktop (Opsional untuk Non-Terminal)

Bagi anggota yang lebih nyaman menggunakan antarmuka grafis (**GitHub Desktop**):
1. Pastikan **Current Branch** berada pada branch milik Anda (misalnya `feature/ferlita-ui-ux`), **bukan** di `main`.
2. Klik **Fetch origin** / **Pull origin** sebelum mulai mengedit file.
3. Untuk menyinkronkan dengan `main`, klik menu **Branch -> Merge into current branch...**, lalu pilih `main`.
4. Periksa daftar **Changes** di panel kiri: pastikan hanya file milik modul Anda yang dicentang, dan tidak ada file `.env` atau kredensial rahasia.
5. Isi **Summary** (misalnya `feat(ui): desain kartu turnamen pada dashboard`), klik **Commit to `<nama-branch-anda>`**, lalu klik **Push origin**.
6. Klik **Preview Pull Request** / **Create Pull Request** untuk membuka halaman pembuatan Pull Request ke `main` di GitHub.

---

## 4. AI Agent Skills & Engineering Standards

Seluruh anggota dan AI Agent yang membantu di repository ini wajib mematuhi standar yang didefinisikan pada [`AGENTS.md`](AGENTS.md) dan folder `.agents/skills/`.

### A. Daftar Skill Project-Level
Folder `.agents/skills/` disimpan langsung di dalam Git agar seluruh anggota mendapatkan aturan yang sama setelah melakukan `git clone` atau sinkronisasi dari `main`.
- **External Skills**:
  - Anti-Slop (`antislop`, `antislop-ui`, `antislop-human`, `antislop-code`, `antislop-copywriting`)
  - Supabase (`supabase`, `supabase-postgres-best-practices`)
  - Arsitektur Python (`hexagonal-python`)
  - Engineering Workflow (`tdd`, `team-code-review`)
  - Desain Frontend (`frontend-design`)
- **Custom Turnamen.in Skills**:
  - `turnamen-project-standards`
  - `turnamen-frontend-ui`
  - `turnamen-python-eel`
  - `turnamen-supabase-security`
  - `turnamen-bracket-engine`
  - `turnamen-flask-api`
  - `turnamen-quality-gates`

### B. Pemetaan Skill per Anggota
| Anggota | Branch Resmi | Skill Wajib | Skill Tambahan / Opsional |
| :--- | :--- | :--- | :--- |
| **Ferlita** | `feature/ferlita-ui-ux` | `antislop`, `antislop-ui`, `antislop-human`, `antislop-copywriting`, `turnamen-project-standards`, `turnamen-frontend-ui`, `turnamen-quality-gates` | `frontend-design`, `tdd` |
| **Fikri** | `feature/fikri-eel` | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-python-eel`, `turnamen-quality-gates` | `hexagonal-python`, `tdd`, `team-code-review` |
| **Habil** | `feature/habil-database-auth` | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-supabase-security`, `turnamen-quality-gates` | `supabase`, `supabase-postgres-best-practices`, `tdd` |
| **Adriel** | `feature/adriel-tournament-match` | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-bracket-engine`, `turnamen-quality-gates` | `tdd`, `team-code-review` |
| **Anisa** | `feature/anisa-api-report` | `antislop`, `antislop-code`, `antislop-copywriting`, `turnamen-project-standards`, `turnamen-flask-api`, `turnamen-quality-gates` | `hexagonal-python`, `tdd`, `team-code-review` |

### C. Memulai Sesi AI Agent (Antigravity / AGY) Baru
Saat memulai sesi bersama AI Agent:
1. Pastikan Anda sudah berada pada branch kerja masing-masing (`git switch <nama-branch-anda>`) dan sinkron dengan `origin/main`.
2. Minta agent membaca:
   - `AGENTS.md`
   - `docs/tasks/<nama-anggota>.md`
   - `docs/GIT_WORKFLOW.md`
   - Seluruh `SKILL.md` yang tercantum sebagai skill wajib pada file tugas tersebut.
   - Dokumen kontrak di `docs/contracts/`.
3. Jangan melakukan commit atau push otomatis melalui script tanpa pemeriksaan anggota.
