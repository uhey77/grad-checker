"""判定履歴の保存・本人限定の取得・不変性・失敗時のロールバックを実SQLiteで確認する。"""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_auth import login, register
from test_requirement_evaluation import grade, snapshot, uid  # noqa: F401

from api.api_service.main import create_app
from config.settings import Settings
from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    import_requirements,
)
from modules.subjects.grad_checker_subjects.application.subject_data_import import (
    import_subject_data,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
)


@pytest.fixture
def checks_app(tmp_path, snapshot):  # noqa: F811
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'checks.db'}"))
    with TestClient(app) as client:
        engine = app.state.database_engine
        import_subject_data(SqliteSubjectDataUnitOfWork(engine), snapshot.subjects)
        import_requirements(engine, snapshot.requirements)
        register(client)
        identity = login(client)
        selected = bridge(
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
        assert selected["data"]["profile"]["data_revision"] == 1
        yield app, client, identity


def bridge(client, path, identity, operation, **fields):
    return client.post(
        path,
        json={"operation": operation, "token": identity["session_token"], **fields},
    ).json()


def create(client, identity, revision, csrf=None):
    return bridge(
        client,
        "/bridge/checks",
        identity,
        "create",
        csrf=identity["csrf_token"] if csrf is None else csrf,
        request={"expected_revision": revision},
    )


def get(client, identity, check_id):
    return bridge(client, "/bridge/checks", identity, "get", check_id=str(check_id))


def save_grades(client, identity, grades, revision):
    result = bridge(
        client,
        "/bridge/grades",
        identity,
        "save",
        csrf=identity["csrf_token"],
        grade_set={
            "expected_revision": revision,
            "grades": [row.model_dump() for row in grades],
        },
    )
    return result["data"]["data_revision"]


def check_count(app):
    with app.state.database_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM check_results")).scalar()


def test_check_is_saved_with_snapshot_and_read_only_by_owner(checks_app):
    app, client, identity = checks_app
    revision = save_grades(client, identity, [grade(uid(i)) for i in (10, 11)], 1)
    created = create(client, identity, revision)["data"]
    assert created["input"]["data_revision"] == revision
    assert created["result"]["data_revision"] == revision
    assert created["created_at"] == created["result"]["evaluated_at"]
    assert [row["course_id"] for row in created["input"]["grades"]] == [
        str(uid(10)),
        str(uid(11)),
    ]
    assert created["result"]["result"] == "fail"
    assert get(client, identity, created["id"])["data"] == created
    with app.state.database_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT curriculum_code, curriculum_revision, data_revision "
                "FROM check_results"
            )
        ).one()
    assert tuple(row) == ("test", 3, revision)
    assert get(client, identity, uuid4())["error"]["code"] == "check_not_found"
    register(client, "other_student")
    other = login(client, "other_student")
    assert get(client, other, created["id"])["error"]["code"] == "check_not_found"


def test_past_check_is_unchanged_after_grade_and_master_updates(checks_app):
    app, client, identity = checks_app
    revision = save_grades(client, identity, [grade(uid(i)) for i in (10, 11)], 1)
    created = create(client, identity, revision)["data"]
    save_grades(client, identity, [grade(uid(i)) for i in (10, 11, 13, 15)], revision)
    engine = app.state.database_engine
    with engine.begin() as connection:
        connection.execute(text("UPDATE courses SET name = '改名後'"))
        connection.execute(text("UPDATE curricula SET revision = 9"))
    assert get(client, identity, created["id"])["data"] == created
    # 現在のマスタが判定できない状態でも、保存済みの過去結果は読める。
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE requirement_scopes"))
    assert get(client, identity, created["id"])["data"] == created
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE check_results SET result_json = '{}'"))
    assert get(client, identity, created["id"])["data"] == created


@pytest.mark.parametrize(
    ("revision", "csrf", "code"),
    [(0, None, "revision_conflict"), (1, "x" * 64, "invalid_csrf")],
)
def test_rejected_checks_leave_no_history(checks_app, revision, csrf, code):
    app, client, identity = checks_app
    assert create(client, identity, revision, csrf)["error"]["code"] == code
    assert check_count(app) == 0


def test_configuration_and_database_failures_leave_no_history(checks_app):
    app, client, identity = checks_app
    engine = app.state.database_engine
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER reject_check BEFORE INSERT ON check_results "
                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
        )
    assert create(client, identity, 1)["error"]["code"] == "check_unavailable"
    with engine.begin() as connection:
        connection.execute(text("DROP TRIGGER reject_check"))
        connection.execute(text("DELETE FROM requirement_scopes"))
    assert create(client, identity, 1)["error"]["code"] == "invalid_evaluation_master"
    assert check_count(app) == 0


def test_concurrent_grade_save_and_check_do_not_mix_revisions(checks_app):
    app, client, identity = checks_app

    def run(task):
        if task == "check":
            return create(client, identity, 1)
        return bridge(
            client,
            "/bridge/grades",
            identity,
            "save",
            csrf=identity["csrf_token"],
            grade_set={"expected_revision": 1, "grades": [grade(uid(10)).model_dump()]},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        check, saved = pool.map(run, ["check", "grades"])
    if "data" in check:
        # 判定が先なら成績保存前の版、成績保存が先なら版の競合になる。
        assert check["data"]["input"] == {
            "program_id": str(uid(1)),
            "curriculum_id": str(uid(2)),
            "data_revision": 1,
            "grades": [],
        }
        assert check_count(app) == 1
    else:
        assert check["error"]["code"] == "revision_conflict"
        assert check_count(app) == 0
    assert saved["data"]["data_revision"] == 2


def test_invalid_bridge_calls_are_rejected(checks_app):
    _, client, identity = checks_app
    for fields in (
        {"operation": "create", "request": {"expected_revision": 1}},
        {"operation": "get", "check_id": str(uuid4()), "csrf": "x" * 64},
        {"operation": "get"},
        {
            "operation": "create",
            "csrf": "x" * 64,
            "request": {"expected_revision": 1},
            "check_id": str(uuid4()),
        },
        {"operation": "create", "csrf": "x" * 64, "request": {"expected_revision": -1}},
    ):
        response = client.post(
            "/bridge/checks", json={"token": identity["session_token"], **fields}
        ).json()
        assert response == {"error": {"code": "invalid_request"}}, fields
