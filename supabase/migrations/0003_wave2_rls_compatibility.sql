-- Turnamen.in: Wave 2.1 Supabase RLS Compatibility RPCs
-- Migration: 0003_wave2_rls_compatibility.sql
-- Target: Supabase PostgreSQL 15+
-- Note: Local migration file prepared for Wave 4 deployment (not applied to Cloud yet).

-- Non-exposed schema housing privileged SECURITY DEFINER implementations.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon;
GRANT USAGE ON SCHEMA private TO authenticated;

-- ----------------------------------------------------------------------------
-- FAIL-1: Controlled tournament status transitions (supports assigned committee)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.transition_tournament_status(
    p_tournament_id UUID,
    p_new_status VARCHAR
)
RETURNS SETOF public.tournaments
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
    v_tournament public.tournaments%ROWTYPE;
    v_is_assigned BOOLEAN := FALSE;
    v_transition_allowed BOOLEAN := FALSE;
    v_final_match_count INTEGER := 0;
    v_final_completed BOOLEAN := FALSE;
    v_has_incomplete_matches BOOLEAN := FALSE;
    v_has_invalid_links BOOLEAN := FALSE;
BEGIN
    IF p_tournament_id IS NULL OR NULLIF(TRIM(COALESCE(p_new_status, '')), '') IS NULL THEN
        RAISE EXCEPTION 'tournament_id dan new_status wajib diisi.' USING ERRCODE = '22023';
    END IF;

    IF p_new_status NOT IN ('draft', 'open_registration', 'registration_closed', 'ongoing', 'completed', 'cancelled') THEN
        RAISE EXCEPTION 'Status turnamen tidak valid.' USING ERRCODE = '22023';
    END IF;

    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NULL THEN
        RAISE EXCEPTION 'Autentikasi diperlukan untuk mengubah status turnamen.' USING ERRCODE = '42501';
    END IF;

    SELECT id, role, is_active
    INTO v_actor
    FROM public.profiles
    WHERE auth_user_id = v_auth_uid
    LIMIT 1;

    IF NOT FOUND OR v_actor.is_active IS NOT TRUE THEN
        RAISE EXCEPTION 'Profil pengguna tidak ditemukan atau tidak aktif.' USING ERRCODE = '42501';
    END IF;

    SELECT *
    INTO v_tournament
    FROM public.tournaments
    WHERE id = p_tournament_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Turnamen tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    IF v_actor.role = 'super_admin' THEN
        NULL;
    ELSIF v_actor.role = 'organizer' THEN
        IF v_tournament.organizer_id IS DISTINCT FROM v_actor.id THEN
            RAISE EXCEPTION 'Organizer hanya dapat mengubah status turnamen miliknya.' USING ERRCODE = '42501';
        END IF;
    ELSIF v_actor.role = 'committee' THEN
        SELECT EXISTS (
            SELECT 1
            FROM public.tournament_staff ts
            WHERE ts.tournament_id = p_tournament_id
              AND ts.user_id = v_actor.id
        ) INTO v_is_assigned;

        IF NOT v_is_assigned THEN
            RAISE EXCEPTION 'Panitia hanya dapat mengubah status turnamen yang ditugaskan.' USING ERRCODE = '42501';
        END IF;

        IF p_new_status = 'ongoing'
           AND v_tournament.status IN ('draft', 'open_registration', 'registration_closed')
           AND EXISTS (SELECT 1 FROM public.matches m WHERE m.tournament_id = p_tournament_id) THEN
            NULL;
        ELSIF p_new_status = 'completed'
              AND v_tournament.status IN ('ongoing', 'completed') THEN
            NULL;
        ELSE
            RAISE EXCEPTION 'Panitia tidak diizinkan melakukan transisi status turnamen tersebut.' USING ERRCODE = '42501';
        END IF;
    ELSE
        RAISE EXCEPTION 'Role pengguna tidak diizinkan mengubah status turnamen.' USING ERRCODE = '42501';
    END IF;

    v_transition_allowed := (
        v_tournament.status = p_new_status
        OR (v_tournament.status = 'draft' AND p_new_status IN ('open_registration', 'registration_closed', 'cancelled'))
        OR (v_tournament.status = 'open_registration' AND p_new_status IN ('draft', 'registration_closed', 'ongoing', 'cancelled'))
        OR (v_tournament.status = 'registration_closed' AND p_new_status IN ('open_registration', 'ongoing', 'cancelled'))
        OR (v_tournament.status = 'ongoing' AND p_new_status IN ('completed', 'cancelled'))
    );

    IF NOT v_transition_allowed THEN
        RAISE EXCEPTION 'Transisi status turnamen tidak diizinkan.' USING ERRCODE = 'P0009';
    END IF;

    IF p_new_status = 'completed' THEN
        SELECT EXISTS (
            SELECT 1
            FROM public.matches m
            WHERE m.tournament_id = p_tournament_id
              AND m.next_match_id IS NOT NULL
              AND (
                  m.next_match_id = m.id
                  OR NOT EXISTS (
                      SELECT 1
                      FROM public.matches nx
                      WHERE nx.id = m.next_match_id
                        AND nx.tournament_id = p_tournament_id
                  )
              )
        ) INTO v_has_invalid_links;

        IF v_has_invalid_links THEN
            RAISE EXCEPTION 'Struktur bracket tidak valid: ditemukan tautan pertandingan lanjutan yang rusak.'
                USING ERRCODE = 'P0009';
        END IF;

        SELECT COUNT(*)
        INTO v_final_match_count
        FROM public.matches m
        WHERE m.tournament_id = p_tournament_id
          AND m.next_match_id IS NULL;

        IF v_final_match_count <> 1 THEN
            RAISE EXCEPTION 'Struktur bracket tidak valid: harus terdapat tepat satu pertandingan Grand Final.'
                USING ERRCODE = 'P0009';
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM public.matches m
            WHERE m.tournament_id = p_tournament_id
              AND m.next_match_id IS NULL
              AND m.status = 'completed'
              AND m.winner_team_id IS NOT NULL
        ) INTO v_final_completed;

        IF NOT v_final_completed THEN
            RAISE EXCEPTION 'Grand Final belum selesai dengan pemenang yang sah.'
                USING ERRCODE = 'P0009';
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM public.matches m
            WHERE m.tournament_id = p_tournament_id
              AND m.status NOT IN ('completed', 'bye')
        ) INTO v_has_incomplete_matches;

        IF v_has_incomplete_matches THEN
            RAISE EXCEPTION 'Turnamen belum dapat diselesaikan karena masih terdapat pertandingan yang belum selesai.'
                USING ERRCODE = 'P0009';
        END IF;
    END IF;

    UPDATE public.tournaments
    SET status = p_new_status,
        updated_at = NOW()
    WHERE id = p_tournament_id
    RETURNING * INTO v_tournament;

    RETURN NEXT v_tournament;
END;
$$;

REVOKE ALL ON FUNCTION private.transition_tournament_status(UUID, VARCHAR) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.transition_tournament_status(UUID, VARCHAR) TO authenticated;

CREATE OR REPLACE FUNCTION public.transition_tournament_status(
    p_tournament_id UUID,
    p_new_status VARCHAR
)
RETURNS SETOF public.tournaments
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT * FROM private.transition_tournament_status(p_tournament_id, p_new_status);
$$;

REVOKE ALL ON FUNCTION public.transition_tournament_status(UUID, VARCHAR) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.transition_tournament_status(UUID, VARCHAR) TO authenticated;

-- ----------------------------------------------------------------------------
-- FAIL-2: Minimal non-PII public profile lookup scoped to owned team roster
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_public_profile_summary(UUID);
DROP FUNCTION IF EXISTS private.get_public_profile_summary(UUID);

CREATE OR REPLACE FUNCTION private.get_public_profile_summary(
    p_profile_id UUID,
    p_team_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    username VARCHAR,
    full_name VARCHAR,
    avatar_url TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
    v_team_owner_id UUID;
BEGIN
    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NULL THEN
        RAISE EXCEPTION 'Autentikasi diperlukan untuk melihat ringkasan profil.' USING ERRCODE = '42501';
    END IF;

    SELECT p.id, p.role, p.is_active
    INTO v_actor
    FROM public.profiles p
    WHERE p.auth_user_id = v_auth_uid
    LIMIT 1;

    IF NOT FOUND OR v_actor.is_active IS NOT TRUE THEN
        RAISE EXCEPTION 'Akun pemanggil tidak aktif atau belum terhubung.' USING ERRCODE = '42501';
    END IF;

    IF v_actor.role = 'super_admin' THEN
        NULL;
    ELSIF v_actor.role = 'team_captain' THEN
        IF p_team_id IS NULL THEN
            RAISE EXCEPTION 'Team Captain wajib menyertakan team_id miliknya untuk lookup anggota.' USING ERRCODE = '42501';
        END IF;

        SELECT t.captain_id
        INTO v_team_owner_id
        FROM public.teams t
        WHERE t.id = p_team_id
        LIMIT 1;

        IF NOT FOUND OR v_team_owner_id IS DISTINCT FROM v_actor.id THEN
            RAISE EXCEPTION 'Team Captain hanya dapat mencari profil anggota untuk tim miliknya sendiri.' USING ERRCODE = '42501';
        END IF;
    ELSE
        RAISE EXCEPTION 'Hanya Super Admin atau Team Captain pemilik tim yang dapat melihat ringkasan profil anggota.' USING ERRCODE = '42501';
    END IF;

    IF p_profile_id IS NULL THEN
        RAISE EXCEPTION 'profile_id wajib diisi.' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    SELECT p.id, p.username, p.full_name, p.avatar_url
    FROM public.profiles p
    WHERE p.id = p_profile_id
      AND p.is_active = TRUE
    LIMIT 1;
END;
$$;

REVOKE ALL ON FUNCTION private.get_public_profile_summary(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.get_public_profile_summary(UUID, UUID) TO authenticated;

CREATE OR REPLACE FUNCTION public.get_public_profile_summary(
    p_profile_id UUID,
    p_team_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    username VARCHAR,
    full_name VARCHAR,
    avatar_url TEXT
)
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT id, username, full_name, avatar_url
    FROM private.get_public_profile_summary(p_profile_id, p_team_id);
$$;

REVOKE ALL ON FUNCTION public.get_public_profile_summary(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_public_profile_summary(UUID, UUID) TO authenticated;

-- ----------------------------------------------------------------------------
-- FAIL-3: Concurrency-safe atomic registration capacity & seed allocation
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.register_team_atomic(
    p_tournament_id UUID,
    p_team_id UUID,
    p_notes TEXT DEFAULT ''
)
RETURNS SETOF public.registrations
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
    v_tournament public.tournaments%ROWTYPE;
    v_team public.teams%ROWTYPE;
    v_existing public.registrations%ROWTYPE;
    v_result public.registrations%ROWTYPE;
    v_active_count INT := 0;
    v_next_seed INT := 1;
    v_clean_notes TEXT := TRIM(COALESCE(p_notes, ''));
BEGIN
    IF p_tournament_id IS NULL OR p_team_id IS NULL THEN
        RAISE EXCEPTION 'tournament_id dan team_id wajib diisi.' USING ERRCODE = '22023';
    END IF;

    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NULL THEN
        RAISE EXCEPTION 'Autentikasi diperlukan untuk mendaftarkan tim.' USING ERRCODE = '42501';
    END IF;

    SELECT id, role, is_active
    INTO v_actor
    FROM public.profiles
    WHERE auth_user_id = v_auth_uid
    LIMIT 1;

    IF NOT FOUND OR v_actor.is_active IS NOT TRUE THEN
        RAISE EXCEPTION 'Profil pengguna tidak aktif atau tidak ditemukan.' USING ERRCODE = '42501';
    END IF;

    IF v_actor.role NOT IN ('super_admin', 'team_captain') THEN
        RAISE EXCEPTION 'Role pengguna tidak diizinkan mendaftarkan tim.' USING ERRCODE = '42501';
    END IF;

    -- Lock tournament row so concurrent registrations serialize cleanly without deadlocks.
    SELECT *
    INTO v_tournament
    FROM public.tournaments
    WHERE id = p_tournament_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Turnamen tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    IF v_tournament.status <> 'open_registration' THEN
        RAISE EXCEPTION 'Pendaftaran ditutup untuk turnamen ini.' USING ERRCODE = 'P0009';
    END IF;

    SELECT *
    INTO v_team
    FROM public.teams
    WHERE id = p_team_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Tim tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    IF v_actor.role = 'team_captain' AND v_team.captain_id IS DISTINCT FROM v_actor.id THEN
        RAISE EXCEPTION 'Kapten hanya dapat mendaftarkan tim miliknya sendiri.' USING ERRCODE = '42501';
    END IF;

    IF v_team.game_id IS DISTINCT FROM v_tournament.game_id THEN
        RAISE EXCEPTION 'Game yang dimainkan tim tidak sesuai dengan game turnamen.' USING ERRCODE = '22023';
    END IF;

    SELECT *
    INTO v_existing
    FROM public.registrations r
    WHERE r.tournament_id = p_tournament_id
      AND r.team_id = p_team_id
    FOR UPDATE;

    IF FOUND AND v_existing.status <> 'withdrawn' THEN
        RAISE EXCEPTION 'Tim ini sudah terdaftar pada turnamen tersebut.' USING ERRCODE = 'P0009';
    END IF;

    SELECT COUNT(*)
    INTO v_active_count
    FROM public.registrations r
    WHERE r.tournament_id = p_tournament_id
      AND r.status IN ('pending', 'approved');

    IF v_active_count >= v_tournament.max_teams THEN
        RAISE EXCEPTION 'Kuota turnamen sudah penuh.' USING ERRCODE = 'P0009';
    END IF;

    SELECT COALESCE(MAX(r.seed_number), 0) + 1
    INTO v_next_seed
    FROM public.registrations r
    WHERE r.tournament_id = p_tournament_id;

    IF v_existing.id IS NOT NULL THEN
        UPDATE public.registrations
        SET registered_by = v_actor.id,
            status = 'pending',
            seed_number = v_next_seed,
            verified_by = NULL,
            verified_at = NULL,
            notes = v_clean_notes,
            registered_at = NOW(),
            updated_at = NOW()
        WHERE id = v_existing.id
        RETURNING * INTO v_result;
    ELSE
        INSERT INTO public.registrations (
            tournament_id,
            team_id,
            registered_by,
            status,
            seed_number,
            notes
        )
        VALUES (
            p_tournament_id,
            p_team_id,
            v_actor.id,
            'pending',
            v_next_seed,
            v_clean_notes
        )
        RETURNING * INTO v_result;
    END IF;

    RETURN NEXT v_result;
END;
$$;

REVOKE ALL ON FUNCTION private.register_team_atomic(UUID, UUID, TEXT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.register_team_atomic(UUID, UUID, TEXT) TO authenticated;

CREATE OR REPLACE FUNCTION public.register_team_atomic(
    p_tournament_id UUID,
    p_team_id UUID,
    p_notes TEXT DEFAULT ''
)
RETURNS SETOF public.registrations
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT * FROM private.register_team_atomic(p_tournament_id, p_team_id, p_notes);
$$;

REVOKE ALL ON FUNCTION public.register_team_atomic(UUID, UUID, TEXT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.register_team_atomic(UUID, UUID, TEXT) TO authenticated;
