import pytest

from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.matches.bracket_engine import (
    SingleEliminationBracketEngine,
    validate_match_score,
)
from backend.modules.matches.service import MatchService
from backend.modules.teams.service import TeamService
from backend.modules.tournaments.service import TournamentService
from backend.repositories.mock.mock_repository import MockDataStoreRepository


def test_generate_8_team_bracket_structure():
    team_ids = [f"team-{i}" for i in range(1, 9)]
    matches = SingleEliminationBracketEngine.generate_bracket(
        tournament_id="tour-8",
        team_ids=team_ids,
        best_of=3,
    )

    assert len(matches) == 7
    qf = [m for m in matches if m["round_number"] == 1]
    sf = [m for m in matches if m["round_number"] == 2]
    final = [m for m in matches if m["round_number"] == 3]

    assert len(qf) == 4
    assert len(sf) == 2
    assert len(final) == 1
    assert qf[0]["round_name"] == "Quarter Final"
    assert sf[0]["round_name"] == "Semi Final"
    assert final[0]["round_name"] == "Grand Final"

    for m in matches:
        assert m["status"] == "scheduled"
        assert m["winner_team_id"] is None

    assert qf[0]["next_match_id"] == sf[0]["id"]
    assert qf[0]["next_slot"] == "A"
    assert qf[1]["next_match_id"] == sf[0]["id"]
    assert qf[1]["next_slot"] == "B"
    assert sf[0]["next_match_id"] == final[0]["id"]
    assert sf[0]["next_slot"] == "A"
    assert sf[1]["next_match_id"] == final[0]["id"]
    assert sf[1]["next_slot"] == "B"


def test_generate_non_power_of_two_bracket_assigns_byes():
    team_ids = [f"team-{i}" for i in range(1, 7)]
    matches = SingleEliminationBracketEngine.generate_bracket(
        tournament_id="tour-6",
        team_ids=team_ids,
        best_of=3,
    )
    assert len(matches) == 7
    qf = [m for m in matches if m["round_number"] == 1]
    sf = [m for m in matches if m["round_number"] == 2]

    byes = [m for m in qf if m["status"] == "bye"]
    scheduled = [m for m in qf if m["status"] == "scheduled"]
    assert len(byes) == 2
    assert len(scheduled) == 2

    assert byes[0]["winner_team_id"] == "team-1"
    assert byes[1]["winner_team_id"] == "team-2"
    assert sf[0]["team_a_id"] == "team-1"
    assert sf[0]["team_b_id"] == "team-2"


def test_generate_7_team_bracket_byes():
    team_ids = [f"team-{i}" for i in range(1, 8)]
    matches = SingleEliminationBracketEngine.generate_bracket(
        tournament_id="tour-7",
        team_ids=team_ids,
        best_of=3,
    )
    assert len(matches) == 7
    qf = [m for m in matches if m["round_number"] == 1]
    sf = [m for m in matches if m["round_number"] == 2]
    final = [m for m in matches if m["round_number"] == 3]

    assert len(qf) == 4
    assert len(sf) == 2
    assert len(final) == 1

    byes = [m for m in qf if m["status"] == "bye"]
    scheduled = [m for m in qf if m["status"] == "scheduled"]
    assert len(byes) == 1
    assert len(scheduled) == 3

    assert byes[0]["winner_team_id"] == "team-1"
    assert sf[0]["team_a_id"] == "team-1"


def test_score_validation_rules():
    assert validate_match_score(2, 0, best_of=3) == "A"
    assert validate_match_score(1, 2, best_of=3) == "B"

    with pytest.raises(DomainValidationError, match="seri"):
        validate_match_score(1, 1, best_of=3)

    with pytest.raises(DomainValidationError):
        validate_match_score(3, 0, best_of=3)

    with pytest.raises(DomainValidationError):
        validate_match_score(1, 0, best_of=3)

    with pytest.raises(DomainValidationError):
        validate_match_score(-1, 2, best_of=3)


def test_generate_4_team_bracket_structure():
    team_ids = [f"team-{i}" for i in range(1, 5)]
    matches = SingleEliminationBracketEngine.generate_bracket(
        tournament_id="tour-4",
        team_ids=team_ids,
        best_of=3,
    )

    assert len(matches) == 3
    sf = [m for m in matches if m["round_number"] == 1]
    gf = [m for m in matches if m["round_number"] == 2]

    assert len(sf) == 2
    assert len(gf) == 1
    assert sf[0]["round_name"] == "Semi Final"
    assert gf[0]["round_name"] == "Grand Final"

    assert sf[0]["next_match_id"] == gf[0]["id"]
    assert sf[0]["next_slot"] == "A"
    assert sf[1]["next_match_id"] == gf[0]["id"]
    assert sf[1]["next_slot"] == "B"


def test_generate_5_team_bracket_byes():
    team_ids = [f"team-{i}" for i in range(1, 6)]
    matches = SingleEliminationBracketEngine.generate_bracket(
        tournament_id="tour-5",
        team_ids=team_ids,
        best_of=3,
    )
    assert len(matches) == 7
    qf = [m for m in matches if m["round_number"] == 1]
    byes = [m for m in qf if m["status"] == "bye"]
    assert len(byes) == 3


def test_bracket_engine_input_validations():
    with pytest.raises(DomainValidationError, match="Minimal 2 tim"):
        SingleEliminationBracketEngine.generate_bracket(
            tournament_id="tour-err",
            team_ids=["team-1"],
        )

    with pytest.raises(DomainValidationError, match="duplikasi tim"):
        SingleEliminationBracketEngine.generate_bracket(
            tournament_id="tour-err",
            team_ids=["team-1", "team-1"],
        )


def test_score_validation_bo1_bo5_bo7():
    assert validate_match_score(1, 0, best_of=1) == "A"
    assert validate_match_score(0, 1, best_of=1) == "B"
    with pytest.raises(DomainValidationError):
        validate_match_score(0, 0, best_of=1)
    with pytest.raises(DomainValidationError):
        validate_match_score(2, 0, best_of=1)

    assert validate_match_score(3, 0, best_of=5) == "A"
    assert validate_match_score(3, 2, best_of=5) == "A"
    assert validate_match_score(1, 3, best_of=5) == "B"
    with pytest.raises(DomainValidationError):
        validate_match_score(2, 2, best_of=5)
    with pytest.raises(DomainValidationError):
        validate_match_score(4, 1, best_of=5)

    assert validate_match_score(4, 0, best_of=7) == "A"
    assert validate_match_score(4, 3, best_of=7) == "A"
    assert validate_match_score(2, 4, best_of=7) == "B"
    with pytest.raises(DomainValidationError):
        validate_match_score(3, 3, best_of=7)
    with pytest.raises(DomainValidationError):
        validate_match_score(5, 2, best_of=7)


def test_match_winner_advancement_and_audit_lock(
    mock_repo: MockDataStoreRepository,
):
    match_service = MatchService(mock_repo)
    committee_user = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert committee_user is not None

    qf4_id = "88888888-8888-4888-8888-888888888804"
    sf2_id = "88888888-8888-4888-8888-888888888806"

    res = match_service.submit_match_result(
        actor=committee_user,
        match_id=qf4_id,
        payload={"score_a": 1, "score_b": 2, "notes": "Dewata menang tipis 2-1"},
    )
    assert res["match"]["status"] == "completed"
    assert res["match"]["winner_team_id"] == "44444444-4444-4444-8444-444444444408"

    sf2 = mock_repo.get_match_by_id(sf2_id)
    assert sf2 is not None
    assert sf2["team_b_id"] == "44444444-4444-4444-8444-444444444408"

    with pytest.raises(DomainConflictError, match="sudah disahkan dan dikunci"):
        match_service.submit_match_result(
            actor=committee_user,
            match_id=qf4_id,
            payload={"score_a": 2, "score_b": 0},
        )

    # Verifikasi force_override berhasil mengubah hasil pertandingan terkunci
    override_res = match_service.submit_match_result(
        actor=committee_user,
        match_id=qf4_id,
        payload={
            "score_a": 2,
            "score_b": 0,
            "force_override": True,
            "notes": "Koreksi skor panitia",
        },
    )
    assert override_res["match"]["winner_team_id"] == "44444444-4444-4444-8444-444444444407"


def test_grand_final_completion_updates_tournament_status(
    mock_repo: MockDataStoreRepository,
):
    match_service = MatchService(mock_repo)
    committee_user = mock_repo.get_profile_by_email("committee@turnamen.in")
    assert committee_user is not None

    sf1_id = "88888888-8888-4888-8888-888888888805"
    gf_id = "88888888-8888-4888-8888-888888888807"
    tournament_id = "33333333-3333-4333-8333-333333333301"

    # Jalankan SF1
    match_service.submit_match_result(
        actor=committee_user,
        match_id=sf1_id,
        payload={"score_a": 2, "score_b": 1},
    )

    # QF4 lalu SF2
    qf4_id = "88888888-8888-4888-8888-888888888804"
    match_service.submit_match_result(
        actor=committee_user,
        match_id=qf4_id,
        payload={"score_a": 2, "score_b": 0},
    )
    sf2_id = "88888888-8888-4888-8888-888888888806"
    match_service.submit_match_result(
        actor=committee_user,
        match_id=sf2_id,
        payload={"score_a": 2, "score_b": 1},
    )

    # Grand Final selesai
    gf_res = match_service.submit_match_result(
        actor=committee_user,
        match_id=gf_id,
        payload={"score_a": 2, "score_b": 0, "notes": "Grand Final selesai"},
    )
    assert gf_res["match"]["status"] == "completed"
    assert gf_res["next_match"] is None

    tournament = mock_repo.get_tournament_by_id(tournament_id)
    assert tournament is not None
    assert tournament["status"] == "completed"


def test_staff_access_control_on_match_management(
    mock_repo: MockDataStoreRepository,
):
    match_service = MatchService(mock_repo)
    captain_user = mock_repo.get_profile_by_email("captain@turnamen.in")
    other_organizer = mock_repo.get_profile_by_email("organizer2@turnamen.in")
    qf4_id = "88888888-8888-4888-8888-888888888804"

    # Kapten tidak memiliki izin submit hasil match
    with pytest.raises(DomainForbiddenError):
        match_service.submit_match_result(
            actor=captain_user,
            match_id=qf4_id,
            payload={"score_a": 2, "score_b": 0},
        )

    # Organizer lain yang tidak memiliki turnamen ditolak
    if other_organizer:
        with pytest.raises(DomainForbiddenError):
            match_service.submit_match_result(
                actor=other_organizer,
                match_id=qf4_id,
                payload={"score_a": 2, "score_b": 0},
            )


def test_tournament_capacity_and_duplicate_registration(
    mock_repo: MockDataStoreRepository,
):
    tournament_service = TournamentService(mock_repo)
    organizer_user = mock_repo.get_profile_by_email("organizer@turnamen.in")
    captain_user = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert organizer_user is not None
    assert captain_user is not None

    tour = tournament_service.create_tournament(
        actor=organizer_user,
        payload={
            "title": "Open MLBB Mini Cup 2026",
            "game_id": "22222222-2222-4222-8222-222222222201",
            "start_date": "2026-12-01T10:00:00Z",
            "max_teams": 2,
            "status": "open_registration",
        },
    )

    # Pendaftaran tim pertama berhasil
    reg1 = tournament_service.register_team(
        actor=captain_user,
        tournament_id=tour["id"],
        payload={"team_id": "44444444-4444-4444-8444-444444444401"},
    )
    assert reg1["status"] == "pending"

    # Tim yang sudah terdaftar ditolak
    with pytest.raises(DomainConflictError, match="sudah terdaftar"):
        tournament_service.register_team(
            actor=captain_user,
            tournament_id=tour["id"],
            payload={"team_id": "44444444-4444-4444-8444-444444444401"},
        )

    # Pendaftaran tim kedua berhasil (kuota penuh: 2/2)
    tournament_service.register_team(
        actor=captain_user,
        tournament_id=tour["id"],
        payload={"team_id": "44444444-4444-4444-8444-444444444402"},
    )

    # Pendaftaran tim ketiga ditolak karena kuota penuh
    with pytest.raises(DomainConflictError, match="Kuota turnamen sudah penuh"):
        tournament_service.register_team(
            actor=captain_user,
            tournament_id=tour["id"],
            payload={"team_id": "44444444-4444-4444-8444-444444444403"},
        )


def test_team_roster_and_member_role_validations(
    mock_repo: MockDataStoreRepository,
):
    team_service = TeamService(mock_repo)
    captain_user = mock_repo.get_profile_by_email("captain@turnamen.in")
    assert captain_user is not None

    # Tag duplikat ditolak
    with pytest.raises(DomainConflictError, match="sudah digunakan"):
        team_service.create_team(
            actor=captain_user,
            payload={
                "name": "Garuda Muda Esports",
                "tag": "GRD",
                "game_id": "22222222-2222-4222-8222-222222222201",
            },
        )

    # Role anggota tidak valid
    with pytest.raises(DomainValidationError, match="tidak valid"):
        team_service.add_member(
            actor=captain_user,
            team_id="44444444-4444-4444-8444-444444444401",
            payload={
                "nickname": "PlayerX",
                "ingame_id": "ML-99999999 (2011)",
                "member_role": "cheerleader",
            },
        )

    # ID Game duplikat di tim yang sama
    with pytest.raises(DomainConflictError, match="sudah terdaftar"):
        team_service.add_member(
            actor=captain_user,
            team_id="44444444-4444-4444-8444-444444444401",
            payload={
                "nickname": "Clone",
                "ingame_id": "ML-10293801 (2011)",
                "member_role": "substitute",
            },
        )
