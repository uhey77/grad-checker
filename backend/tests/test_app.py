from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from api.api_service.main import create_app
from api.api_service.presentation.dependencies import SessionDependency
from config.settings import Settings
from modules.accounts.grad_checker_accounts.application.auth import AuthService


def test_startup_and_python_service(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "test.db"
    application = create_app(Settings(database_url=f"sqlite:///{database_path}"))

    with TestClient(application) as client:
        response = client.post(
            "/bridge/subject-list", json={"operation": "list_programs"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": []}
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert set(inspect(application.state.database_engine).get_table_names()) == {
            "academic_programs",
            "curricula",
            "classifications",
            "courses",
            "course_offerings",
            "curriculum_courses",
            "students",
            "student_credentials",
            "auth_sessions",
            "auth_attempts",
            "grade_attempts",
            "graduation_requirements",
            "requirement_scopes",
            "credit_rules",
            "credit_rule_courses",
            "credit_rule_limits",
            "check_results",
        }
        with application.state.database_engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1

    assert database_path.is_file()


def test_database_url_is_loaded_at_startup(tmp_path: Path, monkeypatch) -> None:
    application = create_app()
    database_path = tmp_path / "configured.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    with TestClient(application):
        assert Path(application.state.database_engine.url.database) == database_path


def test_request_sessions_preserve_commits_and_rollback_uncommitted_changes(
    tmp_path: Path,
) -> None:
    application = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}"))

    # テスト専用ルートで、実際のFastAPI依存解決とリクエスト終了を検証する。
    @application.post("/test/committed")
    def committed(session: SessionDependency) -> dict[str, str]:
        session.connection().execute(text("INSERT INTO records (id) VALUES (1)"))
        session.commit()
        return {"status": "ok"}

    @application.post("/test/uncommitted")
    def uncommitted(session: SessionDependency) -> dict[str, str]:
        session.connection().execute(text("INSERT INTO records (id) VALUES (2)"))
        return {"status": "ok"}

    @application.post("/test/error")
    def error(session: SessionDependency) -> None:
        session.connection().execute(text("INSERT INTO records (id) VALUES (3)"))
        raise RuntimeError("テスト用の障害")

    @application.get("/test/records")
    def records(session: SessionDependency) -> list[int]:
        return list(
            session.connection()
            .execute(text("SELECT id FROM records ORDER BY id"))
            .scalars()
        )

    with TestClient(application, raise_server_exceptions=False) as client:
        with application.state.database_engine.begin() as connection:
            connection.execute(text("CREATE TABLE records (id INTEGER PRIMARY KEY)"))

        assert client.post("/test/committed").status_code == 200
        assert client.post("/test/uncommitted").status_code == 200
        assert client.post("/test/error").status_code == 500
        assert client.get("/test/records").json() == [1]


@pytest.mark.parametrize(
    ("path", "call", "target"),
    [
        (
            "/bridge/subject-list",
            {"operation": "list_programs"},
            "api.api_service.presentation.go_bridge_subject_list.list_subject_programs",
        ),
        ("/bridge/auth", {"operation": "session", "token": "t" * 43}, None),
        ("/bridge/grades", {"operation": "get", "token": "t" * 43}, None),
    ],
)
def test_unexpected_failures_return_internal_error_code(
    tmp_path: Path, monkeypatch, path: str, call: dict[str, str], target: str | None
) -> None:
    def broken(*_args: object) -> None:
        raise RuntimeError("テスト用の障害")

    # 全てのブリッジアダプターが同じ包絡形式で予期しない失敗を返す。
    if target is None:
        monkeypatch.setattr(AuthService, "session", broken)
    else:
        monkeypatch.setattr(target, broken)
    application = create_app(Settings(database_url=f"sqlite:///{tmp_path / 't.db'}"))
    with TestClient(application) as client:
        response = client.post(path, json=call)
    assert response.status_code == 200
    assert response.json() == {"error": {"code": "internal_error"}}
