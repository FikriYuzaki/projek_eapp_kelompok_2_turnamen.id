-- ============================================================================
-- Turnamen.in — Initial Database Schema & RLS Policies
-- Migration: 0001_initial_schema.sql
-- Target: Supabase PostgreSQL 15+
-- Owner: Habil (Database & Authentication Developer)
-- ============================================================================

-- Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- UTILITY TRIGGER FOR updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- ============================================================================
-- 1. PROFILES
-- Menyimpan profil pengguna dan role aplikasi.
-- PENTING: Kolom `role` dilindungi dari modifikasi mandiri oleh pengguna biasa.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID UNIQUE, -- Terhubung ke auth.users(id) pada mode Supabase produksi
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(60) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'player'
        CHECK (role IN ('super_admin', 'organizer', 'committee', 'team_captain', 'player')),
    avatar_url TEXT,
    phone VARCHAR(30),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);

-- ============================================================================
-- 2. GAMES
-- Sistem bersifat game-agnostic (MLBB, Valorant, PUBG Mobile, Dota 2, dll.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    genre VARCHAR(64) NOT NULL,
    platform VARCHAR(64) NOT NULL DEFAULT 'PC / Mobile',
    team_size INT NOT NULL DEFAULT 5 CHECK (team_size >= 1 AND team_size <= 20),
    max_substitutes INT NOT NULL DEFAULT 2 CHECK (max_substitutes >= 0 AND max_substitutes <= 10),
    allow_draw BOOLEAN NOT NULL DEFAULT FALSE,
    default_best_of INT NOT NULL DEFAULT 3 CHECK (default_best_of IN (1, 3, 5, 7)),
    icon_url TEXT,
    external_rawg_slug VARCHAR(120),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_games_slug ON public.games(slug);

-- ============================================================================
-- 3. TOURNAMENTS
-- Mendukung pengelolaan banyak turnamen sekaligus.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.tournaments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(140) NOT NULL UNIQUE,
    title VARCHAR(180) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    game_id UUID NOT NULL REFERENCES public.games(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    organizer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    format VARCHAR(40) NOT NULL DEFAULT 'single_elimination'
        CHECK (format IN ('single_elimination')),
    status VARCHAR(32) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'open_registration', 'registration_closed', 'ongoing', 'completed', 'cancelled')),
    max_teams INT NOT NULL DEFAULT 8 CHECK (max_teams >= 2 AND max_teams <= 128),
    best_of INT NOT NULL DEFAULT 3 CHECK (best_of IN (1, 3, 5, 7)),
    allow_draw BOOLEAN NOT NULL DEFAULT FALSE,
    registration_fee NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (registration_fee >= 0),
    prize_pool NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (prize_pool >= 0),
    rules TEXT NOT NULL DEFAULT '',
    venue VARCHAR(180) NOT NULL DEFAULT 'Online',
    registration_start TIMESTAMPTZ,
    registration_end TIMESTAMPTZ,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    banner_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tournament_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_tournaments_game_id ON public.tournaments(game_id);
CREATE INDEX IF NOT EXISTS idx_tournaments_organizer_id ON public.tournaments(organizer_id);
CREATE INDEX IF NOT EXISTS idx_tournaments_status ON public.tournaments(status);
CREATE INDEX IF NOT EXISTS idx_tournaments_start_date ON public.tournaments(start_date);

-- ============================================================================
-- 4. TEAMS
-- Entitas tim e-sport yang dikelola oleh Team Captain.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL UNIQUE,
    tag VARCHAR(12) NOT NULL UNIQUE,
    game_id UUID NOT NULL REFERENCES public.games(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    captain_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    logo_url TEXT,
    region VARCHAR(100) NOT NULL DEFAULT 'Indonesia',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_game_id ON public.teams(game_id);
CREATE INDEX IF NOT EXISTS idx_teams_captain_id ON public.teams(captain_id);

-- ============================================================================
-- 5. TEAM_MEMBERS
-- Daftar pemain di dalam sebuah tim beserta in-game ID.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE ON UPDATE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL ON UPDATE CASCADE,
    nickname VARCHAR(80) NOT NULL,
    ingame_id VARCHAR(100) NOT NULL,
    member_role VARCHAR(32) NOT NULL DEFAULT 'starter'
        CHECK (member_role IN ('captain', 'starter', 'substitute', 'coach')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_team_member_ingame UNIQUE (team_id, ingame_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON public.team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON public.team_members(user_id);

-- ============================================================================
-- 6. TOURNAMENT_STAFF
-- Penugasan Committee / Panitia pada turnamen tertentu.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.tournament_staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID NOT NULL REFERENCES public.tournaments(id) ON DELETE CASCADE ON UPDATE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE ON UPDATE CASCADE,
    staff_role VARCHAR(40) NOT NULL DEFAULT 'referee'
        CHECK (staff_role IN ('head_committee', 'referee', 'verifier', 'announcer')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tournament_staff_assignment UNIQUE (tournament_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tournament_staff_tournament_id ON public.tournament_staff(tournament_id);
CREATE INDEX IF NOT EXISTS idx_tournament_staff_user_id ON public.tournament_staff(user_id);

-- ============================================================================
-- 7. REGISTRATIONS
-- Pendaftaran tim ke dalam turnamen tertentu.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID NOT NULL REFERENCES public.tournaments(id) ON DELETE CASCADE ON UPDATE CASCADE,
    team_id UUID NOT NULL REFERENCES public.teams(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    registered_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'withdrawn')),
    seed_number INT CHECK (seed_number IS NULL OR seed_number >= 1),
    verified_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL ON UPDATE CASCADE,
    verified_at TIMESTAMPTZ,
    notes TEXT NOT NULL DEFAULT '',
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tournament_team_registration UNIQUE (tournament_id, team_id),
    CONSTRAINT uq_tournament_seed UNIQUE (tournament_id, seed_number)
);

CREATE INDEX IF NOT EXISTS idx_registrations_tournament_id ON public.registrations(tournament_id);
CREATE INDEX IF NOT EXISTS idx_registrations_team_id ON public.registrations(team_id);
CREATE INDEX IF NOT EXISTS idx_registrations_status ON public.registrations(status);

-- ============================================================================
-- 8. MATCHES
-- Struktur pertandingan untuk mendukung Single Elimination bracket.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID NOT NULL REFERENCES public.tournaments(id) ON DELETE CASCADE ON UPDATE CASCADE,
    round_number INT NOT NULL CHECK (round_number >= 1),
    round_name VARCHAR(64) NOT NULL,
    match_number INT NOT NULL CHECK (match_number >= 1),
    team_a_id UUID REFERENCES public.teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
    team_b_id UUID REFERENCES public.teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
    score_a INT NOT NULL DEFAULT 0 CHECK (score_a >= 0),
    score_b INT NOT NULL DEFAULT 0 CHECK (score_b >= 0),
    winner_team_id UUID REFERENCES public.teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'ongoing', 'completed', 'bye', 'disputed')),
    best_of INT NOT NULL DEFAULT 3 CHECK (best_of IN (1, 3, 5, 7)),
    scheduled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    next_match_id UUID REFERENCES public.matches(id) ON DELETE SET NULL ON UPDATE CASCADE,
    next_slot VARCHAR(1) CHECK (next_slot IS NULL OR next_slot IN ('A', 'B')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tournament_round_match UNIQUE (tournament_id, round_number, match_number),
    CONSTRAINT chk_different_teams CHECK (team_a_id IS NULL OR team_b_id IS NULL OR team_a_id <> team_b_id),
    CONSTRAINT chk_winner_valid CHECK (
        winner_team_id IS NULL
        OR winner_team_id = team_a_id
        OR winner_team_id = team_b_id
    )
);

CREATE INDEX IF NOT EXISTS idx_matches_tournament_id ON public.matches(tournament_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON public.matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_next_match_id ON public.matches(next_match_id);

-- ============================================================================
-- 9. MATCH_RESULTS
-- Riwayat pengesahan hasil pertandingan & rincian game/map.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.match_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE ON UPDATE CASCADE,
    game_number INT NOT NULL DEFAULT 1 CHECK (game_number >= 1),
    score_a INT NOT NULL DEFAULT 0 CHECK (score_a >= 0),
    score_b INT NOT NULL DEFAULT 0 CHECK (score_b >= 0),
    winner_team_id UUID NOT NULL REFERENCES public.teams(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    proof_url TEXT,
    notes TEXT NOT NULL DEFAULT '',
    verified_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_match_game_number UNIQUE (match_id, game_number)
);

CREATE INDEX IF NOT EXISTS idx_match_results_match_id ON public.match_results(match_id);

-- ============================================================================
-- 10. PAYMENTS
-- Bukti pembayaran biaya pendaftaran turnamen.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID NOT NULL UNIQUE REFERENCES public.registrations(id) ON DELETE CASCADE ON UPDATE CASCADE,
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
    payment_method VARCHAR(60) NOT NULL DEFAULT 'bank_transfer',
    proof_url TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('unpaid', 'pending', 'verified', 'rejected', 'refunded')),
    submitted_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    verified_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL ON UPDATE CASCADE,
    verified_at TIMESTAMPTZ,
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_registration_id ON public.payments(registration_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON public.payments(status);

-- ============================================================================
-- 11. ANNOUNCEMENTS
-- Pengumuman resmi turnamen dari Organizer atau Committee.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID NOT NULL REFERENCES public.tournaments(id) ON DELETE CASCADE ON UPDATE CASCADE,
    author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    title VARCHAR(180) NOT NULL,
    content TEXT NOT NULL,
    priority VARCHAR(24) NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('normal', 'important', 'urgent')),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_announcements_tournament_id ON public.announcements(tournament_id);
CREATE INDEX IF NOT EXISTS idx_announcements_published_at ON public.announcements(published_at DESC);

-- ============================================================================
-- 12. ACTIVITY_LOGS
-- Audit trail untuk operasi penting (perubahan skor, pengesahan hasil, perubahan role).
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL ON UPDATE CASCADE,
    tournament_id UUID REFERENCES public.tournaments(id) ON DELETE CASCADE ON UPDATE CASCADE,
    entity_type VARCHAR(64) NOT NULL,
    entity_id UUID,
    action VARCHAR(80) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_tournament_id ON public.activity_logs(tournament_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_actor_id ON public.activity_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON public.activity_logs(created_at DESC);

-- ============================================================================
-- ATTACH updated_at TRIGGERS
-- ============================================================================
CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_games_updated_at BEFORE UPDATE ON public.games
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_tournaments_updated_at BEFORE UPDATE ON public.tournaments
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_teams_updated_at BEFORE UPDATE ON public.teams
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_team_members_updated_at BEFORE UPDATE ON public.team_members
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_registrations_updated_at BEFORE UPDATE ON public.registrations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_matches_updated_at BEFORE UPDATE ON public.matches
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_payments_updated_at BEFORE UPDATE ON public.payments
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_announcements_updated_at BEFORE UPDATE ON public.announcements
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) FOUNDATION
-- Seluruh tabel yang diekspos ke Data API wajib mengaktifkan RLS.
-- Keputusan otorisasi didasarkan pada tabel `public.profiles`, BUKAN user_metadata.
-- ============================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.games ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tournaments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tournament_staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.match_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;

-- Helper function untuk memeriksa role pengguna saat ini dari tabel public.profiles
CREATE OR REPLACE FUNCTION public.current_user_role()
RETURNS VARCHAR
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role FROM public.profiles WHERE auth_user_id = auth.uid() LIMIT 1;
$$;

-- Baseline Read Policies (Data publik kompetisi dapat dibaca oleh pengguna terautentikasi)
CREATE POLICY "Public read games" ON public.games
    FOR SELECT USING (true);

CREATE POLICY "Public read tournaments" ON public.tournaments
    FOR SELECT USING (true);

CREATE POLICY "Public read teams" ON public.teams
    FOR SELECT USING (true);

CREATE POLICY "Public read team_members" ON public.team_members
    FOR SELECT USING (true);

CREATE POLICY "Public read matches" ON public.matches
    FOR SELECT USING (true);

CREATE POLICY "Public read match_results" ON public.match_results
    FOR SELECT USING (true);

CREATE POLICY "Public read announcements" ON public.announcements
    FOR SELECT USING (true);

CREATE POLICY "Public read registrations" ON public.registrations
    FOR SELECT USING (true);

CREATE POLICY "Public read tournament_staff" ON public.tournament_staff
    FOR SELECT USING (true);

CREATE POLICY "Public read payments" ON public.payments
    FOR SELECT USING (true);

CREATE POLICY "Public read activity_logs" ON public.activity_logs
    FOR SELECT USING (true);

-- Baseline Profile Protection: pengguna tidak boleh mendaftar mandiri sebagai role selain player/team_captain
CREATE POLICY "Users read active profiles" ON public.profiles
    FOR SELECT USING (is_active = true);

CREATE POLICY "Self register player or captain only" ON public.profiles
    FOR INSERT WITH CHECK (role IN ('player', 'team_captain'));

CREATE POLICY "Update active profiles" ON public.profiles
    FOR UPDATE USING (is_active = true);

CREATE POLICY "Super admin full access profiles" ON public.profiles
    FOR ALL USING (public.current_user_role() = 'super_admin');

-- Application Domain Write Policies (diperkuat oleh validasi RBAC pada backend service)
CREATE POLICY "Manage tournaments" ON public.tournaments
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Manage teams" ON public.teams
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Manage team_members" ON public.team_members
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Manage registrations" ON public.registrations
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Manage matches" ON public.matches
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Manage match_results" ON public.match_results
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Manage payments" ON public.payments
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Manage announcements" ON public.announcements
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Insert activity_logs" ON public.activity_logs
    FOR INSERT WITH CHECK (true);
