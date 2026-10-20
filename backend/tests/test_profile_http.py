"""Go外部API → Python → SQLiteの所属保存・認証・再取得。"""

from pathlib import Path

from test_auth_http import (
    PASSWORD,
    auth_services,  # noqa: F401 -- pytest fixture
)

from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
    load_seed,
)
from modules.subjects.grad_checker_subjects.public import ImportSubjectDataUseCase


def test_real_profile_flow(auth_services, tmp_path):  # noqa: F811 -- pytest fixture
    client = auth_services
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
            load_seed(Path(__file__).resolve().parents[1] / "seeds/cs_2026.json")
        )
    finally:
        engine.dispose()
    for path in ("/api/me", "/api/programs", "/api/me/program"):
        response = (
            client.put(path, json={}) if path.endswith("/program") else client.get(path)
        )
        assert response.status_code == 401
    credentials = {"login_name": "profile_01", "password": PASSWORD}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    auth = client.post("/api/auth/login", json=credentials).json()
    csrf = {"X-CSRF-Token": auth["csrf_token"]}
    initial = client.get("/api/me")
    assert initial.status_code == 200
    assert initial.json()["curriculum_id"] is None
    assert initial.headers["cache-control"] == "no-store"
    options = client.get("/api/programs").json()["programs"]
    assert len(options) == 4
    body = {k: options[0][k] for k in ("program_id", "curriculum_id")}
    body["expected_revision"] = 0
    for headers in (
        {},
        {"X-CSRF-Token": "x" * 64},
        {**csrf, "Origin": "https://evil.example"},
    ):
        assert (
            client.put("/api/me/program", json=body, headers=headers).status_code == 403
        )
    assert client.get("/api/me?student_id=other").status_code == 422
    assert (
        client.put(
            "/api/me/program", json={**body, "student_id": "other"}, headers=csrf
        ).status_code
        == 422
    )
    saved = client.put("/api/me/program", json=body, headers=csrf)
    assert saved.status_code == 200, saved.text
    assert saved.json()["data_revision"] == 1
    assert saved.json()["curriculum_id"] == options[0]["curriculum_id"]
    assert client.put("/api/me/program", json=body, headers=csrf).status_code == 409
    invalid = {**body, "expected_revision": 1, "program_id": options[1]["program_id"]}
    assert client.put("/api/me/program", json=invalid, headers=csrf).status_code == 422
    assert client.get("/api/me").json() == saved.json()
    assert client.post("/api/auth/logout", json={}, headers=csrf).status_code == 200
    assert client.get("/api/me").status_code == 401
    auth = client.post("/api/auth/login", json=credentials).json()
    assert client.get("/api/me").json() == saved.json()
    csrf = {"X-CSRF-Token": auth["csrf_token"]}
    assert client.post("/api/auth/logout", json={}, headers=csrf).status_code == 200
    other = {"login_name": "profile_02", "password": PASSWORD}
    assert client.post("/api/auth/register", json=other).status_code == 201
    assert client.post("/api/auth/login", json=other).status_code == 200
    assert client.get("/api/me").json()["curriculum_id"] is None
