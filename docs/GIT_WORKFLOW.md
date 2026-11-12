# Panduan Resmi Git Branch Workflow: Turnamen.in

Dokumen ini adalah panduan utama penggunaan Git dan GitHub untuk seluruh anggota tim **Turnamen.in**. Setiap anggota bekerja pada branch khusus miliknya agar pengembangan dapat berjalan secara paralel tanpa langsung mengubah kode pada branch utama (`main`).

Repository GitHub resmi:
`https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`

---

## 1. Struktur Branch Resmi

Branch `main` dipertahankan sebagai branch utama dan pusat integrasi seluruh pekerjaan tim. Setiap anggota memiliki satu branch kerja resmi sesuai pembagian tugas berikut:

| Anggota | Tanggung Jawab | Branch Resmi | Folder Utama |
| :--- | :--- | :--- | :--- |
| **Ferlita** | Project Coordinator & UI/UX Designer | `feature/ferlita-ui-ux` | `desktop/web/pages/`, `desktop/web/assets/css/`, `desktop/web/assets/images/`, `desktop/web/assets/js/components/`, `desktop/web/assets/js/pages/`, `DESIGN.md` |
| **Fikri** | System Integration & Python Eel Developer | `feature/fikri-eel` | `desktop/launcher/`, `desktop/bridge/`, `desktop/web/assets/js/core/`, `run.py`, `backend/core/` |
| **Habil** | Database & Authentication Developer | `feature/habil-database-auth` | `supabase/`, `backend/modules/auth/`, `backend/infrastructure/supabase/`, `backend/repositories/`, `docs/database-schema.md`, `docs/security.md` |
| **Adriel** | Tournament & Match System Developer | `feature/adriel-tournament-match` | `backend/modules/tournaments/`, `backend/modules/teams/`, `backend/modules/matches/`, `tests/unit/test_bracket_engine.py` |
| **Anisa** | REST API, Reporting & Testing Developer | `feature/anisa-api-report` | `backend/app.py`, `backend/api/`, `backend/modules/reports/`, `backend/modules/announcements/`, `tests/`, `docs/api/` |

### Aturan Wajib Penggunaan Branch

1. Setiap anggota bekerja pada branch khusus miliknya sesuai tabel di atas.
2. Branch `main` hanya digunakan untuk kode yang sudah diperiksa, lulus pengujian, dan siap diintegrasikan.
3. Anggota dilarang mengerjakan perubahan fitur secara langsung pada branch `main`.
4. Setiap anggota hanya boleh melakukan push ke branch miliknya sendiri.
5. Penggabungan perubahan ke `main` wajib dilakukan melalui **Pull Request (PR)** di GitHub.
6. Dilarang menggunakan `git push --force` atau `git push --force-with-lease`.
7. Jangan menghapus branch anggota selama proyek dan pengembangan masih berlangsung.
8. Jangan mengubah, menulis ulang, atau menghapus commit awal repository (`29350bd`).

---

## 2. Panduan Git Langkah demi Langkah

### A. Clone Repository (Bagi Anggota yang Belum Memiliki Project Lokal)

Jika belum memiliki folder repository di komputer lokal, buka PowerShell lalu jalankan:

```powershell
git clone https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id.git
cd projek_eapp_kelompok_2_turnamen.id
```

Setelah proses clone selesai, buat virtual environment Python dan pasang dependensi sesuai panduan di [`README.md`](file:///C:/Turnamen.in/README.md).

---

### B. Membuat atau Mengaktifkan Branch Pertama Kali

> [!IMPORTANT]
> - Perintah `git switch -c <nama-branch>` **hanya digunakan satu kali** ketika branch tersebut belum ada di lokal maupun di remote (`origin`).
> - Jika branch sudah dibuat di GitHub (remote), jangan gunakan `-c` agar tidak membuat branch duplikat. Cukup jalankan `git fetch origin` lalu `git switch <nama-branch>`.
> - Jika branch sudah ada di komputer lokal Anda, cukup berpindah menggunakan `git switch <nama-branch>`.

#### 1. Ferlita (`feature/ferlita-ui-ux`)
```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/ferlita-ui-ux
git push -u origin feature/ferlita-ui-ux
```

#### 2. Fikri (`feature/fikri-eel`)
```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/fikri-eel
git push -u origin feature/fikri-eel
```

#### 3. Habil (`feature/habil-database-auth`)
```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/habil-database-auth
git push -u origin feature/habil-database-auth
```

#### 4. Adriel (`feature/adriel-tournament-match`)
```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/adriel-tournament-match
git push -u origin feature/adriel-tournament-match
```

#### 5. Anisa (`feature/anisa-api-report`)
```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/anisa-api-report
git push -u origin feature/anisa-api-report
```

#### Cara Checkout jika Branch Sudah Ada di Remote (`origin`)
Apabila branch Anda sudah pernah dibuat di GitHub (misalnya saat berpindah perangkat atau dibuatkan oleh koordinator):

```powershell
git fetch origin
git switch <nama-branch-anda>
git pull --ff-only
```

#### Cara Berpindah jika Branch Sudah Ada di Lokal
Apabila branch sudah tersedia di komputer Anda:

```powershell
git switch <nama-branch-anda>
```

---

### C. Workflow Pekerjaan Sehari-hari

Setiap kali mulai bekerja, pastikan Anda berada di branch milik sendiri dan kondisi pengujian awal berjalan baik.

#### Langkah 1: Periksa Status dan Aktifkan Branch
Contoh untuk Ferlita:

```powershell
git status
git switch feature/ferlita-ui-ux
git pull --ff-only
```

*(Ganti `feature/ferlita-ui-ux` dengan nama branch resmi Anda).*

#### Langkah 2: Jalankan Pengujian Awal
Pastikan aplikasi dan unit/integration test berjalan normal sebelum mengedit file:

```powershell
pytest
python run.py --check
```

#### Langkah 3: Simpan dan Unggah Pekerjaan (Commit & Push)
Setelah menyelesaikan perubahan pada folder tanggung jawab Anda dan memastikan `pytest` lulus:

```powershell
git status
git add .
git commit -m "feat(ui): improve tournament dashboard"
git push
```

> [!TIP]
> Sebelum menjalankan `git add .`, selalu periksa `git status` untuk memastikan tidak ada file `.env` atau perubahan tak disengaja pada folder anggota lain. Anda juga dapat menambahkan path spesifik seperti `git add desktop/web/ DESIGN.md`.

#### Contoh Commit Message Sesuai Peran Anggota

- **Ferlita (`feature/ferlita-ui-ux`):**
  ```powershell
  git add DESIGN.md desktop/web/
  git commit -m "feat(ui): improve tournament dashboard"
  git push
  ```
- **Fikri (`feature/fikri-eel`):**
  ```powershell
  git add run.py desktop/launcher/ desktop/bridge/ desktop/web/assets/js/core/ backend/core/
  git commit -m "feat(desktop): refine eel launcher lifecycle and api client error handling"
  git push
  ```
- **Habil (`feature/habil-database-auth`):**
  ```powershell
  git add supabase/ backend/modules/auth/ backend/infrastructure/supabase/ backend/repositories/
  git commit -m "feat(auth): enforce role permission checks on repository operations"
  git push
  ```
- **Adriel (`feature/adriel-tournament-match`):**
  ```powershell
  git add backend/modules/tournaments/ backend/modules/teams/ backend/modules/matches/ tests/unit/test_bracket_engine.py
  git commit -m "feat(bracket): handle bye advancement for non-power-of-two teams"
  git push
  ```
- **Anisa (`feature/anisa-api-report`):**
  ```powershell
  git add backend/app.py backend/api/ backend/modules/reports/ backend/modules/announcements/ tests/ docs/api/
  git commit -m "feat(api): add tournament standings report endpoint and integration tests"
  git push
  ```

---

### D. Sinkronisasi Branch Anggota dengan `main`

Ketika ada Pull Request anggota lain yang sudah digabungkan (*merged*) ke `main`, Anda perlu memperbarui branch kerja Anda agar selalu selaras dengan perkembangan terbaru tim.

Contoh untuk Ferlita (sesuaikan nama branch untuk anggota lain):

```powershell
git fetch origin
git switch feature/ferlita-ui-ux
git merge origin/main
```

Setelah proses merge berhasil:
1. Jalankan `pytest` dan `python run.py --check` untuk memastikan integrasi berjalan lancar.
2. Unggah pembaruan sinkronisasi ke branch remote Anda:
   ```powershell
   git push
   ```

**Catatan Penting Saat Terjadi Konflik Merge:**
- Jika Git melaporkan adanya *merge conflict*, jangan panik dan jangan langsung menghapus kode milik anggota lain.
- Periksa perubahan dari kedua pihak dengan teliti.
- Apabila Anda tidak yakin cara menyelesaikannya, **berhenti terlebih dahulu dan tanyakan kepada koordinator (Ferlita) atau integrator sistem (Fikri)**. Jangan memaksakan commit atau menghapus pekerjaan anggota lain.

---

### E. Cara Membuat Pull Request (PR) ke `main`

Ketika fitur atau perbaikan pada branch Anda sudah selesai dan lulus pengujian (`pytest`), gabungkan ke `main` melalui Pull Request di GitHub:

1. Buka repository GitHub di browser: `https://github.com/FikriYuzaki/projek_eapp_kelompok_2_turnamen.id`.
2. Pilih branch milik Anda pada menu dropdown branch (atau klik tombol **`Compare & pull request`** yang muncul setelah push).
3. Klik **`Compare & pull request`** (atau masuk ke tab **Pull requests** lalu klik **New pull request**).
4. Pastikan branch tujuan (**base**) adalah `main`.
5. Pastikan branch sumber (**compare**) adalah branch milik Anda (misalnya `feature/ferlita-ui-ux`).
6. Tulis judul dan ringkasan perubahan secara jelas.
7. Cantumkan daftar file, modul, atau fitur yang diubah.
8. Cantumkan hasil pengujian lokal (contoh: `pytest -v: passed`, `python run.py --check: OK`).
9. Klik **`Create pull request`** untuk mengirim Pull Request.
10. Tunggu pemeriksaan (*code review*) dan persetujuan sebelum Pull Request di-merge ke `main`.

#### Setelah Pull Request Berhasil Di-merge ke `main`

Perbarui branch `main` lokal dan sinkronkan kembali branch kerja Anda:

```powershell
git switch main
git pull --ff-only origin main
git switch <nama-branch-anda>
git merge main
git push
```

> [!NOTE]
> Jangan menghapus branch kerja Anda setelah Pull Request di-merge apabila Anda masih akan melanjutkan pekerjaan berikutnya pada branch tersebut.

---

## 3. Aturan Menghindari Konflik Kode

Walaupun setiap anggota memiliki branch masing-masing, seluruh branch tetap merupakan bagian dari satu aplikasi **Turnamen.in**. Ikuti aturan berikut untuk mencegah konflik saat penggabungan ke `main`:

- **Patuhi Batas Kepemilikan Folder:** Setiap anggota hanya mengubah file pada area tanggung jawabnya masing-masing.
- **Jaga Kontrak Bersama:** Jangan mengubah kontrak API (`docs/contracts/api-contract.md`), struktur database (`docs/contracts/database-contract.md`), nama fungsi bersama (`docs/contracts/module-contract.md`), matriks role (`docs/contracts/role-permissions.md`), atau kontrak frontend (`docs/contracts/frontend-contract.md`) tanpa diskusi kelompok.
- **Koordinasi File Konfigurasi dan File Bersama:** File tingkat root atau penghubung lintas modul seperti `run.py`, `backend/app.py`, `backend/core/config.py`, `requirements.txt`, dan `desktop/web/index.html` harus dikoordinasikan terlebih dahulu sebelum diubah.
- **Komunikasi Lintas Modul:** Jika fitur Anda membutuhkan perubahan pada file milik anggota lain, hubungi pemilik modul tersebut agar perubahan dilakukan secara terkoordinasi.
- **Hindari Duplikasi Implementasi:** Jangan membuat fungsi, endpoint, atau helper duplikat dari fitur yang sudah dikerjakan anggota lain.
- **Wajib Uji Sebelum PR:** Jangan mengajukan Pull Request untuk kode yang belum diuji dengan `pytest` dan `python run.py --check`.
- **Sinkronisasi Berkala:** Jangan menunggu terlalu lama untuk melakukan `git fetch origin` dan `git merge origin/main`. Branch yang jarang disinkronkan lebih berisiko mengalami konflik besar.

### Prosedur Ketika Terjadi Konflik (Merge Conflict)

Apabila muncul pesan `CONFLICT (content): Merge conflict in <nama-file>` saat menjalankan `git merge origin/main`:

1. **Periksa `git status`:** Lihat daftar file yang ditandai `both modified`.
2. **Baca file yang mengalami konflik:** Cari penanda konflik Git (`<<<<<<< HEAD`, `=======`, `>>>>>>> origin/main`).
3. **Bandingkan perubahan dari kedua branch:** Pahami maksud perubahan di branch Anda (`HEAD`) dan perubahan yang baru masuk dari `origin/main`.
4. **Diskusikan dengan pemilik perubahan terkait jika diperlukan:** Tanyakan kepada anggota yang menulis kode tersebut agar tidak salah menggabungkan logika.
5. **Selesaikan konflik tanpa menghilangkan pekerjaan yang valid:** Gabungkan kode yang benar dan hapus baris penanda `<<<<<<<`, `=======`, serta `>>>>>>>`.
6. **Jalankan pengujian yang relevan:** Jalankan `pytest -v` dan `python run.py --check` untuk memastikan hasil penggabungan berjalan normal.
7. **Commit hasil penyelesaian konflik:**
   ```powershell
   git add <file-yang-diselesaikan>
   git commit -m "chore(merge): resolve merge conflict with main"
   git push
   ```

*(Jika Anda mengalami kesulitan saat menyelesaikan konflik, jalankan `git merge --abort` untuk membatalkan proses merge sementara dan minta bantuan Fikri atau Ferlita).*

---

## 4. Aturan Koordinasi Khusus Project Turnamen.in

Pekerjaan kelima anggota saling terhubung dalam satu alur arsitektur:

```text
Desktop UI (Ferlita) -> Eel Bridge & API Client (Fikri) -> Flask REST API & Reports (Anisa) -> Tournament, Team & Bracket Services (Adriel) -> Auth & Repositories (Habil)
```

- **Ferlita** merancang UI/UX dan mengonsumsi metode dari `window.TurnamenAPI` serta `window.TurnamenBridge`.
- **Fikri** memastikan launcher desktop Eel dan komunikasi `api-client.js` ke server Flask berjalan sesuai kontrak frontend.
- **Habil** menyediakan skema database, layanan autentikasi RBAC 5 role, serta `MockDataStoreRepository` dan `SupabaseDataStoreRepository`.
- **Adriel** mengembangkan logika bisnis turnamen, tim, pertandingan, dan algoritma bracket Single Elimination di atas interface repository Habil.
- **Anisa** mengekspos logika bisnis Adriel dan Habil melalui endpoint `/api/v1/*`, menyusun laporan/pengumuman, serta menjaga pengujian integrasi.

**Prinsip Kerja Paralel:**
- Jangan menjadikan branch anggota sebagai proyek terpisah yang mengubah struktur dasar repository.
- Seluruh anggota dapat bekerja secara paralel menggunakan `APP_MODE=mock` tanpa harus menunggu anggota lain menyelesaikan seluruh tugasnya.
- Selama kelima anggota mematuhi kontrak di `docs/contracts/`, perubahan dari masing-masing branch akan tetap kompatibel saat digabungkan ke `main`.

---

## 5. Rekomendasi Branch Protection dan Akses GitHub

Untuk menjaga keamanan dan kerapian repository di GitHub, berikut adalah rekomendasi pengaturan repository bagi pemilik/admin repository:

1. **Akses Collaborator:**
   - Pastikan kelima anggota (Ferlita, Fikri, Habil, Adriel, dan Anisa) telah diundang sebagai **Collaborators** pada repository GitHub dengan izin **Write** (push) agar masing-masing dapat mengunggah branch kerjanya dan membuat Pull Request.
2. **Perlindungan Branch Utama (`main`):**
   - Aktifkan aturan perlindungan branch (*Branch protection rule* atau *Ruleset*) pada branch `main`.
   - Aktifkan opsi **Require a pull request before merging** agar perubahan tidak masuk secara langsung ke `main` tanpa peninjauan.
   - Aktifkan opsi **Block force pushes** dan larang penghapusan branch `main`.
3. **Pemeriksaan Sebelum Merge:**
   - Setiap Pull Request sebaiknya diperiksa oleh minimal satu anggota lain (misalnya Project Coordinator atau System Integrator) sebelum digabungkan.
   - Pemeriksaan otomatis (*GitHub Actions* untuk menjalankan `pytest` dan `python scripts/verify_starter.py`) dapat ditambahkan kemudian bila diperlukan oleh tim.
