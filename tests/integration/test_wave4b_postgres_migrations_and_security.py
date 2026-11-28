"""PostgreSQL integration and security tests for Wave 4B migrations 0001-0005.

Runs against an ephemeral, isolated local PostgreSQL cluster created via `initdb`
and bound strictly to `127.0.0.1` on an unused port. Never touches Supabase Cloud
or the developer's main local PostgreSQL cluster.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import uuid
from typing import Any, Iterator

import psycopg
import pytest
from psycopg import errors as pg_errors
from psycopg.rows import dict_row

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"
SEED_FILE = REPO_ROOT / "supabase" / "seed.sql"

MIGRATION_FILES = [
    MIGRATIONS_DIR / "0001_initial_schema.sql",
    MIGRATIONS_DIR / "0002_security_hardening.sql",
    MIGRATIONS_DIR / "0003_wave2_rls_compatibility.sql",
    MIGRATIONS_DIR / "0004_wave2_3_atomic_match_submission.sql",
    MIGRATIONS_DIR / "0005_supa001_auth_trigger_hardening.sql",
    MIGRATIONS_DIR / "0006_wave5_functional_rpc.sql",
    MIGRATIONS_DIR / "20261126232622_wave6_11_custom_game_artwork.sql",
]

AUTH_SHIM_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN BYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
        CREATE ROLE authenticator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD 'test_auth_pw';
    END IF;
END;
$$;

GRANT anon, authenticated, service_role TO authenticator;

CREATE SCHEMA IF NOT EXISTS auth;
REVOKE ALL ON SCHEMA auth FROM PUBLIC;
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;

CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    raw_user_meta_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    email_confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

REVOKE ALL ON TABLE auth.users FROM PUBLIC, anon, authenticated;
GRANT ALL ON TABLE auth.users TO service_role;

CREATE OR REPLACE FUNCTION auth.uid()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(
        COALESCE(
            NULLIF(current_setting('request.jwt.claim.sub', true), ''),
            NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'
        ),
        ''
    )::uuid;
$$;

CREATE OR REPLACE FUNCTION auth.role()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(
        NULLIF(current_setting('request.jwt.claim.role', true), ''),
        NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role',
        current_user::text
    );
$$;

GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION auth.role() TO anon, authenticated, service_role;
"""


def _find_pg_bin(exe_name: str) -> str:
    override_dir = os.environ.get("TURNAMEN_PG_BIN_DIR", "").strip()
    if override_dir:
        candidate = Path(override_dir) / f"{exe_name}.exe"
        if candidate.exists():
            return str(candidate)
        plain = Path(override_dir) / exe_name
        if plain.exists():
            return str(plain)
        raise RuntimeError(f"PostgreSQL binary '{exe_name}' not found in TURNAMEN_PG_BIN_DIR={override_dir}.")
    found = shutil.which(exe_name)
    if found:
        return found
    default_path = Path(r"C:\Program Files\PostgreSQL\18\bin") / f"{exe_name}.exe"
    if default_path.exists():
        return str(default_path)
    raise RuntimeError(f"PostgreSQL binary '{exe_name}' not found.")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_psql_file(port: int, dbname: str, sql_path: Path) -> None:
    psql_bin = _find_pg_bin("psql")
    proc = subprocess.run(
        [
            psql_bin,
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            "-U",
            "postgres",
            "-d",
            dbname,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(sql_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"psql failed on {sql_path.name} (exit={proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def _create_isolated_database(port: int, dbname: str) -> None:
    with psycopg.connect(
        host="127.0.0.1", port=port, user="postgres", dbname="postgres", autocommit=True
    ) as conn:
        conn.execute(f'CREATE DATABASE "{dbname}"')

    with psycopg.connect(
        host="127.0.0.1", port=port, user="postgres", dbname=dbname, autocommit=True
    ) as conn:
        conn.execute(AUTH_SHIM_SQL)

    for migration in MIGRATION_FILES:
        _run_psql_file(port, dbname, migration)

    # Grant schema/table access mirroring Supabase PostgREST defaults so RLS gates access.
    with psycopg.connect(
        host="127.0.0.1", port=port, user="postgres", dbname=dbname, autocommit=True
    ) as conn:
        conn.execute(
            """
            GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
            GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
            REVOKE INSERT, UPDATE, DELETE ON public.match_submission_requests FROM authenticated, anon, PUBLIC;
            GRANT SELECT ON public.match_submission_requests TO authenticated;
            GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
            GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role;
            """
        )


class EphemeralPgCluster:
    """Lifecycle wrapper for an ephemeral initdb/pg_ctl PostgreSQL cluster."""

    def __init__(self) -> None:
        self.base_dir = Path(tempfile.mkdtemp(prefix="turnamen_wave4b_pg_"))
        self.data_dir = self.base_dir / "data"
        self.log_file = self.base_dir / "postgres.log"
        self.port = _find_free_port()
        self.started = False

    def start(self) -> None:
        initdb_bin = _find_pg_bin("initdb")
        pg_ctl_bin = _find_pg_bin("pg_ctl")

        subprocess.run(
            [
                initdb_bin,
                "-D",
                str(self.data_dir),
                "-U",
                "postgres",
                "-A",
                "trust",
                "--encoding=UTF8",
                "--locale=C",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        pg_options = f"-p {self.port} -h 127.0.0.1"
        try:
            # Close inherited stdout/stderr pipes on Windows so pg_ctl start does not hang on postgres.exe.
            subprocess.run(
                [
                    pg_ctl_bin,
                    "-D",
                    str(self.data_dir),
                    "-l",
                    str(self.log_file),
                    "-o",
                    pg_options,
                    "-w",
                    "start",
                ],
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as exc:
            log_tail = (
                self.log_file.read_text(encoding="utf-8", errors="replace")[-2000:]
                if self.log_file.exists()
                else ""
            )
            raise RuntimeError(f"pg_ctl start failed (exit={exc.returncode}):\n{log_tail}") from exc
        self.started = True

    def stop(self) -> None:
        if self.started:
            pg_ctl_bin = _find_pg_bin("pg_ctl")
            subprocess.run(
                [pg_ctl_bin, "-D", str(self.data_dir), "-m", "immediate", "-w", "stop"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.started = False
        shutil.rmtree(self.base_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def pg_cluster() -> Iterator[EphemeralPgCluster]:
    cluster = EphemeralPgCluster()
    cluster.start()
    try:
        yield cluster
    finally:
        cluster.stop()


@pytest.fixture(scope="module")
def seeded_db(pg_cluster: EphemeralPgCluster) -> str:
    dbname = "turnamen_wave4b_main"
    _create_isolated_database(pg_cluster.port, dbname)
    _run_psql_file(pg_cluster.port, dbname, SEED_FILE)
    return dbname


@contextmanager
def as_client_session(
    port: int,
    dbname: str,
    *,
    role: str = "authenticated",
    auth_user_id: str | None = None,
) -> Iterator[psycopg.Connection]:
    """Open an unprivileged authenticator session simulating Supabase PostgREST JWT context."""
    conn = psycopg.connect(
        host="127.0.0.1",
        port=port,
        user="authenticator",
        password="test_auth_pw",
        dbname=dbname,
        row_factory=dict_row,
    )
    try:
        with conn.transaction():
            conn.execute(f"SET LOCAL ROLE {role}")
            claims = {"role": role}
            if auth_user_id:
                claims["sub"] = str(auth_user_id)
                conn.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (str(auth_user_id),))
            else:
                conn.execute("SELECT set_config('request.jwt.claim.sub', '', true)")
            conn.execute("SELECT set_config('request.jwt.claim.role', %s, true)", (role,))
            conn.execute("SELECT set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))
            yield conn
    finally:
        conn.close()


def _create_auth_user(
    port: int,
    dbname: str,
    *,
    email: str,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    confirmed: bool = True,
) -> str:
    uid = user_id or str(uuid.uuid4())
    with psycopg.connect(
        host="127.0.0.1", port=port, user="postgres", dbname=dbname, autocommit=False
    ) as conn:
        with conn.transaction():
            conn.execute(
                """
                INSERT INTO auth.users (id, email, raw_user_meta_data, email_confirmed_at)
                VALUES (%s, %s, %s::jsonb, CASE WHEN %s THEN NOW() ELSE NULL END)
                """,
                (uid, email, json.dumps(metadata or {}), confirmed),
            )
    return uid


def test_fresh_database_migration_order_and_schema_objects(pg_cluster: EphemeralPgCluster) -> None:
    """Verify clean execution of 0001 -> 0005 on a brand-new empty database."""
    fresh_db = "turnamen_wave4b_fresh"
    _create_isolated_database(pg_cluster.port, fresh_db)

    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=fresh_db, row_factory=dict_row
    ) as conn:
        version_row = conn.execute("SELECT version() AS ver").fetchone()
        assert version_row is not None
        expected_major = os.environ.get("TURNAMEN_EXPECTED_PG_MAJOR", "").strip()
        if expected_major:
            assert f"PostgreSQL {expected_major}." in version_row["ver"]
        else:
            assert "PostgreSQL 17." in version_row["ver"] or "PostgreSQL 18." in version_row["ver"]

        tables = {
            r["relname"]: r["relrowsecurity"]
            for r in conn.execute(
                """
                SELECT c.relname, c.relrowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                """
            ).fetchall()
        }
        expected_tables = {
            "profiles",
            "games",
            "tournaments",
            "teams",
            "team_members",
            "tournament_staff",
            "registrations",
            "matches",
            "match_results",
            "payments",
            "announcements",
            "activity_logs",
            "match_submission_requests",
        }
        assert expected_tables.issubset(tables.keys())
        for tbl in expected_tables:
            assert tables[tbl] is True, f"RLS must be enabled on {tbl}"

        indexes = {
            r["indexname"]
            for r in conn.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
            ).fetchall()
        }
        assert "uq_tournament_seed" in indexes
        assert "uq_profiles_lower_email" in indexes

        private_funcs = {
            r["proname"]: r
            for r in conn.execute(
                """
                SELECT p.proname, p.prosecdef, p.proconfig
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'private'
                """
            ).fetchall()
        }
        for fn_name in (
            "validate_tournament_bracket_integrity",
            "transition_tournament_status",
            "get_public_profile_summary",
            "register_team_atomic",
            "submit_match_result_atomic",
            "link_profile_auth_user",
            "assign_user_role",
            "list_committee_candidates",
            "list_tournament_staff",
        ):
            assert fn_name in private_funcs
            assert private_funcs[fn_name]["prosecdef"] is True
            assert any(
                cfg in ('search_path=""', "search_path=")
                for cfg in (private_funcs[fn_name]["proconfig"] or [])
            )

        public_rpcs = {
            r["proname"]: r
            for r in conn.execute(
                """
                SELECT p.proname, p.prosecdef, p.proconfig,
                       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_exec,
                       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_exec
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public'
                """
            ).fetchall()
        }
        for rpc_name in (
            "get_public_profile_summary",
            "transition_tournament_status",
            "register_team_atomic",
            "replace_tournament_matches",
            "submit_match_result_atomic",
            "link_profile_auth_user",
            "assign_user_role",
            "list_committee_candidates",
            "list_tournament_staff",
        ):
            assert rpc_name in public_rpcs
            assert public_rpcs[rpc_name]["anon_exec"] is False
            assert public_rpcs[rpc_name]["auth_exec"] is True
            assert any(
                cfg in ('search_path=""', "search_path=")
                for cfg in (public_rpcs[rpc_name]["proconfig"] or [])
            )

        ann_rpc = public_rpcs["list_tournament_announcements"]
        assert ann_rpc["prosecdef"] is True
        assert ann_rpc["anon_exec"] is True
        assert ann_rpc["auth_exec"] is True
        assert any(
            cfg in ('search_path=""', "search_path=")
            for cfg in (ann_rpc["proconfig"] or [])
        )

        # Critical SUPA-001 helpers must also lock search_path=''
        for helper in (
            "set_updated_at",
            "current_profile_id",
            "current_user_role",
            "is_tournament_organizer",
            "is_tournament_committee",
            "is_team_captain",
            "handle_new_auth_user",
            "prevent_profile_privilege_escalation",
        ):
            assert helper in public_rpcs
            assert any(
                cfg in ('search_path=""', "search_path=")
                for cfg in (public_rpcs[helper]["proconfig"] or [])
            )

        assert public_rpcs["handle_new_auth_user"]["anon_exec"] is False
        assert public_rpcs["handle_new_auth_user"]["auth_exec"] is False
        assert public_rpcs["prevent_profile_privilege_escalation"]["anon_exec"] is False
        assert public_rpcs["prevent_profile_privilege_escalation"]["auth_exec"] is False

        triggers = {
            (r["event_object_schema"], r["event_object_table"], r["trigger_name"])
            for r in conn.execute(
                """
                SELECT event_object_schema, event_object_table, trigger_name
                FROM information_schema.triggers
                """
            ).fetchall()
        }
        assert ("auth", "users", "on_auth_user_created") in triggers
        assert ("public", "profiles", "trg_prevent_profile_privilege_escalation") in triggers


def test_second_fresh_database_independence(pg_cluster: EphemeralPgCluster) -> None:
    """Confirm 0001 -> 0005 also succeed on a second independent fresh database."""
    second_db = "turnamen_wave4b_fresh_2"
    _create_isolated_database(pg_cluster.port, second_db)
    _run_psql_file(pg_cluster.port, second_db, SEED_FILE)

    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=second_db, row_factory=dict_row
    ) as conn:
        cnt = conn.execute("SELECT COUNT(*) AS c FROM public.profiles").fetchone()
        assert cnt is not None and cnt["c"] == 5


def test_supa001_public_signup_cannot_hijack_seeded_profiles(
    pg_cluster: EphemeralPgCluster, seeded_db: str
) -> None:
    """Public signup reusing admin/organizer/committee email must fail and leave seeded row intact."""
    for target_email, expected_role in (
        ("admin@turnamen.in", "super_admin"),
        ("ADMIN@TURNAMEN.IN", "super_admin"),
        ("organizer@turnamen.in", "organizer"),
        ("committee@turnamen.in", "committee"),
    ):
        attacker_uid = str(uuid.uuid4())
        with pytest.raises(pg_errors.UniqueViolation):
            _create_auth_user(
                pg_cluster.port,
                seeded_db,
                email=target_email,
                user_id=attacker_uid,
                metadata={"username": f"hijack_{attacker_uid[:6]}", "role": "player"},
            )

        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
        ) as conn:
            auth_row = conn.execute("SELECT id FROM auth.users WHERE id = %s", (attacker_uid,)).fetchone()
            assert auth_row is None, "Trigger exception must rollback auth.users row"

            prof_row = conn.execute(
                "SELECT auth_user_id, role FROM public.profiles WHERE LOWER(email) = %s",
                (target_email.lower(),),
            ).fetchone()
            assert prof_row is not None
            assert prof_row["auth_user_id"] is None
            assert prof_row["role"] == expected_role


def test_supa001_raw_user_meta_data_cannot_grant_privileged_roles(
    pg_cluster: EphemeralPgCluster, seeded_db: str
) -> None:
    """Spoofing privileged roles in auth signup metadata must downgrade to player."""
    for attempted_role in ("super_admin", "organizer", "committee", "ADMIN"):
        uid = _create_auth_user(
            pg_cluster.port,
            seeded_db,
            email=f"spoof_{attempted_role.lower()}_{uuid.uuid4().hex[:6]}@example.test",
            metadata={"role": attempted_role},
        )
        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
        ) as conn:
            prof = conn.execute(
                "SELECT role, auth_user_id FROM public.profiles WHERE auth_user_id = %s", (uid,)
            ).fetchone()
            assert prof is not None
            assert prof["role"] == "player"
            assert str(prof["auth_user_id"]) == uid

    # Self-registrable roles ('player' and 'team_captain') continue to initialize safely.
    capt_uid = _create_auth_user(
        pg_cluster.port,
        seeded_db,
        email=f"captain_legit_{uuid.uuid4().hex[:6]}@example.test",
        metadata={"role": "team_captain", "full_name": "Legit Captain"},
    )
    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
    ) as conn:
        capt = conn.execute("SELECT role FROM public.profiles WHERE auth_user_id = %s", (capt_uid,)).fetchone()
        assert capt is not None and capt["role"] == "team_captain"


def test_security_regression_privilege_escalation_linking_and_case_sensitivity(
    pg_cluster: EphemeralPgCluster, seeded_db: str
) -> None:
    """Cover non-admin escalation, cross-profile linking, case-insensitive duplicates, and orphan auth users."""
    p1_email = f"MixedCase_{uuid.uuid4().hex[:6]}@Turnamen.Test"
    p1_uid = _create_auth_user(pg_cluster.port, seeded_db, email=p1_email, metadata={"role": "player"})

    # 1. Case-insensitive duplicate signup raises 23505 and rolls back cleanly.
    dup_uid = str(uuid.uuid4())
    with pytest.raises(pg_errors.UniqueViolation):
        _create_auth_user(pg_cluster.port, seeded_db, email=p1_email.lower(), user_id=dup_uid)
    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
    ) as conn:
        assert conn.execute("SELECT 1 FROM auth.users WHERE id = %s", (dup_uid,)).fetchone() is None

    # 2. Direct profile email/role/auth_user_id escalation as authenticated user is denied,
    #    while allowed self-service profile fields (full_name, phone) succeed.
    for column, value in (
        ("role", "super_admin"),
        ("role", "organizer"),
        ("role", "committee"),
        ("auth_user_id", str(uuid.uuid4())),
        ("is_active", False),
        ("email", f"changed_{uuid.uuid4().hex[:6]}@example.test"),
        ("username", f"changed_{uuid.uuid4().hex[:6]}"),
    ):
        with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=p1_uid) as conn:
            with pytest.raises(pg_errors.InsufficientPrivilege):
                conn.execute(
                    f"UPDATE public.profiles SET {column} = %s WHERE auth_user_id = %s",
                    (value, p1_uid),
                )

    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=p1_uid) as conn:
        updated_own = conn.execute(
            "UPDATE public.profiles SET full_name = 'Updated Player Name', phone = '08123456789' "
            "WHERE auth_user_id = %s RETURNING full_name, phone, role",
            (p1_uid,),
        ).fetchone()
        assert updated_own == {"full_name": "Updated Player Name", "phone": "08123456789", "role": "player"}

    # 2b. Anonymous (anon) RLS enforcement: public catalog readable, private tables/profiles hidden.
    with as_client_session(pg_cluster.port, seeded_db, role="anon") as conn:
        games = conn.execute("SELECT id FROM public.games").fetchall()
        assert len(games) >= 3
        assert conn.execute("SELECT id FROM public.profiles").fetchall() == []
        assert conn.execute("SELECT id FROM public.payments").fetchall() == []
        assert conn.execute("SELECT id FROM public.tournament_staff").fetchall() == []
        assert conn.execute("SELECT id FROM public.activity_logs").fetchall() == []
        assert conn.execute("SELECT id FROM public.match_submission_requests").fetchall() == []

    # 3. Non-admin cannot link or update an unlinked profile (auth_user_id IS NULL) nor call assign_user_role.
    seeded_admin_profile_id = "11111111-1111-4111-8111-111111111101"
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=p1_uid) as conn:
        res = conn.execute(
            "UPDATE public.profiles SET auth_user_id = %s WHERE id = %s RETURNING id",
            (p1_uid, seeded_admin_profile_id),
        ).fetchall()
        assert res == []

        with pytest.raises(pg_errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute(
                    "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                    (seeded_admin_profile_id, p1_uid),
                )
        with pytest.raises(pg_errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute(
                    "SELECT * FROM public.assign_user_role(%s::uuid, %s)",
                    (p1_uid, "organizer"),
                )

    # 4. User in auth.users WITHOUT a profile receives NULL identity/role and zero privileged access.
    orphan_auth_uid = str(uuid.uuid4())
    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, autocommit=False
    ) as conn:
        with conn.transaction():
            # Bypass trigger using DISABLE/enable simulation only in test DB to model pre-existing Cloud auth user without profile
            conn.execute("ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created")
            conn.execute(
                "INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, %s, NOW())",
                (orphan_auth_uid, f"noprofile_{uuid.uuid4().hex[:6]}@example.test"),
            )
            conn.execute("ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created")

    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=orphan_auth_uid) as conn:
        ids = conn.execute("SELECT public.current_profile_id() AS pid, public.current_user_role() AS r").fetchone()
        assert ids == {"pid": None, "r": None}
        assert conn.execute("SELECT * FROM public.profiles").fetchall() == []
        with pytest.raises(pg_errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute("SELECT * FROM public.assign_user_role(%s::uuid, 'committee')", (p1_uid,))

    # 5. Trusted linking validation: reject unconfirmed email and email mismatch, accept verified match,
    #    and support service_role via request.jwt.claims.
    seeded_organizer_profile_id = "11111111-1111-4111-8111-111111111102"
    unconfirmed_org_uid = str(uuid.uuid4())
    confirmed_org_uid = str(uuid.uuid4())
    admin_auth_uid = str(uuid.uuid4())
    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
    ) as conn:
        with conn.transaction():
            conn.execute("ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created")
            conn.execute(
                "INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, 'admin@turnamen.in', NOW())",
                (admin_auth_uid,),
            )
            conn.execute(
                "INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, 'organizer@turnamen.in', NULL)",
                (unconfirmed_org_uid,),
            )
            conn.execute("ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created")

            # Unconfirmed auth user must be rejected.
            with pytest.raises(pg_errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(
                        "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                        (seeded_organizer_profile_id, unconfirmed_org_uid),
                    )
            # Email mismatch must be rejected.
            with pytest.raises(pg_errors.InvalidParameterValue):
                with conn.transaction():
                    conn.execute(
                        "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                        (seeded_organizer_profile_id, p1_uid),
                    )

            # Trusted maintenance linking binds seeded admin safely.
            linked = conn.execute(
                "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                (seeded_admin_profile_id, admin_auth_uid),
            ).fetchone()
            assert linked is not None and str(linked["auth_user_id"]) == admin_auth_uid

            # Retrying link_profile_auth_user with the same pair is idempotent.
            idempotent = conn.execute(
                "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                (seeded_admin_profile_id, admin_auth_uid),
            ).fetchone()
            assert idempotent is not None and idempotent["role"] == "super_admin"

            # Prepare verified organizer auth user and link via simulated service_role JWT claims.
            conn.execute("ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created")
            conn.execute(
                "UPDATE auth.users SET id = %s, email_confirmed_at = NOW() WHERE id = %s",
                (confirmed_org_uid, unconfirmed_org_uid),
            )
            conn.execute("ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created")

        # Mismatched overwrite must fail and preserve original super_admin link.
        with pytest.raises(pg_errors.ProgrammingError) as exc_info:
            with conn.transaction():
                conn.execute(
                    "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                    (seeded_admin_profile_id, p1_uid),
                )
        assert exc_info.value.sqlstate == "P0009"

    with as_client_session(pg_cluster.port, seeded_db, role="service_role") as conn:
        linked_org = conn.execute(
            "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
            (seeded_organizer_profile_id, confirmed_org_uid),
        ).fetchone()
        assert linked_org is not None and str(linked_org["auth_user_id"]) == confirmed_org_uid

    # 6. Trusted super_admin can call assign_user_role on linked profiles (and cannot on unlinked profiles),
    #    while organizer/committee cannot scrape unrelated profiles PII.
    seeded_committee_profile_id = "11111111-1111-4111-8111-111111111103"
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=admin_auth_uid) as conn:
        with pytest.raises(pg_errors.ProgrammingError) as exc_info:
            with conn.transaction():
                conn.execute(
                    "SELECT * FROM public.assign_user_role(%s::uuid, 'organizer')",
                    (seeded_committee_profile_id,),
                )
        assert exc_info.value.sqlstate == "P0009"
        promoted = conn.execute(
            "SELECT * FROM public.assign_user_role(%s::uuid, 'organizer')",
            (p1_uid,),
        ).fetchone()
        assert promoted is not None and promoted["role"] == "organizer"

        audit = conn.execute(
            "SELECT action, details FROM public.activity_logs "
            "WHERE entity_id = %s AND action = 'USER_ROLE_UPDATED' ORDER BY created_at DESC LIMIT 1",
            (p1_uid,),
        ).fetchone()
        assert audit is not None
        assert audit["details"]["new_role"] == "organizer"

    # Promoted organizer cannot read unrelated user emails from public.profiles (PII lockdown in 0005).
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=p1_uid) as conn:
        visible = conn.execute("SELECT id, auth_user_id, email FROM public.profiles").fetchall()
        assert len(visible) == 1
        assert str(visible[0]["auth_user_id"]) == p1_uid
        with pytest.raises(pg_errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute(
                    "SELECT * FROM public.assign_user_role(%s::uuid, 'super_admin')",
                    (p1_uid,),
                )

    # Trigger rollback test: duplicate username in auth.users metadata rolls back auth.users insert cleanly.
    dup_username_uid = str(uuid.uuid4())
    with pytest.raises(pg_errors.UniqueViolation):
        _create_auth_user(
            pg_cluster.port,
            seeded_db,
            email=f"dupuser_{uuid.uuid4().hex[:6]}@example.test",
            user_id=dup_username_uid,
            metadata={"username": "superadmin"},
        )
    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
    ) as conn:
        assert conn.execute("SELECT 1 FROM auth.users WHERE id = %s", (dup_username_uid,)).fetchone() is None


def test_rpc_integration_and_concurrent_registration_and_match_submission(
    pg_cluster: EphemeralPgCluster,
) -> None:
    """Exercise all 5 repository RPCs including concurrent registration and match submission."""
    dbname = "turnamen_wave4b_rpc"
    _create_isolated_database(pg_cluster.port, dbname)

    # Create authenticated users across roles via genuine auth.users trigger + super_admin role promotion.
    admin_uid = _create_auth_user(
        pg_cluster.port, dbname, email="rpc_admin@example.test", metadata={"username": "rpc_admin"}
    )
    eo_uid = _create_auth_user(
        pg_cluster.port, dbname, email="rpc_eo@example.test", metadata={"username": "rpc_eo"}
    )
    comm_uid = _create_auth_user(
        pg_cluster.port, dbname, email="rpc_comm@example.test", metadata={"username": "rpc_comm"}
    )
    unassigned_comm_uid = _create_auth_user(
        pg_cluster.port, dbname, email="rpc_unassigned@example.test", metadata={"username": "rpc_unassigned"}
    )
    captain_uids = [
        _create_auth_user(
            pg_cluster.port,
            dbname,
            email=f"rpc_capt_{i}@example.test",
            metadata={"username": f"rpc_capt_{i}", "role": "team_captain"},
        )
        for i in range(4)
    ]

    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=dbname, row_factory=dict_row
    ) as conn:
        with conn.transaction():
            conn.execute("UPDATE public.profiles SET role = 'super_admin' WHERE auth_user_id = %s", (admin_uid,))
            conn.execute("UPDATE public.profiles SET role = 'organizer' WHERE auth_user_id = %s", (eo_uid,))
            conn.execute("UPDATE public.profiles SET role = 'committee' WHERE auth_user_id = %s", (comm_uid,))
            conn.execute("UPDATE public.profiles SET role = 'committee' WHERE auth_user_id = %s", (unassigned_comm_uid,))

            game_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO public.games (id, slug, name, genre, team_size, default_best_of)
                VALUES (%s, 'mlbb-rpc', 'MLBB RPC Test', 'MOBA', 5, 3)
                """,
                (game_id,),
            )

            tournament_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO public.tournaments (
                    id, slug, title, game_id, organizer_id, status, max_teams, best_of, start_date
                )
                VALUES (%s, 'rpc-cup-2026', 'RPC Cup 2026', %s, %s, 'open_registration', 2, 3, NOW() + INTERVAL '1 day')
                """,
                (tournament_id, game_id, eo_uid),
            )
            conn.execute(
                """
                INSERT INTO public.tournament_staff (tournament_id, user_id, staff_role)
                VALUES (%s, %s, 'head_committee')
                """,
                (tournament_id, comm_uid),
            )

            team_ids: list[str] = []
            for idx, capt_uid in enumerate(captain_uids):
                tid = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO public.teams (id, name, tag, game_id, captain_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (tid, f"Squad {idx}", f"SQ{idx}", game_id, capt_uid),
                )
                team_ids.append(tid)

    # 1. get_public_profile_summary: owning captain sees 4 safe columns; non-owner denied; anon denied.
    with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=captain_uids[0]) as conn:
        summary = conn.execute(
            "SELECT * FROM public.get_public_profile_summary(%s::uuid, %s::uuid)",
            (captain_uids[1], team_ids[0]),
        ).fetchone()
        assert set(summary.keys()) == {"id", "username", "full_name", "avatar_url"}
        assert summary["username"] == "rpc_capt_1"

        with pytest.raises(pg_errors.InsufficientPrivilege):
            conn.execute(
                "SELECT * FROM public.get_public_profile_summary(%s::uuid, %s::uuid)",
                (captain_uids[2], team_ids[1]),
            )

    with as_client_session(pg_cluster.port, dbname, role="anon") as conn:
        with pytest.raises(pg_errors.InsufficientPrivilege):
            conn.execute(
                "SELECT * FROM public.get_public_profile_summary(%s::uuid, %s::uuid)",
                (captain_uids[1], team_ids[0]),
            )

    # 2. Concurrent register_team_atomic against max_teams = 2.
    def attempt_register(idx: int) -> str:
        try:
            with as_client_session(
                pg_cluster.port, dbname, role="authenticated", auth_user_id=captain_uids[idx]
            ) as conn:
                conn.execute(
                    "SELECT * FROM public.register_team_atomic(%s::uuid, %s::uuid, %s)",
                    (tournament_id, team_ids[idx], f"Concurrent {idx}"),
                ).fetchone()
            return "ok"
        except pg_errors.Error as exc:
            return f"err:{exc.sqlstate}"

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(attempt_register, range(4)))

    assert outcomes.count("ok") == 2
    assert outcomes.count("err:P0009") == 2

    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=dbname, row_factory=dict_row
    ) as conn:
        regs = conn.execute(
            "SELECT team_id, seed_number FROM public.registrations WHERE tournament_id = %s ORDER BY seed_number",
            (tournament_id,),
        ).fetchall()
        assert len(regs) == 2
        assert [r["seed_number"] for r in regs] == [1, 2]
        winner_teams = [str(r["team_id"]) for r in regs]

    # 3. replace_tournament_matches + transition_tournament_status (assigned committee vs unassigned committee).
    gf_id = str(uuid.uuid4())
    matches_payload = [
        {
            "id": gf_id,
            "round_number": 1,
            "round_name": "Grand Final",
            "match_number": 1,
            "team_a_id": winner_teams[0],
            "team_b_id": winner_teams[1],
            "status": "scheduled",
            "best_of": 3,
        }
    ]
    with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=eo_uid) as conn:
        replaced = conn.execute(
            "SELECT * FROM public.replace_tournament_matches(%s::uuid, %s::jsonb)",
            (tournament_id, json.dumps(matches_payload)),
        ).fetchall()
        assert len(replaced) == 1

    # Unassigned committee cannot transition status.
    with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=unassigned_comm_uid) as conn:
        with pytest.raises(pg_errors.InsufficientPrivilege):
            conn.execute(
                "SELECT * FROM public.transition_tournament_status(%s::uuid, 'ongoing')",
                (tournament_id,),
            )

    # Assigned committee can transition open_registration -> ongoing, NOT cancelled.
    with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=comm_uid) as conn:
        with pytest.raises(pg_errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute(
                    "SELECT * FROM public.transition_tournament_status(%s::uuid, 'cancelled')",
                    (tournament_id,),
                )
        ongoing = conn.execute(
            "SELECT * FROM public.transition_tournament_status(%s::uuid, 'ongoing')",
            (tournament_id,),
        ).fetchone()
        assert ongoing is not None and ongoing["status"] == "ongoing"

    # 4. Concurrent submit_match_result_atomic on Grand Final with same idempotency_key.
    shared_key = f"gf-idem-{uuid.uuid4().hex[:8]}"

    def attempt_submit(_idx: int) -> dict[str, Any]:
        try:
            with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=comm_uid) as conn:
                row = conn.execute(
                    """
                    SELECT public.submit_match_result_atomic(
                        %s::uuid, %s, %s, %s, %s, %s, %s
                    ) AS res
                    """,
                    (gf_id, 2, 1, False, "Grand Final result", 1, shared_key),
                ).fetchone()
            return {"status": "ok", "res": row["res"]}
        except pg_errors.Error as exc:
            return {"status": "err", "sqlstate": exc.sqlstate, "msg": str(exc)}

    with ThreadPoolExecutor(max_workers=3) as pool:
        submit_results = list(pool.map(attempt_submit, range(3)))

    assert all(r["status"] == "ok" for r in submit_results), f"Unexpected error: {submit_results}"
    assert any(r["res"].get("idempotent_replay") is False for r in submit_results)
    assert any(r["res"].get("idempotent_replay") is True for r in submit_results)

    # Using the SAME idempotency_key with a DIFFERENT payload must fail cleanly.
    with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=comm_uid) as conn:
        with pytest.raises(pg_errors.ProgrammingError) as exc_info:
            with conn.transaction():
                conn.execute(
                    "SELECT public.submit_match_result_atomic(%s::uuid, 1, 2, false, 'Tampered', 1, %s)",
                    (gf_id, shared_key),
                )
        assert exc_info.value.sqlstate == "P0009"

        # Idempotent Grand Final force_override keeps tournament completed and does not duplicate match_results.
        override_key = f"gf-override-{uuid.uuid4().hex[:8]}"
        overridden = conn.execute(
            "SELECT public.submit_match_result_atomic(%s::uuid, 2, 0, true, 'Verified score correction', 1, %s) AS res",
            (gf_id, override_key),
        ).fetchone()
        assert overridden is not None
        assert overridden["res"]["tournament_status"] == "completed"
        assert overridden["res"]["match"]["score_a"] == 2
        assert overridden["res"]["match"]["score_b"] == 0

    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=dbname, row_factory=dict_row
    ) as conn:
        mr_count = conn.execute(
            "SELECT COUNT(*) AS c FROM public.match_results WHERE match_id = %s", (gf_id,)
        ).fetchone()
        assert mr_count is not None and mr_count["c"] == 1


def test_linked_seeded_profile_id_distinct_from_auth_uid_works_across_rls_and_rpcs(
    pg_cluster: EphemeralPgCluster, seeded_db: str
) -> None:
    """Verify seeded profiles linked via trusted RPC (id != auth_user_id) operate normally under RLS and RPCs."""
    # In seeded_db, captain@turnamen.in has profile.id = ...1104 and auth_user_id = NULL.
    seeded_captain_profile_id = "11111111-1111-4111-8111-111111111104"
    seeded_team_grd_id = "44444444-4444-4444-8444-444444444401"
    seeded_player_profile_id = "11111111-1111-4111-8111-111111111105"
    seeded_val_tournament_id = "33333333-3333-4333-8333-333333333302"

    captain_auth_uid = str(uuid.uuid4())
    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
    ) as conn:
        with conn.transaction():
            conn.execute("ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created")
            conn.execute(
                "INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, 'captain@turnamen.in', NOW())",
                (captain_auth_uid,),
            )
            conn.execute("ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created")
            linked = conn.execute(
                "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                (seeded_captain_profile_id, captain_auth_uid),
            ).fetchone()
            assert linked is not None
            assert str(linked["id"]) == seeded_captain_profile_id
            assert str(linked["auth_user_id"]) == captain_auth_uid
            assert str(linked["id"]) != str(linked["auth_user_id"])

    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=captain_auth_uid) as conn:
        # Captain can read own profile and look up member summary even though id != auth_user_id.
        own = conn.execute("SELECT id, role FROM public.profiles").fetchall()
        assert len(own) == 1
        assert str(own[0]["id"]) == seeded_captain_profile_id
        summary = conn.execute(
            "SELECT * FROM public.get_public_profile_summary(%s::uuid, %s::uuid)",
            (seeded_player_profile_id, seeded_team_grd_id),
        ).fetchone()
        assert summary is not None and summary["username"] == "aruna_player"

        # Captain can register VALORANT-compatible team or update own team under RLS.
        updated_team = conn.execute(
            "UPDATE public.teams SET region = 'DKI Jakarta' WHERE id = %s RETURNING region",
            (seeded_team_grd_id,),
        ).fetchone()
        assert updated_team == {"region": "DKI Jakarta"}
        # Ensure VALORANT open registration tournament is visible.
        val_t = conn.execute(
            "SELECT id, status FROM public.tournaments WHERE id = %s",
            (seeded_val_tournament_id,),
        ).fetchone()
        assert val_t is not None and val_t["status"] == "open_registration"


def test_wave5_0006_announcement_author_projection_and_staff_rpcs(
    pg_cluster: EphemeralPgCluster, seeded_db: str
) -> None:
    """Verify 0006 announcement author projection & staff RPCs across anon, player, organizer, committee."""
    org_id = "11111111-1111-4111-8111-111111111102"
    comm_id = "11111111-1111-4111-8111-111111111103"
    player_id = "11111111-1111-4111-8111-111111111105"
    tour_id = "33333333-3333-4333-8333-333333333301"
    inactive_author_id = str(uuid.uuid4())
    draft_tour_id = str(uuid.uuid4())

    uids: dict[str, str] = {}
    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
    ) as conn:
        with conn.transaction():
            conn.execute("ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created")
            for email, pid in (
                ("organizer@turnamen.in", org_id),
                ("committee@turnamen.in", comm_id),
                ("player@turnamen.in", player_id),
            ):
                existing = conn.execute(
                    "SELECT id FROM auth.users WHERE email = %s LIMIT 1",
                    (email,),
                ).fetchone()
                if existing:
                    uid = str(existing["id"])
                else:
                    uid = str(uuid.uuid4())
                    conn.execute(
                        "INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, %s, NOW())",
                        (uid, email),
                    )
                uids[email] = uid
                conn.execute(
                    "SELECT * FROM public.link_profile_auth_user(%s::uuid, %s::uuid)",
                    (pid, uid),
                )
            conn.execute("ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created")
            org_uid = uids["organizer@turnamen.in"]
            comm_uid = uids["committee@turnamen.in"]
            player_uid = uids["player@turnamen.in"]

            # Deactivated author profile should fall back to 'Panitia' without exposing PII.
            conn.execute(
                """
                INSERT INTO public.profiles (id, email, username, full_name, role, is_active)
                VALUES (%s, 'ex@turnamen.in', 'ex_mod', 'Ex Panitia', 'committee', FALSE)
                """,
                (inactive_author_id,),
            )
            conn.execute(
                """
                INSERT INTO public.announcements (tournament_id, author_id, title, content, priority, is_pinned)
                VALUES (%s, %s, 'Pengumuman Arsip', 'Author sudah tidak aktif lagi.', 'normal', FALSE)
                """,
                (tour_id, inactive_author_id),
            )
            conn.execute(
                """
                INSERT INTO public.tournaments (id, slug, title, game_id, organizer_id, status, start_date)
                VALUES (%s, 'draft-ann-test', 'Draft Internal', '22222222-2222-4222-8222-222222222201', %s, 'draft', NOW() + INTERVAL '5 days')
                """,
                (draft_tour_id, org_id),
            )
            conn.execute(
                """
                INSERT INTO public.announcements (tournament_id, author_id, title, content, priority)
                VALUES (%s, %s, 'Rahasia Draft', 'Hanya untuk manajer turnamen draft.', 'normal')
                """,
                (draft_tour_id, org_id),
            )

    # Guest (anon) & player & organizer & committee can read public announcements with author_name and NO email/phone.
    for role_kw in (
        {"role": "anon", "auth_user_id": None},
        {"role": "authenticated", "auth_user_id": player_uid},
        {"role": "authenticated", "auth_user_id": org_uid},
        {"role": "authenticated", "auth_user_id": comm_uid},
    ):
        with as_client_session(pg_cluster.port, seeded_db, **role_kw) as conn:
            rows = conn.execute(
                "SELECT * FROM public.list_tournament_announcements(%s::uuid)",
                (tour_id,),
            ).fetchall()
            assert len(rows) >= 3
            assert all("email" not in r and "phone" not in r for r in rows)
            author_names = {r["author_name"] for r in rows}
            assert "Nadia Kusuma (Tournament Organizer)" in author_names
            assert "Bima Saputra (Head Committee)" in author_names
            assert "Panitia" in author_names

    # Direct profiles SELECT remains locked for player (only sees own profile).
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=player_uid) as conn:
        seen_profiles = conn.execute("SELECT id FROM public.profiles").fetchall()
        assert len(seen_profiles) == 1
        assert str(seen_profiles[0]["id"]) == player_id
        draft_rows = conn.execute(
            "SELECT * FROM public.list_tournament_announcements(%s::uuid)",
            (draft_tour_id,),
        ).fetchall()
        assert draft_rows == []
        with pytest.raises(pg_errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM public.list_committee_candidates()")

    # Guest cannot read draft announcements either.
    with as_client_session(pg_cluster.port, seeded_db, role="anon", auth_user_id=None) as conn:
        assert conn.execute(
            "SELECT * FROM public.list_tournament_announcements(%s::uuid)",
            (draft_tour_id,),
        ).fetchall() == []

    # Owning organizer sees draft announcements, committee candidates (without PII), and staff list.
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=org_uid) as conn:
        draft_org_rows = conn.execute(
            "SELECT * FROM public.list_tournament_announcements(%s::uuid)",
            (draft_tour_id,),
        ).fetchall()
        assert len(draft_org_rows) == 1
        cands = conn.execute("SELECT * FROM public.list_committee_candidates()").fetchall()
        assert len(cands) >= 1 and all("email" not in c and "phone" not in c for c in cands)
        staff_rows = conn.execute("SELECT * FROM public.list_tournament_staff(%s::uuid)", (tour_id,)).fetchall()
        assert len(staff_rows) >= 1 and staff_rows[0]["username"] == "panitia_utama"


def test_wave6_11_game_artwork_overrides_migration_and_rls(
    pg_cluster: EphemeralPgCluster, seeded_db: str
) -> None:
    admin_id = "11111111-1111-4111-8111-111111111101"
    player_id = "11111111-1111-4111-8111-111111111105"
    mlbb_id = "22222222-2222-4222-8222-222222222201"
    valid_path = f"mobile-legends/{uuid.uuid4()}.webp"
    updated_path = f"mobile-legends/{uuid.uuid4()}.png"

    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=seeded_db, row_factory=dict_row
    ) as conn:
        with conn.transaction():
            conn.execute("ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created")
            uids: dict[str, str] = {}
            for email, pid in (
                ("admin@turnamen.in", admin_id),
                ("player@turnamen.in", player_id),
            ):
                prof = conn.execute(
                    "SELECT auth_user_id FROM public.profiles WHERE id = %s LIMIT 1",
                    (pid,),
                ).fetchone()
                if prof and prof["auth_user_id"]:
                    uids[pid] = str(prof["auth_user_id"])
                    continue
                existing = conn.execute(
                    "SELECT id FROM auth.users WHERE email = %s LIMIT 1",
                    (email,),
                ).fetchone()
                uid = str(existing["id"]) if existing else str(uuid.uuid4())
                if not existing:
                    conn.execute(
                        "INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, %s, NOW())",
                        (uid, email),
                    )
                conn.execute(
                    "UPDATE public.profiles SET auth_user_id = %s, is_active = TRUE WHERE id = %s",
                    (uid, pid),
                )
                uids[pid] = uid
            conn.execute("ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created")
            admin_uid = uids[admin_id]
            player_uid = uids[player_id]

    # Normal player and anon must fail INSERT into game_artwork_overrides
    with as_client_session(pg_cluster.port, seeded_db, role="anon", auth_user_id=None) as conn:
        with pytest.raises(pg_errors.InsufficientPrivilege):
            conn.execute(
                """
                INSERT INTO public.game_artwork_overrides (game_id, storage_path, mime_type, file_size_bytes, width, height, uploaded_by)
                VALUES (%s, %s, 'image/webp', 120000, 1280, 720, %s)
                """,
                (mlbb_id, valid_path, admin_id),
            )

    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=player_uid) as conn:
        with pytest.raises(pg_errors.InsufficientPrivilege):
            conn.execute(
                """
                INSERT INTO public.game_artwork_overrides (game_id, storage_path, mime_type, file_size_bytes, width, height, uploaded_by)
                VALUES (%s, %s, 'image/webp', 120000, 1280, 720, %s)
                """,
                (mlbb_id, valid_path, player_id),
            )

    # Super Admin succeeds with valid constraints and rejects bad paths/sizes
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=admin_uid) as conn:
        with pytest.raises(pg_errors.CheckViolation):
            conn.execute(
                """
                INSERT INTO public.game_artwork_overrides (game_id, storage_path, mime_type, file_size_bytes, width, height, uploaded_by)
                VALUES (%s, '../evil.svg', 'image/webp', 120000, 1280, 720, %s)
                """,
                (mlbb_id, admin_id),
            )

    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=admin_uid) as conn:
        inserted = conn.execute(
            """
            INSERT INTO public.game_artwork_overrides (game_id, storage_path, mime_type, file_size_bytes, width, height, uploaded_by)
            VALUES (%s, %s, 'image/webp', 120000, 1280, 720, %s)
            RETURNING game_id, storage_path, uploaded_by
            """,
            (mlbb_id, valid_path, admin_id),
        ).fetchone()
        assert inserted is not None and inserted["storage_path"] == valid_path

    # Public anon can read active game override metadata, cannot update or delete
    with as_client_session(pg_cluster.port, seeded_db, role="anon", auth_user_id=None) as conn:
        seen = conn.execute(
            "SELECT storage_path FROM public.game_artwork_overrides WHERE game_id = %s",
            (mlbb_id,),
        ).fetchall()
        assert len(seen) == 1 and seen[0]["storage_path"] == valid_path
        with pytest.raises(pg_errors.InsufficientPrivilege):
            conn.execute("DELETE FROM public.game_artwork_overrides WHERE game_id = %s", (mlbb_id,))

    # Player cannot update or delete existing override
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=player_uid) as conn:
        updated_by_player = conn.execute(
            "UPDATE public.game_artwork_overrides SET storage_path = %s WHERE game_id = %s RETURNING id",
            (updated_path, mlbb_id),
        ).fetchall()
        assert updated_by_player == []
        deleted_by_player = conn.execute(
            "DELETE FROM public.game_artwork_overrides WHERE game_id = %s RETURNING id",
            (mlbb_id,),
        ).fetchall()
        assert deleted_by_player == []

    # Super Admin updates and restores (deletes) cleanly
    with as_client_session(pg_cluster.port, seeded_db, role="authenticated", auth_user_id=admin_uid) as conn:
        upd = conn.execute(
            "UPDATE public.game_artwork_overrides SET storage_path = %s, mime_type = 'image/png' WHERE game_id = %s RETURNING storage_path",
            (updated_path, mlbb_id),
        ).fetchone()
        assert upd is not None and upd["storage_path"] == updated_path
        removed = conn.execute(
            "DELETE FROM public.game_artwork_overrides WHERE game_id = %s RETURNING storage_path",
            (mlbb_id,),
        ).fetchone()
        assert removed is not None and removed["storage_path"] == updated_path


def test_wave6_11_split_storage_deployment_ownership_and_dashboard_policies(
    pg_cluster: EphemeralPgCluster,
) -> None:
    """Simulate Cloud storage.objects ownership split, fail-closed upload window, and least-privilege Dashboard policies."""
    w611_sql = (MIGRATIONS_DIR / "20261126232622_wave6_11_custom_game_artwork.sql").read_text(encoding="utf-8")
    assert "public.game_artwork_overrides" in w611_sql
    assert "INSERT INTO storage.buckets" in w611_sql
    assert "ON storage.objects" not in w611_sql
    assert "ALTER TABLE storage.objects" not in w611_sql
    assert "OWNER TO" not in w611_sql
    assert "GRANT supabase_storage_admin" not in w611_sql

    dbname = "wave611_split_storage_db"
    admin_id = "11111111-1111-4111-8111-111111111101"
    player_id = "11111111-1111-4111-8111-111111111105"
    admin_uid = str(uuid.uuid4())
    player_uid = str(uuid.uuid4())

    with psycopg.connect(
        host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname="postgres", autocommit=True
    ) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        conn.execute(f'CREATE DATABASE "{dbname}"')
        conn.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'supabase_storage_admin') THEN
                    CREATE ROLE supabase_storage_admin NOLOGIN;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cloud_deploy_postgres') THEN
                    CREATE ROLE cloud_deploy_postgres LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
                END IF;
            END;
            $$;
            """
        )

    try:
        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=dbname, autocommit=True
        ) as conn:
            conn.execute(AUTH_SHIM_SQL)

        for migration in MIGRATION_FILES[:-1]:
            _run_psql_file(pg_cluster.port, dbname, migration)
        _run_psql_file(pg_cluster.port, dbname, SEED_FILE)

        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=dbname, autocommit=False
        ) as conn:
            with conn.transaction():
                conn.execute("ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created")
                for email, pid, uid in (
                    ("admin@turnamen.in", admin_id, admin_uid),
                    ("player@turnamen.in", player_id, player_uid),
                ):
                    conn.execute(
                        "INSERT INTO auth.users (id, email, email_confirmed_at) VALUES (%s, %s, NOW())",
                        (uid, email),
                    )
                    conn.execute(
                        "UPDATE public.profiles SET auth_user_id = %s, is_active = TRUE WHERE id = %s",
                        (uid, pid),
                    )
                conn.execute("ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created")

                # Mirror Supabase Cloud storage ownership (owned by supabase_storage_admin, NOT cloud_deploy_postgres)
                conn.execute("CREATE SCHEMA IF NOT EXISTS storage AUTHORIZATION supabase_storage_admin")
                conn.execute("SET LOCAL ROLE supabase_storage_admin")
                conn.execute(
                    """
                    CREATE TABLE storage.buckets (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        public BOOLEAN DEFAULT FALSE,
                        file_size_limit BIGINT,
                        allowed_mime_types TEXT[]
                    );
                    CREATE TABLE storage.objects (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        bucket_id TEXT NOT NULL,
                        name TEXT NOT NULL
                    );
                    ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;
                    """
                )
                conn.execute("RESET ROLE")

                conn.execute(
                    """
                    GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role, cloud_deploy_postgres;
                    GRANT CREATE ON SCHEMA public TO cloud_deploy_postgres;
                    GRANT REFERENCES, SELECT ON public.games, public.profiles TO cloud_deploy_postgres;
                    GRANT EXECUTE ON FUNCTION public.set_updated_at() TO cloud_deploy_postgres;
                    GRANT EXECUTE ON FUNCTION public.current_user_role() TO cloud_deploy_postgres;
                    GRANT EXECUTE ON FUNCTION public.current_profile_id() TO cloud_deploy_postgres;

                    GRANT USAGE ON SCHEMA storage TO anon, authenticated, service_role, cloud_deploy_postgres;
                    GRANT SELECT, INSERT, UPDATE ON storage.buckets TO cloud_deploy_postgres;
                    GRANT SELECT ON storage.objects TO cloud_deploy_postgres;
                    GRANT SELECT, INSERT, UPDATE, DELETE ON storage.objects TO anon, authenticated;
                    """
                )

        # Verify non-owner deployment role cannot create policies on storage.objects directly
        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="cloud_deploy_postgres", dbname=dbname, autocommit=False
        ) as conn:
            with pytest.raises(pg_errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(
                        "CREATE POLICY \"Illegal policy\" ON storage.objects FOR SELECT TO authenticated USING (true)"
                    )

        # Execute revised Wave 6.11 migration strictly as non-superuser cloud_deploy_postgres
        psql_bin = _find_pg_bin("psql")
        proc = subprocess.run(
            [
                psql_bin,
                "-h",
                "127.0.0.1",
                "-p",
                str(pg_cluster.port),
                "-U",
                "cloud_deploy_postgres",
                "-d",
                dbname,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(MIGRATION_FILES[-1]),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert proc.returncode == 0, f"Wave 6.11 migration failed as cloud_deploy_postgres:\n{proc.stderr}"

        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=dbname, row_factory=dict_row
        ) as conn:
            bucket = conn.execute(
                "SELECT id, name, public, file_size_limit, allowed_mime_types FROM storage.buckets WHERE id = 'game-artwork'"
            ).fetchone()
            assert bucket == {
                "id": "game-artwork",
                "name": "game-artwork",
                "public": True,
                "file_size_limit": 5242880,
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
            }
            storage_policies = conn.execute(
                "SELECT policyname FROM pg_policies WHERE schemaname = 'storage' AND tablename = 'objects'"
            ).fetchall()
            assert storage_policies == []

        # Fail-closed check BEFORE Dashboard Storage policies exist: even super_admin cannot upload yet
        with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=admin_uid) as conn:
            with pytest.raises(pg_errors.InsufficientPrivilege):
                conn.execute(
                    "INSERT INTO storage.objects (bucket_id, name) VALUES ('game-artwork', 'mobile-legends/pre.png')"
                )

        # Apply the 4 least-privilege Dashboard Storage policies as supabase_storage_admin (SELECT -> DELETE -> UPDATE -> INSERT)
        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname=dbname, autocommit=False
        ) as conn:
            with conn.transaction():
                conn.execute("SET LOCAL ROLE supabase_storage_admin")
                conn.execute(
                    """
                    CREATE POLICY "Super admin select game-artwork objects" ON storage.objects
                        FOR SELECT
                        TO authenticated
                        USING (
                            bucket_id = 'game-artwork'
                            AND (SELECT public.current_user_role()) = 'super_admin'
                        );

                    CREATE POLICY "Super admin delete game-artwork objects" ON storage.objects
                        FOR DELETE
                        TO authenticated
                        USING (
                            bucket_id = 'game-artwork'
                            AND (SELECT public.current_user_role()) = 'super_admin'
                        );

                    CREATE POLICY "Super admin update game-artwork objects" ON storage.objects
                        FOR UPDATE
                        TO authenticated
                        USING (
                            bucket_id = 'game-artwork'
                            AND (SELECT public.current_user_role()) = 'super_admin'
                        )
                        WITH CHECK (
                            bucket_id = 'game-artwork'
                            AND (SELECT public.current_user_role()) = 'super_admin'
                        );

                    CREATE POLICY "Super admin insert game-artwork objects" ON storage.objects
                        FOR INSERT
                        TO authenticated
                        WITH CHECK (
                            bucket_id = 'game-artwork'
                            AND (SELECT public.current_user_role()) = 'super_admin'
                        );
                    """
                )

        # Anon cannot list metadata or insert into storage.objects
        with as_client_session(pg_cluster.port, dbname, role="anon", auth_user_id=None) as conn:
            assert conn.execute("SELECT name FROM storage.objects WHERE bucket_id = 'game-artwork'").fetchall() == []
            with pytest.raises(pg_errors.InsufficientPrivilege):
                conn.execute(
                    "INSERT INTO storage.objects (bucket_id, name) VALUES ('game-artwork', 'mobile-legends/anon.png')"
                )

        # Normal authenticated player cannot list metadata or insert into storage.objects
        with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=player_uid) as conn:
            assert conn.execute("SELECT name FROM storage.objects WHERE bucket_id = 'game-artwork'").fetchall() == []
            with pytest.raises(pg_errors.InsufficientPrivilege):
                conn.execute(
                    "INSERT INTO storage.objects (bucket_id, name) VALUES ('game-artwork', 'mobile-legends/player.png')"
                )

        # Active super_admin can insert, select, update, delete inside game-artwork only
        obj_path = f"mobile-legends/{uuid.uuid4()}.webp"
        with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=admin_uid) as conn:
            ins = conn.execute(
                "INSERT INTO storage.objects (bucket_id, name) VALUES ('game-artwork', %s) RETURNING name",
                (obj_path,),
            ).fetchone()
            assert ins is not None and ins["name"] == obj_path
            listed = conn.execute(
                "SELECT name FROM storage.objects WHERE bucket_id = 'game-artwork'"
            ).fetchall()
            assert [r["name"] for r in listed] == [obj_path]
            upd = conn.execute(
                "UPDATE storage.objects SET name = %s WHERE bucket_id = 'game-artwork' AND name = %s RETURNING name",
                (f"mobile-legends/{uuid.uuid4()}.png", obj_path),
            ).fetchone()
            assert upd is not None
            removed = conn.execute(
                "DELETE FROM storage.objects WHERE bucket_id = 'game-artwork' RETURNING name"
            ).fetchall()
            assert len(removed) == 1
            with pytest.raises(pg_errors.InsufficientPrivilege):
                conn.execute(
                    "INSERT INTO storage.objects (bucket_id, name) VALUES ('other-bucket', 'mobile-legends/x.png')"
                )

        # Player cannot update or delete super_admin object either
        with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=admin_uid) as conn:
            conn.execute(
                "INSERT INTO storage.objects (bucket_id, name) VALUES ('game-artwork', %s)",
                (obj_path,),
            )
        with as_client_session(pg_cluster.port, dbname, role="authenticated", auth_user_id=player_uid) as conn:
            assert conn.execute("SELECT name FROM storage.objects").fetchall() == []
            assert conn.execute("UPDATE storage.objects SET name = 'x.png' RETURNING id").fetchall() == []
            assert conn.execute("DELETE FROM storage.objects RETURNING id").fetchall() == []
    finally:
        with psycopg.connect(
            host="127.0.0.1", port=pg_cluster.port, user="postgres", dbname="postgres", autocommit=True
        ) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
