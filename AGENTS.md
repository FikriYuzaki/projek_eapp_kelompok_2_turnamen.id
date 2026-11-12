<!-- antislop:start -->
Before writing or editing any code, UI, copy, or comments, load the `antislop` skill at `.agents/skills/antislop/SKILL.md` and the relevant sub-skills (`antislop-ui`, `antislop-human`, `antislop-code`, `antislop-copywriting`) for the task.
<!-- antislop:end -->

# AGENTS.md: Instruksi Global AI Agent Proyek Turnamen.in

Dokumen ini adalah instruksi tingkat root untuk seluruh AI Agent (Antigravity / AGY, Cursor, Claude Code, Codex, dll.) yang bekerja pada repository **Turnamen.in: Esports Tournament Management System**.

---

## 1. Aturan Wajib Seluruh Agent

1. **Ikuti Project Standards:** Setiap agent wajib membaca dan mematuhi `.agents/skills/turnamen-project-standards/SKILL.md`, `.agents/skills/turnamen-quality-gates/SKILL.md`, serta panduan Git di `docs/GIT_WORKFLOW.md` dan `CONTRIBUTING.md`. Note: aturan branch per anggota pada dokumen ini dan `docs/GIT_WORKFLOW.md` menggantikan referensi alur kerja satu branch lama.
2. **Jaga Kepemilikan File (Module Ownership):** Setiap agent hanya boleh memodifikasi file yang berada di bawah tanggung jawab anggota yang sedang dibantu. Jika perubahan lintas modul diperlukan, laporkan terlebih dahulu kepada pengguna dan jangan mengubah kontrak bersama secara sepihak.
3. **Baca Task File Anggota:** Sebelum memulai pekerjaan teknis, baca file tugas anggota terkait di `docs/tasks/<nama-anggota>.md`.
4. **Muat Skill Sesuai Tugas:** Muat hanya skill wajib dan relevan yang tercantum pada pemetaan anggota di bawah. Jangan memuat seluruh skill tambahan yang tidak berkaitan dengan pekerjaan saat ini.
5. **Patuhi Kontrak Bersama (Contract-First):** Semua kode wajib mematuhi kontrak resmi di:
   - `docs/contracts/database-contract.md`
   - `docs/contracts/api-contract.md`
   - `docs/contracts/frontend-contract.md`
   - `docs/contracts/module-contract.md`
   - `docs/contracts/role-permissions.md`
6. **Semua Perubahan Harus Dapat Diuji:** Pastikan aplikasi selalu dapat dijalankan dan diuji dalam `APP_MODE=mock` tanpa kredensial cloud. Jalankan `pytest` untuk memverifikasi perubahan.
7. **Satu Tempat Business Logic:** Jangan membuat implementasi paralel yang menduplikasi logika bisnis di Python Eel (`desktop/`) dan Flask (`backend/`). Logika domain terpusat di `backend/modules/`.
8. **Disiplin Skema Database:** Jangan mengubah skema database tanpa memperbarui dokumen kontrak (`docs/contracts/database-contract.md`, `docs/database-schema.md`) dan file migrasi di `supabase/migrations/`.
9. **Keamanan Mutlak:** Jangan pernah menyimpan secret nyata, `.env`, atau Supabase `service_role` key di repository, frontend, atau log. Jangan pernah mengambil keputusan otorisasi dari metadata yang dapat diubah sendiri oleh pengguna (`user_metadata`).
10. **Member Branch & Pull Request Workflow:** Setiap anggota bekerja pada branch khusus miliknya dan menggabungkan pekerjaan ke `main` melalui Pull Request. Jangan mengerjakan fitur langsung di `main` dan **jangan melakukan `git commit` atau `git push` otomatis** tanpa persetujuan eksplisit dari pengguna.

---

## 2. Aturan Permanen Git Branch Workflow untuk AI Agent

Seluruh AI Agent yang bekerja di repository ini wajib mematuhi aturan Git berikut tanpa pengecualian:

| Anggota | Peran | Branch Resmi |
| :--- | :--- | :--- |
| **Ferlita** | Project Coordinator & UI/UX Designer | `feature/ferlita-ui-ux` |
| **Fikri** | System Integration & Python Eel Developer | `feature/fikri-eel` |
| **Habil** | Database & Authentication Developer | `feature/habil-database-auth` |
| **Adriel** | Tournament & Match System Developer | `feature/adriel-tournament-match` |
| **Anisa** | REST API, Reporting & Testing Developer | `feature/anisa-api-report` |

1. **Periksa Branch Aktif Sebelum Mengubah File:** Jalankan pemeriksaan branch (`git branch --show-current` dan `git status`) sebelum mengedit file apa pun.
2. **Dilarang Mengerjakan Fitur Langsung di `main`:** Branch `main` adalah branch integrasi. Seluruh pengembangan fitur atau perbaikan modul anggota wajib dilakukan pada branch resmi anggota yang bersangkutan.
3. **Peringatan Saat Branch Tidak Sesuai:** Jika agent dijalankan pada branch `main` atau pada branch milik anggota lain yang tidak sesuai dengan tugas yang sedang dikerjakan, **agent wajib memberikan peringatan kepada pengguna dan meminta pengguna berpindah ke branch yang benar (`git switch <nama-branch>`) sebelum melakukan perubahan kode**.
4. **Hormati Tanggung Jawab Pemilik Branch:** Hanya ubah file yang termasuk dalam cakupan pemilik branch aktif.
5. **Jangan Mengubah File Anggota Lain Tanpa Koordinasi:** Apabila suatu tugas membutuhkan perubahan pada file milik anggota lain atau file konfigurasi bersama, laporkan terlebih dahulu kepada pengguna untuk dikoordinasikan.
6. **Periksa Status Git Sebelum dan Sesudah Perubahan:** Selalu jalankan `git status` dan `git diff --check` sebelum memulai dan setelah menyelesaikan perubahan untuk memastikan tidak ada perubahan liar atau error whitespace.
7. **Dilarang Melakukan Force Push:** Jangan pernah menjalankan `git push --force` atau `git push --force-with-lease`.
8. **Dilarang Melakukan Operasi Git Berisiko Tanpa Izin:** Jangan menjalankan `git reset --hard`, `git rebase`, `git clean -fd`, atau menghapus branch lokal/remote tanpa instruksi dan izin eksplisit dari pengguna.
9. **Jaga Kompatibilitas Antarmodul:** Pastikan setiap perubahan pada branch anggota tetap mematuhi kontrak di `docs/contracts/` sehingga tidak merusak integrasi saat digabungkan ke `main`.
10. **Jangan Mengubah Struktur Project Tanpa Alasan Teknis yang Jelas:** Pertahankan struktur direktori repository Turnamen.in yang telah disepakati.

---

## 3. Pemetaan Anggota, Branch, Folder, dan Skill Wajib

### A. FERLITA: Project Coordinator & UI/UX Designer
- **Branch Resmi:** `feature/ferlita-ui-ux`
- **File Tugas:** `docs/tasks/ferlita.md`
- **Folder Utama:** `desktop/web/pages/`, `desktop/web/assets/css/`, `desktop/web/assets/images/`, `desktop/web/assets/js/components/`, `desktop/web/assets/js/pages/`, `DESIGN.md`
- **Skill Wajib:**
  - `antislop`
  - `antislop-ui`
  - `antislop-human`
  - `antislop-copywriting`
  - `turnamen-project-standards`
  - `turnamen-frontend-ui`
  - `turnamen-quality-gates`
- **Skill Opsional:** `frontend-design`, `tdd` (Catatan: `DESIGN.md` dan keputusan Ferlita tetap menjadi acuan utama di atas skill visual eksternal).

### B. FIKRI: System Integration & Python Eel Developer
- **Branch Resmi:** `feature/fikri-eel`
- **File Tugas:** `docs/tasks/fikri.md`
- **Folder Utama:** `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py`, `backend/core/`
- **Skill Wajib:**
  - `antislop`
  - `antislop-code`
  - `turnamen-project-standards`
  - `turnamen-python-eel`
  - `turnamen-quality-gates`
- **Skill Tambahan:** `hexagonal-python`, `tdd`, `team-code-review`

### C. HABIL: Database & Authentication Developer
- **Branch Resmi:** `feature/habil-database-auth`
- **File Tugas:** `docs/tasks/habil.md`
- **Folder Utama:** `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/`
- **Skill Wajib:**
  - `antislop`
  - `antislop-code`
  - `turnamen-project-standards`
  - `turnamen-supabase-security`
  - `turnamen-quality-gates`
- **Skill Tambahan:** `supabase`, `supabase-postgres-best-practices`, `tdd`

### D. ADRIEL: Tournament & Match System Developer
- **Branch Resmi:** `feature/adriel-tournament-match`
- **File Tugas:** `docs/tasks/adriel.md`
- **Folder Utama:** `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/`
- **Skill Wajib:**
  - `antislop`
  - `antislop-code`
  - `turnamen-project-standards`
  - `turnamen-bracket-engine`
  - `turnamen-quality-gates`
- **Skill Tambahan:** `tdd`, `team-code-review`

### E. ANISA: REST API, Reporting & Testing Developer
- **Branch Resmi:** `feature/anisa-api-report`
- **File Tugas:** `docs/tasks/anisa.md`
- **Folder Utama:** `backend/api/`, `backend/modules/reports/`, `backend/modules/announcements/`, `tests/`, `docs/api/`
- **Skill Wajib:**
  - `antislop`
  - `antislop-code`
  - `antislop-copywriting`
  - `turnamen-project-standards`
  - `turnamen-flask-api`
  - `turnamen-quality-gates`
- **Skill Tambahan:** `hexagonal-python`, `tdd`, `team-code-review`

---

## 4. Urutan Baca Saat Memulai Tugas Anggota

Setiap agent yang menerima instruksi dari salah satu anggota kelompok wajib melakukan langkah berikut secara berurutan:
1. Baca `AGENTS.md` (file ini) dan `docs/GIT_WORKFLOW.md`.
2. Periksa branch Git aktif (`git status` / `git branch --show-current`) dan pastikan sesuai dengan branch resmi anggota yang sedang dibantu. Jika belum sesuai, beri peringatan dan minta pengguna berpindah ke branch yang benar.
3. Baca file tugas anggota terkait di `docs/tasks/<nama>.md`.
4. Baca seluruh `SKILL.md` yang diwajibkan pada file tugas tersebut di `.agents/skills/<nama-skill>/SKILL.md`.
5. Baca dokumen kontrak yang relevan di `docs/contracts/`.
6. Periksa status pengujian awal (`pytest`) sebelum menerapkan perubahan kode, lalu periksa kembali `git status` dan `pytest` sesudah perubahan selesai.
