# Kontrak Database (Database Contract) — Turnamen.in

Dokumen ini merupakan kesepakatan resmi skema database antara **Habil** (Database & Auth), **Adriel** (Tournaments, Teams, Matches), **Anisa** (API, Announcements, Reports), dan **Fikri** (System Integration).

> [!WARNING]
> Jangan mengubah nama tabel, nama kolom, atau tipe data pada dokumen ini tanpa memperbarui `supabase/migrations/0001_initial_schema.sql`, `backend/repositories/interfaces/`, dan menginformasikan seluruh anggota tim.

---

## 1. Daftar 12 Tabel Inti

| No | Nama Tabel | Primary Key | Deskripsi Singkat |
| :- | :--- | :--- | :--- |
| 1 | `profiles` | `id (UUID)` | Data profil pengguna dan role aplikasi (`super_admin`, `organizer`, `committee`, `team_captain`, `player`). |
| 2 | `games` | `id (UUID)` | Katalog game yang dipertandingkan (bersifat game-agnostic: ukuran tim, `allow_draw`, `default_best_of`). |
| 3 | `tournaments` | `id (UUID)` | Data utama turnamen, jadwal, biaya registrasi, hadiah, format, dan status turnamen. |
| 4 | `teams` | `id (UUID)` | Entitas tim e-sport yang dipimpin oleh `captain_id` pada suatu `game_id`. |
| 5 | `team_members` | `id (UUID)` | Anggota/roster di dalam sebuah tim (`nickname`, `ingame_id`, `member_role`). |
| 6 | `tournament_staff` | `id (UUID)` | Penugasan pengguna ber-role `committee` pada suatu turnamen. |
| 7 | `registrations` | `id (UUID)` | Pendaftaran tim pada suatu turnamen beserta `status` dan `seed_number`. |
| 8 | `matches` | `id (UUID)` | Pertandingan bracket, skor `score_a` & `score_b`, pemenang `winner_team_id`, serta pointer `next_match_id` & `next_slot`. |
| 9 | `match_results` | `id (UUID)` | Rincian hasil per game/map dan jejak verifikasi panitia (`verified_by`, `verified_at`). |
| 10 | `payments` | `id (UUID)` | Bukti pembayaran pendaftaran turnamen dan status verifikasinya. |
| 11 | `announcements` | `id (UUID)` | Pengumuman resmi turnamen (`priority`: `normal`, `important`, `urgent`). |
| 12 | `activity_logs` | `id (UUID)` | Jejak audit (*audit trail*) untuk setiap perubahan penting (pengesahan skor, pembuatan bracket, perubahan status). |

---

## 2. Kontrak Kolom & Nilai Enum / Check Constraint

### A. `profiles`
- `id`: `UUID`
- `auth_user_id`: `UUID | None`
- `email`: `str` (Unique)
- `username`: `str` (Unique)
- `full_name`: `str`
- `role`: `'super_admin' | 'organizer' | 'committee' | 'team_captain' | 'player'`
- `phone`: `str | None`
- `avatar_url`: `str | None`
- `is_active`: `bool`
- `created_at`, `updated_at`: `ISO-8601 timestamp string`

### B. `games`
- `id`: `UUID`
- `slug`: `str` (Unique)
- `name`: `str`
- `genre`: `str`
- `platform`: `str`
- `team_size`: `int` (1..20)
- `max_substitutes`: `int` (0..10)
- `allow_draw`: `bool`
- `default_best_of`: `1 | 3 | 5 | 7`
- `external_rawg_slug`: `str | None`
- `is_active`: `bool`

### C. `tournaments`
- `id`: `UUID`
- `slug`: `str` (Unique)
- `title`: `str`
- `description`: `str`
- `game_id`: `UUID` (FK → `games.id`)
- `organizer_id`: `UUID` (FK → `profiles.id`)
- `format`: `'single_elimination'`
- `status`: `'draft' | 'open_registration' | 'registration_closed' | 'ongoing' | 'completed' | 'cancelled'`
- `max_teams`: `int` (2..128)
- `best_of`: `1 | 3 | 5 | 7`
- `allow_draw`: `bool`
- `registration_fee`: `float` (>= 0)
- `prize_pool`: `float` (>= 0)
- `rules`: `str`
- `venue`: `str`
- `start_date`, `end_date`: `ISO-8601 timestamp string`

### D. `teams` & `team_members`
- **`teams`**: `id`, `name` (Unique), `tag` (Unique), `game_id`, `captain_id`, `logo_url`, `region`, `is_verified`, `created_at`, `updated_at`.
- **`team_members`**: `id`, `team_id`, `user_id`, `nickname`, `ingame_id` (Unique per `team_id`), `member_role` (`'captain' | 'starter' | 'substitute' | 'coach'`), `is_active`.

### E. `registrations` & `payments`
- **`registrations`**: `id`, `tournament_id`, `team_id`, `registered_by`, `status` (`'pending' | 'approved' | 'rejected' | 'withdrawn'`), `seed_number`, `verified_by`, `verified_at`, `notes`, `registered_at`.
- **`payments`**: `id`, `registration_id` (Unique), `amount`, `payment_method`, `proof_url`, `status` (`'unpaid' | 'pending' | 'verified' | 'rejected' | 'refunded'`), `submitted_by`, `verified_by`, `verified_at`.

### F. `matches` & `match_results`
- **`matches`**:
  - `id`: `UUID`
  - `tournament_id`: `UUID`
  - `round_number`: `int` (>= 1)
  - `round_name`: `str` (mis. `'Quarter Final'`, `'Semi Final'`, `'Grand Final'`)
  - `match_number`: `int` (>= 1, berurutan dalam satu babak)
  - `team_a_id`: `UUID | None`
  - `team_b_id`: `UUID | None`
  - `score_a`: `int` (>= 0)
  - `score_b`: `int` (>= 0)
  - `winner_team_id`: `UUID | None` (Hanya boleh sama dengan `team_a_id` atau `team_b_id`)
  - `status`: `'scheduled' | 'ongoing' | 'completed' | 'bye' | 'disputed'`
  - `best_of`: `1 | 3 | 5 | 7`
  - `scheduled_at`, `completed_at`: `ISO-8601 timestamp string | None`
  - `next_match_id`: `UUID | None` (FK self-reference → `matches.id`)
  - `next_slot`: `'A' | 'B' | None`
- **`match_results`**: `id`, `match_id`, `game_number`, `score_a`, `score_b`, `winner_team_id`, `proof_url`, `notes`, `verified_by`, `verified_at`.

### G. `announcements` & `activity_logs`
- **`announcements`**: `id`, `tournament_id`, `author_id`, `title`, `content`, `priority` (`'normal' | 'important' | 'urgent'`), `is_pinned`, `published_at`.
- **`activity_logs`**: `id`, `actor_id`, `tournament_id`, `entity_type`, `entity_id`, `action`, `details` (`dict`), `created_at`.
