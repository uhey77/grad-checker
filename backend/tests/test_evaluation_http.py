"""Go → Python → SQLiteで本人の保存済み成績を判定する。実DBは変更しない。"""

from sqlalchemy import text
from test_auth_http import PASSWORD, auth_services  # noqa: F401
from test_requirement_evaluation import grade, snapshot, uid  # noqa: F401

from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    import_requirements,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    import_subject_data,
)

ENDPOINT = "/api/me/graduation-requirements"


def test_saved_grades_evaluation_and_owner_isolation(auth_services, tmp_path, snapshot):  # noqa: F811
    client = auth_services
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        import_subject_data(engine, snapshot.subjects)
        import_requirements(engine, snapshot.requirements)
        assert client.get(ENDPOINT).status_code == 401
        credentials = {"login_name": "evaluate_01", "password": PASSWORD}
        assert client.post("/api/auth/register", json=credentials).status_code == 201
        auth = client.post("/api/auth/login", json=credentials).json()
        headers = {"X-CSRF-Token": auth["csrf_token"]}
        missing = client.get(ENDPOINT)
        assert missing.status_code == 409 and "所属" in missing.json()["detail"]
        assert client.post(ENDPOINT).status_code == 405
        assert client.get(ENDPOINT + "?student_id=other").status_code == 422
        assert (
            client.put(
                "/api/me/program",
                headers=headers,
                json={
                    "program_id": str(snapshot.program_id),
                    "curriculum_id": str(snapshot.curriculum_id),
                    "expected_revision": 0,
                },
            ).status_code
            == 200
        )
        initial = client.get(ENDPOINT)
        assert initial.status_code == 200, initial.text
        assert initial.headers["cache-control"] == "no-store"
        assert initial.json()["result"] == "fail"
        assert initial.json()["total"]["shortage"] == 10
        attempts = [grade(uid(i)).model_dump() for i in (10, 11, 13, 15)]
        assert (
            client.put(
                "/api/me/grades",
                headers=headers,
                json={
                    "expected_revision": 1,
                    "grades": attempts,
                },
            ).status_code
            == 200
        )
        before = client.get("/api/me/grades").json()
        result = client.get(ENDPOINT)
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["result"] == "pass"
        assert data["data_revision"] == 2
        assert data["curriculum"]["revision"] == 3
        assert data["total"]["credited_credits"] == 10
        assert data["missing_required_courses"] == []
        assert data["evaluated_at"]
        assert len(data["requirements"]) == 7
        assert client.get(ENDPOINT).json()["result"] == "pass"
        assert client.get("/api/me/grades").json() == before
        assert (
            client.put(
                "/api/me/grades",
                headers=headers,
                json={
                    "expected_revision": 2,
                    "grades": attempts[1:],
                },
            ).status_code
            == 200
        )
        assert client.get(ENDPOINT).json()["missing_required_courses"][0][
            "course_id"
        ] == str(uid(10))
        assert (
            client.post("/api/auth/logout", json={}, headers=headers).status_code == 200
        )
        other = {"login_name": "evaluate_02", "password": PASSWORD}
        client.post("/api/auth/register", json=other)
        second = client.post("/api/auth/login", json=other).json()
        second_headers = {"X-CSRF-Token": second["csrf_token"]}
        client.put(
            "/api/me/program",
            headers=second_headers,
            json={
                "program_id": str(snapshot.program_id),
                "curriculum_id": str(snapshot.curriculum_id),
                "expected_revision": 0,
            },
        )
        assert client.get(ENDPOINT).json()["total"]["earned_credits"] == 0
        assert_configuration_errors(client, engine)
    finally:
        engine.dispose()


def assert_configuration_errors(client, engine):
    # テストDBだけで未確認・設定不足・DB障害を作り、failと区別する。
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE curricula SET verification_status='unverified'")
        )
    unverified = client.get(ENDPOINT)
    assert unverified.status_code == 409
    assert "適用入学年度が未確認" in unverified.json()["detail"]
    assert "result" not in unverified.json()
    with engine.begin() as connection:
        connection.execute(text("UPDATE curricula SET verification_status='verified'"))
        connection.execute(text("DELETE FROM requirement_scopes"))
    assert client.get(ENDPOINT).status_code == 409
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE requirement_scopes"))
    failed = client.get(ENDPOINT)
    assert failed.status_code == 503
    assert "SELECT" not in failed.text
