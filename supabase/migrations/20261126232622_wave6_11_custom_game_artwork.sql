-- Turnamen.in: Wave 6.11 Custom Game Artwork Management
-- Migration: 20261126232622_wave6_11_custom_game_artwork.sql
-- Created via: supabase migration new wave6_11_custom_game_artwork
-- Target: Supabase PostgreSQL 15+ & Supabase Storage (`game-artwork` bucket)

-- ============================================================================
-- 1. SEPARATE ARTWORK METADATA TABLE (`public.game_artwork_overrides`)
-- Keeps `public.games` untouched without widening write grants on `games`.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.game_artwork_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL UNIQUE
        REFERENCES public.games(id) ON DELETE CASCADE ON UPDATE CASCADE,
    storage_path TEXT NOT NULL
        CHECK (
            char_length(btrim(storage_path)) BETWEEN 10 AND 300
            AND storage_path !~ '^/'
            AND storage_path NOT LIKE '%..%'
            AND storage_path NOT LIKE '%://%'
            AND storage_path ~ '^[a-z0-9-]+/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpe?g|png|webp)$'
        ),
    mime_type VARCHAR(32) NOT NULL
        CHECK (mime_type IN ('image/jpeg', 'image/png', 'image/webp')),
    file_size_bytes INT NOT NULL
        CHECK (file_size_bytes > 0 AND file_size_bytes <= 5242880),
    width INT
        CHECK (width IS NULL OR (width >= 320 AND width <= 4096)),
    height INT
        CHECK (height IS NULL OR (height >= 180 AND height <= 4096)),
    uploaded_by UUID
        REFERENCES public.profiles(id) ON DELETE SET NULL ON UPDATE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_artwork_overrides_uploaded_by
    ON public.game_artwork_overrides(uploaded_by);

DROP TRIGGER IF EXISTS trg_game_artwork_overrides_updated_at
    ON public.game_artwork_overrides;
CREATE TRIGGER trg_game_artwork_overrides_updated_at
    BEFORE UPDATE ON public.game_artwork_overrides
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================================
-- 2. LEAST-PRIVILEGE GRANTS & RLS (`public.game_artwork_overrides`)
-- Reuses audited `public.current_user_role()` & `public.current_profile_id()`.
-- Zero new SECURITY DEFINER helpers added.
-- ============================================================================
ALTER TABLE public.game_artwork_overrides ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.game_artwork_overrides FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.game_artwork_overrides TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON TABLE public.game_artwork_overrides TO authenticated;

DROP POLICY IF EXISTS "Public read game artwork overrides" ON public.game_artwork_overrides;
DROP POLICY IF EXISTS "Super admin insert game artwork overrides" ON public.game_artwork_overrides;
DROP POLICY IF EXISTS "Super admin update game artwork overrides" ON public.game_artwork_overrides;
DROP POLICY IF EXISTS "Super admin delete game artwork overrides" ON public.game_artwork_overrides;

CREATE POLICY "Public read game artwork overrides" ON public.game_artwork_overrides
    FOR SELECT
    TO anon, authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.games g
            WHERE g.id = game_artwork_overrides.game_id
              AND (g.is_active = TRUE OR public.current_user_role() = 'super_admin')
        )
    );

CREATE POLICY "Super admin insert game artwork overrides" ON public.game_artwork_overrides
    FOR INSERT
    TO authenticated
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        AND uploaded_by = public.current_profile_id()
    );

CREATE POLICY "Super admin update game artwork overrides" ON public.game_artwork_overrides
    FOR UPDATE
    TO authenticated
    USING (public.current_user_role() = 'super_admin')
    WITH CHECK (
        public.current_user_role() = 'super_admin'
        AND uploaded_by = public.current_profile_id()
    );

CREATE POLICY "Super admin delete game artwork overrides" ON public.game_artwork_overrides
    FOR DELETE
    TO authenticated
    USING (public.current_user_role() = 'super_admin');

-- ============================================================================
-- 3. SUPABASE STORAGE BUCKET (`game-artwork`)
-- Public bucket serves `/storage/v1/object/public/game-artwork/<path>` directly
-- without granting broad `storage.objects` listing to `anon`.
-- Note: `storage.objects` is owned by `supabase_storage_admin` on Supabase Cloud
-- (while deployment role `postgres` is not a member), so the 4 `storage.objects`
-- RLS policies are intentionally managed via Supabase Dashboard -> Storage ->
-- Policies, keeping uploads fail-closed (`0` policies) until all 4 are created.
-- Guarded so plain PostgreSQL CI clusters without `storage` schema can execute cleanly.
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'storage' AND table_name = 'buckets'
    ) THEN
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'game-artwork',
            'game-artwork',
            TRUE,
            5242880,
            ARRAY['image/jpeg', 'image/png', 'image/webp']
        )
        ON CONFLICT (id) DO UPDATE
        SET public = EXCLUDED.public,
            file_size_limit = EXCLUDED.file_size_limit,
            allowed_mime_types = EXCLUDED.allowed_mime_types;
    END IF;
END;
$$;
