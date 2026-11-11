# Panduan Kontribusi — Turnamen.in (Single Main Branch Workflow)

Proyek **Turnamen.in** dikerjakan secara paralel oleh **5 anggota kelompok** dengan alur kerja Git yang sederhana dan terkoordinasi. Seluruh anggota bekerja menggunakan **satu branch utama: `main`**.

> [!IMPORTANT]
> Jangan membuat branch individual, jangan mengubah kontrak bersama secara sepihak, dan jangan pernah menggunakan `git push --force`.

---

## 1. Pembagian Kepemilikan Folder (Module Ownership)

Setiap anggota bertanggung jawab penuh pada area kerjanya masing-masing agar tidak terjadi bentrokan file (*merge conflict*):

| Anggota | Peran | Folder Utama |
| :--- | :--- | :--- |
| **Ferlita** | Project Coordinator & UI/UX Designer | `desktop/web/pages/`, `desktop/web/assets/css/`, `desktop/web/assets/images/`, `DESIGN.md` |
| **Fikri** | System Integration & Python Eel Developer | `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py` |
| **Habil** | Database & Authentication Developer | `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/` |
| **Adriel** | Tournament & Match System Developer | `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/` |
| **Anisa** | REST API, Reporting & Testing Developer | `backend/api/`, `backend/modules/reports/`, `backend/modules/announcements/`, `tests/`, `docs/api/` |

Kepemilikan folder adalah batas tanggung jawab utama. Apabila suatu perubahan menyentuh folder anggota lain atau mengubah kontrak bersama (`docs/contracts/`), wajib dikoordinasikan terlebih dahulu.

---

## 2. Alur Kerja Harian (Single Branch `main`)

### A. Sebelum Mulai Bekerja
Selalu tarik pembaruan terbaru dari `origin/main` sebelum mengedit file apa pun:

```bash
git pull origin main
```

Pastikan pengujian dasar tetap hijau sebelum mulai menulis kode baru:

```bash
pytest
```

### B. Saat Bekerja
1. Baca `AGENTS.md`, file tugas masing-masing di `docs/tasks/<nama>.md`, serta Agent Skills yang diwajibkan.
2. Gunakan `APP_MODE=mock` untuk mengembangkan dan menguji modul secara mandiri tanpa bergantung pada koneksi cloud.
3. Hanya ubah file di dalam area tanggung jawab masing-masing.

### C. Setelah Menyelesaikan Satu Bagian Kecil
Simpan dan unggah perubahan ke `main` dengan pesan commit yang deskriptif:

```bash
git add .
git commit -m "feat: descriptive feature name"
git push origin main
```

Format pesan commit yang disarankan:
- `feat: tambah validasi skor best-of-3 pada modul matches`
- `fix: perbaiki tampilan status badge pada halaman bracket`
- `docs: perbarui dokumentasi endpoint pengumuman`
- `test: tambah pengujian edge case bye pada bracket 6 tim`

---

## 3. Penanganan Konflik Saat Push Ditolak

Jika perintah `git push origin main` ditolak karena anggota lain baru saja melakukan push:

1. **Jangan gunakan `--force`!**
2. Tarik perubahan terbaru dengan rebase atau merge yang aman:
   ```bash
   git pull --rebase origin main
   ```
3. Jika terdapat konflik pada file yang sama:
   - Periksa penanda konflik (`<<<<<<<`, `=======`, `>>>>>>>`).
   - Diskusikan dengan anggota pemilik file tersebut.
   - Jangan menimpa atau menghapus pekerjaan anggota lain.
   - Setelah konflik diselesaikan, jalankan `git add <file>` lalu `git rebase --continue` dan `git push origin main`.

---

## 4. Penggunaan GitHub Desktop (Opsional untuk Non-Terminal)

Bagi anggota yang lebih nyaman menggunakan antarmuka grafis (**GitHub Desktop**):
1. Pastikan **Current Branch** selalu berada di `main`.
2. Klik **Fetch origin** / **Pull origin** sebelum mulai mengedit file.
3. Periksa daftar **Changes** di panel kiri — pastikan hanya file milik modul Anda yang ikut dicentang, dan tidak ada file `.env` atau kredensial rahasia.
4. Isi **Summary** (mis. `feat: desain kartu turnamen pada dashboard`), klik **Commit to main**, lalu klik **Push origin**.

---

## 5. AI Agent Skills & Engineering Standards

Seluruh anggota dan AI Agent yang membantu di repository ini wajib mematuhi standar yang didefinisikan pada `AGENTS.md` dan folder `.agents/skills/`.

### A. Daftar Skill Project-Level
Folder `.agents/skills/` disimpan langsung di dalam Git agar seluruh anggota mendapatkan aturan yang sama setelah melakukan `git clone` atau `git pull origin main`.
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
| Anggota | Skill Wajib | Skill Tambahan / Opsional |
| :--- | :--- | :--- |
| **Ferlita** | `antislop`, `antislop-ui`, `antislop-human`, `antislop-copywriting`, `turnamen-project-standards`, `turnamen-frontend-ui`, `turnamen-quality-gates` | `frontend-design`, `tdd` |
| **Fikri** | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-python-eel`, `turnamen-quality-gates` | `hexagonal-python`, `tdd`, `team-code-review` |
| **Habil** | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-supabase-security`, `turnamen-quality-gates` | `supabase`, `supabase-postgres-best-practices`, `tdd` |
| **Adriel** | `antislop`, `antislop-code`, `turnamen-project-standards`, `turnamen-bracket-engine`, `turnamen-quality-gates` | `tdd`, `team-code-review` |
| **Anisa** | `antislop`, `antislop-code`, `antislop-copywriting`, `turnamen-project-standards`, `turnamen-flask-api`, `turnamen-quality-gates` | `hexagonal-python`, `tdd`, `team-code-review` |

### C. Memulai Sesi AI Agent (Antigravity / AGY) Baru
Saat memulai sesi bersama AI Agent:
1. Jalankan `git pull origin main` terlebih dahulu.
2. Minta agent membaca:
   - `AGENTS.md`
   - `docs/tasks/<nama-anggota>.md`
   - Seluruh `SKILL.md` yang tercantum sebagai skill wajib pada file tugas tersebut.
   - Dokumen kontrak di `docs/contracts/`.
3. Jangan melakukan commit atau push otomatis melalui script tanpa pemeriksaan anggota.
