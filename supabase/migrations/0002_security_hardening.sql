-- Turnamen.in: Security Hardening, Supabase Auth Integration, and Least-Privilege RLS
-- Migration: 0002_security_hardening.sql
-- Target: Supabase PostgreSQL 15+
-- Owner: Habil (Database & Authentication Developer)

CREATE INDEX IF NOT EXISTS idx_profiles_auth_user_id ON public.profiles(auth_user_id);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_schema = 'public'
          AND table_name = 'profiles'
          AND constraint_name = 'fk_profiles_auth_user_id'
    ) THEN
        ALTER TABLE public.profiles
            ADD CONSTRAINT fk_profiles_auth_user_id
            FOREIGN KEY (auth_user_id) REFERENCES auth.users(id)
            ON DELETE SET NULL;
    END IF;
END;
$$;

-- Helper functions for identity and role resolution from trusted public.profiles
CREATE OR REPLACE FUNCTION public.current_profile_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT id
    FROM public.profiles
    WHERE auth_user_id = (SELECT auth.uid())
      AND is_active = TRUE
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.current_user_role()
RETURNS VARCHAR
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role
    FROM public.profiles
    WHERE auth_user_id = (SELECT auth.uid())
      AND is_active = TRUE
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.is_tournament_organizer(p_tournament_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.tournaments t
        JOIN public.profiles p ON p.id = t.organizer_id
        WHERE t.id = p_tournament_id
          AND p.auth_user_id = (SELECT auth.uid())
          AND p.role IN ('organizer', 'super_admin')
          AND p.is_active = TRUE
    );
$$;

CREATE OR REPLACE FUNCTION public.is_tournament_committee(p_tournament_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.tournament_staff ts
        JOIN public.profiles p ON p.id = ts.user_id
        WHERE ts.tournament_id = p_tournament_id
          AND p.auth_user_id = (SELECT auth.uid())
          AND p.role IN ('committee', 'organizer', 'super_admin')
          AND p.is_active = TRUE
    );
$$;

CREATE OR REPLACE FUNCTION public.is_team_captain(p_team_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.teams t
        JOIN public.profiles p ON p.id = t.captain_id
        WHERE t.id = p_team_id
          AND p.auth_user_id = (SELECT auth.uid())
          AND p.role IN ('team_captain', 'super_admin')
          AND p.is_active = TRUE
    );
$$;

-- Trigger to prevent privilege escalation on public.profiles via direct Data API UPDATE
CREATE OR REPLACE FUNCTION public.prevent_profile_privilege_escalation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF current_user IN ('anon', 'authenticated') OR (SELECT auth.uid()) IS NOT NULL THEN
        IF COALESCE(public.current_user_role(), '') <> 'super_admin' THEN
            IF NEW.role IS DISTINCT FROM OLD.role THEN
                RAISE EXCEPTION 'Privilege escalation denied: role cannot be modified by non-admin user'
                    USING ERRCODE = '42501';
            END IF;
            IF NEW.is_active IS DISTINCT FROM OLD.is_active THEN
                RAISE EXCEPTION 'Privilege escalation denied: account active status cannot be modified by non-admin user'
                    USING ERRCODE = '42501';
            END IF;
            IF OLD.auth_user_id IS NOT NULL AND NEW.auth_user_id IS DISTINCT FROM OLD.auth_user_id THEN
                RAISE EXCEPTION 'Privilege escalation denied: auth_user_id cannot be reassigned'
                    USING ERRCODE = '42501';
            END IF;
            IF NEW.email IS DISTINCT FROM OLD.email THEN
                RAISE EXCEPTION 'Email address cannot be modified directly on profile'
                    USING ERRCODE = '42501';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.prevent_profile_privilege_escalation() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS trg_prevent_profile_privilege_escalation ON public.profiles;
CREATE TRIGGER trg_prevent_profile_privilege_escalation
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.prevent_profile_privilege_escalation();

-- Trigger to synchronize new Supabase Auth users into public.profiles safely
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_requested_role VARCHAR(32);
    v_safe_role VARCHAR(32);
    v_username VARCHAR(60);
    v_full_name VARCHAR(120);
BEGIN
    v_requested_role := COALESCE(LOWER(TRIM(NEW.raw_user_meta_data->>'role')), 'player');
    IF v_requested_role IN ('player', 'team_captain') THEN
        v_safe_role := v_requested_role;
    ELSE
        v_safe_role := 'player';
    END IF;

    v_username := COALESCE(
        NULLIF(TRIM(NEW.raw_user_meta_data->>'username'), ''),
        SPLIT_PART(LOWER(NEW.email), '@', 1) || '_' || SUBSTR(REPLACE(NEW.id::text, '-', ''), 1, 6)
    );
    v_full_name := COALESCE(
        NULLIF(TRIM(NEW.raw_user_meta_data->>'full_name'), ''),
        v_username
    );

    UPDATE public.profiles
    SET auth_user_id = NEW.id,
        updated_at = NOW()
    WHERE LOWER(email) = LOWER(NEW.email)
      AND auth_user_id IS NULL;

    IF NOT FOUND THEN
        INSERT INTO public.profiles (id, auth_user_id, email, username, full_name, role, is_active)
        VALUES (NEW.id, NEW.id, LOWER(NEW.email), v_username, v_full_name, v_safe_role, TRUE)
        ON CONFLICT (auth_user_id) DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.handle_new_auth_user() FROM PUBLIC, anon, authenticated;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();
    END IF;
END;
$$;

-- Transactional RPC for atomic bracket replacement (prevents partial deletion if insert fails)
CREATE OR REPLACE FUNCTION public.replace_tournament_matches(
    p_tournament_id UUID,
    p_matches JSONB
)
RETURNS SETOF public.matches
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
    IF p_tournament_id IS NULL THEN
        RAISE EXCEPTION 'tournament_id wajib diisi' USING ERRCODE = '22023';
    END IF;

    DELETE FROM public.matches WHERE tournament_id = p_tournament_id;

    IF p_matches IS NOT NULL AND jsonb_typeof(p_matches) = 'array' AND jsonb_array_length(p_matches) > 0 THEN
        INSERT INTO public.matches (
            id,
            tournament_id,
            round_number,
            round_name,
            match_number,
            team_a_id,
            team_b_id,
            score_a,
            score_b,
            winner_team_id,
            status,
            best_of,
            scheduled_at,
            completed_at,
            next_match_id,
            next_slot
        )
        SELECT
            COALESCE((elem->>'id')::UUID, gen_random_uuid()),
            p_tournament_id,
            (elem->>'round_number')::INT,
            elem->>'round_name',
            (elem->>'match_number')::INT,
            NULLIF(elem->>'team_a_id', '')::UUID,
            NULLIF(elem->>'team_b_id', '')::UUID,
            COALESCE((elem->>'score_a')::INT, 0),
            COALESCE((elem->>'score_b')::INT, 0),
            NULLIF(elem->>'winner_team_id', '')::UUID,
            COALESCE(elem->>'status', 'scheduled'),
            COALESCE((elem->>'best_of')::INT, 3),
            NULLIF(elem->>'scheduled_at', '')::TIMESTAMPTZ,
            NULLIF(elem->>'completed_at', '')::TIMESTAMPTZ,
            NULLIF(elem->>'next_match_id', '')::UUID,
            NULLIF(elem->>'next_slot', '')
        FROM jsonb_array_elements(p_matches) AS elem
        ORDER BY (elem->>'round_number')::INT DESC, (elem->>'match_number')::INT ASC;
    END IF;

    RETURN QUERY
    SELECT *
    FROM public.matches
    WHERE tournament_id = p_tournament_id
    ORDER BY round_number ASC, match_number ASC;
END;
$$;

-- Ensure RLS is enabled on all 12 domain tables
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

-- Remove any legacy or overly permissive policies before applying hardened policies
DROP POLICY IF EXISTS "Users read active profiles" ON public.profiles;
DROP POLICY IF EXISTS "Super admin full access profiles" ON public.profiles;
DROP POLICY IF EXISTS "Self register player or captain only" ON public.profiles;
DROP POLICY IF EXISTS "Update active profiles" ON public.profiles;
DROP POLICY IF EXISTS "Profiles select own or staff" ON public.profiles;
DROP POLICY IF EXISTS "Profiles insert self registration" ON public.profiles;
DROP POLICY IF EXISTS "Profiles update own" ON public.profiles;

DROP POLICY IF EXISTS "Public read games" ON public.games;
DROP POLICY IF EXISTS "Super admin manage games" ON public.games;

DROP POLICY IF EXISTS "Public read tournaments" ON public.tournaments;
DROP POLICY IF EXISTS "Manage tournaments" ON public.tournaments;
DROP POLICY IF EXISTS "Organizer or admin insert tournaments" ON public.tournaments;
DROP POLICY IF EXISTS "Organizer or admin update tournaments" ON public.tournaments;
DROP POLICY IF EXISTS "Organizer or admin delete tournaments" ON public.tournaments;

DROP POLICY IF EXISTS "Public read teams" ON public.teams;
DROP POLICY IF EXISTS "Manage teams" ON public.teams;
DROP POLICY IF EXISTS "Captain or admin insert teams" ON public.teams;
DROP POLICY IF EXISTS "Captain or admin update teams" ON public.teams;
DROP POLICY IF EXISTS "Admin delete teams" ON public.teams;

DROP POLICY IF EXISTS "Public read team_members" ON public.team_members;
DROP POLICY IF EXISTS "Manage team_members" ON public.team_members;
DROP POLICY IF EXISTS "Captain or admin insert team_members" ON public.team_members;
DROP POLICY IF EXISTS "Captain or admin update team_members" ON public.team_members;
DROP POLICY IF EXISTS "Captain or admin delete team_members" ON public.team_members;

DROP POLICY IF EXISTS "Public read tournament_staff" ON public.tournament_staff;
DROP POLICY IF EXISTS "Staff or organizer read tournament_staff" ON public.tournament_staff;
DROP POLICY IF EXISTS "Organizer or admin manage tournament_staff" ON public.tournament_staff;

DROP POLICY IF EXISTS "Public read registrations" ON public.registrations;
DROP POLICY IF EXISTS "Manage registrations" ON public.registrations;
DROP POLICY IF EXISTS "Public read approved registrations" ON public.registrations;
DROP POLICY IF EXISTS "Participants and staff read registrations" ON public.registrations;
DROP POLICY IF EXISTS "Captain or admin insert registrations" ON public.registrations;
DROP POLICY IF EXISTS "Staff or admin update registrations" ON public.registrations;
DROP POLICY IF EXISTS "Admin delete registrations" ON public.registrations;

DROP POLICY IF EXISTS "Public read matches" ON public.matches;
DROP POLICY IF EXISTS "Manage matches" ON public.matches;
DROP POLICY IF EXISTS "Staff or admin insert matches" ON public.matches;
DROP POLICY IF EXISTS "Staff or admin update matches" ON public.matches;
DROP POLICY IF EXISTS "Staff or admin delete matches" ON public.matches;

DROP POLICY IF EXISTS "Public read match_results" ON public.match_results;
DROP POLICY IF EXISTS "Manage match_results" ON public.match_results;
DROP POLICY IF EXISTS "Staff or admin insert match_results" ON public.match_results;
DROP POLICY IF EXISTS "Staff or admin update match_results" ON public.match_results;
DROP POLICY IF EXISTS "Admin delete match_results" ON public.match_results;

DROP POLICY IF EXISTS "Public read payments" ON public.payments;
DROP POLICY IF EXISTS "Manage payments" ON public.payments;
DROP POLICY IF EXISTS "Authorized read payments" ON public.payments;
DROP POLICY IF EXISTS "Captain or admin insert payments" ON public.payments;
DROP POLICY IF EXISTS "Staff or admin update payments" ON public.payments;

DROP POLICY IF EXISTS "Public read announcements" ON public.announcements;
DROP POLICY IF EXISTS "Manage announcements" ON public.announcements;
DROP POLICY IF EXISTS "Staff or admin insert announcements" ON public.announcements;
DROP POLICY IF EXISTS "Staff or admin update announcements" ON public.announcements;
DROP POLICY IF EXISTS "Staff or admin delete announcements" ON public.announcements;

DROP POLICY IF EXISTS "Public read activity_logs" ON public.activity_logs;
DROP POLICY IF EXISTS "Insert activity_logs" ON public.activity_logs;
DROP POLICY IF EXISTS "Authorized read activity_logs" ON public.activity_logs;
DROP POLICY IF EXISTS "Authenticated insert own activity_logs" ON public.activity_logs;

-- 1. PROFILES RLS (Private personal data protected from anonymous and unauthorized scraping)
CREATE POLICY "Profiles select own or staff" ON public.profiles
    FOR SELECT
    TO authenticated
    USING (
        auth_user_id = (SELECT auth.uid())
        OR public.current_user_role() IN ('super_admin', 'organizer', 'committee')
    );

CREATE POLICY "Profiles insert self registration" ON public.profiles
    FOR INSERT
    TO authenticated
    WITH CHECK (
        auth_user_id = (SELECT auth.uid())
        AND role IN ('player', 'team_captain')
        AND is_active = TRUE
    );

CREATE POLICY "Profiles update own" ON public.profiles
    FOR UPDATE
    TO authenticated
    USING (
        auth_user_id = (SELECT auth.uid())
        AND is_active = TRUE
    )
    WITH CHECK (
        auth_user_id = (SELECT auth.uid())
        AND is_active = TRUE
        AND role = (SELECT p.role FROM public.profiles p WHERE p.id = profiles.id)
        AND email = (SELECT p.email FROM public.profiles p WHERE p.id = profiles.id)
    );

CREATE POLICY "Super admin full access profiles" ON public.profiles
    FOR ALL
    TO authenticated
    USING (public.current_user_role() = 'super_admin')
    WITH CHECK (public.current_user_role() = 'super_admin');

-- 2. GAMES RLS
CREATE POLICY "Public read games" ON public.games
    FOR SELECT
    TO anon, authenticated
    USING (is_active = TRUE OR public.current_user_role() = 'super_admin');

CREATE POLICY "Super admin manage games" ON public.games
    FOR ALL
    TO authenticated
    USING (public.current_user_role() = 'super_admin')
    WITH CHECK (public.current_user_role() = 'super_admin');

-- 3. TOURNAMENTS RLS
CREATE POLICY "Public read tournaments" ON public.tournaments
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Organizer or admin insert tournaments" ON public.tournaments
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'organizer'
            AND organizer_id = public.current_profile_id()
        )
    );

CREATE POLICY "Organizer or admin update tournaments" ON public.tournaments
    FOR UPDATE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'organizer'
            AND organizer_id = public.current_profile_id()
        )
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'organizer'
            AND organizer_id = public.current_profile_id()
        )
    );

CREATE POLICY "Organizer or admin delete tournaments" ON public.tournaments
    FOR DELETE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'organizer'
            AND organizer_id = public.current_profile_id()
        )
    );

-- 4. TEAMS RLS
CREATE POLICY "Public read teams" ON public.teams
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Captain or admin insert teams" ON public.teams
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND captain_id = public.current_profile_id()
        )
    );

CREATE POLICY "Captain or admin update teams" ON public.teams
    FOR UPDATE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND captain_id = public.current_profile_id()
        )
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND captain_id = public.current_profile_id()
        )
    );

CREATE POLICY "Admin delete teams" ON public.teams
    FOR DELETE
    TO authenticated
    USING (public.current_user_role() = 'super_admin');

-- 5. TEAM_MEMBERS RLS
CREATE POLICY "Public read team_members" ON public.team_members
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Captain or admin insert team_members" ON public.team_members
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND public.is_team_captain(team_id)
        )
    );

CREATE POLICY "Captain or admin update team_members" ON public.team_members
    FOR UPDATE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND public.is_team_captain(team_id)
        )
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND public.is_team_captain(team_id)
        )
    );

CREATE POLICY "Captain or admin delete team_members" ON public.team_members
    FOR DELETE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND public.is_team_captain(team_id)
        )
    );

-- 6. TOURNAMENT_STAFF RLS
CREATE POLICY "Staff or organizer read tournament_staff" ON public.tournament_staff
    FOR SELECT
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR user_id = public.current_profile_id()
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    );

CREATE POLICY "Organizer or admin manage tournament_staff" ON public.tournament_staff
    FOR ALL
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
    );

-- 7. REGISTRATIONS RLS
CREATE POLICY "Public read approved registrations" ON public.registrations
    FOR SELECT
    TO anon, authenticated
    USING (status = 'approved');

CREATE POLICY "Participants and staff read registrations" ON public.registrations
    FOR SELECT
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR registered_by = public.current_profile_id()
        OR public.is_team_captain(team_id)
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    );

CREATE POLICY "Captain or admin insert registrations" ON public.registrations
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND registered_by = public.current_profile_id()
            AND public.is_team_captain(team_id)
            AND status = 'pending'
        )
    );

CREATE POLICY "Staff or admin update registrations" ON public.registrations
    FOR UPDATE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    );

CREATE POLICY "Admin delete registrations" ON public.registrations
    FOR DELETE
    TO authenticated
    USING (public.current_user_role() = 'super_admin');

-- 8. MATCHES RLS
CREATE POLICY "Public read matches" ON public.matches
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Staff or admin insert matches" ON public.matches
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    );

CREATE POLICY "Staff or admin update matches" ON public.matches
    FOR UPDATE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    );

CREATE POLICY "Staff or admin delete matches" ON public.matches
    FOR DELETE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR public.is_tournament_committee(tournament_id)
    );

-- 9. MATCH_RESULTS RLS
CREATE POLICY "Public read match_results" ON public.match_results
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Staff or admin insert match_results" ON public.match_results
    FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.matches m
            WHERE m.id = match_results.match_id
              AND (
                  public.current_user_role() = 'super_admin'
                  OR public.is_tournament_organizer(m.tournament_id)
                  OR public.is_tournament_committee(m.tournament_id)
              )
        )
    );

CREATE POLICY "Staff or admin update match_results" ON public.match_results
    FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.matches m
            WHERE m.id = match_results.match_id
              AND (
                  public.current_user_role() = 'super_admin'
                  OR public.is_tournament_organizer(m.tournament_id)
                  OR public.is_tournament_committee(m.tournament_id)
              )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.matches m
            WHERE m.id = match_results.match_id
              AND (
                  public.current_user_role() = 'super_admin'
                  OR public.is_tournament_organizer(m.tournament_id)
                  OR public.is_tournament_committee(m.tournament_id)
              )
        )
    );

CREATE POLICY "Admin delete match_results" ON public.match_results
    FOR DELETE
    TO authenticated
    USING (public.current_user_role() = 'super_admin');

-- 10. PAYMENTS RLS (Sensitive financial records restricted to owner captain, tournament staff, and admin)
CREATE POLICY "Authorized read payments" ON public.payments
    FOR SELECT
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR submitted_by = public.current_profile_id()
        OR EXISTS (
            SELECT 1
            FROM public.registrations r
            WHERE r.id = payments.registration_id
              AND (
                  public.is_team_captain(r.team_id)
                  OR public.is_tournament_organizer(r.tournament_id)
                  OR public.is_tournament_committee(r.tournament_id)
              )
        )
    );

CREATE POLICY "Captain or admin insert payments" ON public.payments
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            public.current_user_role() = 'team_captain'
            AND submitted_by = public.current_profile_id()
            AND EXISTS (
                SELECT 1
                FROM public.registrations r
                WHERE r.id = payments.registration_id
                  AND public.is_team_captain(r.team_id)
            )
        )
    );

CREATE POLICY "Staff or admin update payments" ON public.payments
    FOR UPDATE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR EXISTS (
            SELECT 1
            FROM public.registrations r
            WHERE r.id = payments.registration_id
              AND (
                  public.is_tournament_organizer(r.tournament_id)
                  OR public.is_tournament_committee(r.tournament_id)
              )
        )
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR EXISTS (
            SELECT 1
            FROM public.registrations r
            WHERE r.id = payments.registration_id
              AND (
                  public.is_tournament_organizer(r.tournament_id)
                  OR public.is_tournament_committee(r.tournament_id)
              )
        )
    );

-- 11. ANNOUNCEMENTS RLS
CREATE POLICY "Public read announcements" ON public.announcements
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Staff or admin insert announcements" ON public.announcements
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR (
            (public.is_tournament_organizer(tournament_id) OR public.is_tournament_committee(tournament_id))
            AND author_id = public.current_profile_id()
        )
    );

CREATE POLICY "Staff or admin update announcements" ON public.announcements
    FOR UPDATE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR (public.is_tournament_committee(tournament_id) AND author_id = public.current_profile_id())
    )
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR (public.is_tournament_committee(tournament_id) AND author_id = public.current_profile_id())
    );

CREATE POLICY "Staff or admin delete announcements" ON public.announcements
    FOR DELETE
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR public.is_tournament_organizer(tournament_id)
        OR (public.is_tournament_committee(tournament_id) AND author_id = public.current_profile_id())
    );

-- 12. ACTIVITY_LOGS RLS (Append-only audit trail; restricted read and insert, no update/delete)
CREATE POLICY "Authorized read activity_logs" ON public.activity_logs
    FOR SELECT
    TO authenticated
    USING (
        public.current_user_role() = 'super_admin'
        OR actor_id = public.current_profile_id()
        OR (
            tournament_id IS NOT NULL
            AND (
                public.is_tournament_organizer(tournament_id)
                OR public.is_tournament_committee(tournament_id)
            )
        )
    );

CREATE POLICY "Authenticated insert own activity_logs" ON public.activity_logs
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        OR actor_id = public.current_profile_id()
    );
