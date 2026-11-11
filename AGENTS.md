<!-- antislop:start -->
Before writing or editing any code, UI, copy, or comments, load the `antislop` skill at `.agents/skills/antislop/SKILL.md` and the relevant sub-skills (`antislop-ui`, `antislop-human`, `antislop-code`, `antislop-copywriting`) for the task.
<!-- antislop:end -->

# AGENTS.md — Instruksi Global AI Agent Proyek Turnamen.in

Dokumen ini adalah instruksi tingkat root untuk seluruh AI Agent (Antigravity / AGY, Cursor, Claude Code, Codex, dll.) yang bekerja pada repository **Turnamen.in — Esports Tournament Management System**.

---

## 1. Aturan Wajib Seluruh Agent

1. **Ikuti Project Standards:** Setiap agent wajib membaca dan mematuhi `.agents/skills/turnamen-project-standards/SKILL.md` dan `.agents/skills/turnamen-quality-gates/SKILL.md`.
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
10. **Single Main Branch Workflow:** Seluruh anggota bekerja pada satu branch `main`. Jangan membuat branch baru tanpa instruksi eksplisit dan **jangan melakukan `git commit` atau `git push` otomatis** tanpa persetujuan pengguna.

---

## 2. Pemetaan Anggota, Folder, dan Skill Wajib

### A. FERLITA — Project Coordinator & UI/UX Designer
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

### B. FIKRI — System Integration & Python Eel Developer
- **File Tugas:** `docs/tasks/fikri.md`
- **Folder Utama:** `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py`, `backend/core/`
- **Skill Wajib:**
  - `antislop`
  - `antislop-code`
  - `turnamen-project-standards`
  - `turnamen-python-eel`
  - `turnamen-quality-gates`
- **Skill Tambahan:** `hexagonal-python`, `tdd`, `team-code-review`

### C. HABIL — Database & Authentication Developer
- **File Tugas:** `docs/tasks/habil.md`
- **Folder Utama:** `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/`
- **Skill Wajib:**
  - `antislop`
  - `antislop-code`
  - `turnamen-project-standards`
  - `turnamen-supabase-security`
  - `turnamen-quality-gates`
- **Skill Tambahan:** `supabase`, `supabase-postgres-best-practices`, `tdd`

### D. ADRIEL — Tournament & Match System Developer
- **File Tugas:** `docs/tasks/adriel.md`
- **Folder Utama:** `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/`
- **Skill Wajib:**
  - `antislop`
  - `antislop-code`
  - `turnamen-project-standards`
  - `turnamen-bracket-engine`
  - `turnamen-quality-gates`
- **Skill Tambahan:** `tdd`, `team-code-review`

### E. ANISA — REST API, Reporting & Testing Developer
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

## 3. Urutan Baca Saat Memulai Tugas Anggota

Setiap agent yang menerima instruksi dari salah satu anggota kelompok wajib melakukan langkah berikut secara berurutan:
1. Baca `AGENTS.md` (file ini).
2. Baca file tugas anggota terkait di `docs/tasks/<nama>.md`.
3. Baca seluruh `SKILL.md` yang diwajibkan pada file tugas tersebut di `.agents/skills/<nama-skill>/SKILL.md`.
4. Baca dokumen kontrak yang relevan di `docs/contracts/`.
5. Periksa status pengujian awal sebelum menerapkan perubahan kode.
