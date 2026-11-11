# ADDENDUM — EXTERNAL SKILL REPOSITORIES & TECHNICAL KNOWLEDGE SOURCES

Tambahkan sistem external Agent Skills dan repository referensi teknis ke Starter Repository Turnamen.in.

Tujuan:
- Menyatukan standar kerja seluruh AI Agent anggota kelompok.
- Memasang Antislop secara project-level.
- Memanfaatkan skill open-source yang relevan, bukan membuat semuanya dari nol.
- Membuat custom skills khusus sesuai arsitektur dan pembagian tugas Turnamen.in.
- Menghubungkan setiap instruksi anggota dengan skill yang relevan.
- Memastikan skill project-level ikut tersimpan di GitHub agar dapat digunakan seluruh anggota setelah melakukan clone.

Jangan sekadar menambahkan daftar nama skill. Periksa repository sumber, dokumentasi instalasi, struktur skill, lisensi, dan kompatibilitasnya sebelum memasang.

---

## 1. EXTERNAL AGENT SKILL SOURCES

### A. Anti Slop

Repository: <https://github.com/miqdadbadjuber/anti-slop>

Installer:

```powershell
npx antislop-ai
```

Skill yang dipakai:
- `antislop`
- `antislop-ui`
- `antislop-human`
- `antislop-code`
- `antislop-copywriting`

Tidak perlu memasang `antislop-layoutmobile` pada tahap awal karena Turnamen.in merupakan aplikasi desktop-first. Skill tersebut dapat ditambahkan apabila kelak proyek membutuhkan layout responsif lintas ukuran layar.

Penggunaan:
- Ferlita: UI, accessibility, dan copywriting.
- Fikri: standar inti dan kualitas komentar kode.
- Habil: standar inti, keamanan interaksi, dan komentar kode.
- Adriel: standar inti dan komentar kode.
- Anisa: standar inti, copywriting pesan API, dan komentar kode.

Ketentuan instalasi:
- Gunakan project-level installation.
- Targetkan Antigravity apabila didukung installer.
- Pastikan folder skill tersedia di `.agents/skills/`.
- Pertahankan file `VERSION` dan lisensi dari release sumber.
- Jangan memasang native plugin dan skill folder sekaligus apabila menyebabkan duplikasi.
- Jangan mengklaim instalasi berhasil sebelum memverifikasi file yang terpasang.

Antislop adalah filter kualitas, bukan pengganti keputusan desain. `DESIGN.md` dan keputusan desain Ferlita tetap menjadi sumber arahan visual proyek.

### B. Supabase Agent Skills

Repository: <https://github.com/supabase/agent-skills>

Dokumentasi: <https://supabase.com/docs/guides/ai-tools/ai-skills>

Skill yang perlu diperiksa dan dipasang:
- `supabase`
- `supabase-postgres-best-practices`

Perintah instalasi yang dituju:

```bash
npx skills add supabase/agent-skills --skill supabase
npx skills add supabase/agent-skills --skill supabase-postgres-best-practices
```

Penggunaan utama:
- Habil: PostgreSQL schema, Auth, RLS, Storage, Realtime, migrations, dan query practices.
- Fikri: integrasi Supabase dari desktop/backend dan penanganan konfigurasi.
- Anisa: penggunaan Supabase dari REST API dan verifikasi endpoint.

Sebelum implementasi yang sensitif terhadap versi atau konfigurasi, periksa dokumentasi resmi dan changelog Supabase terkini.

### C. Hexagonal Python Skills

Repository: <https://github.com/Remy349/skills>

Skill: `hexagonal-python`

Perintah instalasi:

```bash
npx skills add Remy349/skills --skill hexagonal-python
```

Penggunaan utama:
- Fikri: pemisahan desktop integration, service, dan adapter.
- Anisa: pemisahan Flask API, use case, repository, dan infrastructure.

Skill ini mengajarkan prinsip Ports and Adapters, domain separation, repository boundaries, REST API structure, dan testing per boundary.

PENTING:
- Contoh pada skill dapat memakai SQLAlchemy 2.
- Turnamen.in menggunakan Supabase Python SDK sebagai integrasi database utama.
- Jangan otomatis menambahkan SQLAlchemy hanya karena contoh skill menggunakannya.
- Adaptasikan prinsip arsitektur tanpa menambahkan teknologi yang tidak dibutuhkan.
- Hindari overengineering; gunakan arsitektur secara proporsional.

### D. Engineering Workflow Skills

Repository: <https://github.com/dgalarza/agent-skills>

Skill yang dipakai:
- `tdd`
- `team-code-review`

Perintah instalasi:

```bash
npx skills add dgalarza/agent-skills --skill tdd
npx skills add dgalarza/agent-skills --skill team-code-review
```

Penggunaan:
- Semua anggota: TDD sesuai kebutuhan modul.
- Fikri dan Anisa: integrasi dan code review.
- Habil: pengujian database, Auth, dan RLS.
- Adriel: unit test algoritma bracket dan validasi progression.
- Ferlita: pengujian interaksi UI dan alur pengguna.

Prioritas:
- Red-Green-Refactor.
- Memilih level test yang tepat.
- Memverifikasi bug sebelum melaporkannya.
- Menguji perubahan sebelum integrasi.
- Menghindari perubahan yang merusak modul lain.

Jangan memaksakan TDD untuk perubahan dokumentasi atau pekerjaan yang tidak membutuhkan pengujian kode.

### E. Frontend Design Skill

Repository: <https://github.com/Junaid-PK/frontend-design-skill>

Skill: `frontend-design`

Perintah instalasi:

```bash
npx skills add Junaid-PK/frontend-design-skill --skill frontend-design
```

Penggunaan utama: Ferlita.

Fokus:
- Interface design.
- Visual hierarchy.
- UX consistency.
- Component consistency.
- Usability.

Skill ini opsional karena beberapa area tumpang tindih dengan `antislop-ui`. Jika terdapat konflik, gunakan `DESIGN.md`, kebutuhan produk, accessibility, dan keputusan desain Ferlita sebagai acuan. Jangan mengikuti dua skill visual secara membabi buta.

---

## 2. OFFICIAL TECHNICAL REPOSITORY REFERENCES

Repository berikut merupakan sumber referensi teknis. Tidak semuanya merupakan Agent Skills dan tidak semuanya perlu dipasang sebagai dependency.

### Python Eel

Repository: <https://github.com/python-eel/Eel>

Digunakan oleh Fikri.

Referensi:
- Eel application lifecycle.
- Python-JavaScript bridge.
- Exposed functions.
- Desktop application configuration.
- Local server.

Perhatian: repository Eel telah diarsipkan dan tidak lagi aktif dipelihara. Periksa kompatibilitas, batasi akses lokal, pin versi dependency, dan jangan mengasumsikan adanya pembaruan keamanan. Jangan menambahkan Eel tanpa mengevaluasi konsekuensi pemeliharaannya.

### Flask

Repository: <https://github.com/pallets/flask>

Digunakan oleh Anisa dan Fikri.

Referensi:
- Application factory.
- Blueprint.
- Request handling.
- Routing.
- Error handling.
- API organization.

### pytest

Repository: <https://github.com/pytest-dev/pytest>

Digunakan oleh seluruh anggota.

Referensi:
- Unit testing.
- Fixtures.
- Parameterized tests.
- Mocking.
- Integration testing.

### OWASP Cheat Sheet Series

Repository: <https://github.com/OWASP/CheatSheetSeries>

Digunakan oleh Habil, Fikri, dan Anisa.

Referensi keamanan:
- Authentication.
- Authorization.
- Password storage.
- Session management.
- Input validation.
- API security.
- Secrets management.

OWASP Cheat Sheet Series merupakan referensi keamanan, bukan Agent Skill. Implementasikan panduan yang relevan dengan risiko aplikasi.

### Supabase

Repository: <https://github.com/supabase/supabase>

Dokumentasi resmi: <https://supabase.com/docs>

Gunakan sebagai referensi ekosistem, dokumentasi, konfigurasi, dan contoh implementasi Supabase. Untuk panduan agent-specific, prioritaskan repository `supabase/agent-skills`.

---

## 3. CUSTOM TURNAMEN.IN SKILLS

Tetap buat custom skill khusus proyek. Jangan menggantikan custom skills dengan external skills karena custom skills memuat aturan spesifik Turnamen.in.

Buat struktur berikut:

```text
.agents/skills/
├── turnamen-project-standards/
│   └── SKILL.md
├── turnamen-frontend-ui/
│   └── SKILL.md
├── turnamen-python-eel/
│   └── SKILL.md
├── turnamen-supabase-security/
│   └── SKILL.md
├── turnamen-bracket-engine/
│   └── SKILL.md
├── turnamen-flask-api/
│   └── SKILL.md
└── turnamen-quality-gates/
    └── SKILL.md
```

Setiap `SKILL.md` wajib memiliki YAML frontmatter yang valid, minimal berisi `name` dan `description`.

Setiap skill wajib menjelaskan:
- Scope.
- Responsibilities.
- Architecture rules.
- Allowed directories.
- Prohibited changes.
- Required dependencies.
- Development workflow.
- Testing requirements.
- Acceptance criteria.
- Integration contracts.

### A. `turnamen-project-standards`

Dibaca seluruh anggota.

Berisi:
- Arsitektur resmi Turnamen.in.
- Konvensi folder dan penamaan.
- Standar Python, JavaScript, dan SQL.
- API response contract.
- Error handling.
- Database conventions.
- Git single-main workflow.
- Module ownership.
- Larangan mengubah kontrak tanpa koordinasi.
- Cara mengembangkan modul secara paralel.

### B. `turnamen-frontend-ui`

Untuk Ferlita.

Berisi:
- Design system Turnamen.in.
- Komponen UI.
- Navigasi desktop.
- Dashboard.
- Forms dan data tables.
- Loading, empty, dan error states.
- Accessibility.
- Integrasi dengan API client.
- Konsistensi visual antarmodul.

### C. `turnamen-python-eel`

Untuk Fikri.

Berisi:
- Python Eel architecture.
- Application lifecycle.
- Launcher.
- JavaScript-Python communication.
- API client.
- Error handling.
- Configuration management.
- Logging.
- Modular integration.
- Desktop security.

### D. `turnamen-supabase-security`

Untuk Habil.

Berisi:
- PostgreSQL schema.
- Database relationships.
- Supabase Auth.
- Profile management.
- RBAC.
- RLS policies.
- Storage access policies.
- Realtime.
- Migrations.
- Indexing.
- Secure credential handling.

Jangan pernah mengekspos `service_role` key atau secret key pada aplikasi desktop, frontend, atau repository.

### E. `turnamen-bracket-engine`

Untuk Adriel.

Berisi:
- Tournament lifecycle.
- Team registration contracts.
- Single Elimination algorithm.
- Match state transitions.
- Round progression.
- Score validation.
- Winner determination.
- Next match assignment.
- Bye handling.
- Bracket testing.
- Data consistency.

### F. `turnamen-flask-api`

Untuk Anisa.

Berisi:
- Flask application structure.
- Blueprint organization.
- API versioning.
- Request validation.
- Response format.
- Authentication middleware.
- Authorization.
- Error handling.
- OpenAPI documentation.
- Integration testing.

### G. `turnamen-quality-gates`

Untuk seluruh anggota.

Berisi:
- Unit testing.
- Integration testing.
- API testing.
- Contract testing.
- Input validation.
- Regression testing.
- Test coverage priorities.
- Definition of Done.
- Acceptance criteria.
- Final delivery checklist.

---

## 4. FINAL MEMBER SKILL MAPPING

Setiap anggota harus menggunakan skill project-level yang sama dari repository. Mapping berikut menentukan skill mana yang wajib dibaca berdasarkan tugas.

### FERLITA — Project Coordinator & UI/UX Designer

Wajib:
- `antislop`
- `antislop-ui`
- `antislop-human`
- `antislop-copywriting`
- `turnamen-project-standards`
- `turnamen-frontend-ui`
- `turnamen-quality-gates`

Opsional:
- `frontend-design`
- `tdd` untuk pengujian interaksi UI yang relevan.

### FIKRI — System Integration & Python Eel Developer

Wajib:
- `antislop`
- `antislop-code`
- `turnamen-project-standards`
- `turnamen-python-eel`
- `turnamen-quality-gates`

Tambahan:
- `hexagonal-python`
- `tdd`
- `team-code-review` saat melakukan review integrasi.

### HABIL — Database & Authentication Developer

Wajib:
- `antislop`
- `antislop-code`
- `turnamen-project-standards`
- `turnamen-supabase-security`
- `turnamen-quality-gates`

Tambahan:
- `supabase`
- `supabase-postgres-best-practices`
- `tdd`

### ADRIEL — Tournament & Match System Developer

Wajib:
- `antislop`
- `antislop-code`
- `turnamen-project-standards`
- `turnamen-bracket-engine`
- `turnamen-quality-gates`

Tambahan:
- `tdd`
- `team-code-review` ketika melakukan review algoritma atau integrasi.

### ANISA — REST API, Reporting & Testing Developer

Wajib:
- `antislop`
- `antislop-code`
- `antislop-copywriting`
- `turnamen-project-standards`
- `turnamen-flask-api`
- `turnamen-quality-gates`

Tambahan:
- `hexagonal-python`
- `tdd`
- `team-code-review`

Setiap agent yang menerima tugas anggota harus membaca:
1. Root `AGENTS.md`.
2. File tugas anggota terkait.
3. Semua skill yang diwajibkan dalam file tugas tersebut.
4. Kontrak API, database, dan modul yang berkaitan.

Jangan memuat semua skill tambahan yang tidak relevan pada setiap pekerjaan.

---

## 5. SKILL INSTALLATION STRATEGY

Gunakan instalasi project-level agar skill dapat dibagikan melalui GitHub.

Target folder:

```text
.agents/skills/
```

Sebelum instalasi:
1. Periksa perintah dan opsi installer menggunakan `npx skills add --help`.
2. Periksa nama skill yang tersedia pada setiap repository.
3. Pilih target Antigravity apabila didukung.
4. Gunakan project scope.
5. Gunakan copy mode apabila didukung agar file benar-benar tersimpan di repository.
6. Jangan menggunakan global scope untuk skill proyek.
7. Jangan memasang native plugin duplikat apabila skill project-level sudah digunakan.
8. Periksa apakah installer membuat `skills-lock.json` dan commit file tersebut jika relevan.

Jika instalasi membutuhkan interaksi atau persetujuan pengguna, tampilkan perintah yang harus dijalankan. Jangan mengarang hasil instalasi.

Jangan menyalin repository sumber secara utuh jika hanya folder skill dan resource yang diperlukan.

---

## 6. LICENSE, VERSION & SOURCE MANAGEMENT

Buat file:

`docs/skill-sources.md`

Untuk setiap external skill, catat:
- Nama skill.
- Repository asal.
- URL repository.
- Nama folder skill.
- Versi atau commit SHA yang digunakan.
- Lisensi.
- Anggota pengguna.
- Fungsi.
- Status instalasi.

Buat dan commit `skills-lock.json` apabila didukung installer.

Pertahankan LICENSE, copyright notice, dan attribution dari external skill.

Jangan mengubah source external skill secara langsung. Jika perlu penyesuaian, buat wrapper atau custom skill Turnamen.in yang mengacu pada sumber aslinya.

Periksa perubahan upstream sebelum melakukan update.

---

## 7. ROOT AGENTS.md

Tambahkan instruksi global berikut:
- Semua agent wajib mengikuti project standards.
- Semua agent wajib menjaga kepemilikan file masing-masing.
- Semua agent wajib membaca task file anggota yang relevan.
- Semua agent wajib memuat skill sesuai tugas.
- Semua kode harus mengikuti kontrak bersama.
- Semua perubahan harus dapat diuji.
- Jangan membuat implementasi paralel yang menduplikasi business logic.
- Jangan mengubah database schema tanpa memperbarui kontrak dan migration.
- Semua anggota tetap menggunakan satu branch `main`.

Pertahankan pointer resmi Antislop hasil installer, termasuk marker yang disediakan pembuatnya. Jangan menghapus atau menggandakan pointer tersebut.

---

## 8. DESIGN.md

Buat `DESIGN.md` sebagai dokumen arahan visual awal Turnamen.in.

Isi merupakan draft untuk ditinjau dan disetujui Ferlita.

Arah awal:
- Windows desktop-first.
- Dark esports dashboard.
- Professional.
- Clean dan mudah digunakan.
- Tidak terlalu ramai.
- Typography mudah dibaca.
- Fokus pada informasi pertandingan dan manajemen turnamen.

Jangan mengunci palet warna, font, atau layout final tanpa persetujuan Ferlita.

Antislop merupakan filter kualitas, bukan pengganti keputusan desain.

---

## 9. README & CONTRIBUTING

Tambahkan bagian:

`## AI Agent Skills & Engineering Standards`

Jelaskan:
- External skills.
- Custom project skills.
- Repository referensi.
- Daftar skill setiap anggota.
- Cara instalasi.
- Cara memperbarui.
- Cara memverifikasi.
- Cara memulai sesi AGY baru.

Pastikan folder `.agents/skills/` tidak masuk `.gitignore` sehingga ikut tersimpan di GitHub.

Jelaskan bahwa setiap anggota melakukan:

```bash
git pull origin main
```

Sebelum bekerja, lalu commit dan push setelah pekerjaan selesai.

---

## 10. VERIFICATION

Pastikan:
- Semua skill memiliki `SKILL.md` yang valid.
- YAML frontmatter valid.
- Semua repository sumber tercatat.
- Versi dan lisensi external skill tercatat.
- External skill tidak terduplikasi.
- Lima file instruksi anggota sudah memiliki skill mapping yang benar.
- Semua folder skill tercakup dalam Git.
- `.agents/skills/` tidak diabaikan `.gitignore`.
- Semua anggota dapat membaca instruksi setelah clone.
- README menjelaskan instalasi, update, dan verifikasi.
- Instalasi yang masih memerlukan tindakan manual dinyatakan secara eksplisit.

Jangan mengklaim semua skill berhasil dipasang jika sebagian masih memerlukan instalasi manual.

---

## 11. EXECUTION

Terapkan addendum ini pada Starter Repository Turnamen.in yang sudah dibuat.

Jangan membangun ulang seluruh proyek dari awal.

Jangan menghapus kode maupun dokumentasi yang sudah ada.

Jangan melakukan push atau commit otomatis.

Pertahankan satu branch `main`.

Setelah selesai, tampilkan laporan instalasi dan verifikasi secara jujur.
