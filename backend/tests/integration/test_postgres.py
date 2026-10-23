"""既存の認証・成績・判定仕様を同じケースでPostgreSQLにも適用する。"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlmodel import SQLModel

from apps.bridge.main import create_app
from apps.settings import Settings
from migrations.postgres import TABLES, comparable, migrate, read_rows
from modules.requirements.infrastructure.persistence.unit_of_work import (
    SqliteRequirementUnitOfWork,
)
from modules.requirements.public import ImportRequirementsUseCase
from modules.subjects.infrastructure.persistence.repositories.subject_data import (
    load_seed,
)
from modules.subjects.infrastructure.persistence.unit_of_work import (
    SqliteSubjectDataUnitOfWork,
)
from modules.subjects.public import ImportSubjectDataUseCase
from shared.infrastructure.persistence.unit_of_work import SqlUnitOfWork
from tests.integration import test_auth as auth_cases
from tests.integration import test_check_results as check_cases
from tests.integration import test_grades as grade_cases
from tests.integration import test_profile as profile_cases
from tests.integration import test_unit_of_work as uow_cases
from tests.unit.test_requirement_evaluation import snapshot  # noqa: F401

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture
def auth(postgres_engine):
    app = create_app(
        Settings(database_url=postgres_engine.url.render_as_string(hide_password=False))
    )
    with TestClient(app) as client:
        yield app, client


@pytest.mark.parametrize(
    "case",
    [
        auth_cases.test_registration_login_session_logout,
        auth_cases.test_duplicate_registration_does_not_overwrite_credentials,
        auth_cases.test_recovery_rotates_code_revokes_all_sessions_and_preserves_account,
        auth_cases.test_expired_and_disabled_sessions,
        auth_cases.test_concurrent_registration_creates_one_account,
        auth_cases.test_recovery_is_single_use_and_stale_password_cannot_create_session,
    ],
    ids=lambda case: case.__name__,
)
def test_postgres_auth(auth, case):
    case(auth)


@pytest.fixture
def grades_app(auth):
    app, client = auth
    ImportSubjectDataUseCase(
        SqliteSubjectDataUnitOfWork(app.state.database_engine)
    ).execute(load_seed(BACKEND / "seeds/cs_2026.json"))
    auth_cases.register(client)
    return app, client, auth_cases.login(client)


@pytest.mark.parametrize(
    "case",
    [
        grade_cases.test_full_set_replacement_and_owner_isolation,
        grade_cases.test_invalid_grade_sets_leave_grades_unchanged,
        grade_cases.test_courses_outside_own_curriculum_can_be_saved,
        grade_cases.test_unchanged_attempts_keep_updated_at,
        grade_cases.test_concurrent_grade_saves_have_only_one_winner,
        grade_cases.test_database_rejects_inconsistent_grade_rows,
        profile_cases.test_profile_persistence_and_owner_isolation,
        profile_cases.test_failed_save_does_not_change_profile,
        profile_cases.test_concurrent_revision_updates_have_only_one_winner,
    ],
    ids=lambda case: case.__name__,
)
def test_postgres_grades_and_profile(grades_app, case):
    case(grades_app)


@pytest.fixture
def checks_app(auth, snapshot):  # noqa: F811
    app, client = auth
    engine = app.state.database_engine
    ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
        snapshot.subjects
    )
    ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
        snapshot.requirements
    )
    auth_cases.register(client)
    identity = auth_cases.login(client)
    assert (
        check_cases.bridge(
            client,
            "/bridge/profile",
            identity,
            "save_program",
            csrf=identity["csrf_token"],
            selection={
                "program_id": str(snapshot.program_id),
                "curriculum_id": str(snapshot.curriculum_id),
                "expected_revision": 0,
            },
        )["data"]["profile"]["data_revision"]
        == 1
    )
    return app, client, identity


@pytest.mark.parametrize(
    "case",
    [
        check_cases.test_check_is_saved_with_snapshot_and_read_only_by_owner,
        check_cases.test_pre_recommendation_history_remains_readable_without_recalculation,
        check_cases.test_owner_lists_checks_newest_first_with_paging,
        check_cases.test_list_keeps_saved_summary_and_rejects_broken_records,
        check_cases.test_concurrent_grade_save_and_check_do_not_mix_revisions,
    ],
    ids=lambda case: case.__name__,
)
def test_postgres_checks(checks_app, case):
    case(checks_app)


def test_postgres_history_is_immutable(checks_app):
    app, client, identity = checks_app
    saved = check_cases.create(client, identity, 1)["data"]
    with pytest.raises(DBAPIError), app.state.database_engine.begin() as connection:
        connection.execute(text("UPDATE check_results SET result_json = '{}'"))
    assert check_cases.get(client, identity, saved["id"])["data"] == saved


@pytest.mark.parametrize(
    "case",
    [
        uow_cases.test_write_commits_all_changes_on_success,
        uow_cases.test_write_rolls_back_all_changes_on_business_error,
        uow_cases.test_write_translates_database_errors_and_rolls_back,
        uow_cases.test_read_never_keeps_changes,
    ],
    ids=lambda case: case.__name__,
)
def test_postgres_unit_of_work(postgres_engine, case):
    with postgres_engine.begin() as connection:
        connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY)"))
    case(postgres_engine)


def test_postgres_read_has_one_snapshot(postgres_engine):
    with postgres_engine.begin() as connection:
        connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY)"))
    uow = SqlUnitOfWork(postgres_engine, lambda _: uow_cases.UnavailableError())
    with uow.read():
        assert (
            uow.session.connection()
            .execute(text("SELECT count(*) FROM items"))
            .scalar()
            == 0
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(_insert_item, postgres_engine).result(timeout=10)
        assert (
            uow.session.connection()
            .execute(text("SELECT count(*) FROM items"))
            .scalar()
            == 0
        )
    with uow.read():
        assert (
            uow.session.connection()
            .execute(text("SELECT count(*) FROM items"))
            .scalar()
            == 1
        )


def _insert_item(engine):
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO items VALUES (1)"))


def test_datetime_binds_are_utc(postgres_engine):

    instant = datetime(2026, 10, 23, 12, tzinfo=timezone(timedelta(hours=9)))
    with postgres_engine.begin() as connection:
        connection.execute(
            SQLModel.metadata.tables["students"]
            .insert()
            .values(
                id="tz-test", login_name="tz_test", data_revision=0, created_at=instant
            )
        )
        row = connection.execute(
            text("SELECT created_at FROM students WHERE id = 'tz-test'")
        ).scalar_one()
    assert row == instant.astimezone(UTC).replace(tzinfo=None)


def test_migration_preserves_all_data_and_refuses_reexecution(
    postgres_empty_engine,
    tmp_path,
    snapshot,  # noqa: F811
):
    source = tmp_path / "source.db"
    app = create_app(Settings(database_url=f"sqlite:///{source}"))
    with TestClient(app) as client:
        engine = app.state.database_engine
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
            snapshot.subjects
        )
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
            snapshot.requirements
        )
        auth_cases.register(client)
        identity = auth_cases.login(client)
        check_cases.bridge(
            client,
            "/bridge/profile",
            identity,
            "save_program",
            csrf=identity["csrf_token"],
            selection={
                "program_id": str(snapshot.program_id),
                "curriculum_id": str(snapshot.curriculum_id),
                "expected_revision": 0,
            },
        )
        check_cases.save_grades(
            client, identity, [check_cases.grade(check_cases.uid(10))], 1
        )
        saved = check_cases.create(client, identity, 2)["data"]
        before = source.read_bytes()
        counts = migrate(source, postgres_empty_engine)
        assert not inspect(postgres_empty_engine).get_table_names()
        assert counts["check_results"] == 1
        assert migrate(source, postgres_empty_engine, apply=True) == counts
        assert source.read_bytes() == before
        with engine.connect() as original, postgres_empty_engine.connect() as copied:
            for table in TABLES:
                assert comparable(read_rows(original, table)) == comparable(
                    read_rows(copied, table)
                )
        with pytest.raises(RuntimeError, match="既存テーブル"):
            migrate(source, postgres_empty_engine, apply=True)
    target_app = create_app(
        Settings(
            database_url=postgres_empty_engine.url.render_as_string(hide_password=False)
        )
    )
    with TestClient(target_app) as target_client:
        # 移行前のセッション・CSRFと保存済みスナップショットをそのまま利用できる。
        assert check_cases.get(target_client, identity, saved["id"])["data"] == saved
        assert auth_cases.login(target_client)["student"] == identity["student"]


def test_migration_rolls_back_schema_and_rows_on_bad_source(
    postgres_empty_engine, tmp_path
):
    source = tmp_path / "broken.db"
    app = create_app(Settings(database_url=f"sqlite:///{source}"))
    with TestClient(app):
        with app.state.database_engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA ignore_check_constraints=ON")
            connection.execute(
                text(
                    "INSERT INTO academic_programs (id, code, faculty_name) "
                    "VALUES ('bad', '', 'test')"
                )
            )
    with pytest.raises(DBAPIError):
        migrate(source, postgres_empty_engine, apply=True)
    assert inspect(postgres_empty_engine).get_table_names() == []


def test_connection_script_is_read_only_and_hides_credentials(postgres_engine):
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_database"],
        cwd=BACKEND,
        env={
            **os.environ,
            "DATABASE_URL": postgres_engine.url.render_as_string(hide_password=False),
        },
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "DB connection OK; schema OK (read only)"


def test_postgres_startup_does_not_create_missing_schema(postgres_empty_engine):
    app = create_app(
        Settings(
            database_url=postgres_empty_engine.url.render_as_string(hide_password=False)
        )
    )
    with pytest.raises(RuntimeError, match="未作成"), TestClient(app):
        pass
    assert inspect(postgres_empty_engine).get_table_names() == []


def test_postgres_startup_requires_history_trigger(postgres_engine):
    with postgres_engine.begin() as connection:
        connection.execute(
            text("DROP TRIGGER check_results_immutable ON check_results")
        )
    app = create_app(
        Settings(database_url=postgres_engine.url.render_as_string(hide_password=False))
    )
    with pytest.raises(RuntimeError, match="トリガー"), TestClient(app):
        pass


def test_connection_failure_does_not_print_url_or_password(postgres_engine):
    password = uuid4().hex
    url = postgres_engine.url.set(port=1, password=password)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_database"],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert password not in result.stdout + result.stderr
    assert "postgresql" not in result.stdout + result.stderr
