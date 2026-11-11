# Instruksi Tugas Mandiri — ADRIEL (Tournament & Match System Developer)

---

## 1. Identitas dan Tanggung Jawab Anggota
- **Nama Anggota:** Adriel
- **Peran:** Tournament & Match System Developer
- **Tanggung Jawab Utama:**
  - Mengembangkan logika bisnis manajemen turnamen dan pendaftaran/registrasi tim.
  - Mengelola data tim e-sport dan roster pemain (`team_members`).
  - Merancang dan mengimplementasikan algoritma bracket **Single Elimination**.
  - Mengelola jadwal pertandingan, status pertandingan, validasi skor (`best_of`), penentuan pemenang, penanganan *bye*, dan perpindahan pemenang ke babak berikutnya (`next_match_id` & `next_slot`).
  - Menulis unit test menyeluruh untuk logika turnamen dan bracket.

## 2. Tujuan Pekerjaan
Menyediakan mesin kompetisi (**Tournament, Team, & Bracket Engine**) yang akurat, tahan terhadap input tidak valid, mendukung simulasi penuh 8 tim (Quarter Final → Semi Final → Grand Final) maupun jumlah tim bukan pangkat dua (*bye*), dan dapat diuji sepenuhnya tanpa memerlukan koneksi Supabase.

## 3. Daftar Tugas Terperinci
1. Mengembangkan `TournamentService` di `backend/modules/tournaments/service.py`:
   - Pembuatan turnamen, validasi kuota (`max_teams`), biaya, hadiah, dan format `best_of`.
   - Pendaftaran tim (`register_team`) dan verifikasi status pendaftaran (`approve`/`reject`).
2. Mengembangkan `TeamService` di `backend/modules/teams/service.py`:
   - Pembuatan tim, validasi keunikan nama/tag, dan penambahan anggota tim (`nickname`, `ingame_id`, `member_role`).
3. Mengembangkan `SingleEliminationBracketEngine` dan `MatchService` di `backend/modules/matches/`:
   - Pembuatan struktur bracket untuk 8 tim (4 QF, 2 SF, 1 Final) serta dukungan otomatis *bye* untuk jumlah tim bukan pangkat dua (mis. 5, 6, atau 7 tim).
   - Validasi skor berdasarkan aturan `best_of` (Bo1, Bo3, Bo5, Bo7) dan penolakan hasil seri pada sistem gugur (`allow_draw=False`).
   - Penetapan pemenang dan promosi otomatis pemenang ke `next_match_id` pada slot `A` atau `B`.
   - Perlindungan hasil pertandingan yang sudah `completed` agar tidak dapat ditimpa tanpa otorisasi `force_override` dan pencatatan `activity_logs`.
4. Menulis unit test di `tests/unit/test_bracket_engine.py`.

## 4. Folder yang Menjadi Tanggung Jawab
- `backend/modules/tournaments/`
- `backend/modules/teams/`
- `backend/modules/matches/`
- `tests/unit/test_bracket_engine.py`

## 5. File yang Harus Dibuat / Diubah
- `backend/modules/tournaments/service.py`
- `backend/modules/teams/service.py`
- `backend/modules/matches/bracket_engine.py`
- `backend/modules/matches/service.py`
- `tests/unit/test_bracket_engine.py`

## 6. Batas File yang Tidak Boleh Diubah Tanpa Koordinasi
- `desktop/*` dan `DESIGN.md` (Milik **Ferlita** & **Fikri**).
- `supabase/*`, `backend/modules/auth/*`, dan `backend/repositories/*` (Milik **Habil**).
- `backend/api/*`, `backend/modules/reports/*`, dan `backend/modules/announcements/*` (Milik **Anisa**).

## 7. Dependensi Modul
- Menggunakan `DataStoreRepositoryProtocol` dari `backend/repositories/` (Habil).
- Dipanggil oleh route handler Flask REST API di `backend/api/routes/` (Anisa).

## 8. Kontrak Input / Output
- **Struktur Match Wajib:**
  - `round_number`, `round_name`, `match_number`
  - `team_a_id`, `team_b_id`
  - `score_a`, `score_b`
  - `winner_team_id`
  - `status` (`scheduled`, `ongoing`, `completed`, `bye`, `disputed`)
  - `next_match_id`, `next_slot` (`'A'` atau `'B'`)
- **Output `submit_match_result`:** Mengembalikan dictionary `{"match": updated_match, "next_match": updated_next_match}`.

## 9. Mock Data yang Tersedia
Adriel dapat langsung menguji bracket 8 tim menggunakan data di `backend/repositories/mock/mock_data.py`:
- Turnamen `33333333-3333-4333-8333-333333333301` (*Nusantara Campus Cup 2026*) memiliki 8 tim `approved` (Seed #1 s.d. Seed #8) dan 7 pertandingan Single Elimination.

## 10. Cara Menjalankan Modul
```powershell
# Menjalankan unit test khusus algoritma bracket, bye, validasi skor, dan perpindahan babak
pytest tests/unit/test_bracket_engine.py -v
```

## 11. Skenario Pengujian
1. **Bracket 8 Tim:** Generate bracket untuk 8 tim, pastikan terbentuk 4 pertandingan Quarter Final (Round 1), 2 Semi Final (Round 2), dan 1 Grand Final (Round 3) dengan tautan `next_match_id` dan `next_slot` yang tepat.
2. **Perpindahan Pemenang Otomatis:** Sahkan hasil QF #4 (`score_a=2, score_b=1`), pastikan pemenang otomatis menempati `team_b_id` pada Semi Final #2. Lanjutkan hingga Grand Final dan pastikan juara turnamen terpilih.
3. **Validasi Skor & Seri:** Uji input skor `1-1` atau `3-0` pada pertandingan Best-of-3 (`best_of=3`); pastikan ditolak dengan `DomainValidationError`.
4. **Penanganan Bye (Jumlah Tim Bukan Pangkat Dua):** Generate bracket untuk 6 tim; pastikan ukuran bracket dibulatkan ke 8 slot, 2 tim unggulan teratas mendapat status `bye` di Round 1 dan langsung masuk ke Semi Final.
5. **Perlindungan Hasil Terkunci:** Coba ubah kembali pertandingan yang sudah `completed` tanpa flag `force_override=True`; pastikan ditolak dengan `DomainConflictError`.

## 12. Acceptance Criteria
- Algoritma Single Elimination 8 tim dan penanganan *bye* berfungsi 100% dan terdokumentasi.
- Pertandingan yang belum selesai tidak pernah memiliki `winner_team_id`.
- Seluruh unit test di `tests/unit/test_bracket_engine.py` lulus (`pytest`).

## 13. Checklist Pekerjaan
- [ ] Memverifikasi algoritma `SingleEliminationBracketEngine` untuk 4, 6, dan 8 tim.
- [ ] Memverifikasi aturan validasi skor Bo1, Bo3, Bo5, dan Bo7.
- [ ] Memastikan promosi pemenang ke `next_match_id` (`next_slot` A/B) berjalan otomatis.
- [ ] Menambahkan unit test untuk seluruh edge case.

## 14. Cara Menyerahkan Hasil ke Repository Utama
```powershell
git pull origin main
pytest -v
git add backend/modules/tournaments/ backend/modules/teams/ backend/modules/matches/ tests/unit/test_bracket_engine.py
git commit -m "feat(bracket): implement single elimination engine and match progression"
git push origin main
```

## 15. Agent Skills yang Wajib Dibaca Berdasarkan Addendum
Sebelum meminta bantuan AI Agent, pastikan agent membaca `AGENTS.md`, file tugas ini (`docs/tasks/adriel.md`), dan memuat skill berikut dari `.agents/skills/`:
- **Wajib:**
  - `antislop` (`.agents/skills/antislop/SKILL.md`)
  - `antislop-code` (`.agents/skills/antislop-code/SKILL.md`)
  - `turnamen-project-standards` (`.agents/skills/turnamen-project-standards/SKILL.md`)
  - `turnamen-bracket-engine` (`.agents/skills/turnamen-bracket-engine/SKILL.md`)
  - `turnamen-quality-gates` (`.agents/skills/turnamen-quality-gates/SKILL.md`)
- **Tambahan:**
  - `tdd` (`.agents/skills/tdd/SKILL.md`)
  - `team-code-review` (`.agents/skills/team-code-review/SKILL.md`)
