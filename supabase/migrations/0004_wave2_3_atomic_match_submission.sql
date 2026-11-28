-- Turnamen.in: Wave 2.3 Atomic Match Submission & Full Bracket Graph Integrity
-- Migration: 0004_wave2_3_atomic_match_submission.sql
-- Target: Supabase PostgreSQL 15+
-- Note: Local migration prepared for Wave 4 deployment (not applied to Cloud yet).

CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon;
GRANT USAGE ON SCHEMA private TO authenticated;

-- ----------------------------------------------------------------------------
-- 1. Idempotency Ledger for Match Submission / Override Retries
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.match_submission_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE ON UPDATE CASCADE,
    actor_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    idempotency_key VARCHAR(128) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_match_submission_idempotency UNIQUE (match_id, actor_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_match_submission_requests_match_id
    ON public.match_submission_requests(match_id);

ALTER TABLE public.match_submission_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.match_submission_requests FROM PUBLIC, anon;
REVOKE INSERT, UPDATE, DELETE ON TABLE public.match_submission_requests FROM authenticated;
GRANT SELECT ON TABLE public.match_submission_requests TO authenticated;

DROP POLICY IF EXISTS "Staff or self read match_submission_requests" ON public.match_submission_requests;
CREATE POLICY "Staff or self read match_submission_requests" ON public.match_submission_requests
    FOR SELECT
    TO authenticated
    USING (
        actor_id = (
            SELECT p.id
            FROM public.profiles p
            WHERE p.auth_user_id = (SELECT auth.uid())
            LIMIT 1
        )
        OR public.current_user_role() = 'super_admin'
    );

-- ----------------------------------------------------------------------------
-- 2. Full Bracket Graph Integrity Validator (Recursive CTE)
--    Proves every match has a unique acyclic directed path to 1 Grand Final.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.validate_tournament_bracket_integrity(
    p_tournament_id UUID,
    p_require_final_completed BOOLEAN DEFAULT TRUE,
    p_pending_final_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_total_matches INTEGER := 0;
    v_final_count INTEGER := 0;
    v_final_id UUID;
    v_final_match public.matches%ROWTYPE;
    v_reachable_count INTEGER := 0;
    v_has_bad_edge BOOLEAN := FALSE;
    v_has_dup_slot BOOLEAN := FALSE;
    v_has_bad_round BOOLEAN := FALSE;
    v_has_incomplete BOOLEAN := FALSE;
BEGIN
    SELECT COUNT(*)
    INTO v_total_matches
    FROM public.matches m
    WHERE m.tournament_id = p_tournament_id;

    IF v_total_matches <= 0 THEN
        RAISE EXCEPTION 'Turnamen belum memiliki struktur bracket pertandingan.'
            USING ERRCODE = 'P0009';
    END IF;

    -- 2a. Detect self-loops, cross-tournament/missing links, or invalid next_slot
    SELECT EXISTS (
        SELECT 1
        FROM public.matches m
        WHERE m.tournament_id = p_tournament_id
          AND (
              (m.next_match_id IS NOT NULL AND (
                  m.next_match_id = m.id
                  OR COALESCE(m.next_slot, '') NOT IN ('A', 'B')
                  OR NOT EXISTS (
                      SELECT 1
                      FROM public.matches nx
                      WHERE nx.id = m.next_match_id
                        AND nx.tournament_id = p_tournament_id
                  )
              ))
          )
    ) INTO v_has_bad_edge;

    IF v_has_bad_edge THEN
        RAISE EXCEPTION 'Struktur bracket tidak valid: tautan next_match_id atau next_slot tidak sah.'
            USING ERRCODE = 'P0009';
    END IF;

    -- 2b. Detect duplicate feeder slots (next_match_id, next_slot)
    SELECT EXISTS (
        SELECT 1
        FROM public.matches m
        WHERE m.tournament_id = p_tournament_id
          AND m.next_match_id IS NOT NULL
        GROUP BY m.next_match_id, m.next_slot
        HAVING COUNT(*) > 1
    ) INTO v_has_dup_slot;

    IF v_has_dup_slot THEN
        RAISE EXCEPTION 'Struktur bracket tidak valid: duplikasi feeder slot menuju pertandingan lanjutan.'
            USING ERRCODE = 'P0009';
    END IF;

    -- 2c. Detect backward/same-round feeder progression
    SELECT EXISTS (
        SELECT 1
        FROM public.matches m
        JOIN public.matches nx ON nx.id = m.next_match_id AND nx.tournament_id = p_tournament_id
        WHERE m.tournament_id = p_tournament_id
          AND m.round_number >= nx.round_number
    ) INTO v_has_bad_round;

    IF v_has_bad_round THEN
        RAISE EXCEPTION 'Struktur bracket tidak valid: round_number feeder harus lebih kecil dari babak lanjutan.'
            USING ERRCODE = 'P0009';
    END IF;

    -- 2d. Ensure exactly one terminal Grand Final (next_match_id IS NULL)
    SELECT COUNT(*)
    INTO v_final_count
    FROM public.matches m
    WHERE m.tournament_id = p_tournament_id
      AND m.next_match_id IS NULL;

    IF v_final_count <> 1 THEN
        RAISE EXCEPTION 'Struktur bracket tidak valid: harus terdapat tepat satu pertandingan Grand Final.'
            USING ERRCODE = 'P0009';
    END IF;

    SELECT *
    INTO v_final_match
    FROM public.matches m
    WHERE m.tournament_id = p_tournament_id
      AND m.next_match_id IS NULL
    LIMIT 1;

    v_final_id := v_final_match.id;

    IF NULLIF(COALESCE(v_final_match.next_slot, ''), '') IS NOT NULL THEN
        RAISE EXCEPTION 'Struktur bracket tidak valid: Grand Final tidak boleh memiliki next_slot.'
            USING ERRCODE = 'P0009';
    END IF;

    IF p_pending_final_id IS NOT NULL AND v_final_id IS DISTINCT FROM p_pending_final_id THEN
        RAISE EXCEPTION 'Struktur bracket tidak valid: pertandingan bukan Grand Final yang sah.'
            USING ERRCODE = 'P0009';
    END IF;

    -- 2e. Recursive CTE from single Grand Final root proves all nodes form an acyclic in-tree
    --     (catches 2-node, 3-node, and N-node cycles plus disconnected subgraphs).
    WITH RECURSIVE reachable AS (
        SELECT m.id, 1 AS depth, ARRAY[m.id] AS path
        FROM public.matches m
        WHERE m.tournament_id = p_tournament_id
          AND m.id = v_final_id
        UNION ALL
        SELECT child.id, r.depth + 1, r.path || child.id
        FROM public.matches child
        JOIN reachable r ON child.next_match_id = r.id
        WHERE child.tournament_id = p_tournament_id
          AND NOT (child.id = ANY(r.path))
          AND r.depth < v_total_matches
    )
    SELECT COUNT(*)
    INTO v_reachable_count
    FROM reachable;

    IF v_reachable_count <> v_total_matches THEN
        RAISE EXCEPTION 'Struktur bracket tidak valid: terdapat siklus atau pertandingan yang tidak terhubung ke Grand Final.'
            USING ERRCODE = 'P0009';
    END IF;

    -- 2f. All non-final feeder matches must be completed or bye
    SELECT EXISTS (
        SELECT 1
        FROM public.matches m
        WHERE m.tournament_id = p_tournament_id
          AND m.id <> COALESCE(p_pending_final_id, v_final_id)
          AND m.status NOT IN ('completed', 'bye')
    ) INTO v_has_incomplete;

    IF v_has_incomplete THEN
        RAISE EXCEPTION 'Turnamen belum dapat diselesaikan karena masih terdapat pertandingan yang belum selesai.'
            USING ERRCODE = 'P0009';
    END IF;

    IF p_require_final_completed THEN
        IF v_final_match.status <> 'completed'
           OR v_final_match.winner_team_id IS NULL
           OR v_final_match.winner_team_id NOT IN (v_final_match.team_a_id, v_final_match.team_b_id) THEN
            RAISE EXCEPTION 'Grand Final belum selesai dengan pemenang yang sah.'
                USING ERRCODE = 'P0009';
        END IF;
    END IF;

    RETURN v_final_id;
END;
$$;

REVOKE ALL ON FUNCTION private.validate_tournament_bracket_integrity(UUID, BOOLEAN, UUID)
    FROM PUBLIC, anon, authenticated;

-- ----------------------------------------------------------------------------
-- 3. Upgrade transition_tournament_status to enforce full bracket graph integrity
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
        PERFORM private.validate_tournament_bracket_integrity(p_tournament_id, TRUE, NULL);
    END IF;

    UPDATE public.tournaments
    SET status = p_new_status,
        updated_at = NOW()
    WHERE id = p_tournament_id
    RETURNING * INTO v_tournament;

    RETURN NEXT v_tournament;
END;
$$;

-- ----------------------------------------------------------------------------
-- 4. Single-Transaction Atomic Match Result Submission & Override RPC
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.submit_match_result_atomic(
    p_match_id UUID,
    p_score_a INT,
    p_score_b INT,
    p_force_override BOOLEAN DEFAULT FALSE,
    p_notes TEXT DEFAULT '',
    p_game_number INT DEFAULT 1,
    p_idempotency_key VARCHAR DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_auth_uid UUID;
    v_actor RECORD;
    v_tournament public.tournaments%ROWTYPE;
    v_match public.matches%ROWTYPE;
    v_next_match public.matches%ROWTYPE;
    v_updated_match public.matches%ROWTYPE;
    v_updated_next_match public.matches%ROWTYPE;
    v_idem_row public.match_submission_requests%ROWTYPE;
    v_is_assigned BOOLEAN := FALSE;
    v_clean_notes TEXT := TRIM(COALESCE(p_notes, ''));
    v_clean_idem_key VARCHAR(128) := NULLIF(TRIM(COALESCE(p_idempotency_key, '')), '');
    v_request_hash VARCHAR(64);
    v_best_of INT;
    v_wins_required INT;
    v_winner_score INT;
    v_loser_score INT;
    v_winner_team_id UUID;
    v_downstream_current UUID;
    v_action_name VARCHAR(80);
    v_now TIMESTAMPTZ := NOW();
    v_response JSONB;
BEGIN
    IF p_match_id IS NULL THEN
        RAISE EXCEPTION 'match_id wajib diisi.' USING ERRCODE = '22023';
    END IF;

    IF p_score_a IS NULL OR p_score_b IS NULL OR p_score_a < 0 OR p_score_b < 0 THEN
        RAISE EXCEPTION 'Skor pertandingan tidak boleh negatif atau kosong.' USING ERRCODE = '22023';
    END IF;

    IF p_force_override IS NULL THEN
        RAISE EXCEPTION 'Field force_override wajib bernilai boolean.' USING ERRCODE = '22023';
    END IF;

    IF p_game_number IS NULL OR p_game_number < 1 THEN
        RAISE EXCEPTION 'game_number minimal 1.' USING ERRCODE = '22023';
    END IF;

    IF v_clean_idem_key IS NOT NULL AND LENGTH(v_clean_idem_key) > 128 THEN
        RAISE EXCEPTION 'idempotency_key maksimal 128 karakter.' USING ERRCODE = '22023';
    END IF;

    v_auth_uid := (SELECT auth.uid());
    IF v_auth_uid IS NULL THEN
        RAISE EXCEPTION 'Autentikasi diperlukan untuk mengesahkan hasil pertandingan.' USING ERRCODE = '42501';
    END IF;

    SELECT id, role, is_active
    INTO v_actor
    FROM public.profiles
    WHERE auth_user_id = v_auth_uid
    LIMIT 1;

    IF NOT FOUND OR v_actor.is_active IS NOT TRUE THEN
        RAISE EXCEPTION 'Profil pengguna tidak ditemukan atau tidak aktif.' USING ERRCODE = '42501';
    END IF;

    IF v_actor.role NOT IN ('super_admin', 'organizer', 'committee') THEN
        RAISE EXCEPTION 'Role pengguna tidak memiliki izin untuk mengesahkan hasil pertandingan.'
            USING ERRCODE = '42501';
    END IF;

    -- Locate target match to resolve owning tournament, then lock in canonical order:
    --   1) tournament row FOR UPDATE
    --   2) all tournament match rows ordered by id FOR UPDATE (deadlock-free)
    SELECT m.tournament_id
    INTO v_tournament.id
    FROM public.matches m
    WHERE m.id = p_match_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pertandingan tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    SELECT *
    INTO v_tournament
    FROM public.tournaments t
    WHERE t.id = v_tournament.id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Turnamen pertandingan tidak ditemukan.' USING ERRCODE = 'P0002';
    END IF;

    PERFORM m.id
    FROM public.matches m
    WHERE m.tournament_id = v_tournament.id
    ORDER BY m.id
    FOR UPDATE;

    SELECT *
    INTO v_match
    FROM public.matches m
    WHERE m.id = p_match_id;

    IF v_actor.role = 'organizer' THEN
        IF v_tournament.organizer_id IS DISTINCT FROM v_actor.id THEN
            RAISE EXCEPTION 'Organizer hanya dapat mengelola pertandingan pada turnamen miliknya.'
                USING ERRCODE = '42501';
        END IF;
    ELSIF v_actor.role = 'committee' THEN
        SELECT EXISTS (
            SELECT 1
            FROM public.tournament_staff ts
            WHERE ts.tournament_id = v_tournament.id
              AND ts.user_id = v_actor.id
        ) INTO v_is_assigned;

        IF NOT v_is_assigned THEN
            RAISE EXCEPTION 'Panitia hanya dapat mengelola pertandingan pada turnamen yang ditugaskan.'
                USING ERRCODE = '42501';
        END IF;
    END IF;

    -- Idempotency replay check before completed/override lock
    IF v_clean_idem_key IS NOT NULL THEN
        v_request_hash := encode(
            pg_catalog.sha256(
                convert_to(
                    CONCAT_WS(
                        '|',
                        p_match_id::text,
                        p_score_a::text,
                        p_score_b::text,
                        p_force_override::text,
                        v_clean_notes,
                        p_game_number::text
                    ),
                    'UTF8'
                )
            ),
            'hex'
        );

        SELECT *
        INTO v_idem_row
        FROM public.match_submission_requests r
        WHERE r.match_id = p_match_id
          AND r.actor_id = v_actor.id
          AND r.idempotency_key = v_clean_idem_key
        FOR UPDATE;

        IF FOUND THEN
            IF v_idem_row.request_hash IS DISTINCT FROM v_request_hash THEN
                RAISE EXCEPTION 'Idempotency key sudah digunakan untuk payload skor yang berbeda.'
                    USING ERRCODE = 'P0009';
            END IF;
            RETURN v_idem_row.response_payload || jsonb_build_object('idempotent_replay', TRUE);
        END IF;
    END IF;

    IF v_tournament.status = 'cancelled' THEN
        RAISE EXCEPTION 'Hasil pertandingan tidak dapat disahkan karena turnamen telah dibatalkan.'
            USING ERRCODE = 'P0009';
    END IF;

    IF v_match.status = 'bye' THEN
        RAISE EXCEPTION 'Pertandingan BYE otomatis dimenangkan dan tidak dapat diisi skor secara manual.'
            USING ERRCODE = 'P0009';
    END IF;

    IF v_match.status = 'completed' AND NOT p_force_override THEN
        RAISE EXCEPTION 'Hasil pertandingan ini sudah disahkan dan dikunci. Gunakan force_override untuk mengubahnya.'
            USING ERRCODE = 'P0009';
    END IF;

    IF p_force_override AND LENGTH(v_clean_notes) < 4 THEN
        RAISE EXCEPTION 'Koreksi hasil (force_override) wajib menyertakan alasan audit minimal 4 karakter.'
            USING ERRCODE = '22023';
    END IF;

    IF v_match.team_a_id IS NULL OR v_match.team_b_id IS NULL THEN
        RAISE EXCEPTION 'Pertandingan belum memiliki kedua tim peserta (Team A dan Team B wajib terisi).'
            USING ERRCODE = '22023';
    END IF;

    v_best_of := COALESCE(v_match.best_of, v_tournament.best_of, 3);
    IF v_best_of NOT IN (1, 3, 5, 7) THEN
        RAISE EXCEPTION 'Format best_of pertandingan tidak valid.' USING ERRCODE = '22023';
    END IF;

    IF p_score_a = p_score_b THEN
        RAISE EXCEPTION 'Hasil seri tidak diizinkan. Pertandingan harus memiliki pemenang yang sah.'
            USING ERRCODE = '22023';
    END IF;

    v_wins_required := (v_best_of / 2) + 1;
    v_winner_score := GREATEST(p_score_a, p_score_b);
    v_loser_score := LEAST(p_score_a, p_score_b);

    IF v_winner_score <> v_wins_required THEN
        RAISE EXCEPTION 'Skor pemenang tidak sesuai dengan format best_of pertandingan.'
            USING ERRCODE = '22023';
    END IF;

    IF v_loser_score >= v_wins_required OR (p_score_a + p_score_b) > v_best_of THEN
        RAISE EXCEPTION 'Kombinasi skor melebihi batas game pada format best_of pertandingan.'
            USING ERRCODE = '22023';
    END IF;

    v_winner_team_id := CASE
        WHEN p_score_a > p_score_b THEN v_match.team_a_id
        ELSE v_match.team_b_id
    END;

    IF v_match.next_match_id IS NOT NULL AND v_match.next_slot IN ('A', 'B') THEN
        SELECT *
        INTO v_next_match
        FROM public.matches m
        WHERE m.id = v_match.next_match_id
          AND m.tournament_id = v_tournament.id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Pertandingan babak berikutnya tidak ditemukan pada turnamen ini.'
                USING ERRCODE = 'P0009';
        END IF;

        v_downstream_current := CASE
            WHEN v_match.next_slot = 'A' THEN v_next_match.team_a_id
            ELSE v_next_match.team_b_id
        END;

        IF v_downstream_current IS DISTINCT FROM v_winner_team_id
           AND (v_next_match.status IN ('ongoing', 'completed') OR v_next_match.winner_team_id IS NOT NULL) THEN
            RAISE EXCEPTION 'Pemenang tidak dapat diubah karena pertandingan babak berikutnya sudah berjalan atau selesai.'
                USING ERRCODE = 'P0009';
        END IF;
    ELSE
        IF v_tournament.status NOT IN ('ongoing', 'completed') THEN
            RAISE EXCEPTION 'Grand Final hanya dapat disahkan ketika turnamen berstatus ongoing atau completed.'
                USING ERRCODE = 'P0009';
        END IF;

        PERFORM private.validate_tournament_bracket_integrity(v_tournament.id, FALSE, v_match.id);
    END IF;

    -- Step 6: Update current match
    UPDATE public.matches
    SET score_a = p_score_a,
        score_b = p_score_b,
        winner_team_id = v_winner_team_id,
        status = 'completed',
        completed_at = v_now,
        updated_at = v_now
    WHERE id = v_match.id
    RETURNING * INTO v_updated_match;

    -- Step 7 & 8: Advance winner or atomically validate + complete tournament
    IF v_match.next_match_id IS NOT NULL AND v_match.next_slot IN ('A', 'B') THEN
        IF v_match.next_slot = 'A' THEN
            UPDATE public.matches
            SET team_a_id = v_winner_team_id,
                updated_at = v_now
            WHERE id = v_match.next_match_id
            RETURNING * INTO v_updated_next_match;
        ELSE
            UPDATE public.matches
            SET team_b_id = v_winner_team_id,
                updated_at = v_now
            WHERE id = v_match.next_match_id
            RETURNING * INTO v_updated_next_match;
        END IF;
    ELSE
        PERFORM private.validate_tournament_bracket_integrity(v_tournament.id, TRUE, NULL);

        UPDATE public.tournaments
        SET status = 'completed',
            updated_at = v_now
        WHERE id = v_tournament.id
        RETURNING * INTO v_tournament;
    END IF;

    -- Step 9: Idempotent upsert on (match_id, game_number)
    INSERT INTO public.match_results (
        match_id,
        game_number,
        score_a,
        score_b,
        winner_team_id,
        notes,
        verified_by,
        verified_at
    )
    VALUES (
        v_match.id,
        p_game_number,
        p_score_a,
        p_score_b,
        v_winner_team_id,
        v_clean_notes,
        v_actor.id,
        v_now
    )
    ON CONFLICT (match_id, game_number)
    DO UPDATE SET
        score_a = EXCLUDED.score_a,
        score_b = EXCLUDED.score_b,
        winner_team_id = EXCLUDED.winner_team_id,
        notes = EXCLUDED.notes,
        verified_by = EXCLUDED.verified_by,
        verified_at = EXCLUDED.verified_at;

    -- Step 10: Audit log inside same ACID transaction
    v_action_name := CASE
        WHEN p_force_override THEN 'MATCH_RESULT_OVERRIDDEN'
        ELSE 'MATCH_RESULT_VERIFIED'
    END;

    INSERT INTO public.activity_logs (
        actor_id,
        tournament_id,
        entity_type,
        entity_id,
        action,
        details
    )
    VALUES (
        v_actor.id,
        v_tournament.id,
        'match',
        v_match.id,
        v_action_name,
        jsonb_build_object(
            'score_a', p_score_a,
            'score_b', p_score_b,
            'winner_team_id', v_winner_team_id,
            'next_match_id', v_match.next_match_id,
            'next_slot', v_match.next_slot,
            'notes', v_clean_notes
        )
    );

    v_response := jsonb_build_object(
        'match', to_jsonb(v_updated_match),
        'next_match', CASE
            WHEN v_updated_next_match.id IS NOT NULL THEN to_jsonb(v_updated_next_match)
            ELSE NULL::jsonb
        END,
        'tournament_status', v_tournament.status,
        'idempotent_replay', FALSE
    );

    IF v_clean_idem_key IS NOT NULL THEN
        INSERT INTO public.match_submission_requests (
            match_id,
            actor_id,
            idempotency_key,
            request_hash,
            response_payload
        )
        VALUES (
            v_match.id,
            v_actor.id,
            v_clean_idem_key,
            v_request_hash,
            v_response
        );
    END IF;

    RETURN v_response;
END;
$$;

REVOKE ALL ON FUNCTION private.submit_match_result_atomic(UUID, INT, INT, BOOLEAN, TEXT, INT, VARCHAR)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.submit_match_result_atomic(UUID, INT, INT, BOOLEAN, TEXT, INT, VARCHAR)
    TO authenticated;

CREATE OR REPLACE FUNCTION public.submit_match_result_atomic(
    p_match_id UUID,
    p_score_a INT,
    p_score_b INT,
    p_force_override BOOLEAN DEFAULT FALSE,
    p_notes TEXT DEFAULT '',
    p_game_number INT DEFAULT 1,
    p_idempotency_key VARCHAR DEFAULT NULL
)
RETURNS JSONB
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT private.submit_match_result_atomic(
        p_match_id,
        p_score_a,
        p_score_b,
        p_force_override,
        p_notes,
        p_game_number,
        p_idempotency_key
    );
$$;

REVOKE ALL ON FUNCTION public.submit_match_result_atomic(UUID, INT, INT, BOOLEAN, TEXT, INT, VARCHAR)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.submit_match_result_atomic(UUID, INT, INT, BOOLEAN, TEXT, INT, VARCHAR)
    TO authenticated;
