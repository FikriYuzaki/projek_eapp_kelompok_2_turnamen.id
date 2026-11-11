-- ============================================================================
-- Turnamen.in — Consistent Demo Seed Data
-- File: supabase/seed.sql
-- Berisi: 5 profil (5 role), 3 game, 2 turnamen, 8 tim, 16+ anggota tim,
--         8 registrasi terverifikasi, 7 pertandingan bracket 8 tim,
--         hasil pertandingan QF, pembayaran, pengumuman, dan activity logs.
-- ============================================================================

-- 1. PROFILES (5 Role Utama)
INSERT INTO public.profiles (id, email, username, full_name, role, phone, is_active)
VALUES
    ('11111111-1111-4111-8111-111111111101', 'admin@turnamen.in', 'superadmin', 'Raka Pratama (Super Admin)', 'super_admin', '081100000001', TRUE),
    ('11111111-1111-4111-8111-111111111102', 'organizer@turnamen.in', 'garuda_eo', 'Nadia Kusuma (Tournament Organizer)', 'organizer', '081100000002', TRUE),
    ('11111111-1111-4111-8111-111111111103', 'committee@turnamen.in', 'panitia_utama', 'Bima Saputra (Head Committee)', 'committee', '081100000003', TRUE),
    ('11111111-1111-4111-8111-111111111104', 'captain@turnamen.in', 'garuda_capt', 'Dimas Aditya (Team Captain)', 'team_captain', '081100000004', TRUE),
    ('11111111-1111-4111-8111-111111111105', 'player@turnamen.in', 'aruna_player', 'Rizky Maulana (Player)', 'player', '081100000005', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 2. GAMES (3 Game: Mobile Legends, Valorant, PUBG Mobile)
INSERT INTO public.games (id, slug, name, genre, platform, team_size, max_substitutes, allow_draw, default_best_of, external_rawg_slug)
VALUES
    ('22222222-2222-4222-8222-222222222201', 'mobile-legends', 'Mobile Legends: Bang Bang', 'MOBA', 'Mobile', 5, 2, FALSE, 3, 'mobile-legends-bang-bang'),
    ('22222222-2222-4222-8222-222222222202', 'valorant', 'VALORANT', 'Tactical Shooter', 'PC', 5, 2, FALSE, 3, 'valorant'),
    ('22222222-2222-4222-8222-222222222203', 'ea-sports-fc', 'EA Sports FC 25', 'Sports', 'PC / Console', 1, 1, FALSE, 3, 'ea-sports-fc-24')
ON CONFLICT (id) DO NOTHING;

-- 3. TOURNAMENTS (2 Turnamen: 1 Ongoing 8-Tim dengan Bracket Aktif, 1 Open Registration)
INSERT INTO public.tournaments (
    id, slug, title, description, game_id, organizer_id, format, status,
    max_teams, best_of, allow_draw, registration_fee, prize_pool, rules, venue,
    registration_start, registration_end, start_date, end_date
)
VALUES
    (
        '33333333-3333-4333-8333-333333333301',
        'nusantara-campus-cup-2026',
        'Nusantara Campus Cup 2026 — MLBB Series',
        'Turnamen Mobile Legends tingkat universitas dan komunitas se-Indonesia dengan format Single Elimination 8 tim.',
        '22222222-2222-4222-8222-222222222201',
        '11111111-1111-4111-8111-111111111102',
        'single_elimination',
        'ongoing',
        8,
        3,
        FALSE,
        50000.00,
        10000000.00,
        '1. Format Single Elimination Best of 3 (Final Bo5). 2. Wajib hadir 15 menit sebelum jadwal. 3. Dilarang menggunakan cheat/script.',
        'Hybrid — Jakarta & Discord Arena',
        '2026-11-01T09:00:00+07:00',
        '2026-11-09T23:59:00+07:00',
        '2026-11-11T10:00:00+07:00',
        '2026-11-12T21:00:00+07:00'
    ),
    (
        '33333333-3333-4333-8333-333333333302',
        'jakarta-tactical-clash-valorant-2026',
        'Jakarta Tactical Clash — VALORANT Open 2026',
        'Kompetisi VALORANT terbuka untuk komunitas dan tim semi-pro dengan sistem gugur 8 tim.',
        '22222222-2222-4222-8222-222222222202',
        '11111111-1111-4111-8111-111111111102',
        'single_elimination',
        'open_registration',
        8,
        3,
        FALSE,
        75000.00,
        15000000.00,
        '1. Map veto standar kompetitif. 2. Server Singapore/Jakarta. 3. Wajib menyertakan Riot ID yang valid.',
        'Online — Server Jakarta',
        '2026-11-05T09:00:00+07:00',
        '2026-11-20T23:59:00+07:00',
        '2026-11-22T13:00:00+07:00',
        '2026-11-23T21:00:00+07:00'
    )
ON CONFLICT (id) DO NOTHING;

-- 4. TOURNAMENT STAFF
INSERT INTO public.tournament_staff (id, tournament_id, user_id, staff_role)
VALUES
    ('66666666-6666-4666-8666-666666666601', '33333333-3333-4333-8333-333333333301', '11111111-1111-4111-8111-111111111103', 'head_committee'),
    ('66666666-6666-4666-8666-666666666602', '33333333-3333-4333-8333-333333333302', '11111111-1111-4111-8111-111111111103', 'head_committee')
ON CONFLICT (id) DO NOTHING;

-- 5. TEAMS (8 Tim untuk Simulasi Bracket)
INSERT INTO public.teams (id, name, tag, game_id, captain_id, region, is_verified)
VALUES
    ('44444444-4444-4444-8444-444444444401', 'Garuda Esports', 'GRD', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Jakarta', TRUE),
    ('44444444-4444-4444-8444-444444444402', 'Sriwijaya Vanguard', 'SRW', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Palembang', TRUE),
    ('44444444-4444-4444-8444-444444444403', 'Majapahit Titans', 'MJP', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Surabaya', TRUE),
    ('44444444-4444-4444-8444-444444444404', 'Borneo Phantoms', 'BRN', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Balikpapan', TRUE),
    ('44444444-4444-4444-8444-444444444405', 'Pasundan Wolves', 'PSW', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Bandung', TRUE),
    ('44444444-4444-4444-8444-444444444406', 'Celebes Kraken', 'CLB', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Makassar', TRUE),
    ('44444444-4444-4444-8444-444444444407', 'Mataram Knights', 'MTR', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Yogyakarta', TRUE),
    ('44444444-4444-4444-8444-444444444408', 'Dewata Phoenix', 'DWT', '22222222-2222-4222-8222-222222222201', '11111111-1111-4111-8111-111111111104', 'Denpasar', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 6. TEAM MEMBERS (2 Pemain per Tim sebagai sampel awal)
INSERT INTO public.team_members (id, team_id, user_id, nickname, ingame_id, member_role)
VALUES
    ('55555555-5555-4555-8555-555555555501', '44444444-4444-4444-8444-444444444401', '11111111-1111-4111-8111-111111111104', 'GRD.Aether', 'ML-10293801 (2011)', 'captain'),
    ('55555555-5555-4555-8555-555555555502', '44444444-4444-4444-8444-444444444401', '11111111-1111-4111-8111-111111111105', 'GRD.Aruna', 'ML-10293802 (2011)', 'starter'),
    ('55555555-5555-4555-8555-555555555503', '44444444-4444-4444-8444-444444444402', NULL, 'SRW.Blaze', 'ML-20394801 (2022)', 'captain'),
    ('55555555-5555-4555-8555-555555555504', '44444444-4444-4444-8444-444444444402', NULL, 'SRW.Vortex', 'ML-20394802 (2022)', 'starter'),
    ('55555555-5555-4555-8555-555555555505', '44444444-4444-4444-8444-444444444403', NULL, 'MJP.Gajah', 'ML-30495801 (2033)', 'captain'),
    ('55555555-5555-4555-8555-555555555506', '44444444-4444-4444-8444-444444444403', NULL, 'MJP.Surya', 'ML-30495802 (2033)', 'starter'),
    ('55555555-5555-4555-8555-555555555507', '44444444-4444-4444-8444-444444444404', NULL, 'BRN.Shadow', 'ML-40596801 (2044)', 'captain'),
    ('55555555-5555-4555-8555-555555555508', '44444444-4444-4444-8444-444444444404', NULL, 'BRN.Mandau', 'ML-40596802 (2044)', 'starter'),
    ('55555555-5555-4555-8555-555555555509', '44444444-4444-4444-8444-444444444405', NULL, 'PSW.Kujang', 'ML-50697801 (2055)', 'captain'),
    ('55555555-5555-4555-8555-555555555510', '44444444-4444-4444-8444-444444444405', NULL, 'PSW.Prabu', 'ML-50697802 (2055)', 'starter'),
    ('55555555-5555-4555-8555-555555555511', '44444444-4444-4444-8444-444444444406', NULL, 'CLB.Badik', 'ML-60798801 (2066)', 'captain'),
    ('55555555-5555-4555-8555-555555555512', '44444444-4444-4444-8444-444444444406', NULL, 'CLB.Taufan', 'ML-60798802 (2066)', 'starter'),
    ('55555555-5555-4555-8555-555555555513', '44444444-4444-4444-8444-444444444407', NULL, 'MTR.Senopati', 'ML-70899801 (2077)', 'captain'),
    ('55555555-5555-4555-8555-555555555514', '44444444-4444-4444-8444-444444444407', NULL, 'MTR.Keris', 'ML-70899802 (2077)', 'starter'),
    ('55555555-5555-4555-8555-555555555515', '44444444-4444-4444-8444-444444444408', NULL, 'DWT.Barong', 'ML-80990801 (2088)', 'captain'),
    ('55555555-5555-4555-8555-555555555516', '44444444-4444-4444-8444-444444444408', NULL, 'DWT.Agni', 'ML-80990802 (2088)', 'starter')
ON CONFLICT (id) DO NOTHING;

-- 7. REGISTRATIONS (8 Tim Terdaftar & Approved pada Turnamen 1)
INSERT INTO public.registrations (id, tournament_id, team_id, registered_by, status, seed_number, verified_by, verified_at, notes)
VALUES
    ('77777777-7777-4777-8777-777777777701', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444401', '11111111-1111-4111-8111-111111111104', 'approved', 1, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:00:00+07:00', 'Roster dan pembayaran terverifikasi'),
    ('77777777-7777-4777-8777-777777777702', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444402', '11111111-1111-4111-8111-111111111104', 'approved', 2, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:05:00+07:00', 'Roster dan pembayaran terverifikasi'),
    ('77777777-7777-4777-8777-777777777703', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444403', '11111111-1111-4111-8111-111111111104', 'approved', 3, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:10:00+07:00', 'Roster dan pembayaran terverifikasi'),
    ('77777777-7777-4777-8777-777777777704', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444404', '11111111-1111-4111-8111-111111111104', 'approved', 4, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:15:00+07:00', 'Roster dan pembayaran terverifikasi'),
    ('77777777-7777-4777-8777-777777777705', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444405', '11111111-1111-4111-8111-111111111104', 'approved', 5, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:20:00+07:00', 'Roster dan pembayaran terverifikasi'),
    ('77777777-7777-4777-8777-777777777706', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444406', '11111111-1111-4111-8111-111111111104', 'approved', 6, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:25:00+07:00', 'Roster dan pembayaran terverifikasi'),
    ('77777777-7777-4777-8777-777777777707', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444407', '11111111-1111-4111-8111-111111111104', 'approved', 7, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:30:00+07:00', 'Roster dan pembayaran terverifikasi'),
    ('77777777-7777-4777-8777-777777777708', '33333333-3333-4333-8333-333333333301', '44444444-4444-4444-8444-444444444408', '11111111-1111-4111-8111-111111111104', 'approved', 8, '11111111-1111-4111-8111-111111111103', '2026-11-10T10:35:00+07:00', 'Roster dan pembayaran terverifikasi')
ON CONFLICT (id) DO NOTHING;

-- 8. MATCHES (Single Elimination 8 Tim: 4 QF, 2 SF, 1 Final — Insert dari Final ke QF untuk menjaga FK next_match_id)
INSERT INTO public.matches (
    id, tournament_id, round_number, round_name, match_number,
    team_a_id, team_b_id, score_a, score_b, winner_team_id,
    status, best_of, scheduled_at, completed_at, next_match_id, next_slot
)
VALUES
    -- Round 3: Final (1 Match)
    (
        '88888888-8888-4888-8888-888888888807',
        '33333333-3333-4333-8333-333333333301',
        3, 'Grand Final', 1,
        NULL, NULL, 0, 0, NULL,
        'scheduled', 3, '2026-11-12T19:00:00+07:00', NULL, NULL, NULL
    ),
    -- Round 2: Semi Final (2 Matches)
    (
        '88888888-8888-4888-8888-888888888805',
        '33333333-3333-4333-8333-333333333301',
        2, 'Semi Final', 1,
        '44444444-4444-4444-8444-444444444401', '44444444-4444-4444-8444-444444444403', 0, 0, NULL,
        'scheduled', 3, '2026-11-12T13:00:00+07:00', NULL,
        '88888888-8888-4888-8888-888888888807', 'A'
    ),
    (
        '88888888-8888-4888-8888-888888888806',
        '33333333-3333-4333-8333-333333333301',
        2, 'Semi Final', 2,
        '44444444-4444-4444-8444-444444444405', NULL, 0, 0, NULL,
        'scheduled', 3, '2026-11-12T15:00:00+07:00', NULL,
        '88888888-8888-4888-8888-888888888807', 'B'
    ),
    -- Round 1: Quarter Final (4 Matches — 3 Completed, 1 Scheduled)
    (
        '88888888-8888-4888-8888-888888888801',
        '33333333-3333-4333-8333-333333333301',
        1, 'Quarter Final', 1,
        '44444444-4444-4444-8444-444444444401', '44444444-4444-4444-8444-444444444402', 2, 0, '44444444-4444-4444-8444-444444444401',
        'completed', 3, '2026-11-11T10:00:00+07:00', '2026-11-11T11:15:00+07:00',
        '88888888-8888-4888-8888-888888888805', 'A'
    ),
    (
        '88888888-8888-4888-8888-888888888802',
        '33333333-3333-4333-8333-333333333301',
        1, 'Quarter Final', 2,
        '44444444-4444-4444-8444-444444444403', '44444444-4444-4444-8444-444444444404', 2, 1, '44444444-4444-4444-8444-444444444403',
        'completed', 3, '2026-11-11T12:00:00+07:00', '2026-11-11T13:45:00+07:00',
        '88888888-8888-4888-8888-888888888805', 'B'
    ),
    (
        '88888888-8888-4888-8888-888888888803',
        '33333333-3333-4333-8333-333333333301',
        1, 'Quarter Final', 3,
        '44444444-4444-4444-8444-444444444405', '44444444-4444-4444-8444-444444444406', 2, 0, '44444444-4444-4444-8444-444444444405',
        'completed', 3, '2026-11-11T14:00:00+07:00', '2026-11-11T15:10:00+07:00',
        '88888888-8888-4888-8888-888888888806', 'A'
    ),
    (
        '88888888-8888-4888-8888-888888888804',
        '33333333-3333-4333-8333-333333333301',
        1, 'Quarter Final', 4,
        '44444444-4444-4444-8444-444444444407', '44444444-4444-4444-8444-444444444408', 0, 0, NULL,
        'scheduled', 3, '2026-11-11T16:00:00+07:00', NULL,
        '88888888-8888-4888-8888-888888888806', 'B'
    )
ON CONFLICT (id) DO NOTHING;

-- 9. MATCH RESULTS (Bukti pengesahan untuk 3 pertandingan QF yang sudah selesai)
INSERT INTO public.match_results (id, match_id, game_number, score_a, score_b, winner_team_id, verified_by, notes)
VALUES
    ('99999999-9999-4999-8999-999999999901', '88888888-8888-4888-8888-888888888801', 1, 2, 0, '44444444-4444-4444-8444-444444444401', '11111111-1111-4111-8111-111111111103', 'Garuda menang telak 2-0 atas Sriwijaya'),
    ('99999999-9999-4999-8999-999999999902', '88888888-8888-4888-8888-888888888802', 1, 2, 1, '44444444-4444-4444-8444-444444444403', '11111111-1111-4111-8111-111111111103', 'Majapahit menang 2-1 setelah comeback di Game 3'),
    ('99999999-9999-4999-8999-999999999903', '88888888-8888-4888-8888-888888888803', 1, 2, 0, '44444444-4444-4444-8444-444444444405', '11111111-1111-4111-8111-111111111103', 'Pasundan Wolves menang 2-0')
ON CONFLICT (id) DO NOTHING;

-- 10. PAYMENTS (Contoh pembayaran terverifikasi)
INSERT INTO public.payments (id, registration_id, amount, payment_method, status, submitted_by, verified_by, verified_at, notes)
VALUES
    ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01', '77777777-7777-4777-8777-777777777701', 50000.00, 'QRIS', 'verified', '11111111-1111-4111-8111-111111111104', '11111111-1111-4111-8111-111111111103', '2026-11-10T10:00:00+07:00', 'Lunas via QRIS')
ON CONFLICT (id) DO NOTHING;

-- 11. ANNOUNCEMENTS (2 Pengumuman Contoh)
INSERT INTO public.announcements (id, tournament_id, author_id, title, content, priority, is_pinned, published_at)
VALUES
    (
        'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbb01',
        '33333333-3333-4333-8333-333333333301',
        '11111111-1111-4111-8111-111111111102',
        'Technical Meeting & Check-In Babak Quarter Final',
        'Seluruh kapten tim wajib melakukan check-in di lobby Discord 15 menit sebelum jadwal Quarter Final masing-masing. Keterlambatan lebih dari 10 menit dikenakan penalti walkover.',
        'important',
        TRUE,
        '2026-11-11T08:30:00+07:00'
    ),
    (
        'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbb02',
        '33333333-3333-4333-8333-333333333301',
        '11111111-1111-4111-8111-111111111103',
        'Update Bracket: 3 Tim Melaju ke Semi Final!',
        'Garuda Esports, Majapahit Titans, dan Pasundan Wolves telah mengunci tiket Semi Final. Pertandingan QF #4 antara Mataram Knights vs Dewata Phoenix akan dimulai pukul 16:00 WIB.',
        'normal',
        FALSE,
        '2026-11-11T15:20:00+07:00'
    )
ON CONFLICT (id) DO NOTHING;

-- 12. ACTIVITY LOGS
INSERT INTO public.activity_logs (id, actor_id, tournament_id, entity_type, entity_id, action, details)
VALUES
    (
        'cccccccc-cccc-4ccc-8ccc-cccccccccc01',
        '11111111-1111-4111-8111-111111111102',
        '33333333-3333-4333-8333-333333333301',
        'bracket',
        '33333333-3333-4333-8333-333333333301',
        'BRACKET_GENERATED',
        '{"team_count": 8, "total_matches": 7}'::jsonb
    ),
    (
        'cccccccc-cccc-4ccc-8ccc-cccccccccc02',
        '11111111-1111-4111-8111-111111111103',
        '33333333-3333-4333-8333-333333333301',
        'match',
        '88888888-8888-4888-8888-888888888801',
        'MATCH_RESULT_VERIFIED',
        '{"score_a": 2, "score_b": 0, "winner_team_id": "44444444-4444-4444-8444-444444444401"}'::jsonb
    )
ON CONFLICT (id) DO NOTHING;
