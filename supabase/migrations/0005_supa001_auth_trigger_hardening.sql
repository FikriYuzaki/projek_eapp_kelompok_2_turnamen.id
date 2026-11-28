-- Turnamen.in: SUPA-001 Auth Trigger & Profile Hardening
-- Migration: 0005_supa001_auth_trigger_hardening.sql
-- Target: Supabase PostgreSQL 15+ (tested locally on PostgreSQL 18.6; target Cloud 17.11)

-- Non-exposed schema housing privileged SECURITY DEFINER implementations.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon;
GRANT USAGE ON SCHEMA private TO authenticated;

-- Enforce case-insensitive email uniqueness so concurrent or mixed-case signups cannot collide.
CREATE UNIQUE INDEX IF NOT EXISTS uq_profiles_lower_email
    ON public.profiles (LOWER(email));

-- Harden existing utility & RLS helper functions with an empty search_path.
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = pg_catalog.now();
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.set_updated_at() FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.current_profile_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT id
    FROM public.profiles
    WHERE auth_user_id = (SELECT auth.uid())
      AND is_active = TRUE
    LIMIT 1;
$$;

REVOKE ALL ON FUNCTION public.current_profile_id() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.current_profile_id() TO authenticated;

CREATE OR REPLACE FUNCTION public.current_user_role()
RETURNS VARCHAR
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT role
    FROM public.profiles
    WHERE auth_user_id = (SELECT auth.uid())
      AND is_active = TRUE
    LIMIT 1;
$$;

REVOKE ALL ON FUNCTION public.current_user_role() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.current_user_role() TO anon, authenticated;

CREATE OR REPLACE FUNCTION public.is_tournament_organizer(p_tournament_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
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

REVOKE ALL ON FUNCTION public.is_tournament_organizer(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_tournament_organizer(UUID) TO authenticated;

CREATE OR REPLACE FUNCTION public.is_tournament_committee(p_tournament_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
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

REVOKE ALL ON FUNCTION public.is_tournament_committee(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_tournament_committee(UUID) TO authenticated;

CREATE OR REPLACE FUNCTION public.is_team_captain(p_team_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
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

REVOKE ALL ON FUNCTION public.is_team_captain(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_team_captain(UUID) TO authenticated;

CREATE OR REPLACE FUNCTION public.replace_tournament_matches(
    p_tournament_id UUID,
    p_matches JSONB
)
RETURNS SETOF public.matches
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    IF p_tournament_id IS NULL THEN
        RAISE EXCEPTION 'tournament_id wajib diisi' USING ERRCODE = '22023';
    END IF;

    IF p_matches IS NULL THEN
        RAISE EXCEPTION 'p_matches tidak boleh bernilai NULL' USING ERRCODE = '22023';
    END IF;

    IF pg_catalog.jsonb_typeof(p_matches) <> 'array' THEN
        RAISE EXCEPTION 'p_matches harus berupa JSON array' USING ERRCODE = '22023';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM public.tournaments WHERE id = p_tournament_id) THEN
        RAISE EXCEPTION 'Turnamen tidak ditemukan' USING ERRCODE = 'P0002';
    END IF;

    IF pg_catalog.jsonb_array_length(p_matches) > 0 THEN
        IF EXISTS (
            SELECT 1
            FROM pg_catalog.jsonb_array_elements(p_matches) AS elem
            WHERE pg_catalog.jsonb_typeof(elem) <> 'object'
               OR NULLIF(pg_catalog.btrim(elem->>'round_number'), '') IS NULL
               OR NULLIF(pg_catalog.btrim(elem->>'match_number'), '') IS NULL
               OR (elem->>'round_number') !~ '^[0-9]+$'
               OR (elem->>'match_number') !~ '^[0-9]+$'
        ) THEN
            RAISE EXCEPTION 'Setiap elemen p_matches wajib berupa JSON object dengan round_number dan match_number bertipe integer positif'
                USING ERRCODE = '22023';
        END IF;
    END IF;

    DELETE FROM public.matches WHERE tournament_id = p_tournament_id;

    IF pg_catalog.jsonb_array_length(p_matches) > 0 THEN
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
            COALESCE((elem->>'id')::UUID, pg_catalog.gen_random_uuid()),
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
        FROM pg_catalog.jsonb_array_elements(p_matches) AS elem
        ORDER BY (elem->>'round_number')::INT DESC, (elem->>'match_number')::INT ASC;
    END IF;

    RETURN QUERY
    SELECT *
    FROM public.matches
    WHERE tournament_id = p_tournament_id
    ORDER BY round_number ASC, match_number ASC;
END;
$$;

REVOKE ALL ON FUNCTION public.replace_tournament_matches(UUID, JSONB) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.replace_tournament_matches(UUID, JSONB) TO authenticated;

-- Remove the NULL auth_user_id self-claim exception from profile update trigger.
-- SECURITY INVOKER ensures `current_user` reflects client roles (`anon`/`authenticated`),
-- while `(SELECT auth.uid())` catches calls executed inside SECURITY DEFINER helpers.
CREATE OR REPLACE FUNCTION public.prevent_profile_privilege_escalation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id THEN
        RAISE EXCEPTION 'Immutable field: profile id cannot be modified'
            USING ERRCODE = '42501';
    END IF;
    IF NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'Immutable field: created_at cannot be modified'
            USING ERRCODE = '42501';
    END IF;

    IF current_user IN ('anon', 'authenticated')
       OR COALESCE(
           NULLIF(pg_catalog.current_setting('request.jwt.claim.role', true), ''),
           NULLIF(pg_catalog.current_setting('request.jwt.claims', true), '')::jsonb ->> 'role',
           ''
       ) IN ('anon', 'authenticated')
       OR (SELECT auth.uid()) IS NOT NULL THEN
        IF COALESCE(public.current_user_role(), '') <> 'super_admin' THEN
            IF NEW.role IS DISTINCT FROM OLD.role THEN
                RAISE EXCEPTION 'Privilege escalation denied: role cannot be modified by non-admin user'
                    USING ERRCODE = '42501';
            END IF;
            IF NEW.is_active IS DISTINCT FROM OLD.is_active THEN
                RAISE EXCEPTION 'Privilege escalation denied: account active status cannot be modified by non-admin user'
                    USING ERRCODE = '42501';
            END IF;
            IF NEW.auth_user_id IS DISTINCT FROM OLD.auth_user_id THEN
                RAISE EXCEPTION 'Privilege escalation denied: auth_user_id cannot be modified directly'
                    USING ERRCODE = '42501';
            END IF;
            IF NEW.email IS DISTINCT FROM OLD.email THEN
                RAISE EXCEPTION 'Email address cannot be modified directly on profile'
                    USING ERRCODE = '42501';
            END IF;
            IF NEW.username IS DISTINCT FROM OLD.username THEN
                RAISE EXCEPTION 'Username cannot be modified directly by non-admin user'
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

-- Replace auth signup trigger: NEVER auto-link by email and NEVER grant privileged roles.
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_requested_role VARCHAR(32);
    v_safe_role VARCHAR(32);
    v_username VARCHAR(60);
    v_full_name VARCHAR(120);
    v_phone VARCHAR(30);
    v_clean_email TEXT;
    v_existing_profile RECORD;
BEGIN
    v_clean_email := pg_catalog.lower(pg_catalog.btrim(COALESCE(NEW.email, '')));
    IF v_clean_email = '' THEN
        RAISE EXCEPTION 'Email akun Auth tidak boleh kosong.'
            USING ERRCODE = '22023';
    END IF;

    -- Keep retries / already-linked users idempotent without altering existing profile attributes.
    SELECT id, auth_user_id, email, role
    INTO v_existing_profile
    FROM public.profiles
    WHERE auth_user_id = NEW.id
    LIMIT 1;

    IF FOUND THEN
        RETURN NEW;
    END IF;

    -- Refuse auto-linking onto any pre-existing or unlinked profile (SUPA-001 fix).
    SELECT id, auth_user_id, role
    INTO v_existing_profile
    FROM public.profiles
    WHERE id = NEW.id
       OR pg_catalog.lower(email) = v_clean_email
    LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION 'Email sudah terdaftar pada profil lain dan tidak dapat ditautkan otomatis.'
            USING ERRCODE = '23505';
    END IF;

    -- Public signup may only initialize player or team_captain; privileged roles are rejected.
    v_requested_role := pg_catalog.lower(
        pg_catalog.btrim(COALESCE(NEW.raw_user_meta_data->>'role', 'player'))
    );
    IF v_requested_role IN ('player', 'team_captain') THEN
        v_safe_role := v_requested_role;
    ELSE
        v_safe_role := 'player';
    END IF;

    v_username := COALESCE(
        NULLIF(pg_catalog.btrim(COALESCE(NEW.raw_user_meta_data->>'username', '')), ''),
        pg_catalog.left(pg_catalog.split_part(v_clean_email, '@', 1), 53)
            || '_'
            || pg_catalog.substr(pg_catalog.replace(NEW.id::text, '-', ''), 1, 6)
    );
    v_full_name := COALESCE(
        NULLIF(pg_catalog.btrim(COALESCE(NEW.raw_user_meta_data->>'full_name', '')), ''),
        v_username
    );
    v_phone := NULLIF(pg_catalog.btrim(COALESCE(NEW.raw_user_meta_data->>'phone', '')), '');

    INSERT INTO public.profiles (
        id, auth_user_id, email, username, full_name, role, phone, is_active
    )
    VALUES (
        NEW.id, NEW.id, v_clean_email, v_username, v_full_name, v_safe_role, v_phone, TRUE
    )
    ON CONFLICT (auth_user_id) DO NOTHING;

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

-- Tighten profiles SELECT policy so organizer/committee cannot read unrelated PII via PostgREST.
DROP POLICY IF EXISTS "Users read active profiles" ON public.profiles;
DROP POLICY IF EXISTS "Profiles select own or staff" ON public.profiles;
DROP POLICY IF EXISTS "Profiles select own or admin" ON public.profiles;
CREATE POLICY "Profiles select own or admin" ON public.profiles
    FOR SELECT
    TO authenticated
    USING (
        auth_user_id = (SELECT auth.uid())
        OR public.current_user_role() = 'super_admin'
    );

-- Trusted server-verified auth link RPC (active super_admin or service_role maintenance only).
CREATE OR REPLACE FUNCTION private.link_profile_auth_user(
    p_profile_id UUID,
    p_auth_user_id UUID
)
RETURNS SETOF public.profiles
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
    v_actor_id UUID := NULL;
    v_profile public.profiles%ROWTYPE;
    v_auth_user RECORD;
    v_jwt_role TEXT := COALESCE(
        NULLIF(pg_catalog.current_setting('request.jwt.claim.role', true), ''),
        NULLIF(pg_catalog.current_setting('request.jwt.claims', true), '')::jsonb ->> 'role',
        ''
    );
    v_local_role TEXT := COALESCE(pg_catalog.current_setting('role', true), '');
BEGIN
    IF p_profile_id IS NULL OR p_auth_user_id IS NULL THEN
        RAISE EXCEPTION 'profile_id dan auth_user_id wajib diisi.' USING ERRCODE = '22023';
    END IF;

    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NOT NULL THEN
        SELECT id, role, is_active
        INTO v_actor
        FROM public.profiles
        WHERE auth_user_id = v_auth_uid
        LIMIT 1;

        IF NOT FOUND OR v_actor.is_active IS NOT TRUE OR v_actor.role <> 'super_admin' THEN
            RAISE EXCEPTION 'Hanya Super Admin aktif yang dapat menautkan profil ke akun Auth.'
                USING ERRCODE = '42501';
        END IF;
        v_actor_id := v_actor.id;
    ELSIF v_jwt_role IN ('anon', 'authenticated')
       OR v_local_role IN ('anon', 'authenticated') THEN
        RAISE EXCEPTION 'Autentikasi Super Admin diperlukan untuk menautkan profil ke akun Auth.'
            USING ERRCODE = '42501';
    ELSIF v_jwt_role <> 'service_role'
       AND v_local_role <> 'service_role'
       AND session_user NOT IN ('postgres', 'supabase_admin') THEN
        RAISE EXCEPTION 'Akses ditolak untuk menautkan profil ke akun Auth.'
            USING ERRCODE = '42501';
    END IF;

    SELECT *
    INTO v_profile
    FROM public.profiles
    WHERE id = p_profile_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Profil pengguna tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    IF v_profile.auth_user_id IS NOT NULL THEN
        IF v_profile.auth_user_id = p_auth_user_id THEN
            RETURN NEXT v_profile;
            RETURN;
        END IF;
        RAISE EXCEPTION 'Profil sudah terhubung ke akun Auth lain yang sah.' USING ERRCODE = 'P0009';
    END IF;

    SELECT id, email, email_confirmed_at
    INTO v_auth_user
    FROM auth.users
    WHERE id = p_auth_user_id
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Akun Auth tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    IF v_auth_user.email_confirmed_at IS NULL THEN
        RAISE EXCEPTION 'Akun Auth harus terverifikasi email sebelum ditautkan.' USING ERRCODE = '42501';
    END IF;

    IF pg_catalog.lower(pg_catalog.btrim(COALESCE(v_auth_user.email, '')))
       <> pg_catalog.lower(pg_catalog.btrim(v_profile.email)) THEN
        RAISE EXCEPTION 'Email akun Auth tidak cocok dengan profil target.' USING ERRCODE = '22023';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.profiles p
        WHERE p.auth_user_id = p_auth_user_id
          AND p.id <> p_profile_id
    ) THEN
        RAISE EXCEPTION 'Akun Auth sudah terhubung ke profil lain.' USING ERRCODE = '23505';
    END IF;

    UPDATE public.profiles
    SET auth_user_id = p_auth_user_id,
        updated_at = pg_catalog.now()
    WHERE id = p_profile_id
    RETURNING * INTO v_profile;

    INSERT INTO public.activity_logs (
        actor_id, tournament_id, entity_type, entity_id, action, details
    )
    VALUES (
        COALESCE(v_actor_id, v_profile.id),
        NULL,
        'profile',
        v_profile.id,
        'PROFILE_AUTH_LINKED',
        pg_catalog.jsonb_build_object(
            'profile_id', v_profile.id,
            'auth_user_id', p_auth_user_id
        )
    );

    RETURN NEXT v_profile;
END;
$$;

REVOKE ALL ON FUNCTION private.link_profile_auth_user(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.link_profile_auth_user(UUID, UUID) TO authenticated;

CREATE OR REPLACE FUNCTION public.link_profile_auth_user(
    p_profile_id UUID,
    p_auth_user_id UUID
)
RETURNS SETOF public.profiles
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT * FROM private.link_profile_auth_user(p_profile_id, p_auth_user_id);
$$;

REVOKE ALL ON FUNCTION public.link_profile_auth_user(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.link_profile_auth_user(UUID, UUID) TO authenticated;

-- Explicit super_admin-only RPC for role assignment on linked profiles.
CREATE OR REPLACE FUNCTION private.assign_user_role(
    p_target_profile_id UUID,
    p_new_role VARCHAR
)
RETURNS SETOF public.profiles
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
    v_target public.profiles%ROWTYPE;
    v_clean_role VARCHAR(32);
    v_old_role VARCHAR(32);
BEGIN
    IF p_target_profile_id IS NULL OR NULLIF(pg_catalog.btrim(COALESCE(p_new_role, '')), '') IS NULL THEN
        RAISE EXCEPTION 'target_profile_id dan new_role wajib diisi.' USING ERRCODE = '22023';
    END IF;

    v_clean_role := pg_catalog.lower(pg_catalog.btrim(p_new_role));
    IF v_clean_role NOT IN ('player', 'team_captain', 'committee', 'organizer', 'super_admin') THEN
        RAISE EXCEPTION 'Role pengguna tidak valid.' USING ERRCODE = '22023';
    END IF;

    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NULL THEN
        RAISE EXCEPTION 'Autentikasi Super Admin diperlukan untuk menetapkan role.' USING ERRCODE = '42501';
    END IF;

    SELECT id, role, is_active
    INTO v_actor
    FROM public.profiles
    WHERE auth_user_id = v_auth_uid
    LIMIT 1;

    IF NOT FOUND OR v_actor.is_active IS NOT TRUE OR v_actor.role <> 'super_admin' THEN
        RAISE EXCEPTION 'Hanya Super Admin aktif yang dapat menetapkan role pengguna.' USING ERRCODE = '42501';
    END IF;

    SELECT *
    INTO v_target
    FROM public.profiles
    WHERE id = p_target_profile_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Profil pengguna tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    IF v_target.auth_user_id IS NULL THEN
        RAISE EXCEPTION 'Profil belum terhubung ke akun Auth yang sah.' USING ERRCODE = 'P0009';
    END IF;

    v_old_role := v_target.role;

    UPDATE public.profiles
    SET role = v_clean_role,
        updated_at = pg_catalog.now()
    WHERE id = p_target_profile_id
    RETURNING * INTO v_target;

    INSERT INTO public.activity_logs (
        actor_id, tournament_id, entity_type, entity_id, action, details
    )
    VALUES (
        v_actor.id,
        NULL,
        'profile',
        v_target.id,
        'USER_ROLE_UPDATED',
        pg_catalog.jsonb_build_object(
            'old_role', v_old_role,
            'new_role', v_clean_role
        )
    );

    RETURN NEXT v_target;
END;
$$;

REVOKE ALL ON FUNCTION private.assign_user_role(UUID, VARCHAR) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.assign_user_role(UUID, VARCHAR) TO authenticated;

CREATE OR REPLACE FUNCTION public.assign_user_role(
    p_target_profile_id UUID,
    p_new_role VARCHAR
)
RETURNS SETOF public.profiles
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT * FROM private.assign_user_role(p_target_profile_id, p_new_role);
$$;

REVOKE ALL ON FUNCTION public.assign_user_role(UUID, VARCHAR) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.assign_user_role(UUID, VARCHAR) TO authenticated;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT USAGE ON SCHEMA private TO service_role;
        GRANT EXECUTE ON FUNCTION private.link_profile_auth_user(UUID, UUID) TO service_role;
        GRANT EXECUTE ON FUNCTION public.link_profile_auth_user(UUID, UUID) TO service_role;
        GRANT EXECUTE ON FUNCTION private.assign_user_role(UUID, VARCHAR) TO service_role;
        GRANT EXECUTE ON FUNCTION public.assign_user_role(UUID, VARCHAR) TO service_role;
    END IF;
END;
$$;
