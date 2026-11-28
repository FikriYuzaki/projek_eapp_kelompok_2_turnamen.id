-- Turnamen.in: Wave 5 Functional RPCs (Announcement Author Projection & Staff Management)
-- Migration: 0006_wave5_functional_rpc.sql
-- Target: Supabase PostgreSQL 15+ (Verified on PG 17/18)
-- Note: Preserves 0001-0005 untouched while adding strict least-privilege projections.

-- ----------------------------------------------------------------------------
-- 1. Safe announcement listing with author display name only (no PII)
--    Replaces direct SELECT on public.profiles which is blocked by 0005 RLS.
--    Lives directly in public (SECURITY DEFINER) so schema private keeps REVOKE ALL FROM anon.
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.list_tournament_announcements(UUID);
DROP FUNCTION IF EXISTS private.list_tournament_announcements(UUID);

CREATE OR REPLACE FUNCTION public.list_tournament_announcements(
    p_tournament_id UUID
)
RETURNS TABLE (
    id UUID,
    tournament_id UUID,
    author_id UUID,
    title VARCHAR,
    content TEXT,
    priority VARCHAR,
    is_pinned BOOLEAN,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    author_name VARCHAR
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_tournament RECORD;
    v_auth_uid UUID;
    v_actor RECORD;
    v_can_view_draft BOOLEAN := FALSE;
BEGIN
    IF p_tournament_id IS NULL THEN
        RETURN;
    END IF;

    SELECT t.id, t.status, t.organizer_id
    INTO v_tournament
    FROM public.tournaments t
    WHERE t.id = p_tournament_id
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Draft tournaments are restricted to super_admin, owning organizer, or assigned committee.
    IF v_tournament.status = 'draft' THEN
        v_auth_uid := (SELECT auth.uid());
        IF v_auth_uid IS NOT NULL THEN
            SELECT p.id, p.role, p.is_active
            INTO v_actor
            FROM public.profiles p
            WHERE p.auth_user_id = v_auth_uid
            LIMIT 1;

            IF FOUND AND v_actor.is_active IS TRUE THEN
                IF v_actor.role = 'super_admin' THEN
                    v_can_view_draft := TRUE;
                ELSIF v_actor.role = 'organizer' AND v_tournament.organizer_id = v_actor.id THEN
                    v_can_view_draft := TRUE;
                ELSIF v_actor.role = 'committee' AND EXISTS (
                    SELECT 1
                    FROM public.tournament_staff ts
                    WHERE ts.tournament_id = p_tournament_id
                      AND ts.user_id = v_actor.id
                ) THEN
                    v_can_view_draft := TRUE;
                END IF;
            END IF;
        END IF;

        IF NOT v_can_view_draft THEN
            RETURN;
        END IF;
    END IF;

    RETURN QUERY
    SELECT
        a.id,
        a.tournament_id,
        a.author_id,
        a.title,
        a.content,
        a.priority,
        a.is_pinned,
        a.published_at,
        a.created_at,
        a.updated_at,
        COALESCE(
            NULLIF(pg_catalog.btrim(p.full_name), ''),
            'Panitia'
        )::VARCHAR AS author_name
    FROM public.announcements a
    LEFT JOIN public.profiles p ON p.id = a.author_id AND p.is_active IS TRUE
    WHERE a.tournament_id = p_tournament_id
    ORDER BY a.is_pinned DESC, a.published_at DESC;
END;
$$;

REVOKE ALL ON FUNCTION public.list_tournament_announcements(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.list_tournament_announcements(UUID) TO anon, authenticated;

-- ----------------------------------------------------------------------------
-- 2. Scoped committee candidate lookup for tournament staff assignment
--    Restricted exclusively to active super_admin or organizer. Exposes no PII.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.list_committee_candidates()
RETURNS TABLE (
    id UUID,
    username VARCHAR,
    full_name VARCHAR,
    role VARCHAR
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
BEGIN
    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NULL THEN
        RAISE EXCEPTION 'Autentikasi diperlukan untuk melihat daftar kandidat panitia.' USING ERRCODE = '42501';
    END IF;

    SELECT p.id, p.role, p.is_active
    INTO v_actor
    FROM public.profiles p
    WHERE p.auth_user_id = v_auth_uid
    LIMIT 1;

    IF NOT FOUND OR v_actor.is_active IS NOT TRUE OR v_actor.role NOT IN ('super_admin', 'organizer') THEN
        RAISE EXCEPTION 'Hanya Super Admin atau Organizer aktif yang dapat melihat kandidat panitia.' USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
    SELECT p.id, p.username, p.full_name, p.role
    FROM public.profiles p
    WHERE p.role = 'committee'
      AND p.is_active IS TRUE
    ORDER BY p.full_name ASC, p.username ASC;
END;
$$;

REVOKE ALL ON FUNCTION private.list_committee_candidates() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.list_committee_candidates() TO authenticated;

CREATE OR REPLACE FUNCTION public.list_committee_candidates()
RETURNS TABLE (
    id UUID,
    username VARCHAR,
    full_name VARCHAR,
    role VARCHAR
)
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT * FROM private.list_committee_candidates();
$$;

REVOKE ALL ON FUNCTION public.list_committee_candidates() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_committee_candidates() TO authenticated;

-- ----------------------------------------------------------------------------
-- 3. Scoped tournament staff listing with non-PII profile labels
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.list_tournament_staff(
    p_tournament_id UUID
)
RETURNS TABLE (
    id UUID,
    tournament_id UUID,
    user_id UUID,
    staff_role VARCHAR,
    assigned_at TIMESTAMPTZ,
    username VARCHAR,
    full_name VARCHAR
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
    v_tournament RECORD;
BEGIN
    IF p_tournament_id IS NULL THEN
        RAISE EXCEPTION 'tournament_id wajib diisi.' USING ERRCODE = '22023';
    END IF;

    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NULL THEN
        RAISE EXCEPTION 'Autentikasi diperlukan untuk melihat daftar panitia turnamen.' USING ERRCODE = '42501';
    END IF;

    SELECT p.id, p.role, p.is_active
    INTO v_actor
    FROM public.profiles p
    WHERE p.auth_user_id = v_auth_uid
    LIMIT 1;

    IF NOT FOUND OR v_actor.is_active IS NOT TRUE THEN
        RAISE EXCEPTION 'Akun pemanggil tidak aktif atau belum terhubung.' USING ERRCODE = '42501';
    END IF;

    SELECT t.id, t.organizer_id
    INTO v_tournament
    FROM public.tournaments t
    WHERE t.id = p_tournament_id
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Turnamen tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    IF v_actor.role = 'super_admin' THEN
        NULL;
    ELSIF v_actor.role = 'organizer' AND v_tournament.organizer_id = v_actor.id THEN
        NULL;
    ELSIF v_actor.role = 'committee' AND EXISTS (
        SELECT 1
        FROM public.tournament_staff ts
        WHERE ts.tournament_id = p_tournament_id
          AND ts.user_id = v_actor.id
    ) THEN
        NULL;
    ELSE
        RAISE EXCEPTION 'Akses daftar panitia ditolak.' USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
    SELECT
        ts.id,
        ts.tournament_id,
        ts.user_id,
        ts.staff_role,
        ts.assigned_at,
        COALESCE(p.username, '')::VARCHAR AS username,
        COALESCE(p.full_name, '')::VARCHAR AS full_name
    FROM public.tournament_staff ts
    LEFT JOIN public.profiles p ON p.id = ts.user_id
    WHERE ts.tournament_id = p_tournament_id
    ORDER BY ts.assigned_at ASC;
END;
$$;

REVOKE ALL ON FUNCTION private.list_tournament_staff(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.list_tournament_staff(UUID) TO authenticated;

CREATE OR REPLACE FUNCTION public.list_tournament_staff(
    p_tournament_id UUID
)
RETURNS TABLE (
    id UUID,
    tournament_id UUID,
    user_id UUID,
    staff_role VARCHAR,
    assigned_at TIMESTAMPTZ,
    username VARCHAR,
    full_name VARCHAR
)
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT * FROM private.list_tournament_staff(p_tournament_id);
$$;

REVOKE ALL ON FUNCTION public.list_tournament_staff(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_tournament_staff(UUID) TO authenticated;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION public.list_tournament_announcements(UUID) TO service_role;
        GRANT EXECUTE ON FUNCTION private.list_committee_candidates() TO service_role;
        GRANT EXECUTE ON FUNCTION public.list_committee_candidates() TO service_role;
        GRANT EXECUTE ON FUNCTION private.list_tournament_staff(UUID) TO service_role;
        GRANT EXECUTE ON FUNCTION public.list_tournament_staff(UUID) TO service_role;
    END IF;
END;
$$;
