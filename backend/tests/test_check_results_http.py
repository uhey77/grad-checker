"""Go → Python → SQLiteで判定履歴を保存・再取得する。実DBは変更しない。"""

from uuid import uuid4

from sqlalchemy import text
from test_auth_http import PASSWORD, auth_services  # noqa: F401
from test_requirement_evaluation import grade, snapshot, uid  # noqa: F401

from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    import_requirements,
)
from modules.subjects.grad_checker_subjects.application.subject_data_import import (
    import_subject_data,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
)


def sign_in(client, login_name, snapshot):  # noqa: F811
    credentials = {"login_name": login_name, "password": PASSWORD}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    auth = client.post("/api/auth/login", json=credentials).json()
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    client.put(
        "/api/me/program",
        headers=headers,
        json={
            "program_id": str(snapshot.program_id),
            "curriculum_id": str(snapshot.curriculum_id),
            "expected_revision": 0,
        },
    ).raise_for_status()
    return headers


def test_check_snapshot_is_saved_and_read_only_by_owner(
    auth_services,  # noqa: F811
    tmp_path,
    snapshot,  # noqa: F811
):
    client = auth_services
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")

    def count():
        with engine.connect() as connection:
            return connection.execute(
                text("SELECT count(*) FROM check_results")
            ).scalar()

    try:
        import_subject_data(SqliteSubjectDataUnitOfWork(engine), snapshot.subjects)
        import_requirements(engine, snapshot.requirements)
        assert (
            client.post("/api/checks", json={"expected_revision": 0}).status_code == 401
        )
        headers = sign_in(client, "check_owner", snapshot)
        attempts = [grade(uid(i)).model_dump() for i in (10, 11, 13, 15)]
        saved = client.put(
            "/api/me/grades",
            headers=headers,
            json={"expected_revision": 1, "grades": attempts},
        )
        revision = saved.json()["data_revision"]
        # GETの判定では履歴を作らない。
        assert client.get("/api/me/graduation-requirements").status_code == 200
        assert count() == 0

        stale = client.post(
            "/api/checks", headers=headers, json={"expected_revision": 1}
        )
        assert stale.status_code == 409
        forged = client.post(
            "/api/checks",
            headers={"X-CSRF-Token": "x" * 64},
            json={"expected_revision": revision},
        )
        assert forged.status_code == 403
        foreign = client.post(
            "/api/checks",
            headers={**headers, "Origin": "https://evil.example"},
            json={"expected_revision": revision},
        )
        assert foreign.status_code == 403
        assert count() == 0

        created = client.post(
            "/api/checks", headers=headers, json={"expected_revision": revision}
        )
        assert created.status_code == 201, created.text
        assert created.headers["cache-control"] == "no-store"
        data = created.json()
        assert data["result"]["result"] == "pass"
        assert data["input"]["data_revision"] == data["result"]["data_revision"]
        assert len(data["input"]["grades"]) == 4
        assert count() == 1

        detail = client.get(f"/api/checks/{data['id']}")
        assert detail.status_code == 200
        assert detail.json() == data
        assert client.get(f"/api/checks/{data['id'].upper()}").json() == data
        assert client.get(f"/api/checks/{uuid4()}").status_code == 404

        # 成績・マスタを変えても過去の入力・結果・版は変わらない。
        client.put(
            "/api/me/grades",
            headers=headers,
            json={"expected_revision": revision, "grades": attempts[1:]},
        ).raise_for_status()
        with engine.begin() as connection:
            connection.execute(text("UPDATE courses SET name = '改名後'"))
        assert client.get("/api/me/graduation-requirements").json()["result"] == "fail"
        assert client.get(f"/api/checks/{data['id']}").json() == data

        client.post("/api/auth/logout", json={}, headers=headers).raise_for_status()
        sign_in(client, "check_other", snapshot)
        hidden = client.get(f"/api/checks/{data['id']}")
        assert hidden.status_code == 404
        assert "result" not in hidden.json()
    finally:
        engine.dispose()
